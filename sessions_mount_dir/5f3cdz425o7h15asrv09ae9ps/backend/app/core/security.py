import random
import time
import redis
from redis import Redis

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

redis_client = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

def generate_verification_code(length: int = 6) -> str:
    """生成指定长度的数字验证码"""
    return ''.join(random.choices('0123456789', k=length))

def store_verification_code(contact_type: str, contact: str, code: str, expiration: int = 300):
    """将验证码存储到Redis，设置过期时间"""
    key = f"verification:{contact_type}:{contact}"
    redis_client.setex(key, expiration, code)

def send_verification_code(contact_type: str, contact: str, code: str):
    """发送验证码到邮箱/手机（模拟API调用）"""
    print(f"[SIMULATED] Sending {code} to {contact_type}: {contact}")
    store_verification_code(contact_type, contact, code)

def verify_verification_code(contact_type: str, contact: str, code: str) -> bool:
    """验证验证码是否正确"""
    key = f"verification:{contact_type}:{contact}"
    stored_code = redis_client.get(key)
    if stored_code and stored_code.decode('utf-8') == code:
        redis_client.delete(key)
        return True
    return False