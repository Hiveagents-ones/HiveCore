from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import logging
from datetime import datetime

from ..schemas import MemberRegisterRequest, MemberRegisterResponse
from ..models import Member
from ..database import get_db

router = APIRouter(prefix="/register", tags=["register"])
logger = logging.getLogger(__name__)

def generate_member_account(name: str, phone: str) -> str:
    """生成唯一的会员账号"""
    # 使用姓名首字母和手机号后4位生成账号
    name_initial = name[0].upper() if name else 'M'
    phone_suffix = phone[-4:] if phone else '0000'
    timestamp = datetime.now().strftime('%m%d')
    return f"{name_initial}{phone_suffix}{timestamp}"

@router.post("/", response_model=MemberRegisterResponse)
async def register_member(
    member_data: MemberRegisterRequest,
    db: Session = Depends(get_db)
):
    """会员注册接口"""
    try:
        # 检查手机号是否已注册
        existing_phone = db.query(Member).filter(Member.phone == member_data.phone).first()
        if existing_phone:
            logger.warning(f"注册失败: 手机号 {member_data.phone} 已被注册")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该手机号已被注册"
            )
        
        # 检查身份证号是否已注册
        existing_id_card = db.query(Member).filter(Member.id_card == member_data.id_card).first()
        if existing_id_card:
            logger.warning(f"注册失败: 身份证号 {member_data.id_card} 已被注册")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="该身份证号已被注册"
            )
        
        # 生成会员账号
        member_account = generate_member_account(member_data.name, member_data.phone)
        
        # 确保账号唯一
        while db.query(Member).filter(Member.account_number == member_account).first():
            member_account = generate_member_account(member_data.name, member_data.phone)
        
        # 创建新会员
        new_member = Member(
            name=member_data.name,
            phone=member_data.phone,
            id_card=member_data.id_card,
            account_number=member_account
        )
        
        db.add(new_member)
        db.commit()
        db.refresh(new_member)
        
        logger.info(f"会员注册成功: {new_member.name} (账号: {member_account})")
        
        return MemberRegisterResponse(
            success=True,
            message="注册成功",
            member_id=str(new_member.id),
            member_account=member_account,
            registration_time=new_member.created_at
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
