from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..schemas.payments import RefundCreate, RefundOut
from ..database import get_db
from ..models import Payment, Refund
from ..services.payment_service import process_refund
from ..services.payment_service import approve_refund

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["refunds"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/{payment_id}/refunds",
    response_model=RefundOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a refund request"
)
def create_refund(




@router.put(
    "/refunds/{refund_id}/approve",
    response_model=RefundOut,
    status_code=status.HTTP_200_OK,
    summary="Approve a refund request"
)
def approve_refund_request(
    refund_id: int,
    db: Session = Depends(get_db)
):
    """
    Approve a pending refund request

    Args:
        refund_id: ID of the refund to approve

    Returns:
        RefundOut: The approved refund record
    """
    # Check if refund exists
    db_refund = db.query(Refund).filter(Refund.id == refund_id).first()
    if not db_refund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found"
        )

    # Check if refund is already processed
    if db_refund.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund is already processed"
        )

    # Process refund approval through payment service
    try:
        refund_record = approve_refund(db, refund_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

    return refund_record
    payment_id: int,
    refund: RefundCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new refund request for a payment
    
    Args:
        payment_id: ID of the payment to refund
        refund: Refund details including amount and reason
        
    Returns:
        RefundOut: The created refund record
    """
    # Check if payment exists
    db_payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not db_payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # Validate refund amount
    if refund.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund amount must be positive"
        )
    
    remaining_amount = db_payment.amount - db_payment.refund_amount
    if refund.amount > remaining_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Refund amount exceeds remaining amount. Max refund: {remaining_amount}"
        )
    
    # Process refund through payment service
    try:
        refund_record = process_refund(db, payment_id, refund)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    
    return refund_record