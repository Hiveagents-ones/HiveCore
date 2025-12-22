from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..models import User
from ..schemas import UserRegister, UserLogin, UserResponse, UserSession
from ..utils import hash_password, verify_password
from ..database import get_db

router = APIRouter(prefix="/api/v1/users", tags=["users"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: UserRegister, db: Session = Depends(get_db)):
    """
    用户注册接口
    """
    # 检查用户名是否已存在
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 创建新用户
    hashed_password = hash_password(user.password)
    new_user = User(
        username=user.username,
        password_hash=hashed_password
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.post("/login", response_model=UserSession)
def login(user: UserLogin, db: Session = Depends(get_db)):
    """
    用户登录接口
    """
    # 查找用户
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 验证密码
    if not verify_password(user.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 生成会话令牌（这里简化处理，实际应用中应使用更安全的方式）
    session_token = hash_password(f"{user.username}{db_user.id}")
    
    return UserSession(
        session_token=session_token,
        user_id=db_user.id
    )

@router.get("/me", response_model=UserResponse)
def get_current_user(current_user: User = Depends(get_current_user)):
    """
    获取当前用户信息
    """
    return current_user

def get_current_user(session_token: str, db: Session = Depends(get_db)):
    """
    根据会话令牌获取当前用户
    """
    # 这里简化处理，实际应用中应从请求头中获取令牌
    # 并验证令牌的有效性
    # 这里仅作为示例，实际实现可能需要更复杂的逻辑
    return None
