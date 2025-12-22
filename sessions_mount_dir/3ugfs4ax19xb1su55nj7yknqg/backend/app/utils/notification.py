from typing import Optional
import pika
from pika.exceptions import AMQPConnectionError
import json
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class NotificationService:
    """
    通知服务工具类，用于处理与消息队列的交互
    """
    
    def __init__(self, rabbitmq_url: str = "amqp://guest:guest@localhost/", queue_name: str = "notifications"):
        """
        初始化通知服务
        
        Args:
            rabbitmq_url: RabbitMQ连接URL
            queue_name: 队列名称
        """
        self.rabbitmq_url = rabbitmq_url
        self.queue_name = queue_name
        self.connection = None
        self.channel = None
    
    def connect(self) -> bool:
        """
        连接到RabbitMQ服务器
        
        Returns:
            bool: 连接是否成功
        """
        try:
            self.connection = pika.BlockingConnection(pika.URLParameters(self.rabbitmq_url))
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=self.queue_name, durable=True)
            return True
        except AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    def send_notification(self, message: dict, routing_key: Optional[str] = None) -> bool:
        """
        发送通知到消息队列
        
        Args:
            message: 要发送的消息内容
            routing_key: 路由键，默认为None
            
        Returns:
            bool: 消息是否发送成功
        """
        if not self.connection or self.connection.is_closed:
            if not self.connect():
                raise HTTPException(status_code=503, detail="Notification service unavailable")
        
        try:
            self.channel.basic_publish(
                exchange='',
                routing_key=routing_key or self.queue_name,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # 使消息持久化
                )
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False
    
    def close(self):
        """
        关闭连接
        """
        if self.connection and not self.connection.is_closed:
            self.connection.close()


# 全局通知服务实例
notification_service = NotificationService()


def get_notification_service() -> NotificationService:
    """
    获取通知服务实例
    
    Returns:
        NotificationService: 通知服务实例
    """
    return notification_service