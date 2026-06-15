import os
import secrets
import random
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from jose import jwt, JWTError
from passlib.context import CryptContext


load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
PASSWORD_RESET_EXPIRE_MINUTES = int(os.getenv("PASSWORD_RESET_EXPIRE_MINUTES", 30))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def validate_bcrypt_password(password: str):
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must be 72 characters or less")


def hash_password(password: str):
    validate_bcrypt_password(password)
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def generate_reset_code() -> tuple[str, datetime]:
    code = str(random.randint(100000, 999999))
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=PASSWORD_RESET_EXPIRE_MINUTES
    )
    return code, expires


def is_reset_code_valid(
    stored_code: str | None,
    stored_expiry: datetime | None,
    provided_code: str
) -> bool:
    if not stored_code or not stored_expiry:
        return False

    expiry = (
        stored_expiry
        if stored_expiry.tzinfo
        else stored_expiry.replace(tzinfo=timezone.utc)
    )

    if datetime.now(timezone.utc) > expiry:
        return False

    return secrets.compare_digest(stored_code, provided_code)