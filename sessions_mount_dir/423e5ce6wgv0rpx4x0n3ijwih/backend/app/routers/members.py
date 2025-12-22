import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from .. import models, schemas, utils

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=schemas.MemberResponse, status_code=status.HTTP_201_CREATED)
def register_member(member: schemas.MemberCreate, db: Session = Depends(get_db)):
    """
    注册新会员
    - **name**: 会员姓名
    - **phone**: 手机号，必须是唯一且格式正确
    - **id_card**: 身份证号，必须是唯一且格式正确
    """
    logger.info(f"Attempting to register new member with phone: {member.phone}")

    # 检查手机号是否已存在
    db_member_by_phone = db.query(models.Member).filter(models.Member.phone == member.phone).first()
    if db_member_by_phone:
        logger.warning(f"Registration failed: Phone number {member.phone} already exists.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="此手机号已被注册"
        )

    # 检查身份证号是否已存在（先加密再查询）
    encrypted_id_card = utils.encrypt_sensitive_data(member.id_card)
    db_member_by_id_card = db.query(models.Member).filter(models.Member.id_card == encrypted_id_card).first()
    if db_member_by_id_card:
        logger.warning(f"Registration failed: ID card number already exists.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="此身份证号已被注册"
        )

    # 创建新会员
    try:
        new_member_id = utils.generate_unique_member_id()
        db_member = models.Member(
            id=new_member_id,
            name=member.name,
            phone=member.phone,
            id_card=encrypted_id_card  # 存储加密后的身份证号
        )
        db.add(db_member)
        db.commit()
        db.refresh(db_member)
        logger.info(f"Successfully registered new member with ID: {db_member.id}")

        return db_member
    except Exception as e:
        db.rollback()
        logger.error(f"An error occurred during member registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="服务器内部错误，请稍后再试"
        )


@router.get("/", response_model=List[schemas.MemberResponse])
def list_members(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    获取会员列表
    - **skip**: 跳过的记录数
    - **limit**: 返回的最大记录数
    """
    members = db.query(models.Member).offset(skip).limit(limit).all()
    return members


@router.post("/checkin", response_model=schemas.CheckinRecordResponse, status_code=status.HTTP_201_CREATED)
def check_in_member(checkin: schemas.MemberCheckin, db: Session = Depends(get_db)):
    """
    会员签到
    - **member_id**: 会员的唯一ID
    """
    logger.info(f"Member {checkin.member_id} is attempting to check in.")
    
    # 检查会员是否存在
    db_member = db.query(models.Member).filter(models.Member.id == checkin.member_id).first()
    if not db_member:
        logger.warning(f"Check-in failed: Member with ID {checkin.member_id} not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会员不存在"
        )
    
    # 创建签到记录
    try:
        db_checkin = models.CheckinRecord(member_id=checkin.member_id)
        db.add(db_checkin)
        db.commit()
        db.refresh(db_checkin)
        logger.info(f"Member {checkin.member_id} successfully checked in at {db_checkin.checkin_time}.")
        return db_checkin
    except Exception as e:
        db.rollback()
        logger.error(f"An error occurred during member check-in: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="签到失败，请稍后再试"
        )
