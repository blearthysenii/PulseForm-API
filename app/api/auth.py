import os
import smtplib
from email.mime.text import MIMEText

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from google.oauth2 import id_token
from google.auth.transport import requests

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserRegister, UserLogin, UserResponse, TokenResponse
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    generate_reset_code,
    is_reset_code_valid,
)

router = APIRouter(prefix="/auth", tags=["Auth"])

bearer_scheme = HTTPBearer()


class GoogleLoginRequest(BaseModel):
    credential: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    code: str
    new_password: str
    confirm_password: str


class MessageResponse(BaseModel):
    message: str


def send_reset_email(email: str, code: str):
    subject = "PulseForm Password Reset Code"

    body = f"""
Hello,

You requested a password reset for your PulseForm account.

Your password reset code is:

{code}

This code will expire soon. If you did not request this password reset, please ignore this email.

PulseForm Team
"""

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = os.getenv("SMTP_USER")
    msg["To"] = email

    try:
        with smtplib.SMTP(
            os.getenv("SMTP_HOST"),
            int(os.getenv("SMTP_PORT", 587))
        ) as server:
            server.starttls()
            server.login(
                os.getenv("SMTP_USER"),
                os.getenv("SMTP_PASSWORD")
            )
            server.send_message(msg)

        print(f"[EMAIL SENT] Password reset code sent to {email}")

    except Exception as e:
        print(f"[EMAIL ERROR] {e}")


@router.post("/register", response_model=UserResponse)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_data.email).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    new_user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role="creator"
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/login", response_model=TokenResponse)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_data.email).first()

    if not user or not user.password_hash or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "role": user.role
    })

    return {"access_token": token, "token_type": "bearer"}


@router.post("/google-login", response_model=TokenResponse)
def google_login(data: GoogleLoginRequest, db: Session = Depends(get_db)):
    google_client_id = os.getenv("GOOGLE_CLIENT_ID")

    if not google_client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GOOGLE_CLIENT_ID is not configured"
        )

    try:
        google_user = id_token.verify_oauth2_token(
            data.credential,
            requests.Request(),
            google_client_id,
            clock_skew_in_seconds=30
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    email = google_user.get("email")
    full_name = google_user.get("name")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account email not found"
        )

    user = db.query(User).filter(User.email == email).first()

    if not user:
        user = User(
            full_name=full_name or email,
            email=email,
            password_hash=None,
            role="creator",
            auth_provider="google"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "role": user.role
    })

    return {"access_token": token, "token_type": "bearer"}


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == data.email).first()

    if user and user.auth_provider == "local":
        reset_code, expires = generate_reset_code()
        user.password_reset_token = reset_code
        user.password_reset_expires = expires
        db.commit()
        background_tasks.add_task(send_reset_email, user.email, reset_code)

    return {"message": "If that email is registered, a reset code has been sent."}


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    if len(data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters"
        )
    if data.new_password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match"
    )

    user = db.query(User).filter(
        User.password_reset_token == data.code
    ).first()

    if not user or not is_reset_code_valid(
        user.password_reset_token,
        user.password_reset_expires,
        data.code,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code"
        )

    user.password_hash = hash_password(data.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    db.commit()

    return {"message": "Password updated successfully. You can now log in."}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    user = db.query(User).filter(User.id == int(user_id)).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user