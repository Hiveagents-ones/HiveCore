from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import ValidationError
import logging
import random
import string

from .. import models, schemas
from ..core.security import encrypt_sensitive_data
from ..database import get_db

router = APIRouter(prefix="/register", tags=["register"])
logger = logging.getLogger(__name__)

def generate_member_id() -> str:
    """
    生成唯一的会员ID
    格式: M + 年份后两位 + 月份 + 6位随机数字
    例如: M2401001234
    """
    now = datetime.now()
    date_prefix = now.strftime("%y%m")
    random_suffix = ''.join(random.choices(string.digits, k=6))
    return f"M{date_prefix}{random_suffix}"

@router.post("/", response_model=schemas.MemberResponse, status_code=status.HTTP_201_CREATED)
async def register_member(
    member_data: schemas.MemberCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    注册新会员
    """
    try:
        # 验证输入数据
        if not member_data.privacy_policy_accepted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="必须同意隐私政策才能注册"
            )

        # 检查手机号是否已存在
        existing_member = db.query(models.Member).filter(
            models.Member.phone == member_data.phone
        ).first()
        if existing_member:
            logger.warning(f"注册失败: 手机号 {member_data.phone} 已存在")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该手机号已被注册"
            )

        # 获取会员卡类型
        membership_type_map = {
            schemas.MembershipType.MONTHLY: 1,
            schemas.MembershipType.QUARTERLY: 3,
            schemas.MembershipType.YEARLY: 12
        }
        duration_months = membership_type_map.get(member_data.membership_type)
        if not duration_months:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的会员卡类型"
            )

        # 生成唯一会员ID
        max_attempts = 10
        for _ in range(max_attempts):
            new_member_id = generate_member_id()
            if not db.query(models.Member).filter(
                models.Member.member_id == new_member_id
            ).first():
                break
        else:
            logger.error("无法生成唯一的会员ID")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="系统错误，请稍后重试"
            )

        # 创建会员记录
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=30 * duration_months)
        
        db_member = models.Member(
            member_id=new_member_id,
            name=member_data.name,
            phone=member_data.phone,
            id_card=member_data.id_card,  # 会自动加密
            membership_type_id=duration_months,
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )

        db.add(db_member)
        db.commit()
        db.refresh(db_member)

        # 记录日志
        logger.info(f"新会员注册成功: {db_member.member_id} - {db_member.name}")

        # 添加后台任务（例如发送欢迎短信）
        background_tasks.add_task(
            send_welcome_message,
            member_id=db_member.member_id,
            phone=db_member.phone
        )

        return schemas.MemberResponse(
            success=True,
            message="注册成功",
 data=schemas.Member.from_orm(db_member)
        )

    except ValidationError as e:
        logger.error(f"输入验证错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"注册过程中发生错误: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册失败，请稍后重试"
        )

async def send_welcome_message(member_id: str, phone: str):
    """
    发送欢迎消息（后台任务）
    """
    try:
        # 这里可以集成短信服务API
        logger.info(f"模拟发送欢迎短信到 {phone}: 会员 {member_id} 注册成功")
    except Exception as e:
        logger.error(f"发送欢迎消息失败: {str(e)}")

@router.get("/check-phone/{phone}", response_model=dict)
async def check_phone_availability(phone: str, db: Session = Depends(get_db)):
    """
    检查手机号是否可用
    """
    try:
        if len(phone) != 11 or not phone.startswith('1'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的手机号格式"
            )

        existing_member = db.query(models.Member).filter(
            models.Member.phone == phone
        ).first()
        
        return {
            "available": existing_member is None,
            "message": "手机号可用" if not existing_member else "手机号已被注册"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"检查手机号可用性时发生错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="检查失败，请稍后重试"
        )
