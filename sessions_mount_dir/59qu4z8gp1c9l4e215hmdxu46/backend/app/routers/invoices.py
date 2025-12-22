from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..schemas.payments import InvoiceCreate, InvoiceResponse
from ..services.payment_service import create_invoice, get_invoices
from ..services.payment_service import get_invoice_by_id, update_invoice_status
from ..database import get_db

router = APIRouter(
    prefix="/api/v1/invoices",
    tags=["invoices"],
    responses={404: {"description": "Not found"}},
)

@router.post(
    "/",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new invoice"
)
async def create_new_invoice(
    invoice: InvoiceCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new electronic invoice for a payment.
    
    Args:
        invoice: InvoiceCreate schema containing payment_id and invoice details
        
    Returns:
        The created invoice with generated invoice number
    """
    try:
        return create_invoice(db=db, invoice=invoice)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get(
    "/",
    response_model=List[InvoiceResponse],
    summary="Get all invoices"
)
async def list_invoices(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):



@router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    summary="Get invoice by ID"
)
async def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve a specific electronic invoice by ID.

    Args:
        invoice_id: The ID of the invoice to retrieve

    Returns:
        InvoiceResponse object
    """
    invoice = get_invoice_by_id(db=db, invoice_id=invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    return invoice

    """
    Retrieve a list of all electronic invoices.
    
    Args:
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        
    Returns:
        List of InvoiceResponse objects
    """
    return get_invoices(db=db, skip=skip, limit=limit)

@router.put(
    "/{invoice_id}/status",
    response_model=InvoiceResponse,
    summary="Update invoice status"
)
async def update_status(
    invoice_id: int,
    status: str,
    db: Session = Depends(get_db)
):
    """
    Update the status of an electronic invoice.

    Args:
        invoice_id: The ID of the invoice to update
        status: New status for the invoice

    Returns:
        Updated InvoiceResponse object
    """
    try:
        return update_invoice_status(db=db, invoice_id=invoice_id, status=status)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )