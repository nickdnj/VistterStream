"""
Authentication API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt
from jose.exceptions import JWTError
import bcrypt
import logging

from models.database import get_db, User
from models.schemas import UserCreate, User as UserSchema, Token, PasswordChangeRequest

router = APIRouter()
logger = logging.getLogger(__name__)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# JWT settings
SECRET_KEY = "your-secret-key-here"  # Should be in environment variables
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
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
        logger.warning(f"Login attempt failed: user '{username}' not found")
        return None
    if not user.is_active:
        logger.warning(f"Login attempt failed: user '{username}' is inactive")
        return None
    try:
        if not verify_password(password, user.password_hash):
            logger.warning(f"Login attempt failed: incorrect password for user '{username}'")
            return None
    except Exception as e:
        logger.error(f"Password verification error for user '{username}': {e}")
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
async def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
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
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login user and return access token"""
    logger.info(f"Login attempt for username: '{form_data.username}'")
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        logger.warning(f"Login failed for username: '{form_data.username}'")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.info(f"Login successful for user: '{user.username}' (id: {user.id}, active: {user.is_active})")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/diagnose")
async def diagnose_auth(db: Session = Depends(get_db)):
    """Diagnostic endpoint to check admin user status (for debugging)"""
    admin_user = get_user_by_username(db, "admin")
    
    if not admin_user:
        return {
            "admin_exists": False,
            "message": "Admin user does not exist"
        }
    
    # Test password verification (without exposing the hash)
    test_result = None
    try:
        test_result = verify_password("admin", admin_user.password_hash)
    except Exception as e:
        test_result = f"ERROR: {str(e)}"
    
    return {
        "admin_exists": True,
        "user_id": admin_user.id,
        "username": admin_user.username,
        "is_active": admin_user.is_active,
        "has_password_hash": bool(admin_user.password_hash),
        "password_hash_length": len(admin_user.password_hash) if admin_user.password_hash else 0,
        "test_password_verification": test_result,
        "message": "Admin user found"
    }

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


@router.get("/me", response_model=UserSchema)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserSchema.from_orm(current_user)
