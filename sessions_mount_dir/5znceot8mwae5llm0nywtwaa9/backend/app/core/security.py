import hashlib
import hmac
import time
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta

# 配置常量
SECRET_KEY = "your-secret-key-here"  # 在生产环境中应从环境变量获取
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
NONCE_EXPIRE_SECONDS = 300  # 5分钟

# 安全实例
security = HTTPBearer()

# 存储已使用的nonce（生产环境应使用Redis等分布式存储）
used_nonces: Dict[str, float] = {}

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建JWT访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials) -> dict:
    """验证JWT令牌"""
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

def generate_signature(data: Dict[str, Any], api_key: str) -> str:
    """生成API签名"""
    # 按键排序确保一致性
    sorted_data = sorted(data.items(), key=lambda x: x[0])
    # 构建签名字符串
    sign_str = "&".join([f"{k}={v}" for k, v in sorted_data])
    # 使用HMAC-SHA256生成签名
    signature = hmac.new(
        api_key.encode("utf-8"),
        sign_str.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return signature

def verify_signature(request: Request, api_key: str) -> bool:
    """验证API签名"""
    # 获取请求头中的签名
    signature = request.headers.get("X-Signature")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing signature",
        )
    
    # 获取请求体
    body = request.body()
    if not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty request body",
        )
    
    # 解析请求体
    try:
        import json
        data = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON",
        )
    
    # 生成预期签名
    expected_signature = generate_signature(data, api_key)
    
    # 使用恒定时间比较防止时序攻击
    return hmac.compare_digest(signature, expected_signature)

def verify_nonce(request: Request) -> bool:
    """验证nonce防止重放攻击"""
    # 获取请求头中的nonce
    nonce = request.headers.get("X-Nonce")
    if not nonce:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing nonce",
        )
    
    # 获取当前时间戳
    current_time = time.time()
    
    # 检查nonce是否已使用
    if nonce in used_nonces:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nonce already used",
        )
    
    # 记录nonce使用时间
    used_nonces[nonce] = current_time
    
    # 清理过期的nonce
    expired_nonces = [
        n for n, t in used_nonces.items() 
        if current_time - t > NONCE_EXPIRE_SECONDS
    ]
    for n in expired_nonces:
        del used_nonces[n]
    
    return True

def verify_timestamp(request: Request) -> bool:
    """验证请求时间戳防止重放攻击"""
    # 获取请求头中的时间戳
    timestamp = request.headers.get("X-Timestamp")
    if not timestamp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing timestamp",
        )
    
    try:
        request_time = float(timestamp)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid timestamp format",
        )
    
    # 获取当前时间戳
    current_time = time.time()
    
    # 检查时间差是否在允许范围内（5分钟）
    if abs(current_time - request_time) > NONCE_EXPIRE_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Request timestamp too old",
        )
    
    return True

def verify_api_request(request: Request, api_key: str) -> bool:
    """综合验证API请求"""
    # 验证签名
    if not verify_signature(request, api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )
    
    # 验证nonce
    if not verify_nonce(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid nonce",
        )
    
    # 验证时间戳
    if not verify_timestamp(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid timestamp",
        )
    
    return True

def get_current_user(credentials: HTTPAuthorizationCredentials = security):
    """获取当前用户"""
    payload = verify_token(credentials)
    return payload

def hash_password(password: str) -> str:
    """密码哈希"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return hash_password(plain_password) == hashed_password
