from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ....crud.member import MemberCRUD
from ....models.member import Member
from ....core.rbac import get_current_user, Permission
from ....database import get_db

router = APIRouter()

@router.post("/", response_model=dict)
def create_member(
    member_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    创建新会员
    """
    try:
        crud = MemberCRUD(db)
        member = crud.create_member(
            member_data=member_data,
            user_id=current_user["id"],
            ip_address=current_user.get("ip_address")
        )
        return {"status": "success", "data": member.to_dict()}
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/{member_id}", response_model=dict)
def get_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取单个会员信息
    """
    try:
        crud = MemberCRUD(db)
        member = crud.get_member(
            member_id=member_id,
            user_id=current_user["id"],
            ip_address=current_user.get("ip_address")
        )
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )
        return {"status": "success", "data": member.to_dict()}
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/", response_model=dict)
def get_members(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    获取会员列表
    """
    try:
        crud = MemberCRUD(db)
        members = crud.get_members(
            skip=skip,
            limit=limit,
            user_id=current_user["id"],
            ip_address=current_user.get("ip_address")
        )
        return {
            "status": "success",
            "data": [member.to_dict() for member in members],
            "total": len(members)
        }
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/{member_id}", response_model=dict)
def update_member(
    member_id: int,
    member_data: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    更新会员信息
    """
    try:
        crud = MemberCRUD(db)
        member = crud.update_member(
            member_id=member_id,
            member_data=member_data,
            user_id=current_user["id"],
            ip_address=current_user.get("ip_address")
        )
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )
        return {"status": "success", "data": member.to_dict()}
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.delete("/{member_id}", response_model=dict)
def delete_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    删除会员
    """
    try:
        crud = MemberCRUD(db)
        success = crud.delete_member(
            member_id=member_id,
            user_id=current_user["id"],
            ip_address=current_user.get("ip_address")
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )
        return {"status": "success", "message": "Member deleted successfully"}
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/{member_id}/extend_membership", response_model=dict)
def extend_membership(
    member_id: int,
    days: float,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    延长会员会籍
    """
    try:
        crud = MemberCRUD(db)
        member = crud.extend_membership(
            member_id=member_id,
            days=days,
            user_id=current_user["id"],
            ip_address=current_user.get("ip_address")
        )
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )
        return {"status": "success", "data": member.to_dict()}
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post("/{member_id}/consume_membership", response_model=dict)
def consume_membership(
    member_id: int,
    days: float,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    消耗会员会籍
    """
    try:
        crud = MemberCRUD(db)
        result = crud.consume_membership(
            member_id=member_id,
            days=days,
            user_id=current_user["id"],
            ip_address=current_user.get("ip_address")
        )
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient membership days"
            )
        return {"status": "success", "message": "Membership consumed successfully"}
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.put("/{member_id}/level", response_model=dict)
def update_membership_level(
    member_id: int,
    level: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    更新会员等级
    """
    try:
        crud = MemberCRUD(db)
        member = crud.update_membership_level(
            member_id=member_id,
            level=level,
            user_id=current_user["id"],
            ip_address=current_user.get("ip_address")
        )
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found"
            )
        return {"status": "success", "data": member.to_dict()}
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
