from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PaymentBase(BaseModel):
    member_id: int
    amount: float
    payment_date: datetime
    payment_type: str


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    member_id: Optional[int] = None
    amount: Optional[float] = None
    payment_date: Optional[datetime] = None
    payment_type: Optional[str] = None


class Payment(PaymentBase):
    id: int

    class Config:
        orm_mode = True


class PaymentReport(BaseModel):
    total_amount: float
    payment_count: int
    start_date: datetime
    end_date: datetime