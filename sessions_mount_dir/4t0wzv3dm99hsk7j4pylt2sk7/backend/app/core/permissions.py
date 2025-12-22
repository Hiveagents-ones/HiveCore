from typing import List, Dict, Set, Optional
from functools import wraps
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime

class Permission:
    def __init__(self, name: str, resource: str, action: str):
        self.name = name
        self.resource = resource
        self.action = action
    
    def __str__(self):
        return f"{self.resource}:{self.action}"

class Role:
    def __init__(self, name: str, permissions: List[Permission]):
        self.name = name
        self.permissions = set(permissions)
    
    def has_permission(self, permission: Permission) -> bool:
        return permission in self.permissions

class RBAC:
    def __init__(self):
        self.roles: Dict[str, Role] = {}
        self.user_roles: Dict[str, str] = {}
        
        # 初始化默认角色
        self._init_default_roles()
    
    def _init_default_roles(self):
        # 管理员角色
        admin_perms = [
            Permission("manage_members", "members", "*"),
            Permission("manage_courses", "courses", "*"),
            Permission("manage_payments", "payments", "*"),
            Permission("view_reports", "reports", "*"),
            Permission("manage_roles", "roles", "*")
        ]
        self.roles["admin"] = Role("admin", admin_perms)
        
        # 分析师角色
        analyst_perms = [
            Permission("view_reports", "reports", "view"),
            Permission("view_reports", "reports", "export"),
            Permission("view_members", "members", "view")
        ]
        self.roles["analyst"] = Role("analyst", analyst_perms)
        
        # 普通员工角色
        employee_perms = [
            Permission("view_members", "members", "view"),
            Permission("view_courses", "courses", "view")
        ]
        self.roles["employee"] = Role("employee", employee_perms)
    
    def add_role(self, role: Role) -> None:
        self.roles[role.name] = role
    
    def assign_role(self, user_id: str, role_name: str) -> None:
        if role_name in self.roles:
            self.user_roles[user_id] = role_name
    
    def get_user_role(self, user_id: str) -> Optional[Role]:
        role_name = self.user_roles.get(user_id)
        if role_name:
            return self.roles.get(role_name)
        return None
    
    def check_permission(self, user_id: str, permission: Permission) -> bool:
        role = self.get_user_role(user_id)
        if not role:
            return False
        return role.has_permission(permission)
    
    def check_resource_permission(self, user_id: str, resource: str, action: str) -> bool:
        permission = Permission("", resource, action)
        return self.check_permission(user_id, permission)

rbac = RBAC()
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = security):
    try:
        payload = jwt.decode(credentials.credentials, "SECRET_KEY", algorithms=["HS256"])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_permission(resource: str, action: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            request = kwargs.get('request')
            if not request:
                raise HTTPException(status_code=500, detail="Request object not found")
            
            # 从请求头获取token
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                raise HTTPException(status_code=401, detail="Authorization header missing")
            
            try:
                token = auth_header.split(' ')[1]
                payload = jwt.decode(token, "SECRET_KEY", algorithms=["HS256"])
                user_id = payload.get("sub")
                
                if not rbac.check_resource_permission(user_id, resource, action):
                    raise HTTPException(status_code=403, detail="Insufficient permissions")
                
                kwargs['current_user'] = user_id
                return func(*args, **kwargs)
            except (jwt.PyJWTError, IndexError):
                raise HTTPException(status_code=401, detail="Invalid token")
        return wrapper
    return decorator

def permission_middleware(request: Request, call_next):
    # 记录API访问
    path = request.url.path
    method = request.method
    
    # 需要权限检查的路径
    protected_paths = {
        "/api/v1/reports": "reports:view",
        "/api/v1/members": "members:view",
        "/api/v1/courses": "courses:view",
        "/api/v1/payments": "payments:view"
    }
    
    # 检查权限
    for protected_path, permission in protected_paths.items():
        if path.startswith(protected_path):
            auth_header = request.headers.get('Authorization')
            if auth_header:
                try:
                    token = auth_header.split(' ')[1]
                    payload = jwt.decode(token, "SECRET_KEY", algorithms=["HS256"])
                    user_id = payload.get("sub")
                    resource, action = permission.split(':')
                    
                    if not rbac.check_resource_permission(user_id, resource, action):
                        from fastapi import HTTPException
                        raise HTTPException(status_code=403, detail="Insufficient permissions")
                except (jwt.PyJWTError, IndexError):
                    from fastapi import HTTPException
                    raise HTTPException(status_code=401, detail="Invalid token")
            break
    
    response = call_next(request)
    return response
