from datetime import datetime
from typing import Optional
from typing import Dict, List

from pydantic import BaseModel


class PaymentBase(BaseModel):
    i18n_fields: Dict[str, str] = {
        "member_id": "会员ID",
        "amount": "金额",
        "payment_method": "支付方式"
    }
    member_id: int
    amount: float
    payment_method: str


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    i18n_fields: Dict[str, str] = {
        "amount": "金额",
        "payment_method": "支付方式",
        "status": "状态"
    }
    amount: Optional[float] = None
    payment_method: Optional[str] = None
    status: Optional[str] = None


class PaymentAuditLog(BaseModel):
    i18n_fields: Dict[str, str] = {
        "id": "ID",
        "payment_id": "支付ID",
        "action": "操作",
        "changed_by": "修改人",
        "changed_at": "修改时间",
        "old_values": "旧值",
        "new_values": "新值"
    }
    id: int
    payment_id: int
    action: str
    changed_by: str
    changed_at: datetime
    old_values: dict
    new_values: dict

    class Config:
        orm_mode = True


class Payment(PaymentBase):
    i18n_fields: Dict[str, str] = {
        "id": "ID",
        "member_id": "会员ID",
        "amount": "金额",
        "payment_method": "支付方式",
        "payment_date": "支付日期",
        "status": "状态",
        "invoice_number": "发票号"
    }
    id: int
    payment_date: datetime
    status: str
    invoice_number: Optional[str] = None

    class Config:
        orm_mode = True


class PaymentConfig(BaseModel):
    """
    支付配置模型
    """
    supported_currencies: List[str] = ["CNY", "USD", "EUR"]
    default_currency: str = "CNY"
    supported_methods: List[str] = ["Alipay", "WeChat Pay", "Bank Transfer", "Cash"]
    invoice_enabled: bool = True
    tax_rate: float = 0.0
    
    class Config:
        orm_mode = True