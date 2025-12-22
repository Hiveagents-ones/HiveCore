from sqlalchemy.orm import Session
from typing import List, Optional
from ..models.member import Member
from ..schemas.member import MemberCreate, MemberUpdate

def get_member(db: Session, member_id: int, include_deleted: bool = False) -> Optional[Member]:
    """根据ID获取单个会员"""
    query = db.query(Member).filter(Member.id == member_id)
    if not include_deleted:
        query = query.filter(Member.is_deleted == False)
    return query.first()

def get_member_by_phone(db: Session, phone: str, include_deleted: bool = False) -> Optional[Member]:
    """根据手机号获取会员"""
    query = db.query(Member).filter(Member.phone == phone)
    if not include_deleted:
        query = query.filter(Member.is_deleted == False)
    return query.first()

def get_members(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    level: Optional[str] = None,
    is_active: Optional[bool] = None
) -> List[Member]:
    """获取会员列表"""
    query = db.query(Member)
    
    if level:
        query = query.filter(Member.level == level)
    
    if is_active is not None:
        query = query.filter(Member.is_active == is_active)
    
    return query.offset(skip).limit(limit).all()

def create_member(db: Session, member: MemberCreate) -> Member:
    """创建新会员"""
    db_member = Member(
        name=member.name,
        phone=member.phone,
        email=member.email,
        level=member.level,
        points=member.points,
        remaining_membership=member.remaining_membership,
        notes=member.notes
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member

def update_member(db: Session, member_id: int, member: MemberUpdate) -> Optional[Member]:
    """更新会员信息"""
    db_member = db.query(Member).filter(Member.id == member_id).first()
    if db_member:
        update_data = member.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_member, field, value)
        db.commit()
        db.refresh(db_member)
    return db_member

def delete_member(db: Session, member_id: int) -> Optional[Member]:
    """软删除会员"""
    db_member = db.query(Member).filter(Member.id == member_id).first()
    if db_member:
        db_member.is_active = False
        db_member.is_deleted = True
        db.commit()
        db.refresh(db_member)
    return db_member

def deactivate_member(db: Session, member_id: int) -> Optional[Member]:
    """停用会员"""
    db_member = db.query(Member).filter(Member.id == member_id).first()
    if db_member:
        db_member.is_active = False
        db.commit()
        db.refresh(db_member)
    return db_member

def activate_member(db: Session, member_id: int) -> Optional[Member]:
    """激活会员"""
    db_member = db.query(Member).filter(Member.id == member_id).first()
    if db_member:
        db_member.is_active = True
        db.commit()
        db.refresh(db_member)
    return db_member

def update_membership(db: Session, member_id: int, months: int) -> Optional[Member]:
    """更新会员会籍"""
    db_member = db.query(Member).filter(Member.id == member_id).first()
    if db_member:
        db_member.remaining_membership += months
        db.commit()
        db.refresh(db_member)
    return db_member

def add_points(db: Session, member_id: int, points: int) -> Optional[Member]:
    """增加会员积分"""
    db_member = db.query(Member).filter(Member.id == member_id).first()
    if db_member:
        db_member.points += points
        db.commit()
        db.refresh(db_member)
    return db_member

def deduct_points(db: Session, member_id: int, points: int) -> Optional[Member]:
    """扣除会员积分"""
    db_member = db.query(Member).filter(Member.id == member_id).first()
    if db_member and db_member.points >= points:
        db_member.points -= points
        db.commit()
        db.refresh(db_member)
    return db_member
