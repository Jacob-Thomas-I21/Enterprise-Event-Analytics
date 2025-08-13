"""
User service for database operations
"""

from sqlalchemy.orm import Session
from typing import Optional, List
import logging
import secrets
import string

from models.user import User, UserCreate, UserUpdate
from core.auth import get_password_hash, UserRole
from core.database import get_db

logger = logging.getLogger(__name__)

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """Get list of users with pagination"""
    return db.query(User).offset(skip).limit(limit).all()

def create_user(db: Session, user: UserCreate) -> User:
    """Create a new user"""
    hashed_password = get_password_hash(user.password)
    
    db_user = User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role=user.role,
        is_active=True,
        is_verified=False
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    logger.info(f"Created user: {db_user.email}")
    return db_user

def update_user(db: Session, user_id: int, user_update: UserUpdate) -> Optional[User]:
    """Update user information"""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    update_data = user_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    
    logger.info(f"Updated user: {db_user.email}")
    return db_user

def delete_user(db: Session, user_id: int) -> bool:
    """Delete user (soft delete by deactivating)"""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return False
    
    db_user.is_active = False
    db.commit()
    
    logger.info(f"Deactivated user: {db_user.email}")
    return True

def activate_user(db: Session, user_id: int) -> bool:
    """Activate user account"""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return False
    
    db_user.is_active = True
    db.commit()
    
    logger.info(f"Activated user: {db_user.email}")
    return True

def verify_user(db: Session, user_id: int) -> bool:
    """Verify user account"""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return False
    
    db_user.is_verified = True
    db.commit()
    
    logger.info(f"Verified user: {db_user.email}")
    return True

def get_users_by_role(db: Session, role: UserRole) -> List[User]:
    """Get users by role"""
    return db.query(User).filter(User.role == role).all()

def count_users(db: Session) -> int:
    """Count total users"""
    return db.query(User).count()

def count_active_users(db: Session) -> int:
    """Count active users"""
    return db.query(User).filter(User.is_active == True).count()

def generate_secure_password(length: int = 16) -> str:
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    
    # Ensure password meets requirements
    if (any(c.islower() for c in password) and
        any(c.isupper() for c in password) and
        any(c.isdigit() for c in password) and
        any(c in "!@#$%^&*" for c in password)):
        return password
    else:
        return generate_secure_password(length)  # Retry if requirements not met

async def create_default_users():
    """Create default users for the system with secure passwords"""
    from core.database import SessionLocal
    
    db = SessionLocal()
    try:
        # Check if admin user exists
        admin_user = get_user_by_email(db, "admin@company.com")
        if not admin_user:
            admin_password = generate_secure_password()
            admin_data = UserCreate(
                email="admin@company.com",
                password=admin_password,
                full_name="System Administrator",
                role=UserRole.ADMIN
            )
            create_user(db, admin_data)
            logger.warning(f"Created default admin user with password: {admin_password}")
            logger.warning("SECURITY: Please change the default admin password immediately!")
        
        # Check if manager user exists
        manager_user = get_user_by_email(db, "manager@company.com")
        if not manager_user:
            manager_password = generate_secure_password()
            manager_data = UserCreate(
                email="manager@company.com",
                password=manager_password,
                full_name="System Manager",
                role=UserRole.MANAGER
            )
            create_user(db, manager_data)
            logger.warning(f"Created default manager user with password: {manager_password}")
            logger.warning("SECURITY: Please change the default manager password immediately!")
        
        # Check if analyst user exists
        analyst_user = get_user_by_email(db, "analyst@company.com")
        if not analyst_user:
            analyst_password = generate_secure_password()
            analyst_data = UserCreate(
                email="analyst@company.com",
                password=analyst_password,
                full_name="System Analyst",
                role=UserRole.ANALYST
            )
            create_user(db, analyst_data)
            logger.warning(f"Created default analyst user with password: {analyst_password}")
            logger.warning("SECURITY: Please change the default analyst password immediately!")
            
    except Exception as e:
        logger.error(f"Failed to create default users: {e}")
        db.rollback()
    finally:
        db.close()