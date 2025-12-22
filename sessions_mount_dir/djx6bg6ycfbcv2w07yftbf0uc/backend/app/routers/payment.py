from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import logging
import time
from datetime import datetime, timedelta
import redis
from prometheus_client import Counter, Histogram, generate_latest

from ..core.security import SecurityManager, security
from ..core.config import settings
from ..services.payment_gateway import PaymentGateway, AlipayGateway, PaymentResult, PaymentGatewayError

# Initialize router
router = APIRouter(prefix="/payment", tags=["payment"])

# Initialize Redis client
redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)

# Initialize payment gateway
payment_gateway = AlipayGateway()

# Prometheus metrics
payment_requests_total = Counter('payment_requests_total', 'Total payment requests', ['method', 'status'])
payment_request_duration = Histogram('payment_request_duration_seconds', 'Payment request duration')

# Logger
logger = logging.getLogger(__name__)

@router.post("/create")
async def create_payment(
    request: Request,
    order_id: str,
    amount: float,
    currency: str = "CNY",
    subject: str = "Membership Renewal",
    return_url: Optional[str] = None,
    notify_url: Optional[str] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Create a payment order"""
    start_time = time.time()
    
    try:
        # Verify token
        payload = SecurityManager.verify_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        
        # Rate limiting check
        rate_limit_key = f"payment_rate_limit:{user_id}"
        current_requests = redis_client.get(rate_limit_key)
        if current_requests and int(current_requests) > 5:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many payment requests")
        
        # Create payment
        result = await payment_gateway.create_payment(
            order_id=order_id,
            amount=amount,
            currency=currency,
            subject=subject,
            return_url=return_url or settings.DEFAULT_RETURN_URL,
            notify_url=notify_url or settings.DEFAULT_NOTIFY_URL
        )
        
        # Update rate limit
        redis_client.incr(rate_limit_key)
        redis_client.expire(rate_limit_key, 3600)
        
        # Record metrics
        payment_requests_total.labels(method="create", status="success").inc()
        payment_request_duration.observe(time.time() - start_time)
        
        return {
            "success": result.success,
            "transaction_id": result.transaction_id,
            "payment_url": result.gateway_response.get("payment_url"),
            "message": "Payment order created successfully"
        }
    
    except PaymentGatewayError as e:
        payment_requests_total.labels(method="create", status="error").inc()
        logger.error(f"Payment gateway error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    except Exception as e:
        payment_requests_total.labels(method="create", status="error").inc()
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.post("/verify")
async def verify_payment(
    request: Request,
    notification_data: Dict[str, Any],
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Verify payment result"""
    start_time = time.time()
    
    try:
        # Verify token
        payload = SecurityManager.verify_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        
        # Verify payment
        result = await payment_gateway.verify_payment(notification_data)
        
        # Record metrics
        payment_requests_total.labels(method="verify", status="success" if result.success else "error").inc()
        payment_request_duration.observe(time.time() - start_time)
        
        return {
            "success": result.success,
            "transaction_id": result.transaction_id,
            "message": "Payment verified successfully" if result.success else "Payment verification failed",
            "error_message": result.error_message
        }
    
    except PaymentGatewayError as e:
        payment_requests_total.labels(method="verify", status="error").inc()
        logger.error(f"Payment gateway error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    except Exception as e:
        payment_requests_total.labels(method="verify", status="error").inc()
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.get("/query/{order_id}")
async def query_payment(
    order_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Query payment status"""
    start_time = time.time()
    
    try:
        # Verify token
        payload = SecurityManager.verify_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        
        # Query payment
        result = await payment_gateway.query_payment(order_id)
        
        # Record metrics
        payment_requests_total.labels(method="query", status="success" if result.success else "error").inc()
        payment_request_duration.observe(time.time() - start_time)
        
        return {
            "success": result.success,
            "transaction_id": result.transaction_id,
            "status": result.gateway_response.get("status"),
            "message": "Payment status retrieved successfully" if result.success else "Failed to retrieve payment status",
            "error_message": result.error_message
        }
    
    except PaymentGatewayError as e:
        payment_requests_total.labels(method="query", status="error").inc()
        logger.error(f"Payment gateway error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    except Exception as e:
        payment_requests_total.labels(method="query", status="error").inc()
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")

@router.get("/metrics")
async def get_metrics():
    """Get Prometheus metrics"""
    try:
        metrics = generate_latest()
        return JSONResponse(content=metrics.decode("utf-8"), media_type="text/plain")
    except Exception as e:
        logger.error(f"Failed to generate metrics: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to generate metrics")
