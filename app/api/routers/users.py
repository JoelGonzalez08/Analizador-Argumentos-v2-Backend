"""
Users router - endpoints for user management (Updated for new schema)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.models import User, SessionToken, Conversation
from app.core.auth import verify_password, get_password_hash, generate_token, create_expiration_time
from app.schemas.schemas import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    SessionTokenResponse,
    ConversationResponse,
    MessageResponseGeneric
)

router = APIRouter()


# Dependency to get current user from token
async def get_current_user(
    authorization: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from authorization header"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    token = authorization.replace("Bearer ", "")
    
    session = db.query(SessionToken).filter(
        SessionToken.token == token
    ).first()
    
    if not session or session.is_expired:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user = db.query(User).filter(User.id == session.user_id).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new user"""
    # Check if user exists
    existing_user = db.query(User).filter(
        (User.email == user.email) | (User.username == user.username)
    ).first()
    
    if existing_user:
        if existing_user.email == user.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Hash password
    hashed_password = get_password_hash(user.password)
    
    db_user = User(
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        bio=user.bio,
        country=user.country,
        profession=user.profession,
        password_hash=hashed_password
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


@router.post("/login", response_model=SessionTokenResponse)
async def login_user(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """Login user and create session token"""
    # Find user
    user = db.query(User).filter(User.username == credentials.username).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create session token
    token = generate_token()
    expires_at = create_expiration_time(days=7)
    
    session = SessionToken(
        user_id=user.id,
        token=token,
        expires_at=expires_at
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return SessionTokenResponse(
        token=token,
        expires_at=expires_at,
        user=UserResponse.model_validate(user)
    )


@router.post("/logout")
async def logout_user(
    current_user: User = Depends(get_current_user),
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """Logout user and invalidate session token"""
    token = authorization.replace("Bearer ", "")
    
    session = db.query(SessionToken).filter(
        SessionToken.token == token
    ).first()
    
    if session:
        db.delete(session)
        db.commit()
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.avatar_url is not None:
        current_user.avatar_url = user_update.avatar_url
    if user_update.bio is not None:
        current_user.bio = user_update.bio
    if user_update.country is not None:
        current_user.country = user_update.country
    if user_update.profession is not None:
        current_user.profession = user_update.profession
    
    current_user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.get("/{user_id}/conversations", response_model=List[ConversationResponse])
async def get_user_conversations(
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get user's conversations"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    conversations = db.query(Conversation).filter(
        Conversation.user_id == user_id
    ).order_by(
        Conversation.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return conversations


@router.delete("/{user_id}", response_model=MessageResponseGeneric)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Delete a user and all related data (cascade)"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    db.delete(user)
    db.commit()
    
    return MessageResponseGeneric(
        message="User deleted successfully",
        success=True
    )
