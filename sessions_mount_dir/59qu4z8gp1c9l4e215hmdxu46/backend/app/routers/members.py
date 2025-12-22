from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload, load_only
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..middlewares.security import JWTBearer, verify_token
from ..database import get_db
from ..schemas.members import MemberCreate, MemberUpdate, MemberResponse, MemberCardResponse
from ..database import Member, MemberCard, MembershipLevel

from ..database import get_db
from ..schemas.members import MemberCreate, MemberUpdate, MemberResponse, MemberCardResponse
from ..database import Member, MemberCard
from ..database import MembershipLevel

router = APIRouter(
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"description": "Forbidden"},
        status.HTTP_404_NOT_FOUND: {"description": "Member not found"}
    }
    prefix="/api/v1/members",
    tags=["members"],
    dependencies=[Depends(JWTBearer())]
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
@router.get("/", response_model=List[MemberResponse], summary="List members", description="Get paginated list of members with filtering and field selection")
def get_members(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, le=1000, description="Maximum number of records to return"),
    name: Optional[str] = Query(None, description="Filter by name (partial match)"),
    email: Optional[str] = Query(None, description="Filter by email (partial match)"),
    phone: Optional[str] = Query(None, description="Filter by phone (partial match)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    gender: Optional[str] = Query(None, description="Filter by gender"),
    join_date_start: Optional[datetime] = Query(None, description="Filter members joined after this date"),
    join_date_end: Optional[datetime] = Query(None, description="Filter members joined before this date"),
    fields: Optional[List[str]] = Query(None, description="Fields to include in response"),
    db: Session = Depends(get_db),
    token: dict = Depends(verify_token)
) -> List[MemberResponse]:
    """
    Get paginated list of members with advanced filtering and field selection.
    
    Requires admin or staff role.
    """
    # Role check
    if token["role"] not in ["admin", "staff"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )

    query = db.query(Member)

    # Apply filters
    if name:
        query = query.filter(Member.name.ilike(f"%{name}%"))
    if email:
        query = query.filter(Member.email.ilike(f"%{email}%"))
    if phone:
        query = query.filter(Member.phone.ilike(f"%{phone}%"))
    if is_active is not None:
        query = query.filter(Member.is_active == is_active)
    if gender:
        query = query.filter(Member.gender == gender)
    if join_date_start:
        query = query.filter(Member.join_date >= join_date_start)
    if join_date_end:
        query = query.filter(Member.join_date <= join_date_end)

    # Dynamic field selection with validation
    if fields:
        valid_fields = [field for field in fields if hasattr(Member, field)]
        if len(valid_fields) != len(fields):
            invalid_fields = set(fields) - set(valid_fields)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid fields: {', '.join(invalid_fields)}"
            )
        load_options = [load_only(*[getattr(Member, field) for field in valid_fields])]
    else:
        load_options = [load_only(
            Member.id,
            Member.name,
            Member.email,
            Member.phone,
            Member.join_date,
            Member.is_active
        )]

    members = query.options(*load_options).offset(skip).limit(limit).all()
    return members


@router.get("/", response_model=List[MemberResponse])
def get_members(
    skip: int = 0,
    limit: int = 100,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    is_active: Optional[bool] = None,
    gender: Optional[str] = None,
    join_date_start: Optional[str] = None,
    join_date_end: Optional[str] = None,
    db: Session = Depends(get_db),
    token: dict = Depends(verify_token)
):
    """
    Get list of all members with pagination and filtering
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        name: Filter by name (partial match)
        email: Filter by email (partial match)
        phone: Filter by phone (partial match)
        is_active: Filter by active status
        gender: Filter by gender
        join_date_start: Filter members joined after this date
        join_date_end: Filter members joined before this date
    """
    query = db.query(Member)

    if name:
        query = query.filter(Member.name.ilike(f"%{name}%"))
    if email:
        query = query.filter(Member.email.ilike(f"%{email}%"))
    if phone:
        query = query.filter(Member.phone.ilike(f"%{phone}%"))
    if is_active is not None:
        query = query.filter(Member.is_active == is_active)
    if gender:
        query = query.filter(Member.gender == gender)
    if join_date_start:
        query = query.filter(Member.join_date >= join_date_start)
    if join_date_end:
        query = query.filter(Member.join_date <= join_date_end)

    # Optimized query with only needed columns
    members = query.options(
        load_only(
            Member.id, 
            Member.name, 
            Member.email,
            Member.phone,
            Member.join_date,
            Member.is_active
        )
    ).offset(skip).limit(limit).all()
    
    return members


@router.get("/verify-token")
async def verify_token(token: str = Depends(oauth2_scheme)):
    """
    Verify access token
    """
    # In a real implementation, this would decode and verify the JWT
    # For now, we'll just check if it's a valid admin token
    if token == "admin_token":
        return {"sub": "admin", "role": "admin"}
    elif token == "staff_token":
        return {"sub": "staff", "role": "staff"}
    
    raise HTTPException(
        status_code=401,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"}
    )
