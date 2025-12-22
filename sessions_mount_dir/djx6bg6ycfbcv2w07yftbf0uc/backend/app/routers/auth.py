from datetime import datetime, timedelta
from typing import Any, Union

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import database, models, schemas
from ..core import security

router = APIRouter()


@router.post("/register", response_model=schemas.User)
def register(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    """
    Register a new user.
    """
    # Check if user already exists
    db_user = db.query(models.User).filter(
        (models.User.email == user.email) | (models.User.username == user.username)
    ).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered"
        )
    
    # Create new user
    hashed_password = security.get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        phone=user.phone,
        nickname=user.nickname
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create privacy settings for the user
    privacy_settings = models.PrivacySettings(user_id=db_user.id)
    db.add(privacy_settings)
    db.commit()
    
    return db_user


@router.post("/token", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db)
):
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    user = security.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create access token
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # Log login
    login_log = models.LoginLog(
        user_id=user.id,
        login_type="email",
        success=True
    )
    db.add(login_log)
    db.commit()
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=schemas.Token)
def login(
    user_credentials: schemas.UserLogin,
    db: Session = Depends(database.get_db)
):
    """
    Login with email/username and password.
    """
    # Try to find user by email or username
    db_user = db.query(models.User).filter(
        (models.User.email == user_credentials.login) | 
        (models.User.username == user_credentials.login)
    ).first()
    
    if not db_user or not security.verify_password(user_credentials.password, db_user.hashed_password):
        # Log failed login attempt
        if db_user:
            login_log = models.LoginLog(
                user_id=db_user.id,
                login_type="email",
                success=False
            )
            db.add(login_log)
            db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect login credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    db_user.last_login = datetime.utcnow()
    db.commit()
    
    # Create access token
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": db_user.username}, expires_delta=access_token_expires
    )
    
    # Log successful login
    login_log = models.LoginLog(
        user_id=db_user.id,
        login_type="email",
        success=True
    )
    db.add(login_log)
    db.commit()
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(security.get_current_active_user)):
    """
    Get current user.
    """
    return current_user


@router.post("/logout")
def logout(current_user: models.User = Depends(security.get_current_active_user)):
    """
    Logout current user.
    Note: In a stateless JWT implementation, actual logout would require token blacklisting
    which is not implemented here. This endpoint is for API completeness.
    """
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=schemas.Token)
def refresh_token(current_user: models.User = Depends(security.get_current_active_user)):
    """
    Refresh access token.
    """
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": current_user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/verify-email")
def verify_email(
    verification_data: schemas.VerifyEmail,
    db: Session = Depends(database.get_db)
):
    """
    Verify user email with verification code.
    """
    # Find verification code
    verification = db.query(models.VerificationCode).filter(
        models.VerificationCode.email == verification_data.email,
        models.VerificationCode.code == verification_data.code,
        models.VerificationCode.purpose == "email_verification",
        models.VerificationCode.is_used == False
    ).first()
    
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )
    
    # Check if code is expired (24 hours)
    if verification.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired"
        )
    
    # Get user and mark as verified
    user = db.query(models.User).filter(models.User.email == verification_data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_verified = True
    verification.is_used = True
    db.commit()
    
    return {"message": "Email verified successfully"}


@router.post("/forgot-password")
def forgot_password(
    request: schemas.ForgotPassword,
    db: Session = Depends(database.get_db)
):
    """
    Request password reset.
    """
    user = db.query(models.User).filter(models.User.email == request.email).first()
    if not user:
        # Don't reveal that email doesn't exist
        return {"message": "If the email exists, a reset link has been sent"}
    
    # In a real implementation, you would:
    # 1. Generate a unique reset token
    # 2. Store it in the database with expiration
    # 3. Send email with reset link
    
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password")
def reset_password(
    request: schemas.ResetPassword,
    db: Session = Depends(database.get_db)
):
    """
    Reset password with token.
    """
    # In a real implementation, you would:
    # 1. Verify the reset token
    # 2. Check if it's expired
    # 3. Update the user's password
    # 4. Invalidate the token
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Password reset not implemented yet"
    )
