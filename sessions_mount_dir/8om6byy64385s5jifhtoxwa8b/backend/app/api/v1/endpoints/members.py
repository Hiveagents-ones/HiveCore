from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ....database import get_db
from ....crud.member import MemberCRUD
from ....schemas.member import (
    MemberCreate,
    MemberUpdate,
    MemberResponse,
    MemberListResponse,
    MemberQuery
)

router = APIRouter()

@router.post("/", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
def create_member(
    member_data: MemberCreate,
    db: Session = Depends(get_db)
):
    """创建新会员"""
    crud = MemberCRUD(db)
    return crud.create_member(member_data)

@router.get("/{member_id}", response_model=MemberResponse)
def get_member(
    member_id: int,
    db: Session = Depends(get_db)
):
    """获取单个会员信息"""
    crud = MemberCRUD(db)
    member = crud.get_member_by_id(member_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    return member

@router.put("/{member_id}", response_model=MemberResponse)
def update_member(
    member_id: int,
    member_data: MemberUpdate,
    db: Session = Depends(get_db)
):
    """更新会员信息"""
    crud = MemberCRUD(db)
    return crud.update_member(member_id, member_data)

@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    member_id: int,
    db: Session = Depends(get_db)
):
    """注销会员"""
    crud = MemberCRUD(db)
    success = crud.delete_member(member_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

@router.get("/", response_model=MemberListResponse)
def list_members(
    name: Optional[str] = Query(None, description="会员姓名"),
    phone: Optional[str] = Query(None, description="手机号码"),
    email: Optional[str] = Query(None, description="电子邮箱"),
    member_card_number: Optional[str] = Query(None, description="会员卡号"),
    member_level: Optional[str] = Query(None, regex="^(basic|silver|gold|platinum)$", description="会员等级"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db)
):
    """查询会员列表"""
    query = MemberQuery(
        name=name,
        phone=phone,
        email=email,
        member_card_number=member_card_number,
        member_level=member_level,
        is_active=is_active,
        page=page,
        size=size
    )
    crud = MemberCRUD(db)
    return crud.get_members(query)
