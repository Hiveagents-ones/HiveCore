from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from .. import models, schemas
from ..core.config import settings
from ..database import get_db

router = APIRouter()


@router.post("/", response_model=schemas.MemberResponse)
def register_member(
    member_data: schemas.MemberCreate,
    privacy_policy_accepted: bool = False,
    db: Session = Depends(get_db)
):
    """
    注册新会员
    
    Args:
        member_data: 会员注册信息
        privacy_policy_accepted: 是否同意隐私政策
        db: 数据库会话
    
    Returns:
        MemberResponse: 注册成功的会员信息
    
    Raises:
        HTTPException: 当手机号或身份证已存在时
    """
    # 检查隐私政策同意
    if not privacy_policy_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须同意隐私政策才能注册"
        )
    
    # 检查手机号是否已存在
    existing_phone = db.query(models.User).filter(
        models.User.phone == member_data.phone
    ).first()
    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该手机号已被注册"
        )
    
    # 检查身份证是否已存在
    existing_id_card = db.query(models.User).filter(
        models.User.id_card == member_data.id_card
    ).first()
    if existing_id_card:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该身份证号已被注册"
        )
    
    # 检查会员套餐是否存在
    membership_plan = db.query(models.MembershipPlan).filter(
        models.MembershipPlan.id == member_data.package_id,
        models.MembershipPlan.is_active == True
    ).first()
    if not membership_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定的会员套餐不存在或已下架"
        )
    
    # 创建用户
    db_user = models.User(
        name=member_data.name,
        phone=member_data.phone,
        id_card=member_data.id_card
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # 创建会员记录
    start_date = datetime.utcnow()
    end_date = start_date + timedelta(days=membership_plan.duration_months * 30)
    
    db_membership = models.Membership(
        user_id=db_user.id,
        plan_id=membership_plan.id,
        start_date=start_date,
        end_date=end_date
    )
    db.add(db_membership)
    db.commit()
    db.refresh(db_membership)
    
    # 创建支付记录
    db_payment = models.Payment(
        membership_id=db_membership.id,
        amount=membership_plan.price,
        payment_method=member_data.payment_method,
        transaction_id=f"TXN{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{db_user.id}",
        status="pending"
    )
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    
    # 返回会员信息
    return schemas.MemberResponse(
        id=db_user.id,
        name=db_user.name,
        phone=db_user.phone,
        id_card=db_user.id_card,
        package_id=membership_plan.id,
        status="active" if db_membership.is_active else "inactive",
        created_at=db_user.created_at,
        updated_at=db_user.updated_at
    )


@router.get("/privacy-policy")
def get_privacy_policy():
    """
    获取隐私政策内容
    
    Returns:
        dict: 隐私政策内容
    """
    return {
        "title": "健身房会员隐私政策",
        "content": """
        1. 信息收集
        我们会收集您的个人信息，包括但不限于姓名、手机号、身份证号等，用于会员注册和管理。
        
        2. 信息使用
        您的个人信息将仅用于会员管理、课程预约、费用结算等与健身房服务相关的用途。
        
        3. 信息保护
        我们将采取合理的技术和管理措施保护您的个人信息安全，防止信息泄露、丢失或被滥用。
        
        4. 信息共享
        未经您的同意，我们不会向任何第三方共享您的个人信息，法律法规另有规定的除外。
        
        5. 信息存储
        您的个人信息将被安全存储在服务器上，存储期限不超过法律规定的最长期限。
        
        6. 您的权利
        您有权查询、更正、删除您的个人信息，如需行使这些权利，请联系我们的客服。
        
        7. 政策更新
        我们可能会不时更新本隐私政策，更新后的政策将在健身房内公示。
        
        8. 联系我们
        如您对本隐私政策有任何疑问，请通过以下方式联系我们：
        电话：400-123-4567
        邮箱：privacy@gym.com
        """,
        "version": "1.0",
        "effective_date": "2023-01-01"
    }
