import re
from typing import Dict, Optional, Tuple
from datetime import datetime

from pydantic import BaseModel, validator


class PCICheckResult(BaseModel):
    """PCI DSS合规检查结果模型"""
    is_compliant: bool
    failed_checks: Dict[str, str]
    timestamp: datetime = datetime.now()


class PaymentSecurityService:
    """支付安全服务，实现PCI DSS合规检查"""

    @staticmethod
    def validate_card_number(card_number: str) -> Tuple[bool, Optional[str]]:
        """验证信用卡号码是否符合PCI DSS标准"""
        if not card_number:
            return False, "Card number cannot be empty"
        
        # 移除所有非数字字符
        cleaned_number = re.sub(r'[^0-9]', '', card_number)
        
        # 检查长度是否在13-19位之间
        if not 13 <= len(cleaned_number) <= 19:
            return False, "Invalid card number length"
        
        # 执行Luhn算法检查
        total = 0
        for i, digit in enumerate(reversed(cleaned_number)):
            n = int(digit)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n = (n // 10) + (n % 10)
            total += n
        
        if total % 10 != 0:
            return False, "Invalid card number (Luhn check failed)"
            
        return True, None

    @staticmethod
    def validate_cvv(cvv: str) -> Tuple[bool, Optional[str]]:
        """验证CVV码是否符合PCI DSS标准"""
        if not cvv:
            return False, "CVV cannot be empty"
        
        if not cvv.isdigit():
            return False, "CVV must contain only digits"
            
        if len(cvv) not in (3, 4):
            return False, "CVV must be 3 or 4 digits"
            
        return True, None

    @staticmethod
    def validate_expiry_date(expiry_date: str) -> Tuple[bool, Optional[str]]:
        """验证信用卡有效期是否符合PCI DSS标准"""
        if not expiry_date:
            return False, "Expiry date cannot be empty"
            
        try:
            month, year = expiry_date.split('/')
            month = int(month)
            year = int(year)
            
            if not (1 <= month <= 12):
                return False, "Invalid month"
                
            current_year = datetime.now().year % 100
            current_month = datetime.now().month
            
            if year < current_year or (year == current_year and month < current_month):
                return False, "Card has expired"
                
            return True, None
            
        except ValueError:
            return False, "Invalid expiry date format (MM/YY expected)"

    @classmethod
    def perform_pci_check(cls, card_data: Dict) -> PCICheckResult:
        """执行完整的PCI DSS合规检查"""
        failed_checks = {}
        
        # 检查信用卡号
        is_valid, error = cls.validate_card_number(card_data.get('card_number', ''))
        if not is_valid:
            failed_checks['card_number'] = error
        
        # 检查CVV
        is_valid, error = cls.validate_cvv(card_data.get('cvv', ''))
        if not is_valid:
            failed_checks['cvv'] = error
        
        # 检查有效期
        is_valid, error = cls.validate_expiry_date(card_data.get('expiry_date', ''))
        if not is_valid:
            failed_checks['expiry_date'] = error
        
        # 检查是否存储敏感数据
        if card_data.get('store_card', False):
            failed_checks['storage'] = "Storing full card data violates PCI DSS"
        
        return PCICheckResult(
            is_compliant=len(failed_checks) == 0,
            failed_checks=failed_checks
        )

    @classmethod
    def mask_card_number(cls, card_number: str) -> str:
        """掩码处理信用卡号，符合PCI DSS显示要求"""
        if not card_number or len(card_number) < 4:
            return "****"
            
        cleaned_number = re.sub(r'[^0-9]', '', card_number)
        return f"****-****-****-{cleaned_number[-4:]}"