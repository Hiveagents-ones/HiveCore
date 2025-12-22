from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .models import Member, get_db

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2密码流
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# JWT配置
SECRET_KEY = "your-secret-key-here"  # 在生产环境中应使用环境变量
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    return pwd_context.hash(password)

def authenticate_member(db: Session, card_number: str, password: str) -> Optional[Member]:
    """验证会员身份"""
    member = db.query(Member).filter(Member.card_number == card_number).first()
    if not member:
        return None
    if not verify_password(password, member.hashed_password):
        return None
    return member

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_member(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Member:
    """获取当前会员"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        card_number: str = payload.get("sub")
        if card_number is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    member = db.query(Member).filter(Member.card_number == card_number).first()
    if member is None:
        raise credentials_exception
    return member

def get_current_active_member(current_member: Member = Depends(get_current_member)) -> Member:
    """获取当前活跃会员"""
    if not current_member.is_active:
        raise HTTPException(status_code=400, detail="Inactive member")
    return current_member

def check_member_permission(current_member: Member, required_level: str) -> bool:
    """检查会员权限"""
    level_hierarchy = {
        "bronze": 1,
        "silver": 2,
        "gold": 3,
        "platinum": 4,
        "diamond": 5
    }
    
    member_level = level_hierarchy.get(current_member.level.lower(), 0)
    required_level_value = level_hierarchy.get(required_level.lower(), 0)
    
    return member_level >= required_level_value

def require_permission(required_level: str):
    """权限装饰器"""
    def permission_checker(current_member: Member = Depends(get_current_active_member)):
        if not check_member_permission(current_member, required_level):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_member
    return permission_checker

def encrypt_sensitive_data(data: str) -> str:
    """加密敏感数据"""
    # 这里应该实现实际的加密逻辑
    # 示例中使用简单的Base64编码，生产环境应使用更强的加密
    import base64
    encoded_bytes = base64.b64encode(data.encode("utf-8"))
    return encoded_bytes.decode("utf-8")

def decrypt_sensitive_data(encrypted_data: str) -> str:
    """解密敏感数据"""
    # 这里应该实现实际的解密逻辑
    import base64
    decoded_bytes = base64.b64decode(encrypted_data.encode("utf-8"))
    return decoded_bytes.decode("utf-8")
