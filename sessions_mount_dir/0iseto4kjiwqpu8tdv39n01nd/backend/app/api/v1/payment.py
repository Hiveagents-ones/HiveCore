from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session

from ....database import get_db
from ....models.order import Order, OrderStatus, PaymentMethod
from ....models.subscription import Subscription
from ....schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderWithTransactions,
    PaymentRequest,
    PaymentResponse,
    TransactionCreate,
    TransactionResponse,
)
from ....payment_gateways.base import PaymentGateway
from ....payment_gateways.alipay import AlipayGateway
from ....payment_gateways.wechat import WechatGateway
from ....payment_gateways.stripe import StripeGateway

router = APIRouter()

# 支付网关配置
PAYMENT_GATEWAYS: Dict[PaymentMethod, PaymentGateway] = {
    PaymentMethod.ALIPAY: AlipayGateway({
        "app_id": "your_alipay_app_id",
        "merchant_private_key": "your_private_key",
        "alipay_public_key": "your_public_key",
        "notify_url": "https://yourdomain.com/api/v1/payment/callback/alipay",
        "return_url": "https://yourdomain.com/payment/success",
    }),
    PaymentMethod.WECHAT: WechatGateway({
        "app_id": "your_wechat_app_id",
        "mch_id": "your_mch_id",
        "api_key": "your_api_key",
        "notify_url": "https://yourdomain.com/api/v1/payment/callback/wechat",
    }),
    PaymentMethod.STRIPE: StripeGateway({
        "secret_key": "sk_test_your_stripe_secret_key",
        "publishable_key": "pk_test_your_stripe_publishable_key",
        "webhook_secret": "whsec_your_webhook_secret",
    }),
}


@router.post("/orders", response_model=OrderResponse)
async def create_order(order_data: OrderCreate, db: Session = Depends(get_db)):
    """
    创建新订单
    """
    # 验证支付方式是否支持
    if order_data.payment_method not in PAYMENT_GATEWAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment method {order_data.payment_method} is not supported"
        )

    # 验证货币是否支持
    gateway = PAYMENT_GATEWAYS[order_data.payment_method]
    if not gateway.is_currency_supported(order_data.currency):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Currency {order_data.currency} is not supported by {order_data.payment_method}"
        )

    # 创建订单
    order = Order(
        membership_plan_id=order_data.membership_plan_id,
        payment_method=order_data.payment_method,
        amount=order_data.amount,
        currency=order_data.currency,
        expires_at=order_data.expires_at,
        is_renewal=order_data.is_renewal,
        status=OrderStatus.PENDING,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    return order


@router.post("/pay", response_model=PaymentResponse)
async def process_payment(payment_request: PaymentRequest, db: Session = Depends(get_db)):
    """
    处理支付请求
    """
    # 获取订单
    order = db.query(Order).filter(Order.id == payment_request.order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is not in a payable state"
        )

    # 获取支付网关
    gateway = PAYMENT_GATEWAYS.get(payment_request.payment_method)
    if not gateway:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment method not supported"
        )

    # 创建支付
    try:
        payment_result = await gateway.create_payment(order)
        
        # 更新订单状态
        order.status = OrderStatus.PROCESSING
        db.commit()

        # 创建交易记录
        transaction = TransactionCreate(
            transaction_id=payment_result["transaction_id"],
            payment_method=payment_request.payment_method,
            amount=order.amount,
            currency=order.currency,
            status=payment_result["status"],
            gateway_response=str(payment_result),
            order_id=order.id,
        )
        db_transaction = Transaction(**transaction.dict())
        db.add(db_transaction)
        db.commit()
        db.refresh(db_transaction)

        return PaymentResponse(
            payment_url=payment_result.get("payment_url"),
            transaction_id=payment_result["transaction_id"],
            status=payment_result["status"],
            message=payment_result.get("message"),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment processing failed: {str(e)}"
        )


@router.post("/callback/{payment_method}")
async def payment_callback(payment_method: PaymentMethod, request: Request, db: Session = Depends(get_db)):
    """
    处理支付回调
    """
    gateway = PAYMENT_GATEWAYS.get(payment_method)
    if not gateway:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment method not supported"
        )

    # 获取回调数据
    if payment_method == Payment.ALIPAY:
        data = await request.form()
        callback_data = dict(data)
    elif payment_method == Payment.WECHAT:
        data = await request.body()
        callback_data = xmltodict.parse(data.decode("utf-8"))
    elif payment_method == Payment.STRIPE:
        data = await request.json()
        callback_data = data
    else:
        callback_data = await request.json()

    # 验证支付
    try:
        is_valid = await gateway.verify_payment(callback_data)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payment callback"
            )

        # 获取交易ID
        transaction_id = callback_data.get("transaction_id") or callback_data.get("id")
        if not transaction_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transaction ID not found in callback"
            )

        # 查找交易记录
        transaction = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found"
            )

        # 更新交易状态
        transaction.status = "completed"
        transaction.gateway_response = str(callback_data)
        db.commit()

        # 更新订单状态
        order = db.query(Order).filter(Order.id == transaction.order_id).first()
        if order:
            order.status = OrderStatus.COMPLETED
            db.commit()

            # 如果是续费订单，更新订阅
            if order.is_renewal:
                subscription = db.query(Subscription).filter(Subscription.user_id == order.user_id).first()
                if subscription:
                    subscription.extend_membership(order.expires_at)
                    db.commit()

        return {"status": "success"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Callback processing failed: {str(e)}"
        )


@router.get("/orders/{order_id}", response_model=OrderWithTransactions)
async def get_order(order_id: UUID, db: Session = Depends(get_db)):
    """
    获取订单详情
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    transactions = db.query(Transaction).filter(Transaction.order_id == order_id).all()
    order_response = OrderResponse.from_orm(order)
    transactions_response = [TransactionResponse.from_orm(t) for t in transactions]

    return OrderWithTransactions(
        **order_response.dict(),
        transactions=transactions_response
    )


@router.post("/refund/{order_id}")
async def refund_order(order_id: UUID, db: Session = Depends(get_db)):
    """
    订单退款
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.status != OrderStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only completed orders can be refunded"
        )

    gateway = PAYMENT_GATEWAYS.get(order.payment_method)
    if not gateway:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment method not supported"
        )

    try:
        refund_success = await gateway.refund_payment(order)
        if refund_success:
            order.status = OrderStatus.REFUNDED
            db.commit()
            return {"status": "success", "message": "Order refunded successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Refund failed"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Refund processing failed: {str(e)}"
        )
