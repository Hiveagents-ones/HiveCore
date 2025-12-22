import logging
import sys
from typing import Any, Dict, Optional
from datetime import datetime
import json
from pythonjsonlogger import jsonlogger


class StructuredLogger:
    """结构化日志记录器，支持可观测性埋点"""
    
    def __init__(self, name: str = "gym_system"):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """配置日志记录器"""
        self.logger.setLevel(logging.INFO)
        
        # 清除现有处理器
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # JSON格式化器
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s %(pathname)s %(lineno)d',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def log_event(
        self,
        event_name: str,
        level: str = "info",
        user_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None
    ):
        """记录结构化事件日志"""
        log_data = {
            "event": event_name,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "trace_id": trace_id,
            "service": "gym_membership",
        }
        
        if extra_data:
            log_data.update(extra_data)
        
        if error:
            log_data["error"] = {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": getattr(error, '__traceback__', None)
            }
        
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(json.dumps(log_data, default=str))
    
    def log_registration(
        self,
        user_id: str,
        phone: str,
        success: bool = True,
        error_msg: Optional[str] = None
    ):
        """记录会员注册事件"""
        self.log_event(
            event_name="member_registration",
            level="info" if success else "error",
            user_id=user_id,
            extra_data={
                "phone": phone[:3] + "****" + phone[-4:],  # 脱敏处理
                "success": success,
                "error_msg": error_msg
            }
        )
    
    def log_authentication(
        self,
        user_id: str,
        action: str,  # login, logout, token_refresh
        success: bool = True,
        ip_address: Optional[str] = None
    ):
        """记录认证事件"""
        self.log_event(
            event_name="authentication",
            level="info" if success else "warning",
            user_id=user_id,
            extra_data={
                "action": action,
                "success": success,
                "ip_address": ip_address
            }
        )
    
    def log_api_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        user_id: Optional[str] = None
    ):
        """记录API请求日志"""
        self.log_event(
            event_name="api_request",
            level="info" if status_code < 400 else "error",
            user_id=user_id,
            extra_data={
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms
            }
        )
    
    def log_database_operation(
        self,
        operation: str,
        table: str,
        duration_ms: float,
        success: bool = True,
        error_msg: Optional[str] = None
    ):
        """记录数据库操作日志"""
        self.log_event(
            event_name="database_operation",
            level="info" if success else "error",
            extra_data={
                "operation": operation,
                "table": table,
                "duration_ms": duration_ms,
                "success": success,
                "error_msg": error_msg
            }
        )


# 全局日志记录器实例
logger = StructuredLogger()


def get_logger() -> StructuredLogger:
    """获取日志记录器实例"""
    return logger