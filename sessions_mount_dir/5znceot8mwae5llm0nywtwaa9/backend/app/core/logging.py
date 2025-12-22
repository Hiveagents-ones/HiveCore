import logging
import sys
from typing import Any, Dict
import json
from datetime import datetime


class StructuredLogger:
    """结构化日志记录器，支持支付相关日志输出"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # 避免重复添加handler
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log_payment_event(self, 
                         event_type: str,
                         user_id: int,
                         membership_id: int,
                         amount: float,
                         payment_method: str,
                         status: str,
                         transaction_id: str = None,
                         error_message: str = None,
                         extra_data: Dict[str, Any] = None):
        """记录支付相关事件
        
        Args:
            event_type: 事件类型 (payment_initiated, payment_success, payment_failed, etc.)
            user_id: 用户ID
            membership_id: 会员ID
            amount: 支付金额
            payment_method: 支付方式 (wechat, alipay, manual)
            status: 支付状态 (pending, success, failed)
            transaction_id: 交易ID
            error_message: 错误信息（如果有）
            extra_data: 额外的结构化数据
        """
        log_data = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "membership_id": membership_id,
            "amount": amount,
            "payment_method": payment_method,
            "status": status,
            "transaction_id": transaction_id
        }
        
        if error_message:
            log_data["error"] = error_message
        
        if extra_data:
            log_data.update(extra_data)
        
        # 根据状态选择日志级别
        if status == "failed":
            self.logger.error(f"PAYMENT_EVENT: {json.dumps(log_data)}")
        elif status == "success":
            self.logger.info(f"PAYMENT_EVENT: {json.dumps(log_data)}")
        else:
            self.logger.info(f"PAYMENT_EVENT: {json.dumps(log_data)}")
    
    def log_membership_renewal(self,
                              user_id: int,
                              membership_id: int,
                              old_expiry: str,
                              new_expiry: str,
                              plan_type: str,
                              renewal_type: str):
        """记录会员续费事件
        
        Args:
            user_id: 用户ID
            membership_id: 会员ID
            old_expiry: 原到期时间
            new_expiry: 新到期时间
            plan_type: 套餐类型
            renewal_type: 续费类型 (online, manual)
        """
        log_data = {
            "event_type": "membership_renewal",
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "membership_id": membership_id,
            "old_expiry": old_expiry,
            "new_expiry": new_expiry,
            "plan_type": plan_type,
            "renewal_type": renewal_type
        }
        
        self.logger.info(f"MEMBERSHIP_EVENT: {json.dumps(log_data)}")
    
    def info(self, message: str, extra: Dict[str, Any] = None):
        """记录普通信息日志"""
        if extra:
            message = f"{message} | {json.dumps(extra)}"
        self.logger.info(message)
    
    def error(self, message: str, extra: Dict[str, Any] = None):
        """记录错误日志"""
        if extra:
            message = f"{message} | {json.dumps(extra)}"
        self.logger.error(message)
    
    def warning(self, message: str, extra: Dict[str, Any] = None):
        """记录警告日志"""
        if extra:
            message = f"{message} | {json.dumps(extra)}"
        self.logger.warning(message)


# 创建全局日志记录器实例
payment_logger = StructuredLogger("payment")
membership_logger = StructuredLogger("membership")


def get_logger(name: str) -> StructuredLogger:
    """获取指定名称的结构化日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        StructuredLogger实例
    """
    return StructuredLogger(name)