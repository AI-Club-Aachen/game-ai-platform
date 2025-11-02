from typing import Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.api.deps import get_session
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.email import email_service
from app.models.user import User
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserCreate, UserResponse
from app.core.tokens import generate_secure_token, hash_token, get_token_expiry
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
        user_data: UserCreate,
        session: Annotated[Session, Depends(get_session)]
) -> User:
    """Register a new user and send verification email"""

    # Check if username already exists
    statement = select(User).where(User.username == user_data.username)
    existing_user = session.exec(statement).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Check if email already exists
    statement = select(User).where(User.email == user_data.email)
    existing_user = session.exec(statement).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user (unverified by default)
    hashed_password = get_password_hash(user_data.password)

    # Generate email verification token
    verification_token = generate_secure_token()
    verification_token_hash = hash_token(verification_token)
    verification_expires_at = get_token_expiry(
        hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS
    )

    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password,
        email_verified=False,
        email_verification_token_hash=verification_token_hash,
        email_verification_expires_at=verification_expires_at,
    )

    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    # Send verification email
    verification_url = f"https://your-frontend-domain.com/verify-email?token={verification_token}"
    html_content = f"""
    <html>
      <body>
        <h1>Welcome to AI Game Competition Platform</h1>
        <p>Hello {new_user.username},</p>
        <p>Please verify your email by clicking the link below:</p>
        <p><a href="{verification_url}">Verify Email</a></p>
        <p>This link expires in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS} hours.</p>
        <p>If you did not create this account, please ignore this email.</p>
      </body>
    </html>
    """

    await email_service.send_email(
        to_email=new_user.email,
        subject="Verify Your Email - AI Game Competition Platform",
        html_content=html_content,
    )

    return new_user


@router.post("/login", response_model=Token)
async def login(
        credentials: LoginRequest,
        session: Annotated[Session, Depends(get_session)]
) -> Token:
    """Login and receive JWT access token"""

    # Find user by email
    statement = select(User).where(User.email == credentials.email)
    user = session.exec(statement).first()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if email is verified
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please check your inbox.",
        )

    # Create access token
    access_token = create_access_token(data={"sub": str(user.id)})

    return Token(access_token=access_token)
