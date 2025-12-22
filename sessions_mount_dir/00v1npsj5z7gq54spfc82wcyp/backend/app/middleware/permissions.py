from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Callable, Awaitable
from functools import wraps

class PermissionMiddleware:
    """
    细粒度权限控制中间件
    根据用户角色和请求方法/路径进行权限验证
    """
    
    # 权限映射表
    PERMISSION_MAP = {
        "admin": {
            "GET": ["/api/v1/members", "/api/v1/courses", "/api/v1/coaches/schedule", "/api/v1/payments", "/api/v1/reports"],
            "POST": ["/api/v1/members", "/api/v1/courses/book", "/api/v1/coaches/schedule", "/api/v1/payments"],
            "PUT": ["/api/v1/members", "/api/v1/coaches/schedule"],
            "DELETE": ["/api/v1/members", "/api/v1/courses/book", "/api/v1/coaches/schedule"]
        },
        "staff": {
            "GET": ["/api/v1/members", "/api/v1/courses", "/api/v1/coaches/schedule"],
            "POST": ["/api/v1/members", "/api/v1/courses/book"],
            "PUT": ["/api/v1/members"],
            "DELETE": []
        },
        "member": {
            "GET": ["/api/v1/members", "/api/v1/courses"],
            "POST": ["/api/v1/courses/book"],
            "PUT": [],
            "DELETE": ["/api/v1/courses/book"]
        }
    }

    @classmethod
    def check_permission(cls, role: str, method: str, path: str) -> bool:
        """
        检查用户是否有权限访问指定路径
        :param role: 用户角色
        :param method: HTTP方法
        :param path: 请求路径
        :return: 是否有权限
        """
        if role not in cls.PERMISSION_MAP:
            return False
            
        allowed_paths = cls.PERMISSION_MAP[role].get(method, [])
        
        # 检查精确匹配或前缀匹配
        for allowed_path in allowed_paths:
            if path == allowed_path or path.startswith(allowed_path + '/'):
                return True
        
        return False

    @classmethod
    def middleware(cls, request: Request, call_next: Callable[[Request], Awaitable[JSONResponse]]) -> JSONResponse:
        """
        权限中间件主逻辑
        """
        # 从请求头或JWT中获取用户角色 (示例中简化处理)
        role = request.headers.get("X-User-Role", "member")
        
        # 检查权限
        if not cls.check_permission(role, request.method, request.url.path):
            raise HTTPException(
                status_code=403,
                detail="Permission denied"
            )
        
        return call_next(request)

    @classmethod
    def permission_required(cls, role: str = None):
        """
        装饰器版本权限检查
        :param role: 要求的角色
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                request = kwargs.get("request")
                if not request:
                    for arg in args:
                        if isinstance(arg, Request):
                            request = arg
                            break
                
                if not request:
                    raise HTTPException(status_code=500, detail="Request object not found")
                
                user_role = request.headers.get("X-User-Role", "member")
                
                # 如果指定了角色，检查是否匹配
                if role and user_role != role:
                    raise HTTPException(status_code=403, detail=f"Require {role} role")
                
                # 检查权限
                if not cls.check_permission(user_role, request.method, request.url.path):
                    raise HTTPException(status_code=403, detail="Permission denied")
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator