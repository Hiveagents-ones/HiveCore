from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import date, datetime

from app.models.member import Member, MemberLevel, HealthStatus
from app.schemas.member import MemberCreate, MemberUpdate


class CRUDMember:
    def get(self, db: Session, id: int) -> Optional[Member]:
        """根据ID获取会员信息"""
        return db.query(Member).filter(Member.id == id).first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Member]:
        """获取会员列表"""
        return db.query(Member).offset(skip).limit(limit).all()

    def get_by_phone(self, db: Session, *, phone: str) -> Optional[Member]:
        """根据手机号获取会员信息"""
        return db.query(Member).filter(Member.phone == phone).first()

    def get_by_email(self, db: Session, *, email: str) -> Optional[Member]:
        """根据邮箱获取会员信息"""
        return db.query(Member).filter(Member.email == email).first()

    def get_active_members(self, db: Session) -> List[Member]:
        """获取所有活跃会员"""
        return db.query(Member).filter(
            and_(Member.is_active == True, Member.expiry_date >= date.today())
        ).all()

    def get_expired_members(self, db: Session) -> List[Member]:
        """获取所有过期会员"""
        return db.query(Member).filter(
            and_(Member.is_active == True, Member.expiry_date < date.today())
        ).all()

    def search_members(
        self, db: Session, *, query: str, skip: int = 0, limit: int = 100
    ) -> List[Member]:
        """搜索会员（按姓名、手机号、邮箱）"""
        return (
            db.query(Member)
            .filter(
                or_(
                    Member.name.ilike(f"%{query}%"),
                    Member.phone.ilike(f"%{query}%"),
                    Member.email.ilike(f"%{query}%"),
                )
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(self, db: Session, *, obj_in: MemberCreate) -> Member:
        """创建新会员"""
        db_obj = Member(
            name=obj_in.name,
            phone=obj_in.phone,
            email=obj_in.email,
            member_level=obj_in.member_level,
            join_date=obj_in.join_date,
            expiry_date=obj_in.expiry_date,
            health_status=obj_in.health_status,
            health_notes=obj_in.health_notes,
            emergency_contact=obj_in.emergency_contact,
            emergency_phone=obj_in.emergency_phone,
            is_active=obj_in.is_active,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, *, db_obj: Member, obj_in: MemberUpdate | Dict[str, Any]
    ) -> Member:
        """更新会员信息"""
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)

        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])

        db_obj.updated_at = datetime.utcnow()
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> Optional[Member]:
        """删除会员"""
        obj = db.query(Member).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

    def deactivate(self, db: Session, *, id: int) -> Optional[Member]:
        """停用会员"""
        obj = db.query(Member).get(id)
        if obj:
            obj.is_active = False
            obj.updated_at = datetime.utcnow()
            db.add(obj)
            db.commit()
            db.refresh(obj)
        return obj

    def activate(self, db: Session, *, id: int) -> Optional[Member]:
        """激活会员"""
        obj = db.query(Member).get(id)
        if obj:
            obj.is_active = True
            obj.updated_at = datetime.utcnow()
            db.add(obj)
            db.commit()
            db.refresh(obj)
        return obj

    def extend_membership(
        self, db: Session, *, id: int, days: int
    ) -> Optional[Member]:
        """延长会员资格"""
        obj = db.query(Member).get(id)
        if obj:
            if obj.expiry_date < date.today():
                obj.expiry_date = date.today()
            obj.expiry_date = date.fromordinal(
                obj.expiry_date.toordinal() + days
            )
            obj.updated_at = datetime.utcnow()
            db.add(obj)
            db.commit()
            db.refresh(obj)
        return obj

    def get_members_by_level(
        self, db: Session, *, level: MemberLevel
    ) -> List[Member]:
        """根据会员等级获取会员列表"""
        return (
            db.query(Member)
            .filter(Member.member_level == level)
            .all()
        )

    def get_members_by_health_status(
        self, db: Session, *, status: HealthStatus
    ) -> List[Member]:
        """根据健康状况获取会员列表"""
        return (
            db.query(Member)
            .filter(Member.health_status == status)
            .all()
        )

    def count_total(self, db: Session) -> int:
        """获取会员总数"""
        return db.query(Member).count()

    def count_active(self, db: Session) -> int:
        """获取活跃会员数"""
        return (
            db.query(Member)
            .filter(
                and_(Member.is_active == True, Member.expiry_date >= date.today())
            )
            .count()
        )

    def count_by_level(self, db: Session, *, level: MemberLevel) -> int:
        """根据会员等级统计会员数"""
        return (
            db.query(Member)
            .filter(Member.member_level == level)
            .count()
        )


member = CRUDMember()
