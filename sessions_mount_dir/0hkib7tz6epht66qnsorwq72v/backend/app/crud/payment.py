from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import json

from ..models.payment import PaymentOrder, PaymentTransaction, Refund, PaymentStatus, PaymentMethod
from ..schemas.payment import PaymentOrderCreate, PaymentOrderUpdate, PaymentTransactionCreate, RefundCreate
from ..core.database import get_db


class PaymentCRUD:
    def __init__(self, db: Session):
        self.db = db

    def create_payment_order(self, order_data: PaymentOrderCreate) -> PaymentOrder:
        """Create a new payment order"""
        db_order = PaymentOrder(
            user_id=order_data.user_id,
            membership_id=order_data.membership_id,
            amount=order_data.amount,
            currency=order_data.currency,
            payment_method=order_data.payment_method,
            description=order_data.description,
            metadata=json.dumps(order_data.metadata) if order_data.metadata else None,
            expires_at=datetime.utcnow() + timedelta(hours=24),  # Default 24h expiry
            is_recurring=order_data.is_recurring if hasattr(order_data, 'is_recurring') else False,
            next_billing_date=order_data.next_billing_date if hasattr(order_data, 'next_billing_date') else None
        )
        self.db.add(db_order)
        self.db.commit()
        self.db.refresh(db_order)
        return db_order

    def get_payment_order(self, order_id: uuid.UUID) -> Optional[PaymentOrder]:
        """Get a payment order by ID"""
        return self.db.query(PaymentOrder).filter(PaymentOrder.id == order_id).first()

    def get_payment_orders_by_user(self, user_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[PaymentOrder]:
        """Get all payment orders for a user"""
        return (
            self.db.query(PaymentOrder)
            .filter(PaymentOrder.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_payment_order_status(self, order_id: uuid.UUID, status: PaymentStatus) -> Optional[PaymentOrder]:
        """Update payment order status"""
        db_order = self.get_payment_order(order_id)
        if db_order:
            db_order.status = status
            db_order.updated_at = datetime.utcnow()
            if status == PaymentStatus.CANCELLED:
                db_order.cancelled_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(db_order)
        return db_order

    def update_payment_order(self, order_id: uuid.UUID, order_data: PaymentOrderUpdate) -> Optional[PaymentOrder]:
        """Update payment order details"""
        db_order = self.get_payment_order(order_id)
        if db_order:
            update_data = order_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if field == "metadata" and value:
                    setattr(db_order, field, json.dumps(value))
                else:
                    setattr(db_order, field, value)
            db_order.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(db_order)
        return db_order

    def create_payment_transaction(self, transaction_data: PaymentTransactionCreate) -> PaymentTransaction:
        """Create a new payment transaction"""
        db_transaction = PaymentTransaction(
            payment_order_id=transaction_data.payment_order_id,
            gateway_transaction_id=transaction_data.gateway_transaction_id,
            gateway=transaction_data.gateway,
            amount=transaction_data.amount,
            currency=transaction_data.currency,
            status=transaction_data.status,
            gateway_response=json.dumps(transaction_data.gateway_response) if transaction_data.gateway_response else None
        )
        self.db.add(db_transaction)
        self.db.commit()
        self.db.refresh(db_transaction)
        return db_transaction

    def get_transactions_by_order(self, order_id: uuid.UUID) -> List[PaymentTransaction]:
        """Get all transactions for a payment order"""
        return (
            self.db.query(PaymentTransaction)
            .filter(PaymentTransaction.payment_order_id == order_id)
            .all()
        )

    def update_transaction_status(self, transaction_id: uuid.UUID, status: PaymentStatus, failure_reason: Optional[str] = None) -> Optional[PaymentTransaction]:
        """Update transaction status"""
        db_transaction = self.db.query(PaymentTransaction).filter(PaymentTransaction.id == transaction_id).first()
        if db_transaction:
            db_transaction.status = status
            db_transaction.failure_reason = failure_reason
            db_transaction.updated_at = datetime.utcnow()
            if status == PaymentStatus.COMPLETED:
                db_transaction.processed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(db_transaction)
        return db_transaction

    def create_refund(self, refund_data: RefundCreate) -> Refund:
        """Create a new refund"""
        db_refund = Refund(
            payment_order_id=refund_data.payment_order_id,
            amount=refund_data.amount,
            reason=refund_data.reason,
            status=PaymentStatus.PENDING,
            metadata=json.dumps(refund_data.metadata) if refund_data.metadata else None
        )
        self.db.add(db_refund)
        self.db.commit()
        self.db.refresh(db_refund)
        return db_refund

    def get_refunds_by_order(self, order_id: uuid.UUID) -> List[Refund]:
        """Get all refunds for a payment order"""
        return (
            self.db.query(Refund)
            .filter(Refund.payment_order_id == order_id)
            .all()
        )

    def update_refund_status(self, refund_id: uuid.UUID, status: PaymentStatus) -> Optional[Refund]:
        """Update refund status"""
        db_refund = self.db.query(Refund).filter(Refund.id == refund_id).first()
        if db_refund:
            db_refund.status = status
            if status == PaymentStatus.COMPLETED:
                db_refund.processed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(db_refund)
        return db_refund

    def get_payment_statistics(self, user_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
    def get_recurring_orders(self, user_id: Optional[uuid.UUID] = None) -> List[PaymentOrder]:
        """Get all recurring payment orders"""
        query = self.db.query(PaymentOrder).filter(PaymentOrder.is_recurring == True)
        if user_id:
            query = query.filter(PaymentOrder.user_id == user_id)
        return query.all()

    def update_next_billing_date(self, order_id: uuid.UUID, next_date: datetime) -> Optional[PaymentOrder]:
        """Update next billing date for recurring orders"""
        db_order = self.get_payment_order(order_id)
        if db_order and db_order.is_recurring:
            db_order.next_billing_date = next_date
            db_order.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(db_order)
        return db_order

    def get_orders_by_status(self, status: PaymentStatus, skip: int = 0, limit: int = 100) -> List[PaymentOrder]:
        """Get payment orders by status"""
        return (
            self.db.query(PaymentOrder)
            .filter(PaymentOrder.status == status)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_expired_orders(self) -> List[PaymentOrder]:
        """Get all expired payment orders"""
        return (
            self.db.query(PaymentOrder)
            .filter(PaymentOrder.expires_at < datetime.utcnow())
            .filter(PaymentOrder.status == PaymentStatus.PENDING)
            .all()
        )


        """Get payment statistics"""
        query = self.db.query(PaymentOrder)
        if user_id:
            query = query.filter(PaymentOrder.user_id == user_id)
        
        total_orders = query.count()
        completed_orders = query.filter(PaymentOrder.status == PaymentStatus.COMPLETED).count()
        total_amount = query.filter(PaymentOrder.status == PaymentStatus.COMPLETED).with_entities(
            self.db.func.sum(PaymentOrder.amount)
        ).scalar() or 0
        
        return {
            "total_orders": total_orders,
            "completed_orders": completed_orders,
            "total_amount": float(total_amount),
            "success_rate": (completed_orders / total_orders * 100) if total_orders > 0 else 0
        }


def get_payment_crud(db: Session = None) -> PaymentCRUD:
    """Get a PaymentCRUD instance"""
    if db is None:
        db = next(get_db())
    return PaymentCRUD(db)
