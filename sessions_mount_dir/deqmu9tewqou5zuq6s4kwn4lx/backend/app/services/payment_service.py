import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.core.config import settings
from app.models.payment import Payment
from app.models.user import User
from app.models.membership import Membership
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.core.security import verify_anti_replay_token
import time
from prometheus_client import Counter, Histogram, Gauge

# Prometheus metrics
PAYMENT_REQUESTS = Counter('payment_requests_total', 'Total payment requests', ['status'])
PAYMENT_DURATION = Histogram('payment_duration_seconds', 'Payment processing duration')
ACTIVE_MEMBERSHIPS = Gauge('active_memberships_total', 'Total active memberships')

logger = logging.getLogger(__name__)

class PaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.timeout = settings.PAYMENT_TIMEOUT if hasattr(settings, 'PAYMENT_TIMEOUT') else 30

    @PAYMENT_DURATION.time()
    def process_payment(
        self,
        user_id: int,
        payment_data: PaymentCreate,
        anti_replay_token: str
    ) -> PaymentResponse:
        """Process payment with timeout control and metrics recording."""
        start_time = time.time()
        
        try:
            # Verify anti-replay token
            verify_anti_replay_token(anti_replay_token, "payment")
            
            # Check timeout
            if time.time() - start_time > self.timeout:
                PAYMENT_REQUESTS.labels(status='timeout').inc()
                raise HTTPException(
                    status_code=status.HTTP_408_REQUEST_TIMEOUT,
                    detail="Payment processing timeout"
                )
            
            # Validate user exists
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                PAYMENT_REQUESTS.labels(status='user_not_found').inc()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Create payment record
            payment = Payment(
                user_id=user_id,
                amount=payment_data.amount,
                package_type=payment_data.package_type,
                status="pending",
                created_at=datetime.utcnow()
            )
            
            self.db.add(payment)
            self.db.commit()
            self.db.refresh(payment)
            
            # Process payment (mock implementation)
            if self._process_payment_gateway(payment):
                # Update membership
                self._update_membership(user_id, payment_data.package_type)
                
                # Update payment status
                payment.status = "completed"
                payment.completed_at = datetime.utcnow()
                self.db.commit()
                
                # Update metrics
                PAYMENT_REQUESTS.labels(status='success').inc()
                self._update_membership_metrics()
                
                return PaymentResponse.from_orm(payment)
            else:
                payment.status = "failed"
                payment.failed_at = datetime.utcnow()
                self.db.commit()
                
                PAYMENT_REQUESTS.labels(status='failed').inc()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Payment processing failed"
                )
                
        except Exception as e:
            PAYMENT_REQUESTS.labels(status='error').inc()
            logger.error(f"Payment processing error: {str(e)}")
            raise

    def _process_payment_gateway(self, payment: Payment) -> bool:
        """Mock payment gateway processing with timeout."""
        start_time = time.time()
        
        # Simulate payment processing
        time.sleep(0.5)  # Mock processing time
        
        # Check timeout
        if time.time() - start_time > self.timeout:
            return False
            
        # Mock success (90% success rate)
        import random
        return random.random() > 0.1

    def _update_membership(self, user_id: int, package_type: str) -> None:
        """Update user membership based on package type."""
        membership = self.db.query(Membership).filter(Membership.user_id == user_id).first()
        
        if not membership:
            membership = Membership(
                user_id=user_id,
                package_type=package_type,
                start_date=datetime.utcnow(),
                end_date=self._calculate_end_date(package_type),
                is_active=True
            )
            self.db.add(membership)
        else:
            # Extend existing membership
            if membership.end_date and membership.end_date > datetime.utcnow():
                membership.end_date = self._calculate_end_date(package_type, membership.end_date)
            else:
                membership.start_date = datetime.utcnow()
                membership.end_date = self._calculate_end_date(package_type)
            membership.package_type = package_type
            membership.is_active = True
            
        self.db.commit()

    def _calculate_end_date(self, package_type: str, start_date: Optional[datetime] = None) -> datetime:
        """Calculate membership end date based on package type."""
        if not start_date:
            start_date = datetime.utcnow()
            
        if package_type == "monthly":
            return start_date + timedelta(days=30)
        elif package_type == "quarterly":
            return start_date + timedelta(days=90)
        elif package_type == "yearly":
            return start_date + timedelta(days=365)
        else:
            raise ValueError(f"Invalid package type: {package_type}")

    def _update_membership_metrics(self) -> None:
        """Update membership metrics for monitoring."""
        count = self.db.query(Membership).filter(Membership.is_active == True).count()
        ACTIVE_MEMBERSHIPS.set(count)

    def get_payment_history(self, user_id: int, limit: int = 10) -> list[PaymentResponse]:
        """Get payment history for a user with timeout control."""
        start_time = time.time()
        
        try:
            if time.time() - start_time > self.timeout:
                raise HTTPException(
                    status_code=status.HTTP_408_REQUEST_TIMEOUT,
                    detail="Request timeout"
                )
                
            payments = (
                self.db.query(Payment)
                .filter(Payment.user_id == user_id)
                .order_by(Payment.created_at.desc())
                .limit(limit)
                .all()
            )
            
            return [PaymentResponse.from_orm(p) for p in payments]
            
        except Exception as e:
            logger.error(f"Error fetching payment history: {str(e)}")
            raise

    def refund_payment(self, payment_id: int, user_id: int, anti_replay_token: str) -> bool:
        """Process payment refund with timeout control."""
        start_time = time.time()
        
        try:
            # Verify anti-replay token
            verify_anti_replay_token(anti_replay_token, "refund")
            
            if time.time() - start_time > self.timeout:
                raise HTTPException(
                    status_code=status.HTTP_408_REQUEST_TIMEOUT,
                    detail="Refund processing timeout"
                )
                
            payment = self.db.query(Payment).filter(
                Payment.id == payment_id,
                Payment.user_id == user_id
            ).first()
            
            if not payment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Payment not found"
                )
                
            if payment.status != "completed":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Only completed payments can be refunded"
                )
                
            # Process refund (mock)
            if self._process_refund_gateway(payment):
                payment.status = "refunded"
                payment.refunded_at = datetime.utcnow()
                self.db.commit()
                
                # Update membership if needed
                self._handle_membership_refund(user_id, payment.package_type)
                
                PAYMENT_REQUESTS.labels(status='refund_success').inc()
                self._update_membership_metrics()
                
                return True
            else:
                PAYMENT_REQUESTS.labels(status='refund_failed').inc()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Refund processing failed"
                )
                
        except Exception as e:
            PAYMENT_REQUESTS.labels(status='refund_error').inc()
            logger.error(f"Refund processing error: {str(e)}")
            raise

    def _process_refund_gateway(self, payment: Payment) -> bool:
        """Mock refund gateway processing."""
        # Simulate refund processing
        time.sleep(0.3)
        
        # Mock success (95% success rate)
        import random
        return random.random() > 0.05

    def _handle_membership_refund(self, user_id: int, package_type: str) -> None:
        """Handle membership adjustment after refund."""
        membership = self.db.query(Membership).filter(Membership.user_id == user_id).first()
        
        if membership and membership.is_active:
            # Subtract the refunded duration
            duration_map = {
                "monthly": timedelta(days=30),
                "quarterly": timedelta(days=90),
                "yearly": timedelta(days=365)
            }
            
            if package_type in duration_map:
                membership.end_date = membership.end_date - duration_map[package_type]
                
                # Deactivate if end date is in the past
                if membership.end_date <= datetime.utcnow():
                    membership.is_active = False
                    
                self.db.commit()
