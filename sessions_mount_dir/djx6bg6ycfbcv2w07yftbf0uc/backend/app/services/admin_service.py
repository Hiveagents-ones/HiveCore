from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from ..models.user import User
from ..schemas.admin_users import UserListResponse, UserBanRequest, UserAppealRequest, UserAppealResponse

class AdminService:
    def __init__(self, db: Session):
        self.db = db

    def get_all_users(self, skip: int = 0, limit: int = 100) -> List[UserListResponse]:
        """获取所有用户列表"""
        users = self.db.query(User).offset(skip).limit(limit).all()
        return [UserListResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            is_banned=user.is_banned,
            created_at=user.created_at,
            last_login=user.last_login
        ) for user in users]

    def ban_user(self, user_id: int, ban_request: UserBanRequest) -> bool:
        """封禁用户"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.is_banned = True
        user.ban_reason = ban_request.reason
        user.banned_at = ban_request.banned_at
        self.db.commit()
        return True

    def unban_user(self, user_id: int) -> bool:
        """解封用户"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.is_banned = False
        user.ban_reason = None
        user.banned_at = None
        self.db.commit()
        return True

    def handle_appeal(self, appeal_request: UserAppealRequest) -> UserAppealResponse:
        """处理用户申诉"""
        user = self.db.query(User).filter(User.id == appeal_request.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if appeal_request.action == "unban":
            user.is_banned = False
            user.ban_reason = None
            user.banned_at = None
            message = "User has been unbanned successfully"
        else:
            message = "Appeal has been rejected"
        
        self.db.commit()
        return UserAppealResponse(
            user_id=user.id,
            status="processed",
            message=message
        )

    def get_user_details(self, user_id: int) -> Optional[UserListResponse]:
        """获取用户详细信息"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        return UserListResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            is_banned=user.is_banned,
            created_at=user.created_at,
            last_login=user.last_login
        )
