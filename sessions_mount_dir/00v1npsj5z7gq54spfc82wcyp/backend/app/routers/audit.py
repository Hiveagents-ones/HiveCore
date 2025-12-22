from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..schemas import audit as schemas
from ..models import Payment
from ..models import Member
from ..models import MemberOperation

router = APIRouter(
    prefix="/api/v1/audit",
    tags=["audit"],
    responses={404: {"description": "Not found"}},
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.get("/payments", response_model=List[schemas.PaymentAudit])
async def get_payment_audit_logs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """
    Retrieve payment audit logs with pagination
    """
    payments = db.query(Payment).offset(skip).limit(limit).all()
    return payments

@router.get("/payments/{payment_id}", response_model=schemas.PaymentAuditDetail)

@router.get("/members", response_model=List[schemas.MemberAudit])
async def get_member_audit_logs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """
    Retrieve member audit logs with pagination
    """
    members = db.query(Member).offset(skip).limit(limit).all()
    return members

@router.get("/members/{member_id}", response_model=schemas.MemberAuditDetail)
@router.get("/member-operations", response_model=List[schemas.MemberOperationAudit])
async def get_member_operation_logs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """
    Retrieve member operation audit logs with pagination
    """
    operations = db.query(MemberOperation).offset(skip).limit(limit).all()
    return operations

@router.get("/member-operations/{operation_id}", response_model=schemas.MemberOperationAuditDetail)
async def get_member_operation_detail(
    operation_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """
    Get detailed audit log for a specific member operation
    """
    operation = db.query(MemberOperation).filter(MemberOperation.id == operation_id).first()
    if not operation:
        raise HTTPException(status_code=404, detail="Member operation not found")
    return operation
async def get_member_audit_detail(
    member_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """
    Get detailed audit log for a specific member
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member
async def get_payment_audit_detail(
    payment_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """
    Get detailed audit log for a specific payment
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment