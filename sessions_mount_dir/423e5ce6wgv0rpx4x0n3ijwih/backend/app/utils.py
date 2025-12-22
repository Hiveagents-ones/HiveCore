import hashlib
import re
from typing import Optional

def hash_password(password: str) -> str:
    """
    使用SHA-256算法对密码进行哈希处理
    
    Args:
        password: 原始密码
        
    Returns:
        str: 哈希后的密码字符串
    """
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    验证密码强度
    
    Args:
        password: 待验证的密码
        
    Returns:
        tuple[bool, Optional[str]]: (是否通过验证, 错误信息)
    """
    if len(password) < 8:
        return False, "密码长度至少需要8个字符"
    
    if not re.search(r'[A-Z]', password):
        return False, "密码必须包含至少一个大写字母"
    
    if not re.search(r'[a-z]', password):
        return False, "密码必须包含至少一个小写字母"
    
    if not re.search(r'\d', password):
        return False, "密码必须包含至少一个数字"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "密码必须包含至少一个特殊字符"
    
    return True, None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码是否匹配
    
    Args:
        plain_password: 原始密码
        hashed_password: 哈希后的密码
        
    Returns:
        bool: 密码是否匹配
    """
    return hash_password(plain_password) == hashed_password
