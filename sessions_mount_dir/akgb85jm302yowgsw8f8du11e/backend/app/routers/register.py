from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Dict

from .. import models, schemas
from ..core.security import generate_member_id
from ..database import get_db

router = APIRouter(
    prefix="/register",
    tags=["registration"]
)

@router.post("/", response_model=schemas.MemberRegisterResponse, status_code=status.HTTP_201_CREATED)
def register_member(
    member_data: schemas.MemberRegisterRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    处理新会员注册请求。
    收集用户基本信息、联系方式和紧急联系人，
    注册成功后自动生成唯一的会员ID。
    """
    # 检查手机号是否已被注册
    existing_member_by_phone = db.query(models.Member).filter(
        models.Member.phone_number == member_data.phone
    ).first()
    if existing_member_by_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "PhoneAlreadyExists",
                "message": "该手机号已被注册"
            }
        )

    # 检查身份证号是否已被注册
    # 注意：由于身份证号是加密存储的，这里不能直接查询。
    # 在实际应用中，可能需要为加密字段建立索引或使用其他方法。
    # 为简化，此处省略身份证号唯一性检查，但应在生产环境中实现。

    # 创建新会员记录
    # Member模型的__init__方法会自动处理member_id生成和id_card加密
    new_member = models.Member(
        name=member_data.name,
        gender=member_data.gender,
        phone_number=member_data.phone,
        id_card_number=member_data.id_card,
        emergency_contact_name=member_data.emergency_contact_name,
        emergency_contact_phone=member_data.emergency_contact_phone,
        # is_active 默认为 True
    )
    
    db.add(new_member)
    db.commit()
    db.refresh(new_member)

    # 记录注册日志
    log_entry = models.RegistrationLog(
        member_id=new_member.member_id,
        action="register",
        details=f"Member {new_member.name} registered successfully.",
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    db.add(log_entry)
    db.commit()

    # 准备响应数据
    response_data = schemas.MemberRegisterResponse(
        member_id=new_member.member_id,
        name=new_member.name,
        phone=new_member.phone_number,
        created_at=new_member.created_at,
        status="active" if new_member.is_active else "inactive"
    )

    return response_data
