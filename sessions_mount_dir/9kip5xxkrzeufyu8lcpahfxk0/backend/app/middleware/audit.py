from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime
import json
from typing import Callable, Awaitable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Send, Scope
from backend.app.database import get_db
from backend.app.models import AuditLog
from backend.app.models import Member
from backend.app.models import CourseBooking
from backend.app.models import CoachSchedule
from backend.app.models import Payment
from backend.app.models import MemberCard

class AuditMiddleware(BaseHTTPMiddleware):
    """
    审计日志中间件，记录所有API请求的关键信息
    """
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable]) -> JSONResponse:
        """
        处理请求并记录审计日志
        """
        try:
            # 获取请求基本信息
            audit_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else None,
                "user_id": request.user.id if hasattr(request, 'user') and request.user else None,
                "user_agent": request.headers.get("user-agent"),
                "query_params": dict(request.query_params),
            }
            
            # 对于POST/PUT请求，记录请求体（敏感信息需过滤）
            if request.method in ("POST", "PUT"):
                try:
                    body = await request.json()
                    # 过滤掉可能的敏感字段
                    filtered_body = {
                        k: "[FILTERED]" if k.lower() in {"password", "token", "card_number"} else v 
                        for k, v in body.items()
                    }
                    audit_data["request_body"] = filtered_body
                except json.JSONDecodeError:
                    audit_data["request_body"] = "[NON_JSON_DATA]"
            
            # 对于会员卡操作，记录更多详细信息
            if "members" in audit_data["path"] and "cards" in audit_data["path"] and request.method in ("POST", "PUT"):
            # 对于教练排班操作，记录更多详细信息
            if "coaches/schedules" in audit_data["path"] and request.method in ("POST", "PUT", "DELETE"):
                try:
                    body = await request.json() if request.method in ("POST", "PUT") else {}
                    audit_data["schedule_operation"] = {
                        "coach_id": body.get("coach_id") if request.method in ("POST", "PUT") else None,
                        "start_time": body.get("start_time") if request.method in ("POST", "PUT") else None,
                        "end_time": body.get("end_time") if request.method in ("POST", "PUT") else None,
                        "action": "create" if request.method == "POST" else "update" if request.method == "PUT" else "delete"
                    }
                except json.JSONDecodeError:
                    audit_data["schedule_operation"] = "[NON_JSON_DATA]"
            # 对于课程预约操作，记录更多详细信息
            if "bookings" in audit_data["path"] and request.method in ("POST", "DELETE"):
                try:
                    body = await request.json() if request.method == "POST" else {}
                    audit_data["booking_operation"] = {
                        "member_id": body.get("member_id") if request.method == "POST" else None,
                        "schedule_id": body.get("schedule_id") if request.method == "POST" else None,
                        "action": "create" if request.method == "POST" else "cancel"
                    }
                except json.JSONDecodeError:
                    audit_data["booking_operation"] = "[NON_JSON_DATA]"
                try:
                    body = await request.json()
                    audit_data["card_operation"] = {
                        "card_number": body.get("card_number", "")[:6] + "****" if body.get("card_number") else None,
                        "action": "create" if request.method == "POST" else "update",
                        "member_id": body.get("member_id")
                    }
                except json.JSONDecodeError:
                    audit_data["card_operation"] = "[NON_JSON_DATA]"
            
            # 处理请求
            response = await call_next(request)
            
            # 记录响应信息
            audit_data.update({
                "status_code": response.status_code,
                "response_size": len(response.body) if hasattr(response, "body") else 0,
            })
            
            # 将审计日志写入数据库
            db = next(get_db())
            try:
                db_log = AuditLog(
                    timestamp=datetime.utcnow(),
                    method=audit_data["method"],
                    path=audit_data["path"],
                    client_ip=audit_data["client_ip"],
                    user_agent=audit_data["user_agent"],
                    status_code=audit_data["status_code"],
                    request_body=json.dumps(audit_data.get("request_body", {})),
                    response_size=audit_data["response_size"],
                    user_id=audit_data.get("user_id"),
                    action_type="member_operation" if "members" in audit_data["path"] and "cards" not in audit_data["path"] else "member_card_operation" if "members" in audit_data["path"] and "cards" in audit_data["path"] else "course_booking" if "bookings" in audit_data["path"] else "coach_schedule" if "coaches/schedules" in audit_data["path"] else "payment_operation" if "payments" in audit_data["path"] else "other_operation"
                )
                db.add(db_log)
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"Failed to save audit log: {str(e)}")
            finally:
                db.close()
            
            return response
            
        except HTTPException as http_exc:
            # 处理HTTP异常
            raise http_exc
        except Exception as exc:
            # 处理其他异常
            raise HTTPException(
                status_code=500, 
                detail=f"Internal Server Error: {str(exc)}"
            )

# 中间件使用示例（需要在main.py中注册）
# app.add_middleware(AuditMiddleware)