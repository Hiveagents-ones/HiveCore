from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, validator
from typing import Optional
import logging
from ..database import get_db
from ..models import Member, MembershipPlan
from ..services.id_generator import id_generator

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/register", tags=["registration"])

class MemberRegistrationRequest(BaseModel):
    name: str
    phone: str
    id_card: str
    membership_plan_id: int

    @validator('phone')
    def validate_phone(cls, v):
        if not v.isdigit() or len(v) not in [10, 11]:
            raise ValueError('Phone number must be 10-11 digits')
        return v

    @validator('id_card')
    def validate_id_card(cls, v):
        if not v.isdigit() or len(v) != 18:
            raise ValueError('ID card must be 18 digits')
        return v

class MemberRegistrationResponse(BaseModel):
    member_id: str
    name: str
    phone: str
    membership_plan: str
    created_at: str

@router.post("/", response_model=MemberRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_member(
    request: MemberRegistrationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new member with transaction support and logging.
    """
    try:
        # Start transaction
        async with db.begin():
            # Validate membership plan exists and is active
            plan_result = await db.execute(
                select(MembershipPlan).where(
                    MembershipPlan.id == request.membership_plan_id,
                    MembershipPlan.is_active == True
                )
            )
            plan = plan_result.scalar_one_or_none()
            if not plan:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or inactive membership plan"
                )

            # Check for existing phone or ID card
            existing_member = await db.execute(
                select(Member).where(
                    (Member.phone == request.phone) | (Member.id_card == request.id_card)
                )
            )
            if existing_member.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Phone number or ID card already registered"
                )

            # Generate unique member ID
            member_id = await id_generator.generate_member_id(db)

            # Create new member
            new_member = Member(
                id=member_id,
                name=request.name,
                phone=request.phone,
                id_card=request.id_card,
                membership_plan_id=request.membership_plan_id
            )

            # Add to database
            db.add(new_member)
            await db.flush()  # Ensure the member is persisted

            # Log successful registration
            logger.info(f"New member registered: {member_id} - {request.name}")

            # Prepare response
            response = MemberRegistrationResponse(
                member_id=member_id,
                name=new_member.name,
                phone=new_member.phone,
                membership_plan=plan.name,
                created_at=new_member.created_at.isoformat()
            )

            return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed due to internal error"
        )
