from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from ....db.session import get_db
from ....models.member import Member
from ....schemas.member import (
    MemberCreate,
    MemberUpdate,
    MemberResponse,
    MemberListResponse,
    MemberQuery
)
from ....core.security import get_current_user

router = APIRouter()


@router.post("/", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
def create_member(
    member: MemberCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    创建新会员
    """
    # 检查手机号是否已存在
    existing_member = db.query(Member).filter(Member.phone_number == member.phone_number).first()
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="手机号已存在"
        )
    
    # 检查身份证号是否已存在
    existing_member = db.query(Member).filter(Member.id_card_number == member.id_card_number).first()
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="身份证号已存在"
        )
    
    db_member = Member(**member.dict())
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member


@router.get("/", response_model=MemberListResponse)
def list_members(
    name: str = Query(None, description="按姓名查询"),
    phone_number: str = Query(None, description="按手机号查询"),
    id_card_number: str = Query(None, description="按身份证号查询"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取会员列表
    """
    query = db.query(Member)
    
    if name:
        query = query.filter(Member.name.ilike(f"%{name}%"))
    if phone_number:
        query = query.filter(Member.phone_number == phone_number)
    if id_card_number:
        query = query.filter(Member.id_card_number == id_card_number)
    
    total = query.count()
    members = query.offset((page - 1) * size).limit(size).all()
    
    return MemberListResponse(
        members=members,
        total=total,
        page=page,
        size=size
    )


@router.get("/{member_id}", response_model=MemberResponse)
def get_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取单个会员详情
    """
    member = db.query(Member).filter(Member.id == member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会员不存在"
        )
    return member


@router.put("/{member_id}", response_model=MemberResponse)
def update_member(
    member_id: int,
    member_update: MemberUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    更新会员信息
    """
    db_member = db.query(Member).filter(Member.id == member_id).first()
    if not db_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会员不存在"
        )
    
    update_data = member_update.dict(exclude_unset=True)
    
    # 检查手机号是否已被其他会员使用
    if "phone_number" in update_data:
        existing_member = db.query(Member).filter(
            Member.phone_number == update_data["phone_number"],
            Member.id != member_id
        ).first()
        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="手机号已被其他会员使用"
            )
    
    # 检查身份证号是否已被其他会员使用
    if "id_card_number" in update_data:
        existing_member = db.query(Member).filter(
            Member.id_card_number == update_data["id_card_number"],
            Member.id != member_id
        ).first()
        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="身份证号已被其他会员使用"
            )
    
    for field, value in update_data.items():
        setattr(db_member, field, value)
    
    db.commit()
    db.refresh(db_member)
    return db_member


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    删除会员
    """
    db_member = db.query(Member).filter(Member.id == member_id).first()
    if not db_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会员不存在"
        )
    
    db.delete(db_member)
    db.commit()
    return None
