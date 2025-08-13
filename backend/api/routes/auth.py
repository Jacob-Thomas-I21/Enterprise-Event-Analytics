"""
Authentication API routes
JWT-based authentication with role-based access control
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging
import time
from typing import Dict

from core.database import get_db
from core.auth import (
    verify_password, get_password_hash, create_token_pair, 
    verify_token, TokenType, blacklist_token, get_current_user,
    refresh_access_token, security, Token
)
from models.user import User, UserLogin, UserCreate, UserResponse, PasswordChange
from services.user_service import get_user_by_email, create_user

router = APIRouter()
logger = logging.getLogger(__name__)

# Rate limiting storage (in production, use Redis)
login_attempts: Dict[str, list] = {}
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 900  # 15 minutes

def check_rate_limit(request: Request, max_attempts: int = MAX_LOGIN_ATTEMPTS) -> bool:
    """Check if IP has exceeded rate limit"""
    client_ip = request.client.host
    current_time = time.time()
    
    # Clean old attempts
    if client_ip in login_attempts:
        login_attempts[client_ip] = [
            attempt_time for attempt_time in login_attempts[client_ip]
            if current_time - attempt_time < LOCKOUT_DURATION
        ]
    
    # Check if rate limit exceeded
    if client_ip in login_attempts and len(login_attempts[client_ip]) >= max_attempts:
        return False
    
    return True

def record_failed_attempt(request: Request):
    """Record a failed login attempt"""
    client_ip = request.client.host
    current_time = time.time()
    
    if client_ip not in login_attempts:
        login_attempts[client_ip] = []
    
    login_attempts[client_ip].append(current_time)

@router.post("/login", response_model=Token)
async def login(
    user_credentials: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """Authenticate user and return JWT tokens with rate limiting"""
    
    # Check rate limit
    if not check_rate_limit(request):
        logger.warning(f"Rate limit exceeded for IP: {request.client.host}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later."
        )
    
    # Get user from database
    user = get_user_by_email(db, user_credentials.email)
    if not user:
        logger.warning(f"Login attempt with non-existent email: {user_credentials.email}")
        record_failed_attempt(request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(user_credentials.password, user.hashed_password):
        logger.warning(f"Failed login attempt for user: {user_credentials.email}")
        record_failed_attempt(request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        logger.warning(f"Login attempt by inactive user: {user_credentials.email}")
        record_failed_attempt(request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated"
        )
    
    # Clear failed attempts on successful login
    client_ip = request.client.host
    if client_ip in login_attempts:
        del login_attempts[client_ip]
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create token pair
    tokens = create_token_pair(user.id, user.email, user.role)
    
    logger.info(f"Successful login for user: {user.email}")
    return tokens

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    
    # Check if user already exists
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    try:
        new_user = create_user(db, user_data)
        logger.info(f"New user registered: {new_user.email}")
        return new_user
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account"
        )

from pydantic import BaseModel

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/refresh")
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token"""
    
    try:
        # Verify refresh token
        token_data = verify_token(request.refresh_token, TokenType.REFRESH)
        
        # Verify user still exists and is active
        from models.user import User
        user = db.query(User).filter(User.id == token_data.user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive"
            )
        
        # Create new access token
        new_access_token = refresh_access_token(request.refresh_token)
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: User = Depends(get_current_user)
):
    """Logout user and blacklist token"""
    
    token = credentials.credentials
    
    try:
        # Blacklist the current token
        blacklist_token(token)
        
        logger.info(f"User logged out: {current_user.email}")
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    try:
        current_user.hashed_password = get_password_hash(password_data.new_password)
        db.commit()
        
        logger.info(f"Password changed for user: {current_user.email}")
        return {"message": "Password changed successfully"}
        
    except Exception as e:
        logger.error(f"Password change failed: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )

@router.get("/verify-token")
async def verify_current_token(current_user: User = Depends(get_current_user)):
    """Verify if current token is valid"""
    return {
        "valid": True,
        "user_id": current_user.id,
        "email": current_user.email,
        "role": current_user.role
    }