from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.subscription import Subscription
from app.schemas.payment import PaymentRequest
from app.services.reminder_service import check_and_send_reminders
from app.db import get_db

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


def apply_discount_rules(current_end: datetime, duration: int) -> datetime:
    """应用续费优惠规则（如续费半年送1个月）"""
    # 优惠规则配置：续费180天（半年）额外赠送30天
    if duration == 180:
        return current_end + timedelta(days=30)
    return current_end

@router.post("/subscribe")
async def subscribe(
    payment_data: PaymentRequest,
    db: Session = Depends(get_db)
):
    # 验证用户订阅状态
    subscription = db.query(Subscription).filter(
        Subscription.user_id == payment_data.user_id,
        Subscription.status == "active"
    ).first()

    if not subscription:
        raise HTTPException(
            status_code=404,
            detail="No active subscription found"
        )

    # 计算续费后结束日期（应用优惠规则）
    new_end_date = apply_discount_rules(
        current_end=subscription.end_date,
        duration=payment_data.duration
    )

    # 更新订阅信息
    subscription.end_date = new_end_date
    subscription.status = "active"
    db.commit()

    # 发送续费成功通知（需实现通知服务）
    # send_payment_success_notification(payment_data.user_id)

    # 检查并发送新的到期提醒
    check_and_send_reminders(db)

    return {
        "status": "success",
        "new_end_date": new_end_date.isoformat(),
        "discount_applied": payment_data.duration == 180
    }