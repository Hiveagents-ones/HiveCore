from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Callable, Awaitable
from datetime import datetime
import hmac
import hashlib
from config import settings
import logging

logger = logging.getLogger(__name__)

class PaymentSecurityMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next: Callable[[Request], Awaitable[JSONResponse]]) -> JSONResponse:
        # Skip middleware for non-payment routes
        if not request.url.path.startswith('/api/v1/payments'):
            return await call_next(request)
        
        try:
            # Validate payment requests
            if request.method in ('POST', 'PUT'):
                # Check for required headers and signatures
                required_headers = ['X-Request-ID', 'X-Signature', 'X-Timestamp']
                for header in required_headers:
                    if not request.headers.get(header):
                        raise HTTPException(status_code=400, detail=f"Missing {header} header")
                
                # Verify request signature
                timestamp = request.headers['X-Timestamp']
                payload = await request.body()
                expected_signature = hmac.new(
                    settings.PAYMENT_SECRET_KEY.encode(),
                    f"{timestamp}:{payload.decode()}".encode(),
                    hashlib.sha256
                ).hexdigest()
                
                if not hmac.compare_digest(expected_signature, request.headers['X-Signature']):
                    raise HTTPException(status_code=401, detail="Invalid request signature")
                
                # Log payment requests for audit
                logger.info(
                    f"Payment request: {request.method} {request.url.path} | "
                    f"Client: {request.client.host} | "
                    f"User-Agent: {request.headers.get('user-agent', 'unknown')} | "
                    f"Request-ID: {request.headers['X-Request-ID']} | "
                    f"Time: {datetime.utcnow().isoformat()}"
                )
                
                # Rate limiting check could be added here
                
            # Validate GET requests for sensitive data
            elif request.method == 'GET':
                # Ensure member_id is provided and valid for payment history
                if 'member_id' not in request.query_params:
                    raise HTTPException(status_code=400, detail="member_id parameter is required")
                
                # Verify API key for sensitive data access
                if not request.headers.get('X-API-Key') or request.headers['X-API-Key'] != settings.PAYMENT_API_KEY:
                    raise HTTPException(status_code=403, detail="Invalid API key")
                
            return await call_next(request)
            
        except HTTPException as http_exc:
            return JSONResponse(
                status_code=http_exc.status_code,
                content={"detail": http_exc.detail}
            )
        except Exception as e:
            logger.error(f"Payment security error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"}
            )