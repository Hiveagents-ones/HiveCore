from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict

from .. import models, schemas
from ..database import get_db
from ..crud import get_membership_plan_by_id
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/register",
    tags=["registration"]
)


@router.post("/", response_model=schemas.MemberResponse, status_code=status.HTTP_201_CREATED)
def register_member(
    member_data: schemas.MemberRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new gym member.
    
    This endpoint handles the core registration logic:
    1. Validates the incoming data via Pydantic schema.
    2. Checks for uniqueness of phone number and ID card number.
    3. Verifies the selected membership plan exists.
    4. Generates a unique account number.
    5. Encrypts sensitive data (phone, ID card) before saving.
    6. Persists the new member record in the database.
    7. Logs the registration process.
    """
    logger.info(f"Attempting to register new member with phone: {member_data.phone}")

    # 1. Check for uniqueness of phone number and ID card number
    # Note: The check is done on the raw, unencrypted data.
    # The actual storage will be encrypted.
    existing_member_by_phone = db.query(models.Member).filter(
        models.Member.phone == models.Member.encrypt_sensitive_data(member_data.phone)
    ).first()
    if existing_member_by_phone:
        logger.warning(f"Registration failed: Phone number {member_data.phone} already exists.")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This phone number is already registered.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    existing_member_by_id_card = db.query(models.Member).filter(
        models.Member.id_card == models.Member.encrypt_sensitive_data(member_data.id_card)
    ).first()
    if existing_member_by_id_card:
        logger.warning(f"Registration failed: ID card number {member_data.id_card} already exists.")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This ID card number is already registered.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Verify the selected membership plan exists
    membership_plan = get_membership_plan_by_id(db, plan_id=member_data.membership_plan_id)
    if not membership_plan:
        logger.warning(f"Registration failed: Membership plan with ID {member_data.membership_plan_id} not found.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Membership plan with ID {member_data.membership_plan_id} not found.",
        )

    # 3. Create a new member instance and populate it
    new_member = models.Member(
        name=member_data.name,
        membership_plan=membership_plan.name
    )

    # 4. Generate a unique account number
    new_member.account_number = new_member.generate_account_number()
    logger.info(f"Generated account number: {new_member.account_number}")

    # 5. Encrypt and set sensitive data
    new_member.set_phone(member_data.phone)
    new_member.set_id_card(member_data.id_card)

    # 6. Add the new member to the database and commit
    try:
        db.add(new_member)
        db.commit()
        db.refresh(new_member)
        logger.info(f"Successfully registered member with account number: {new_member.account_number}")
    except Exception as e:
        db.rollback()
        logger.error(f"Database error during registration for phone {member_data.phone}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while registering the member. Please try again later."
        )

    # 7. Return the newly created member's data
    # The response model will handle data serialization from the ORM object.
    return new_member
