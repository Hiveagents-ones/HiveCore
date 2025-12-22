from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
import redis
import logging

from ..models.user import User
from ..models.membership import Membership
from ..core.database import get_db
from ..core.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()
redis_client = redis.Redis.from_url(settings.REDIS_URL)

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# RBAC权限定义
class Permission:
    VIEW_MEMBERSHIP = "view_membership"
    RENEW_MEMBERSHIP = "renew_membership"
    PROCESS_PAYMENT = "process_payment"
    VIEW_PAYMENT_HISTORY = "view_payment_history"
    ADMIN_PANEL = "admin_panel"

# 角色权限映射
ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "user": [
        Permission.VIEW_MEMBERSHIP,
        Permission.RENEW_MEMBERSHIP,
        Permission.PROCESS_PAYMENT,
        Permission.VIEW_PAYMENT_HISTORY,
    ],
    "admin": [
        Permission.VIEW_MEMBERSHIP,
        Permission.RENEW_MEMBERSHIP,
        Permission.PROCESS_PAYMENT,
        Permission.VIEW_PAYMENT_HISTORY,
        Permission.ADMIN_PANEL,
    ],
}

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db)
) -> User:
    username = token_data.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def check_permission(permission: str):
    def permission_checker(
        current_user: User = Depends(get_current_user)
    ):
        user_permissions = ROLE_PERMISSIONS.get(current_user.role, [])
        if permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        return current_user
    return permission_checker

def check_minor_payment_limit(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    检查未成年人支付限制
    - 未满18岁用户每日支付限额为100元
    - 未满16岁用户每日支付限额为50元
    """
    if current_user.age is None:
        logger.warning(f"User {current_user.id} age not set, allowing payment")
        return current_user
    
    today = datetime.utcnow().date()
    cache_key = f"payment_limit:{current_user.id}:{today}"
    
    # 获取今日已支付金额
    today_paid = redis_client.get(cache_key)
    if today_paid:
        today_paid = float(today_paid)
    else:
        # 从数据库计算今日支付金额
        from ..models.payment import Payment
        today_paid = db.query(Payment).filter(
            Payment.user_id == current_user.id,
            Payment.status == "success",
            Payment.created_at >= today
        ).with_entities(Payment.amount).all()
        today_paid = sum(p.amount for p in today_paid) if today_paid else 0.0
        redis_client.setex(cache_key, 86400, str(today_paid))
    
    # 设置支付限额
    if current_user.age < 16:
        daily_limit = 50.0
    elif current_user.age < 18:
        daily_limit = 100.0
    else:
        return current_user  # 成年人无限制
    
    if today_paid >= daily_limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Daily payment limit of ¥{daily_limit} exceeded for minors",
        )
    
    return current_user

def update_payment_limit(user_id: int, amount: float):
    """
    更新用户今日支付限额
    """
    today = datetime.utcnow().date()
    cache_key = f"payment_limit:{user_id}:{today}"
    
    # 原子性增加已支付金额
    pipe = redis_client.pipeline()
    pipe.incrbyfloat(cache_key, amount)
    pipe.expire(cache_key, 86400)
    pipe.execute()

def require_membership(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    检查用户是否为有效会员
    """
    membership = db.query(Membership).filter(
        Membership.user_id == current_user.id,
        Membership.status == "active",
        Membership.end_date > datetime.utcnow()
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active membership required",
        )
    
    return current_user

def get_user_permissions(user: User) -> List[str]:
    """
    获取用户权限列表
    """
    return ROLE_PERMISSIONS.get(user.role, [])

def has_permission(user: User, permission: str) -> bool:
    """
    检查用户是否具有特定权限
    """
    return permission in get_user_permissions(user)

# 中间件工厂函数
def create_permission_middleware(required_permissions: List[str]):
    """
    创建需要多个权限的中间件
    """
    def multi_permission_checker(
        current_user: User = Depends(get_current_user)
    ):
        user_permissions = get_user_permissions(current_user)
        missing_permissions = [p for p in required_permissions if p not in user_permissions]
        
        if missing_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {', '.join(missing_permissions)}",
            )
        
        return current_user
    
    return multi_permission_checker

# 速率限制装饰器
def rate_limit(max_requests: int, window_seconds: int):
    """
    基于Redis的速率限制
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 从kwargs中获取current_user
            current_user = kwargs.get('current_user')
            if not current_user:
                return func(*args, **kwargs)
            
            key = f"rate_limit:{current_user.id}:{func.__name__}"
            
            # 使用滑动窗口算法
            now = datetime.utcnow().timestamp()
            window_start = now - window_seconds
            
            # 清理过期记录
            redis_client.zremrangebyscore(key, 0, window_start)
            
            # 检查当前窗口内的请求数
            current_requests = redis_client.zcard(key)
            
            if current_requests >= max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                )
            
            # 记录当前请求
            redis_client.zadd(key, {str(now): now})
            redis_client.expire(key, window_seconds)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator