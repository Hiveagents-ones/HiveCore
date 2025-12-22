from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Literal
from app.core.security import generate_verification_code, send_verification_code, verify_verification_code
from app.services.member_service import MemberService

router = APIRouter(prefix="/members", tags=["members"])

class RegisterRequest(BaseModel):
    name: str
    contact_type: Literal["email", "phone"]
    contact: str
    health_info: str
    verification_code: str

@router.post("/verify")
async def send_verification(contact_type: str, contact: str):
    if contact_type not in ["email", "phone"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid contact type. Must be 'email' or 'phone'"
        )
    
    code = generate_verification_code()
    send_verification_code(contact_type, contact, code)
    return {"message": "Verification code sent successfully"}

@router.post("/register")
async def register(request: RegisterRequest):
    if not verify_verification_code(
        request.contact_type,
        request.contact,
        request.verification_code
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code"
        )
    
    member_id = MemberService.generate_member_id()
    
    # In a real implementation, you would save the member data here
    # For now, we just return the generated ID
    return {
        "member_id": member_id,
        "message": "Registration successful"
    }