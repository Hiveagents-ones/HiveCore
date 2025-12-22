from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
from . import models, schemas

def get_membership_plan(db: Session, plan_id: int) -> Optional[models.MembershipPlan]:
    return db.query(models.MembershipPlan).filter(models.MembershipPlan.id == plan_id).first()

def get_membership_plans(db: Session, skip: int = 0, limit: int = 100) -> List[models.MembershipPlan]:
    return db.query(models.MembershipPlan).filter(models.MembershipPlan.is_active == True).offset(skip).limit(limit).all()

def create_membership_plan(db: Session, plan: schemas.MembershipPlanCreate) -> models.MembershipPlan:
    db_plan = models.MembershipPlan(
        name=plan.name,
        description=plan.description,
        price=plan.price,
        duration_months=plan.duration_months
    )
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    return db_plan

def update_membership_plan(db: Session, plan_id: int, plan: schemas.MembershipPlanUpdate) -> Optional[models.MembershipPlan]:
    db_plan = get_membership_plan(db, plan_id)
    if db_plan:
        for field, value in plan.dict(exclude_unset=True).items():
            setattr(db_plan, field, value)
        db_plan.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_plan)
    return db_plan

def delete_membership_plan(db: Session, plan_id: int) -> bool:
    db_plan = get_membership_plan(db, plan_id)
    if db_plan:
        db_plan.is_active = False
        db.commit()
        return True
    return False

def get_subscription_record(db: Session, record_id: int) -> Optional[models.SubscriptionRecord]:
    return db.query(models.SubscriptionRecord).filter(models.SubscriptionRecord.id == record_id).first()

def get_subscription_records_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[models.SubscriptionRecord]:
    return db.query(models.SubscriptionRecord).filter(models.SubscriptionRecord.user_id == user_id).offset(skip).limit(limit).all()

def create_subscription_record(db: Session, record: schemas.SubscriptionRecordCreate) -> models.SubscriptionRecord:
    plan = get_membership_plan(db, record.plan_id)
    if not plan:
        raise ValueError("Invalid membership plan")
    
    start_date = record.start_date or datetime.utcnow()
    end_date = start_date + timedelta(days=plan.duration_months * 30)
    
    db_record = models.SubscriptionRecord(
        user_id=record.user_id,
        plan_id=record.plan_id,
        amount_paid=record.amount_paid,
        payment_date=record.payment_date or datetime.utcnow(),
        start_date=start_date,
        end_date=end_date,
        payment_method=record.payment_method,
        transaction_id=record.transaction_id,
        status=record.status or "completed"
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    
    # Update or create membership record
    membership = db.query(models.MembershipRecord).filter(models.MembershipRecord.user_id == record.user_id).first()
    if membership:
        membership.end_date = max(membership.end_date, end_date)
        membership.updated_at = datetime.utcnow()
    else:
        membership = models.MembershipRecord(
            user_id=record.user_id,
            start_date=start_date,
            end_date=end_date
        )
        db.add(membership)
    
    db.commit()
    return db_record

def update_subscription_record(db: Session, record_id: int, record: schemas.SubscriptionRecordUpdate) -> Optional[models.SubscriptionRecord]:
    db_record = get_subscription_record(db, record_id)
    if db_record:
        for field, value in record.dict(exclude_unset=True).items():
            setattr(db_record, field, value)
        db.commit()
        db.refresh(db_record)
    return db_record

def delete_subscription_record(db: Session, record_id: int) -> bool:
    db_record = get_subscription_record(db, record_id)
    if db_record:
        db.delete(db_record)
        db.commit()
        return True
    return False

def get_active_membership(db: Session, user_id: int) -> Optional[models.MembershipRecord]:
    return db.query(models.MembershipRecord).filter(
        models.MembershipRecord.user_id == user_id,
        models.MembershipRecord.is_active == True,
        models.MembershipRecord.end_date > datetime.utcnow()
    ).first()

def renew_membership(db: Session, user_id: int, plan_id: int, payment_method: str, transaction_id: str) -> models.SubscriptionRecord:
    plan = get_membership_plan(db, plan_id)
    if not plan:
        raise ValueError("Invalid membership plan")
    
    current_membership = get_active_membership(db, user_id)
    start_date = current_membership.end_date if current_membership else datetime.utcnow()
    end_date = start_date + timedelta(days=plan.duration_months * 30)
    
    subscription = schemas.SubscriptionRecordCreate(
        user_id=user_id,
        plan_id=plan_id,
        amount_paid=plan.price,
        payment_method=payment_method,
        transaction_id=transaction_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return create_subscription_record(db, subscription)
