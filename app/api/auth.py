import os
from typing import Optional

import resend
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.auth.transport import requests
from google.oauth2 import id_token
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    decode_token,
    generate_reset_code,
    hash_password,
    is_reset_code_valid,
    verify_password,
)
from app.database import get_db
from app.models.user import User
from app.schemas.user import TokenResponse, UserLogin, UserRegister, UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])
bearer_scheme = HTTPBearer()

MAX_BCRYPT_PASSWORD_BYTES = 72


class GoogleLoginRequest(BaseModel):
    credential: str


class GoogleLoginResponse(BaseModel):
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    needs_registration: bool = False
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    google_registration_token: Optional[str] = None


class CompleteGoogleRegisterRequest(BaseModel):
    google_registration_token: str
    full_name: str
    organization: Optional[str] = None
    password: str
    confirm_password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    code: str
    new_password: str
    confirm_password: str


class MessageResponse(BaseModel):
    message: str


def validate_password(password: str):
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters",
        )

    if len(password.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be 72 characters or less",
        )


def create_user_token(user: User) -> dict:
    token = create_access_token(
        {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer",
    }


def verify_google_credential(credential: str) -> dict:
    google_client_id = os.getenv("GOOGLE_CLIENT_ID")

    if not google_client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GOOGLE_CLIENT_ID is not configured",
        )

    try:
        return id_token.verify_oauth2_token(
            credential,
            requests.Request(),
            google_client_id,
            clock_skew_in_seconds=30,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google credential",
        )


def send_reset_email(email: str, code: str) -> bool:
    resend_api_key = os.getenv("RESEND_API_KEY")
    email_from = os.getenv(
        "EMAIL_FROM",
        "PulseForm <noreply@pulseform-genpact.com>",
    )

    if not resend_api_key:
        return False

    resend.api_key = resend_api_key

    try:
        resend.Emails.send(
            {
                "from": email_from,
                "to": [email],
                "subject": "PulseForm Password Reset Code",
                "html": f"""
                    <h2>PulseForm Password Reset</h2>
                    <p>You requested a password reset for your PulseForm account.</p>
                    <p>Your reset code is:</p>
                    <h1 style="letter-spacing: 4px;">{code}</h1>
                    <p>This code will expire soon.</p>
                    <p>If you did not request this, please ignore this email.</p>
                    <br />
                    <p>PulseForm Team</p>
                """,
            }
        )
        return True

    except Exception:
        return False


@router.post("/register", response_model=UserResponse)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_data.email).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    validate_password(user_data.password)

    new_user = User(
        full_name=user_data.full_name,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role="creator",
        auth_provider="local",
        organization=user_data.organization,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/login", response_model=TokenResponse)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_data.email).first()

    if (
        not user
        or not user.password_hash
        or not verify_password(user_data.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return create_user_token(user)


@router.post("/google-login", response_model=GoogleLoginResponse)
def google_login(data: GoogleLoginRequest, db: Session = Depends(get_db)):
    google_user = verify_google_credential(data.credential)

    email = google_user.get("email")
    full_name = google_user.get("name")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account email not found",
        )

    user = db.query(User).filter(User.email == email).first()

    if user:
        token_data = create_user_token(user)

        return {
            "access_token": token_data["access_token"],
            "token_type": token_data["token_type"],
            "needs_registration": False,
        }

    return {
        "needs_registration": True,
        "email": email,
        "full_name": full_name or email,
        "google_registration_token": data.credential,
    }


@router.post("/complete-google-register", response_model=TokenResponse)
def complete_google_register(
    data: CompleteGoogleRegisterRequest,
    db: Session = Depends(get_db),
):
    google_user = verify_google_credential(data.google_registration_token)
    email = google_user.get("email")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account email not found",
        )

    existing_user = db.query(User).filter(User.email == email).first()

    if existing_user:
        return create_user_token(existing_user)

    validate_password(data.password)

    if data.password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )

    new_user = User(
        full_name=data.full_name,
        email=email,
        password_hash=hash_password(data.password),
        role="creator",
        auth_provider="google",
        organization=data.organization,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return create_user_token(new_user)


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == data.email).first()

    if user and user.password_hash:
        reset_code, expires = generate_reset_code()
        user.password_reset_token = reset_code
        user.password_reset_expires = expires
        db.commit()

        send_reset_email(user.email, reset_code)

    return {"message": "If that email is registered, a reset code has been sent."}


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    validate_password(data.new_password)

    if data.new_password != data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )

    user = db.query(User).filter(User.password_reset_token == data.code).first()

    if not user or not is_reset_code_valid(
        user.password_reset_token,
        user.password_reset_expires,
        data.code,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code",
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
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = db.query(User).filter(User.id == int(user_id)).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
