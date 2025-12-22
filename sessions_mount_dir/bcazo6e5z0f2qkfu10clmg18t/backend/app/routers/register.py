from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..core.security import encrypt_sensitive_data, generate_member_id
from ..database import get_db

router = APIRouter(
    prefix="/register",
    tags=["register"]
)

@router.post("/", response_model=schemas.MemberRegisterResponse, status_code=status.HTTP_201_CREATED)
def register_member(member_data: schemas.MemberRegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new member.
    - **name**: Member's full name
    - **phone**: Member's phone number (must be unique)
    - **id_card**: Member's ID card number (must be unique)
    - **email**: Member's email (optional, must be unique if provided)
    - **address**: Member's address (optional)
    - **emergency_contact**: Emergency contact name (optional)
    - **emergency_phone**: Emergency contact phone (optional)
    """
    # Check if phone number already exists
    existing_phone = db.query(models.Member).filter(models.Member.phone == member_data.phone).first()
    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered."
        )

    # Check if ID card already exists
    existing_id_card = db.query(models.Member).filter(models.Member.id_card == member_data.id_card).first()
    if existing_id_card:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID card number already registered."
        )

    # Check if email already exists (if provided)
    if member_data.email:
        existing_email = db.query(models.Member).filter(models.Member.email == member_data.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address already registered."
            )

    # Generate a unique member ID
    new_member_id = generate_member_id()

    # Encrypt sensitive data
    encrypted_phone = encrypt_sensitive_data(member_data.phone)
    encrypted_id_card = encrypt_sensitive_data(member_data.id_card)
    encrypted_email = encrypt_sensitive_data(member_data.email) if member_data.email else None
    encrypted_emergency_phone = encrypt_sensitive_data(member_data.emergency_phone) if member_data.emergency_phone else None

    # Create new member instance
    new_member = models.Member(
        member_id=new_member_id,
        name=member_data.name,
        phone=encrypted_phone,
        id_card=encrypted_id_card,
        email=encrypted_email,
        address=member_data.address,
        emergency_contact=member_data.emergency_contact,
        emergency_phone=encrypted_emergency_phone,
        status=True  # Default to active
    )

    # Add to database
    db.add(new_member)
    db.commit()
    db.refresh(new_member)

    # --- Buried Point Logic ---
    # Log the registration event. In a real application, this might be sent to a logging service,
    # a message queue, or a dedicated analytics system.
    # For this example, we'll just print it to the console.
    print(
        f"[埋点] New Member Registered: "
        f"MemberID='{new_member.member_id}', "
        f"Name='{new_member.name}', "
        f"Timestamp='{datetime.utcnow().isoformat()}'"
    )
    # --- End of Buried Point Logic ---

    # Prepare the response
    response_data = {
        "member_id": new_member.member_id,
        "name": new_member.name,
        "phone": member_data.phone, # Return original, unencrypted phone for user confirmation
        "registration_date": new_member.registration_date,
        "status": "active" if new_member.status else "inactive"
    }

    return response_data