def get_members(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get list of all members with pagination
    """
    query = db.query(Member)
    
    if name:
        query = query.filter(Member.name.ilike(f"%{name}%"))
    if email:
        query = query.filter(Member.email.ilike(f"%{email}%"))
    if phone:
        query = query.filter(Member.phone.ilike(f"%{phone}%"))
    if is_active is not None:
        query = query.filter(Member.is_active == is_active)
        
    members = query.offset(skip).limit(limit).all()
    return members

@router.post("/", response_model=MemberResponse)
def create_member(member: MemberCreate, db: Session = Depends(get_db), token: dict = Depends(verify_token)):
    """
    Create a new member
    """
    # Check if email or phone already exists
    db_member_email = db.query(Member).filter(Member.email == member.email).first()
    if db_member_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    db_member_phone = db.query(Member).filter(Member.phone == member.phone).first()
    if db_member_phone:
        raise HTTPException(status_code=400, detail="Phone already registered")
    
    # Create new member
    db_member = Member(**member.dict())
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member

@router.get("/{member_id}", response_model=MemberResponse)
def get_member(member_id: int, db: Session = Depends(get_db), token: dict = Depends(verify_token)):
    """
    Get member by ID with optimized query
    """
    db_member = db.query(Member).options(
        joinedload(Member.cards)
    ).filter(Member.id == member_id).first()
    
    if db_member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return db_member

@router.put("/{member_id}", response_model=MemberResponse)
def update_member(member_id: int, member: MemberUpdate, db: Session = Depends(get_db), token: dict = Depends(verify_token)):
    """
    Update member information
    """
    db_member = db.query(Member).filter(Member.id == member_id).first()
    if db_member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Check if new email or phone conflicts with existing records
    if member.email and member.email != db_member.email:
        existing_email = db.query(Member).filter(Member.email == member.email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already in use")
    
    if member.phone and member.phone != db_member.phone:
        existing_phone = db.query(Member).filter(Member.phone == member.phone).first()
        if existing_phone:
            raise HTTPException(status_code=400, detail="Phone already in use")
    
    # Update fields
    for field, value in member.dict(exclude_unset=True).items():
        setattr(db_member, field, value)
    
    db.commit()
    db.refresh(db_member)
    return db_member

@router.delete("/{member_id}")
def delete_member(member_id: int, db: Session = Depends(get_db), token: dict = Depends(verify_token)):
    """
    Delete a member (soft delete by setting is_active=False)
    """
    db_member = db.query(Member).filter(Member.id == member_id).first()
    if db_member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    
    db_member.is_active = False
    db.commit()
    return {"message": "Member deactivated successfully"}

@router.get("/{member_id}/cards", response_model=List[MemberCardResponse])
def get_member_cards(member_id: int, db: Session = Depends(get_db), token: dict = Depends(verify_token)):
    """
    Get all cards for a member
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    
    cards = db.query(MemberCard).filter(MemberCard.member_id == member_id).all()
    return cards
@router.get("/{member_id}/level", response_model=dict)
def get_member_level(member_id: int, db: Session = Depends(get_db), token: dict = Depends(verify_token)):
    """
    Get member's membership level based on activity
    """
    # Get member
    member = db.query(Member).filter(Member.id == member_id).first()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # TODO: Implement level calculation logic based on member activity
    # Placeholder - get level from member's card
    level = db.query(MembershipLevel).join(MemberCard, MemberCard.level_id == MembershipLevel.id)\
        .filter(MemberCard.member_id == member_id).first()
    
    if not level:
        return {"level": "basic", "benefits": []}
    
    return {"level": level.name, "benefits": level.benefits}

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
@router.get("/{member_id}/level", response_model=dict)
def get_member_level(member_id: int, db: Session = Depends(get_db), token: dict = Depends(verify_token)):
    """
    Get member's membership level based on activity
    """
    # Get member
    member = db.query(Member).filter(Member.id == member_id).first()
    if member is None:
        raise HTTPException(status_code=404, detail="Member not found")

    # Calculate level based on activity points
    activity_points = member.activity_points or 0
    
    # Query available membership levels
    levels = db.query(MembershipLevel).order_by(MembershipLevel.required_points.desc()).all()
    
    # Determine current level
    current_level = None
    for level in levels:
        if activity_points >= level.required_points:
            current_level = level
            break
    
    if not current_level:
        current_level = db.query(MembershipLevel).filter(MembershipLevel.name == "basic").first()
    
    return {
        "level": current_level.name,
        "benefits": current_level.benefits,
        "next_level": {
            "name": levels[0].name if len(levels) > 0 else None,
            "required_points": levels[0].required_points if len(levels) > 0 else None
        } if current_level.name == "basic" and levels else None
    }

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
@router.get("/{member_id}/cards", response_model=List[MemberCardResponse])
def get_member_cards(member_id: int, db: Session = Depends(get_db), token: dict = Depends(verify_token)):
    """
    Get all cards for a member with optimized query
    """
    # Check member exists first with minimal query
    exists = db.query(Member.id).filter(Member.id == member_id).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Member not found")
        
    # Then fetch cards with joined membership level info
    cards = db.query(MemberCard).\
        options(joinedload(MemberCard.level)).\
        filter(MemberCard.member_id == member_id).\
        all()
        
    return cards

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
@router.get("/{member_id}/cards", response_model=List[MemberCardResponse])
def get_member_cards(member_id: int, db: Session = Depends(get_db), token: dict = Depends(verify_token)):
    """
    Get all cards for a member with optimized query
    """
    # Check member exists first with minimal query
    exists = db.query(Member.id).filter(Member.id == member_id).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Member not found")

    # Then fetch cards with joined membership level info
    cards = db.query(MemberCard).\
        options(joinedload(MemberCard.level)).\
        filter(MemberCard.member_id == member_id).\
        all()

    return cards

# [AUTO-APPENDED] Failed to replace, adding new code:
@router.get("/{member_id}/level", response_model=dict)
def get_member_level(member_id: int, db: Session = Depends(get_db), token: dict = Depends(verify_token)):
    """
    Get member's membership level with optimized query
    """
    # Check member exists first with minimal query
    exists = db.query(Member.id).filter(Member.id == member_id).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Member not found")

    # Get member's activity points
    activity_points = db.query(Member.activity_points).filter(Member.id == member_id).scalar() or 0

    # Find matching level in single query
    current_level = db.query(MembershipLevel).\
        filter(MembershipLevel.required_points <= activity_points).\
        order_by(MembershipLevel.required_points.desc()).\
        first()

    if not current_level:
        current_level = db.query(MembershipLevel).filter(MembershipLevel.name == "basic").first()

    # Get next level if exists
    next_level = db.query(MembershipLevel).\
        filter(MembershipLevel.required_points > activity_points).\
        order_by(MembershipLevel.required_points.asc()).\
        first()

    return {
        "level": current_level.name,
        "benefits": current_level.benefits,
        "next_level": {
            "name": next_level.name if next_level else None,
            "required_points": next_level.required_points if next_level else None
        } if current_level.name == "basic" else None
    }

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
@router.get("/", response_model=List[MemberResponse])
def get_members(
    skip: int = 0,
    limit: int = 100,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    is_active: Optional[bool] = None,
    gender: Optional[str] = None,
    join_date_start: Optional[str] = None,
    join_date_end: Optional[str] = None,
    fields: Optional[List[str]] = Query(None, description="Fields to include in response"),
    db: Session = Depends(get_db),
    token: dict = Depends(verify_token)
):
    """
    Get list of all members with pagination, filtering and field selection

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        name: Filter by name (partial match)
        email: Filter by email (partial match)
        phone: Filter by phone (partial match)
        is_active: Filter by active status
        gender: Filter by gender
        join_date_start: Filter members joined after this date
        join_date_end: Filter members joined before this date
        fields: List of fields to include in response (all fields if None)
    """
    query = db.query(Member)

    # Apply filters
    if name:
        query = query.filter(Member.name.ilike(f"%{name}%"))
    if email:
        query = query.filter(Member.email.ilike(f"%{email}%"))

# [AUTO-APPENDED] Failed to insert:

@router.get("/{member_id}/cards", response_model=List[MemberCardResponse])
def get_member_cards(member_id: int, db: Session = Depends(get_db), token: dict = Depends(verify_token)):
    """
    Get all cards for a member with optimized query
    """
    # Check member exists first with minimal query
    exists = db.query(Member.id).filter(Member.id == member_id).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Member not found")

    # Then fetch cards with joined membership level info
    cards = db.query(MemberCard).\
        options(joinedload(MemberCard.level)).\
        filter(MemberCard.member_id == member_id).\
        all()

    return cards

@router.get("/{member_id}/level", response_model=dict)
def get_member_level(member_id: int, db: Session = Depends(get_db), token: dict = Depends(verify_token)):
    """
    Get member's membership level with optimized query
    """
    # Check member exists first with minimal query
    exists = db.query(Member.id).filter(Member.id == member_id).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Member not found")

    # Get member's activity points
    activity_points = db.query(Member.activity_points).filter(Member.id == member_id).scalar() or 0

    # Find matching level in single query
    current_level = db.query(MembershipLevel).\
        filter(MembershipLevel.required_points <= activity_points).\
        order_by(MembershipLevel.required_points.desc()).\
        first()

    if not current_level:
        current_level = db.query(MembershipLevel).filter(MembershipLevel.name == "basic").first()

    # Get next level if exists
    next_level = db.query(MembershipLevel).\
        filter(MembershipLevel.required_points > activity_points).\
        order_by(MembershipLevel.required_points.asc()).\
        first()

    return {
        "level": current_level.name,
        "benefits": current_level.benefits,
        "next_level": {
            "name": next_level.name if next_level else None,
            "required_points": next_level.required_points if next_level else None
        } if current_level.name == "basic" else None
    }