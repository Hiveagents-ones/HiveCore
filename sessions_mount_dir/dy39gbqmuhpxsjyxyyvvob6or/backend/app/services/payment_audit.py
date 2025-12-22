from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from .database import Base, get_db
from .schemas.payment import PaymentCreate, PaymentUpdate


class PaymentAuditService:
    """
    Payment audit service for tracking payment-related activities
    """
    
    @staticmethod
    def log_payment_creation(db: Session, payment_data: PaymentCreate, member_id: int, user_id: Optional[int] = None):
        """
        Log payment creation event
        
        Args:
            db: Database session
            payment_data: Payment data being created
            member_id: ID of the member making payment
            user_id: Optional ID of the admin user processing the payment
        """
        audit_log = {
            "event_type": "payment_created",
            "member_id": member_id,
            "amount": payment_data.amount,
            "payment_method": payment_data.payment_method,
            "timestamp": datetime.utcnow(),
            "user_id": user_id,
            "details": f"Payment created for member {member_id}"
        }
        # In a real implementation, this would write to an audit log table
        print(f"[AUDIT LOG] {audit_log}")
    
    @staticmethod
    def log_payment_update(db: Session, payment_id: int, original_data: dict, updated_data: PaymentUpdate, user_id: Optional[int] = None):
        """
        Log payment update event
        
        Args:
            db: Database session
            payment_id: ID of the payment being updated
            original_data: Original payment data before update
            updated_data: New payment data
            user_id: Optional ID of the admin user updating the payment
        """
        changes = {}
        for field, new_value in updated_data.dict(exclude_unset=True).items():
            if original_data.get(field) != new_value:
                changes[field] = {"old": original_data.get(field), "new": new_value}
        
        if changes:
            audit_log = {
                "event_type": "payment_updated",
                "payment_id": payment_id,
                "changes": changes,
                "timestamp": datetime.utcnow(),
                "user_id": user_id,
                "details": f"Payment {payment_id} updated"
            }
            # In a real implementation, this would write to an audit log table
            print(f"[AUDIT LOG] {audit_log}")
    
    @staticmethod
    def log_payment_deletion(db: Session, payment_id: int, payment_data: dict, user_id: Optional[int] = None):
        """
        Log payment deletion event
        
        Args:
            db: Database session
            payment_id: ID of the payment being deleted
            payment_data: Payment data being deleted
            user_id: Optional ID of the admin user deleting the payment
        """
        audit_log = {
            "event_type": "payment_deleted",
            "payment_id": payment_id,
            "member_id": payment_data['member_id'],
            "amount": payment_data['amount'],
            "timestamp": datetime.utcnow(),
            "user_id": user_id,
            "details": f"Payment {payment_id} deleted"
        }
        # In a real implementation, this would write to an audit log table
        print(f"[AUDIT LOG] {audit_log}")
    
    @staticmethod
    def log_payment_status_change(db: Session, payment_id: int, old_status: str, new_status: str, user_id: Optional[int] = None):
        """
        Log payment status change event
        
        Args:
            db: Database session
            payment_id: ID of the payment
            old_status: Previous status
            new_status: New status
            user_id: Optional ID of the admin user changing the status
        """
        audit_log = {
            "event_type": "payment_status_changed",
            "payment_id": payment_id,
            "old_status": old_status,
            "new_status": new_status,
            "timestamp": datetime.utcnow(),
            "user_id": user_id,
            "details": f"Payment {payment_id} status changed from {old_status} to {new_status}"
        }
        # In a real implementation, this would write to an audit log table
        print(f"[AUDIT LOG] {audit_log}")