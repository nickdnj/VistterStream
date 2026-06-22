"""
Authentication API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt
from jose.exceptions import JWTError
from slowapi import Limiter
from slowapi.util import get_remote_address
import bcrypt
import logging
import os
import secrets

from models.database import get_db, User, Settings
from models.schemas import (
    UserCreate,
    User as UserSchema,
    Token,
    PasswordChangeRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    RecoveryEmailRequest,
)
from services import email_service

router = APIRouter()
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY environment variable must be set. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Password reset code settings
RESET_CODE_TTL_MINUTES = 15
# Unambiguous alphabet — no 0/O, 1/I/L to avoid transcription errors
_RESET_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

def generate_reset_code(length: int = 8) -> str:
    """Generate a short, unambiguous one-time reset code (uppercase)."""
    return "".join(secrets.choice(_RESET_CODE_ALPHABET) for _ in range(length))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate a user"""
    user = get_user_by_username(db, username)
    if not user:
        logger.warning("Login attempt failed: user '%s' not found", username)
        return None
    if not user.is_active:
        logger.warning("Login attempt failed: user '%s' is inactive", username)
        return None
    try:
        if not verify_password(password, user.password_hash):
            logger.warning("Login attempt failed: incorrect password for user '%s'", username)
            return None
    except Exception as e:
        logger.error("Password verification error for user '%s': %s", username, e)
        return None
    return user

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Get current authenticated user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_username(db, username)
    if user is None:
        raise credentials_exception
    return user

@router.post("/register", response_model=UserSchema)
@limiter.limit("3/5minutes")
async def register_user(request: Request, user: UserCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """Register a new user (admin only)"""
    if current_user.username != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create accounts")
    # Check if user already exists
    existing_user = get_user_by_username(db, user.username)
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        username=user.username,
        password_hash=hashed_password
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return UserSchema.from_orm(db_user)

@router.post("/login", response_model=Token)
@limiter.limit("5/5minutes")
async def login_user(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login user and return access token"""
    logger.info("Login attempt for username: '%s'", form_data.username)
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        logger.warning("Login failed for username: '%s'", form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.info("Login successful for user: '%s' (id: %s, active: %s)", user.username, user.id, user.is_active)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/change-password")
async def change_password(
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change the authenticated user's password"""
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password",
        )

    current_user.password_hash = get_password_hash(payload.new_password)
    db.add(current_user)
    db.commit()
    return {"success": True}


@router.post("/recovery-email", response_model=UserSchema)
async def set_recovery_email(
    payload: RecoveryEmailRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set or clear the current user's password-recovery email."""
    email = (payload.recovery_email or "").strip() or None
    if email and ("@" not in email or "." not in email.split("@")[-1]):
        raise HTTPException(status_code=400, detail="Invalid email address")
    current_user.recovery_email = email
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    logger.info("Updated recovery email for user '%s'", current_user.username)
    return UserSchema.from_orm(current_user)


@router.post("/forgot-password")
@limiter.limit("3/15minutes")
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """Begin password recovery: email a one-time code to the recovery address.

    The code is also written to the application logs so the admin can recover
    via the container logs if email delivery is unavailable. Always returns a
    generic response so the endpoint does not reveal whether an account or
    recovery email exists.
    """
    generic = {
        "message": "If an account with a recovery email exists, a reset code has been sent."
    }
    user = get_user_by_username(db, payload.username)
    if not user or not user.is_active or not user.recovery_email:
        logger.info(
            "Forgot-password requested for '%s' — no deliverable recovery email",
            payload.username,
        )
        return generic

    code = generate_reset_code()
    user.reset_code_hash = get_password_hash(code)
    user.reset_code_expires = datetime.now(timezone.utc) + timedelta(minutes=RESET_CODE_TTL_MINUTES)
    db.add(user)
    db.commit()

    # Fallback channel: always log the code so the admin can recover from the
    # container logs (docker logs vistterstream-backend) without email.
    logger.warning("=" * 60)
    logger.warning(
        "*** PASSWORD RESET CODE for '%s': %s (valid %d min) ***",
        user.username, code, RESET_CODE_TTL_MINUTES,
    )
    logger.warning("=" * 60)

    settings = db.query(Settings).first()
    body = (
        f"A password reset was requested for the VistterStream account "
        f"'{user.username}'.\n\n"
        f"Your one-time reset code is:\n\n    {code}\n\n"
        f"This code expires in {RESET_CODE_TTL_MINUTES} minutes. Enter it on the "
        f"reset screen along with your new password.\n\n"
        f"If you did not request this, you can ignore this email — your password "
        f"has not been changed."
    )
    try:
        email_service.send_email(
            settings, user.recovery_email, "VistterStream password reset code", body
        )
    except email_service.EmailNotConfigured:
        logger.warning(
            "Forgot-password: SMTP not configured; reset code available in logs only"
        )
    except email_service.EmailSendError as exc:
        logger.error("Forgot-password: failed to send reset email: %s", exc)

    return generic


@router.post("/reset-password")
@limiter.limit("5/15minutes")
async def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Complete password recovery using the one-time code."""
    invalid = HTTPException(status_code=400, detail="Invalid or expired reset code")
    user = get_user_by_username(db, payload.username)
    if not user or not user.reset_code_hash or not user.reset_code_expires:
        raise invalid

    # SQLite returns naive datetimes — treat stored expiry as UTC.
    expires = user.reset_code_expires
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires:
        raise invalid

    try:
        if not verify_password(payload.code.strip().upper(), user.reset_code_hash):
            raise invalid
    except HTTPException:
        raise
    except Exception:
        raise invalid

    user.password_hash = get_password_hash(payload.new_password)
    user.reset_code_hash = None
    user.reset_code_expires = None
    db.add(user)
    db.commit()
    logger.info("Password reset completed for user '%s'", user.username)
    return {"success": True}


@router.get("/me", response_model=UserSchema)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserSchema.from_orm(current_user)
