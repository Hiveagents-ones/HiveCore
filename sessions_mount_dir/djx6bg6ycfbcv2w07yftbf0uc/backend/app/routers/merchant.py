from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas
from ..database import get_db

router = APIRouter(
    prefix="/merchants",
    tags=["merchants"]
)

@router.post("/", response_model=schemas.Merchant, status_code=status.HTTP_201_CREATED)
def create_merchant(merchant: schemas.MerchantCreate, db: Session = Depends(get_db)):
    db_merchant = models.Merchant(**merchant.dict())
    db.add(db_merchant)
    db.commit()
    db.refresh(db_merchant)
    return db_merchant

@router.get("/", response_model=List[schemas.Merchant])
def list_merchants(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    merchants = db.query(models.Merchant).offset(skip).limit(limit).all()
    return merchants

@router.get("/{merchant_id}", response_model=schemas.Merchant)
def get_merchant(merchant_id: int, db: Session = Depends(get_db)):
    merchant = db.query(models.Merchant).filter(models.Merchant.id == merchant_id).first()
    if merchant is None:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return merchant

@router.put("/{merchant_id}", response_model=schemas.Merchant)
def update_merchant(merchant_id: int, merchant_update: schemas.MerchantUpdate, db: Session = Depends(get_db)):
    db_merchant = db.query(models.Merchant).filter(models.Merchant.id == merchant_id).first()
    if db_merchant is None:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    update_data = merchant_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_merchant, field, value)
    
    db.commit()
    db.refresh(db_merchant)
    return db_merchant

@router.delete("/{merchant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_merchant(merchant_id: int, db: Session = Depends(get_db)):
    db_merchant = db.query(models.Merchant).filter(models.Merchant.id == merchant_id).first()
    if db_merchant is None:
        raise HTTPException(status_code=404, detail="Merchant not found")
    db.delete(db_merchant)
    db.commit()
    return None

@router.post("/{merchant_id}/approve", response_model=schemas.Merchant)
def approve_merchant(merchant_id: int, db: Session = Depends(get_db)):
    db_merchant = db.query(models.Merchant).filter(models.Merchant.id == merchant_id).first()
    if db_merchant is None:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    db_merchant.status = "approved"
    db.commit()
    db.refresh(db_merchant)
    return db_merchant

@router.post("/{merchant_id}/suspend", response_model=schemas.Merchant)
def suspend_merchant(merchant_id: int, db: Session = Depends(get_db)):
    db_merchant = db.query(models.Merchant).filter(models.Merchant.id == merchant_id).first()
    if db_merchant is None:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    db_merchant.is_active = False
    db.commit()
    db.refresh(db_merchant)
    return db_merchant

@router.get("/{merchant_id}/logs", response_model=List[schemas.OperationLog])
def get_merchant_logs(merchant_id: int, db: Session = Depends(get_db)):
    logs = db.query(models.OperationLog).filter(models.OperationLog.merchant_id == merchant_id).all()
    return logs

@router.post("/{merchant_id}/logs", response_model=schemas.OperationLog, status_code=status.HTTP_201_CREATED)
def create_operation_log(merchant_id: int, log: schemas.OperationLogCreate, db: Session = Depends(get_db)):
    db_log = models.OperationLog(**log.dict())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

@router.get("/{merchant_id}/with-logs", response_model=schemas.MerchantWithLogs)
def get_merchant_with_logs(merchant_id: int, db: Session = Depends(get_db)):
    merchant = db.query(models.Merchant).filter(models.Merchant.id == merchant_id).first()
    if merchant is None:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    logs = db.query(models.OperationLog).filter(models.OperationLog.merchant_id == merchant_id).all()
    merchant_dict = merchant.__dict__.copy()
    merchant_dict['operation_logs'] = logs
    return merchant_dict
