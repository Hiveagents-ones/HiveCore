from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from ..database import get_db
from ..models import Member, CheckinRecord
from ..schemas import MemberCheckin, CheckinResponse

router = APIRouter()

@router.post("/api/v1/members/checkin", response_model=CheckinResponse)
def checkin_member(checkin_data: MemberCheckin, db: Session = Depends(get_db)):
    """
    会员签到接口
    - 可以通过 member_id, phone 或 id_card 进行签到
    - 记录签到时间
    """
    member = None
    
    # 1. 根据提供的标识查找会员
    if checkin_data.member_id:
        member = db.query(Member).filter(Member.id == checkin_data.member_id).first()
    elif checkin_data.phone:
        member = db.query(Member).filter(Member.phone == checkin_data.phone).first()
    elif checkin_data.id_card:
        # id_card 在此上下文中作为会员号使用
        member = db.query(Member).filter(Member.id_card == checkin_data.id_card).first()
    
    # 2. 校验是否提供了有效的标识
    if not any([checkin_data.member_id, checkin_data.phone, checkin_data.id_card]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One of member_id, phone, or id_card must be provided for checkin."
        )
        
    # 3. 如果会员不存在，返回错误
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found. Please check the provided member ID, phone, or ID card number."
        )
    
    # 4. 创建签到记录
    checkin_time = checkin_data.checkin_time if checkin_data.checkin_time else datetime.utcnow()
    checkin_record = CheckinRecord(
        member_id=member.id,
        checkin_time=checkin_time
    )
    db.add(checkin_record)
    db.commit()
    db.refresh(checkin_record)
    
    # 5. 返回成功响应
    return CheckinResponse(
        success=True,
        message=f"Member {member.name} checked in successfully.",
        member_id=member.id,
        member_name=member.name,
        checkin_time=checkin_record.checkin_time
    )
