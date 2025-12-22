from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ....crud import (
    create_member,
    delete_member,
    get_member,
    get_member_by_card_number,
    get_member_by_phone,
    get_members,
    update_member,
)
from ....dependencies import get_database, get_admin_user
from ....schemas import Member, MemberCreate, MemberUpdate

router = APIRouter()


@router.post("/", response_model=Member, status_code=status.HTTP_201_CREATED)
def create_member_endpoint(
    member: MemberCreate,
    db: Session = Depends(get_database),
    _admin: Member = Depends(get_admin_user),
):
    """
    创建新会员
    - **name**: 会员姓名
    - **phone**: 手机号码
    - **card_number**: 会员卡号
    - **level**: 会员等级 (basic, bronze, silver, gold, platinum, diamond)
    - **remaining_months**: 剩余会籍时长（月）
    - **is_active**: 是否激活
    """
    # 检查手机号是否已存在
    db_member_by_phone = get_member_by_phone(db, phone=member.phone)
    if db_member_by_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered",
        )
    # 检查会员卡号是否已存在
    db_member_by_card = get_member_by_card_number(db, card_number=member.card_number)
    if db_member_by_card:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Card number already registered",
        )
    return create_member(db=db, member=member)


@router.get("/", response_model=List[Member])
def read_members(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_database),
    _admin: Member = Depends(get_admin_user),
):
    """
    获取会员列表
    - **skip**: 跳过的记录数
    - **limit**: 返回的最大记录数
    """
    members = get_members(db, skip=skip, limit=limit)
    return members


@router.get("/{member_id}", response_model=Member)
def read_member(
    member_id: int,
    db: Session = Depends(get_database),
    _admin: Member = Depends(get_admin_user),
):
    """
    获取单个会员信息
    - **member_id**: 会员ID
    """
    db_member = get_member(db, member_id=member_id)
    if db_member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return db_member


@router.put("/{member_id}", response_model=Member)
def update_member_endpoint(
    member_id: int,
    member: MemberUpdate,
    db: Session = Depends(get_database),
    _admin: Member = Depends(get_admin_user),
):
    """
    更新会员信息
    - **member_id**: 会员ID
    - **name**: 会员姓名 (可选)
    - **phone**: 手机号码 (可选)
    - **card_number**: 会员卡号 (可选)
    - **level**: 会员等级 (可选)
    - **remaining_months**: 剩余会籍时长（月） (可选)
    - **is_active**: 是否激活 (可选)
    """
    db_member = update_member(db, member_id=member_id, member=member)
    if db_member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return db_member


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member_endpoint(
    member_id: int,
    db: Session = Depends(get_database),
    _admin: Member = Depends(get_admin_user),
):
    """
    删除会员
    - **member_id**: 会员ID
    """
    success = delete_member(db, member_id=member_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return None
