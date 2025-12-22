from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class TaxRate(Base):
    """
    税率模型
    - 存储不同地区/类型的税率信息
    """
    __tablename__ = 'tax_rates'

    id = Column(Integer, primary_key=True, index=True)
    region_code = Column(String(10), nullable=False, comment='地区编码')
    tax_type = Column(String(50), nullable=False, comment='税种类型')
    rate = Column(Numeric(5, 4), nullable=False, comment='税率值')
    effective_date = Column(DateTime, nullable=False, comment='生效日期')
    expiration_date = Column(DateTime, comment='失效日期')


class TaxRecord(Base):
    """
    税务记录模型
    - 关联支付记录和税率
    """
    __tablename__ = 'tax_records'

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey('payments.id'), nullable=False, comment='关联支付ID')
    tax_rate_id = Column(Integer, ForeignKey('tax_rates.id'), nullable=False, comment='关联税率ID')
    taxable_amount = Column(Numeric(12, 2), nullable=False, comment='应税金额')
    tax_amount = Column(Numeric(12, 2), nullable=False, comment='税额')
    calculated_at = Column(DateTime, nullable=False, comment='计算时间')

    payment = relationship("Payment", back_populates="tax_records")
    tax_rate = relationship("TaxRate")
