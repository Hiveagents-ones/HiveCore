import json
from fastapi import Request, Response
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import AuditLog

class AuditMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next):
        # 审计会员和课程相关的增删改操作
        if ("/api/v1/members" in request.url.path or "/api/v1/courses" in request.url.path) and request.method in ["POST", "PUT", "DELETE"]:
            # 获取请求体
            body = await request.body()
            try:
                body_data = json.loads(body.decode()) if body else {}
            except json.JSONDecodeError:
                body_data = {}

            # 获取用户ID（从请求头或认证信息中获取）
            user_id = request.headers.get("X-User-ID")
            if not user_id:
                # 如果没有X-User-ID，尝试从JWT token或其他认证方式获取
                # 这里简化处理，实际应该从认证中间件获取
                user_id = "anonymous"
            
            # 获取请求路径中的ID（用于PUT和DELETE操作）
            path_id = None
            if request.method in ["PUT", "DELETE"]:
                path_parts = request.url.path.split("/")
                if len(path_parts) >= 5 and path_parts[4].isdigit():
                    path_id = int(path_parts[4])

            # 执行请求
            response = await call_next(request)

            # 记录审计日志
            if response.status_code in [200, 201, 204]:
                # 对于PUT和DELETE操作，需要获取旧值
                old_values = None
                if request.method in ["PUT", "DELETE"]:
                    db = next(get_db())
                    table_name = "members" if "/api/v1/members" in request.url.path else "courses"
                    record_id = path_id or body_data.get("id")
                    
                    # 从数据库获取旧值
                    if table_name == "members":
                        from ..models import Member
                        old_record = db.query(Member).filter(Member.id == record_id).first()
                    else:
                        from ..models import Course
                        old_record = db.query(Course).filter(Course.id == record_id).first()
                    
                    if old_record:
                        old_values = json.dumps({
                            "name": old_record.name,
                            "coach": getattr(old_record, "coach", None),
                            "time": getattr(old_record, "time", None),
                            "location": getattr(old_record, "location", None),
                            "capacity": getattr(old_record, "capacity", None),
                            "description": getattr(old_record, "description", None)
                        })
                    
                    await self.log_audit(
                        db=db,
                        action=request.method,
                        table_name=table_name,
                        record_id=record_id,
                        old_values=old_values,
                        new_values=json.dumps(body_data) if body_data else None,
                        user_id=user_id
                    )
                else:
                    # POST操作
                    await self.log_audit(
                        db=next(get_db()),
                        action=request.method,
                        table_name="members" if "/api/v1/members" in request.url.path else "courses",
                        record_id=body_data.get("id"),
                        old_values=None,
                        new_values=json.dumps(body_data) if body_data else None,
                        user_id=user_id
                    )

            return response

        # 非会员相关操作直接放行
        return await call_next(request)

    async def log_audit(
        self,
        db: Session,
        action: str,
        table_name: str,
        record_id: int,
        old_values: str = None,
        new_values: str = None,
        user_id: str = None
    ):
        """记录审计日志到数据库"""
        try:
            audit_log = AuditLog(
                action=action,
                table_name=table_name,
                record_id=record_id,
                old_values=old_values,
                new_values=new_values,
                user_id=user_id
            )
            db.add(audit_log)
            db.commit()
            db.refresh(audit_log)
        except Exception as e:
            db.rollback()
            # 记录错误日志但不影响主流程
            print(f"Failed to log audit: {str(e)}")
