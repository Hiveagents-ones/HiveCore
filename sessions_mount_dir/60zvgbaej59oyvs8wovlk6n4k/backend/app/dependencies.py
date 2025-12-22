from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from .models import get_db, Member
from .security import get_current_active_member

from datetime import datetime, timedelta

def get_database() -> Generator[Session, None, None]:
    """获取数据库会话"""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

def get_current_user(
    token: str,
    db: Session = Depends(get_database)
) -> Member:
    """获取当前用户（用于认证中间件）"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        member = get_current_active_member(token, db)
        if not member.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return member
    except HTTPException as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

def get_optional_current_user(
    token: Optional[str] = None,
    db: Session = Depends(get_database)
) -> Optional[Member]:
    """获取可选的当前用户（用于不需要认证的端点）"""
    if not token:
        return None
    try:
        return get_current_active_member(token, db)
    except HTTPException:
        return None

def require_min_level(min_level: str):
    """装饰器工厂：要求会员达到最低等级"""
    def dependency(
        current_member: Member = Depends(get_current_user)
    ) -> Member:
        level_hierarchy = {
            "bronze": 1,
            "silver": 2,
            "gold": 3,
            "platinum": 4,
            "diamond": 5
        }
        
        member_level = level_hierarchy.get(current_member.level.lower(), 0)
        required_level = level_hierarchy.get(min_level.lower(), 0)
        
        if member_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {min_level} level or higher"
            )
        return current_member
    return dependency

def get_admin_user(
    current_member: Member = Depends(get_current_user)
) -> Member:
    """获取管理员用户（需要diamond等级）"""
    return require_min_level("diamond")(current_member)


def check_membership_expiry(
    current_member: Member = Depends(get_current_user)
) -> Member:
    """检查会员会籍是否过期"""
    if current_member.membership_expiry and current_member.membership_expiry < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Membership has expired"
        )
    return current_member

def get_member_profile(
    member_id: int,
    db: Session = Depends(get_database),
    current_member: Member = Depends(get_current_user)
) -> Member:
    """获取会员资料（仅限本人或管理员）"""
    if current_member.id != member_id and current_member.level.lower() != "diamond":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this profile"
        )
    
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    return member