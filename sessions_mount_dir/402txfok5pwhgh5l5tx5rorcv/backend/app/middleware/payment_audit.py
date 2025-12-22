import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from .database import get_db
from .models import PaymentAuditLog
from .models import Payment
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class PaymentAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 只审计支付相关的请求
        if "/api/v1/payments" not in request.url.path:
            return await call_next(request)

        # 获取支付ID（如果存在）
        payment_id = None
        if request.method == "POST" and "/api/v1/payments" in request.url.path:
            try:
                request_data = json.loads(request_body) if request_body else {}
                payment_id = request_data.get("payment_id")
            except json.JSONDecodeError:
                pass

        # 记录请求开始时间
        start_time = datetime.utcnow()
        
        # 获取请求体
        request_body = ""
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                request_body = await request.body()
                request_body = request_body.decode("utf-8")
            except Exception as e:
                logger.error(f"Failed to read request body: {e}")
                request_body = ""

        # 处理请求
        response = await call_next(request)

        # 记录响应时间
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        # 获取响应体
        response_body = ""
        try:
            response_body = response.body.decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to read response body: {e}")
            response_body = ""

        # 获取数据库会话
        db: Session = next(get_db())
        try:
            # 创建审计日志
            audit_log = PaymentAuditLog(
                endpoint=str(request.url.path),
                method=request.method,
                request_body=request_body,
                response_body=response_body,
                status_code=response.status_code,
                duration=duration,
                client_ip=request.client.host if request.client else "",
                user_agent=request.headers.get("user-agent", ""),
                payment_id=payment_id,
                created_at=start_time
            )
            
            # 保存到数据库
            db.add(audit_log)
            db.commit()
            logger.info(f"Payment audit log created for {request.method} {request.url.path}")
        except Exception as e:
            logger.error(f"Failed to create payment audit log: {e}")
            db.rollback()
        finally:
            db.close()

        return response