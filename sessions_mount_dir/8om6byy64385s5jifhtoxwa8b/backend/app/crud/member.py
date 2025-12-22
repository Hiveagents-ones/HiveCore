from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from fastapi import HTTPException, status
from datetime import datetime

from ..models.member import Member
from ..schemas.member import MemberCreate, MemberUpdate, MemberQuery

class MemberCRUD:
    def __init__(self, db: Session):
        self.db = db

    def get_member_by_id(self, member_id: int) -> Optional[Member]:
        """根据ID获取会员信息"""
        return self.db.query(Member).filter(Member.id == member_id).first()

    def get_member_by_card_number(self, card_number: str) -> Optional[Member]:
        """根据会员卡号获取会员信息"""
        return self.db.query(Member).filter(Member.member_card_number == card_number).first()

    def get_member_by_phone(self, phone: str) -> Optional[Member]:
        """根据手机号获取会员信息"""
        return self.db.query(Member).filter(Member.phone == phone).first()

    def create_member(self, member_data: MemberCreate) -> Member:
        """创建新会员"""
        # 检查会员卡号是否已存在
        if self.get_member_by_card_number(member_data.member_card_number):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Member card number already exists"
            )
        
        # 检查手机号是否已存在
        if self.get_member_by_phone(member_data.phone):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already exists"
            )

        db_member = Member(**member_data.dict())
        self.db.add(db_member)
        self.db.commit()
        self.db.refresh(db_member)
        return db_member

    def update_member(self, member_id: int, member_data: MemberUpdate) -> Member:
        """更新会员信息"""
        db_member = self.get_member_by_id(member_id)
        if not db_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )

        update_data = member_data.dict(exclude_unset=True)
        
        # 如果更新手机号，检查是否已存在
        if 'phone' in update_data:
            existing_member = self.get_member_by_phone(update_data['phone'])
            if existing_member and existing_member.id != member_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already exists"
                )

        # 如果更新会员卡号，检查是否已存在
        if 'member_card_number' in update_data:
            existing_member = self.get_member_by_card_number(update_data['member_card_number'])
            if existing_member and existing_member.id != member_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Member card number already exists"
                )

        for field, value in update_data.items():
            setattr(db_member, field, value)

        self.db.commit()
        self.db.refresh(db_member)
        return db_member

    def delete_member(self, member_id: int) -> bool:
        """删除会员（软删除）"""
        db_member = self.get_member_by_id(member_id)
        if not db_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )

        db_member.is_active = False
        self.db.commit()
        return True

    def get_members(self, query: MemberQuery) -> tuple[List[Member], int]:
        """获取会员列表（支持分页和筛选）"""
        db_query = self.db.query(Member)

        # 构建筛选条件
        filters = []
        
        if query.name:
            filters.append(Member.name.ilike(f"%{query.name}%"))
        
        if query.phone:
            filters.append(Member.phone.ilike(f"%{query.phone}%"))
        
        if query.email:
            filters.append(Member.email.ilike(f"%{query.email}%"))
        
        if query.member_card_number:
            filters.append(Member.member_card_number.ilike(f"%{query.member_card_number}%"))
        
        if query.member_level:
            filters.append(Member.member_level == query.member_level)
        
        if query.is_active is not None:
            filters.append(Member.is_active == query.is_active)

        if filters:
            db_query = db_query.filter(and_(*filters))

        # 获取总数
        total = db_query.count()

        # 分页
        offset = (query.page - 1) * query.size
        members = db_query.offset(offset).limit(query.size).all()

        return members, total

    def bulk_update_member_level(self, member_ids: List[int], new_level: str) -> int:
        """批量更新会员等级"""
        if new_level not in ['basic', 'silver', 'gold', 'platinum']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid member level"
            )

        updated_count = self.db.query(Member).filter(
            Member.id.in_(member_ids)
        ).update({Member.member_level: new_level}, synchronize_session=False)
        
        self.db.commit()
        return updated_count

    def bulk_add_sessions(self, member_ids: List[int], sessions_to_add: int) -> int:
        """批量增加课时"""
        if sessions_to_add <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sessions to add must be positive"
            )

        updated_count = self.db.query(Member).filter(
            and_(Member.id.in_(member_ids), Member.is_active == True)
        ).update(
            {Member.remaining_sessions: Member.remaining_sessions + sessions_to_add},
            synchronize_session=False
        )
        
        self.db.commit()
        return updated_count

    def get_member_statistics(self) -> Dict[str, Any]:
        """获取会员统计信息"""
        stats = {
            'total_members': self.db.query(func.count(Member.id)).scalar(),
            'active_members': self.db.query(func.count(Member.id)).filter(Member.is_active == True).scalar(),
            'members_by_level': self.db.query(
                Member.member_level,
                func.count(Member.id).label('count')
            ).group_by(Member.member_level).all(),
            'expiring_soon': self.db.query(func.count(Member.id)).filter(
                and_(
                    Member.expiry_date.isnot(None),
                    Member.expiry_date <= datetime.now(),
                    Member.is_active == True
                )
        ).scalar(),
            'low_sessions': self.db.query(func.count(Member.id)).filter(
                and_(
                    Member.remaining_sessions <= 5,
                    Member.remaining_sessions > 0,
                    Member.is_active == True
                )
            ).scalar()
        }
        
        # 转换成员等级统计为字典
        stats['members_by_level'] = dict(stats['members_by_level'])
        
        return stats

    def search_members(self, keyword: str, limit: int = 10) -> List[Member]:
        """搜索会员（支持多字段模糊搜索）"""
        if not keyword or len(keyword) < 2:
            return []

        search_filter = or_(
            Member.name.ilike(f"%{keyword}%"),
            Member.phone.ilike(f"%{keyword}%"),
            Member.email.ilike(f"%{keyword}%"),
            Member.member_card_number.ilike(f"%{keyword}%")
        )

        members = self.db.query(Member).filter(
            and_(search_filter, Member.is_active == True)
        ).limit(limit).all()

        return members

    def get_expired_members(self, days: int = 30) -> List[Member]:
        """获取过期会员"""
        from datetime import timedelta
        
        expiry_threshold = datetime.now() - timedelta(days=days)
        
        members = self.db.query(Member).filter(
            and_(
                Member.expiry_date <= expiry_threshold,
                Member.is_active == True
            )
        ).all()

        return members

    def renew_membership(self, member_id: int, new_expiry_date: datetime, additional_sessions: int = 0) -> Member:
        """续费会员"""
        db_member = self.get_member_by_id(member_id)
        if not db_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )

        if new_expiry_date <= datetime.now():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New expiry date must be in the future"
            )

        db_member.expiry_date = new_expiry_date
        if additional_sessions > 0:
            db_member.remaining_sessions += additional_sessions
        
        # 确保会员是激活状态
        db_member.is_active = True
        
        self.db.commit()
        self.db.refresh(db_member)
        return db_member

# 便捷函数
def get_member_crud(db: Session) -> MemberCRUD:
    """获取会员CRUD实例"""
    return MemberCRUD(db)
