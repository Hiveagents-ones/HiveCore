from fastapi import Request
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import json
from datetime import datetime
from typing import Callable, Awaitable

from ..models.log import OperationLog, SystemLog
from ..models.payment import PaymentLog, Payment
from ..models.booking import Booking
from ..services.billing import get_billing_history
from ..database import get_db


async def log_request(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """
    请求日志中间件
    记录所有API请求和响应信息，包含操作者、IP和变更前后状态
    """
    """
    请求日志中间件
    记录所有API请求和响应信息
    """
    db: Session = next(get_db())
    
    try:
        # 记录请求开始
        request_time = datetime.utcnow()
        # 获取用户身份信息
        user_id = None
        if 'Authorization' in request.headers:
            try:
                token = request.headers['Authorization'].split(' ')[1]
                from ..middleware.security import decode_access_token
                payload = decode_access_token(token)
                user_id = payload.get('sub')
            except Exception:
                pass
        
        # 处理请求
        response = await call_next(request)
        
        # 记录请求结束
        response_time = datetime.utcnow()
        process_time = (response_time - request_time).total_seconds() * 1000
        
        # 获取请求信息
        request_body = await request.body()
        
        # 创建操作日志
                # 获取请求前的状态（适用于PUT/DELETE请求）
        old_state = None
        if request.method in ('PUT', 'DELETE') and request.url.path.startswith('/api/v1/'):
            try:
                if request.url.path.startswith('/api/v1/payments'):
                # 记录财务操作详情
                if request.method == 'POST' and request.url.path == '/api/v1/payments':
                    try:
                        request_data = json.loads(request_body.decode('utf-8')) if request_body else {}
                        payment_log = PaymentLog(
                            member_id=request_data.get('member_id'),
                            amount=request_data.get('amount'),
                            payment_method=request_data.get('payment_method'),
                            transaction_id=request_data.get('transaction_id'),
                            status='PENDING',
                            created_at=datetime.utcnow()
                        )
                        db.add(payment_log)
                        db.flush()
                        old_state = {"payment": payment_log.to_dict()}
                    except Exception as e:
                        system_log = SystemLog(
                            level="WARNING",
                            module="middleware.logging",
                            message=f"Failed to create payment log: {str(e)}",
                            stack_trace=str(e.__traceback__)
                        )
                        db.add(system_log)
                    payment_id = request.url.path.split('/')[-1]
                    if payment_id.isdigit():
                        old_state = db.query(PaymentLog).filter(PaymentLog.id == payment_id).first()
                        if old_state:
                            old_state = old_state.to_dict()
                            # 记录财务变更详情
                            if request.method == 'PUT':
                                try:
                                    request_data = json.loads(request_body.decode('utf-8')) if request_body else {}
                                    old_state["changes"] = {
                                        "amount": request_data.get('amount', old_state.get('amount')),
                                        "status": request_data.get('status', old_state.get('status')),
                                        "payment_method": request_data.get('payment_method', old_state.get('payment_method'))
                                    }
                                except Exception as e:
                                    system_log = SystemLog(
                                        level="WARNING",
                                        module="middleware.logging",
                                        message=f"Failed to track payment changes: {str(e)}",
                                        stack_trace=str(e.__traceback__)
                                    )
                                    db.add(system_log)
                            old_state = old_state.to_dict()
                elif request.url.path.startswith('/api/v1/members'):
                    member_id = request.url.path.split('/')[-1]
                    if member_id.isdigit():
                        billing_history = get_billing_history(member_id)
                        if billing_history:
                            old_state = {"billing_history": billing_history}
                elif request.url.path.startswith('/api/v1/bookings'):
                    booking_id = request.url.path.split('/')[-1]
                    if booking_id.isdigit():
                        old_state = db.query(Booking).filter(Booking.id == booking_id).first()
                        if old_state:
                            old_state = old_state.to_dict()
            except Exception as e:
                system_log = SystemLog(
                    level="WARNING",
                    module="middleware.logging",
                    message=f"Failed to get old state: {str(e)}",
                    stack_trace=str(e.__traceback__)
                )
                db.add(system_log)

        operation_log = OperationLog(
            action=request.method,
            entity_type=request.url.path.split('/')[3] if len(request.url.path.split('/')) > 3 else None,
            details=json.dumps({
                "path": request.url.path,
                "method": request.method,
                "query_params": dict(request.query_params),
                "request_body": request_body.decode('utf-8') if request_body else None,
                "status_code": response.status_code,
                "process_time_ms": process_time,
                "headers": dict(request.headers),
                "user_id": user_id,
                "payment_id": request.url.path.split('/')[-1] if request.url.path.startswith('/api/v1/payments') else None,
                "booking_id": request.url.path.split('/')[-1] if request.url.path.startswith('/api/v1/bookings') else None,
                "old_state": old_state,
                "new_state": json.loads(response.body.decode('utf-8')) if response.status_code == 200 and response.body else None
            }),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent'),
            created_at=datetime.utcnow()
        )
        
        db.add(operation_log)
        db.commit()
        
        return response
    
    except Exception as e:
        # 记录系统错误日志
        system_log = SystemLog(
            level="ERROR",
            module="middleware.logging",
            message=f"Request logging failed: {str(e)}",
            stack_trace=str(e.__traceback__)
        )
        db.add(system_log)
        db.commit()
        
        # 重新抛出异常
        raise
    
    finally:
        db.close()


def setup_logging_middleware(app):
    """
    设置日志中间件
    """
    app.middleware('http')(log_request)
    return app