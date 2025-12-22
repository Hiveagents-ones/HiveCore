from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models import Payment, Refund, Invoice, Member
from ..schemas import PaymentCreate, RefundCreate, InvoiceCreate
from ..schemas import PaymentUpdate
from ..enums import PaymentStatus

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["payments"]
)


@router.get("/", response_model=List[Payment])
@router.get("/member/{member_id}", response_model=List[Payment])
def get_member_payments(member_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get all payments for a specific member
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    return db.query(Payment).filter(Payment.member_id == member_id).offset(skip).limit(limit).all()
@router.get("/{payment_id}", response_model=Payment)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    """
    Get a specific payment by ID
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    return payment
def get_payments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get all payments
    """
    return db.query(Payment).offset(skip).limit(limit).all()


@router.post("/", response_model=Payment, status_code=status.HTTP_201_CREATED)


@router.put("/{payment_id}", response_model=Payment)
def update_payment(payment_id: int, payment: PaymentUpdate, db: Session = Depends(get_db)):
    """
    Update a payment
    """
    db_payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not db_payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    for key, value in payment.dict(exclude_unset=True).items():
        setattr(db_payment, key, value)
    
    db.commit()
    db.refresh(db_payment)
    return db_payment
def create_payment(payment: PaymentCreate, db: Session = Depends(get_db)):
    """
    Create a new payment
    """
    # Check if member exists
    member = db.query(Member).filter(Member.id == payment.member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    
    db_payment = Payment(**payment.dict())
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment


@router.post("/{payment_id}/refunds", response_model=Refund, status_code=status.HTTP_201_CREATED)

@router.post("/{payment_id}/callback", status_code=status.HTTP_200_OK)
def payment_callback(
    payment_id: int, 
    status: PaymentStatus,
    transaction_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Handle payment callback from payment gateway
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # Validate status transition
    if payment.status == PaymentStatus.COMPLETED and status == PaymentStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment already completed"
        )
    
    if payment.status == PaymentStatus.FAILED and status == PaymentStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment already failed"
        )
    
    # Update payment status
    payment.status = status
    if transaction_id:
        payment.transaction_id = transaction_id
    
    db.commit()
    db.refresh(payment)
    
    return {"message": "Payment status updated successfully"}
def create_refund(payment_id: int, refund: RefundCreate, db: Session = Depends(get_db)):
    """
    Create a refund for a payment
    """
    # Check if payment exists
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    db_refund = Refund(
        payment_id=payment_id,
        **refund.dict()
    )
    db.add(db_refund)
    db.commit()
    db.refresh(db_refund)
    return db_refund


@router.get("/invoices", response_model=List[Invoice])
@router.get("/invoices/{invoice_id}", response_model=Invoice)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """
    Get a specific invoice by ID
    """
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    return invoice
def get_invoices(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get all invoices
    """
    return db.query(Invoice).offset(skip).limit(limit).all()


@router.post("/invoices", response_model=Invoice, status_code=status.HTTP_201_CREATED)
def create_invoice(invoice: InvoiceCreate, db: Session = Depends(get_db)):
    """
    Create a new invoice
    """
    # Check if payment exists
    payment = db.query(Payment).filter(Payment.id == invoice.payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    db_invoice = Invoice(**invoice.dict())
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)
    return db_invoice

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
    # Validate status transition
    if payment.status == status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment already {status.value}"
        )
        
    # Validate allowed transitions
    if payment.status == PaymentStatus.COMPLETED and status != PaymentStatus.REFUNDED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change status from completed"
        )
        
    if payment.status == PaymentStatus.FAILED and status != PaymentStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only retry failed payments"
        )