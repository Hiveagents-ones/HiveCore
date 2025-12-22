from datetime import datetime
from typing import Optional

from fastapi import Depends
from fastapi import Request
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models.payment import Payment
from ..database import get_db
from ..utils.i18n import get_translation


class InvoiceService:
    """
    发票生成服务
    """

    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    def generate_invoice(self, payment_id: int, request: Optional[Request] = None) -> dict:
        """
        根据支付记录生成发票信息
        
        Args:
            payment_id: 支付记录ID
            
        Returns:
            dict: 包含发票信息的字典
            
        Raises:
            ValueError: 如果支付记录不存在
        """
        payment = self.db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise ValueError(f"Payment with ID {payment_id} not found")
            
        invoice_data = {
            "invoice_number": f"INV-{datetime.now().strftime('%Y%m%d')}-{payment_id}",
            "payment_id": payment.id,
            "member_id": payment.member_id,
            "amount": payment.amount,
            "payment_date": payment.payment_date,
            "payment_method": payment.payment_method,
            "issue_date": datetime.now().date(),
            "language": get_translation(request.headers.get("Accept-Language", "en") if request else "en"),
            "items": [],
            # 多语言字段
            "title": get_translation("Invoice", get_translation(request.headers.get("Accept-Language", "en") if request else "en")),
            "payment_label": get_translation("Payment", get_translation(request.headers.get("Accept-Language", "en") if request else "en")),
            "amount_label": get_translation("Amount", get_translation(request.headers.get("Accept-Language", "en") if request else "en")),
            "date_label": get_translation("Date", get_translation(request.headers.get("Accept-Language", "en") if request else "en")),
            "method_label": get_translation("Method", get_translation(request.headers.get("Accept-Language", "en") if request else "en")),
            "invoice_label": get_translation("Invoice Number", get_translation(request.headers.get("Accept-Language", "en") if request else "en")),
            "member_label": get_translation("Member ID", get_translation(request.headers.get("Accept-Language", "en") if request else "en"))
        }
        
        return invoice_data

    def get_invoice_history(self, member_id: int, request: Optional[Request] = None) -> list[dict]:
        """
        获取会员的发票历史记录
        
        Args:
            member_id: 会员ID
            
        Returns:
            list[dict]: 发票历史记录列表
        """
        payments = self.db.query(Payment).filter(Payment.member_id == member_id).all()
        
        invoices = []
        for payment in payments:
            invoice = self.generate_invoice(payment.id, request)
            invoices.append(invoice)
            
        return invoices

    def download_invoice(self, invoice_number: str, request: Optional[Request] = None) -> Optional[dict]:
        """
        下载指定发票号的发票
        
        Args:
            invoice_number: 发票号
            
        Returns:
            Optional[dict]: 发票信息，如果不存在则返回None
        """
        try:
            # 从发票号中提取支付ID
            payment_id = int(invoice_number.split('-')[-1])
            return self.generate_invoice(payment_id, request)
        except (ValueError, IndexError):
            return None