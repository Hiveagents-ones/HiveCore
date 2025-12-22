from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ....core import security
from ....core.config import settings
from ....db.session import get_db
from ....models.member import Member
from ....schemas.member import MemberCreate, MemberResponse, Token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


@router.post("/register", response_model=MemberResponse)
def register(member_data: MemberCreate, db: Session = Depends(get_db)):
    """
    Register a new member.
    """
    # Check if member already exists
    db_member = db.query(Member).filter(Member.id_card == member_data.id_card).first()
    if db_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Member with this ID card already registered",
        )
    
    # Hash the password
    hashed_password = security.get_password_hash(member_data.password)
    
    # Encrypt sensitive fields
    encrypted_id_card = security.encrypt_field(member_data.id_card)
    encrypted_phone = security.encrypt_field(member_data.phone)
    
    # Create new member
    db_member = Member(
        name=member_data.name,
        id_card=encrypted_id_card,
        phone=encrypted_phone,
        health_status=member_data.health_status,
        hashed_password=hashed_password,
    )
    
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    
    # Prepare response with decrypted fields
    response_data = {
        "id": db_member.id,
        "name": db_member.name,
        "id_card": member_data.id_card,
        "phone": member_data.phone,
        "health_status": db_member.health_status,
        "created_at": db_member.created_at,
        "updated_at": db_member.updated_at,
    }
    
    return MemberResponse(**response_data)


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    """
    Authenticate a member and return an access token.
    """
    # Find member by ID card (username)
    members = db.query(Member).all()
    member = None
    
    for m in members:
        try:
            decrypted_id_card = security.decrypt_field(m.id_card)
            if decrypted_id_card == form_data.username:
                member = m
                break
        except Exception:
            continue
    
    if not member or not security.verify_password(form_data.password, member.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect ID card or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=member.id, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=MemberResponse)
def read_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    """
    Get the current authenticated member's information.
    """
    user_id = security.verify_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    member = db.query(Member).filter(Member.id == user_id).first()
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found",
        )
    
    # Decrypt sensitive fields for response
    try:
        decrypted_id_card = security.decrypt_field(member.id_card)
        decrypted_phone = security.decrypt_field(member.phone)
    except Exception:
        decrypted_id_card = ""
        decrypted_phone = ""
    
    response_data = {
        "id": member.id,
        "name": member.name,
        "id_card": decrypted_id_card,
        "phone": decrypted_phone,
        "health_status": member.health_status,
        "created_at": member.created_at,
        "updated_at": member.updated_at,
    }
    
    return MemberResponse(**response_data)
