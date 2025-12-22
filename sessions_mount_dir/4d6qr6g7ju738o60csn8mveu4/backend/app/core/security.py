from cryptography.fernet import Fernet
from typing import Optional
import os
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# 从环境变量获取加密密钥，如果不存在则生成一个新密钥
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
if not ENCRYPTION_KEY:
    # 在生产环境中应该从安全的配置管理中获取
    ENCRYPTION_KEY = Fernet.generate_key().decode()
else:
    # 如果环境变量中的密钥不是base64编码的，需要转换
    try:
        key_bytes = ENCRYPTION_KEY.encode()
        # 检查是否已经是有效的Fernet密钥
        Fernet(key_bytes)
    except (ValueError, base64.binascii.Error):
        # 如果不是，使用PBKDF2从环境变量派生密钥
        salt = b'salt_'  # 在生产环境中应该使用随机盐
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key_bytes = base64.urlsafe_b64encode(kdf.derive(key_bytes))
        ENCRYPTION_KEY = key_bytes.decode()

cipher_suite = Fernet(ENCRYPTION_KEY.encode())

def encrypt_sensitive_data(data: str) -> str:
    """
    加密敏感数据（如身份证号）
    
    Args:
        data: 需要加密的原始数据
        
    Returns:
        str: 加密后的数据（base64编码）
    """
    if not data:
        return ""
    
    try:
        encrypted_data = cipher_suite.encrypt(data.encode())
        return encrypted_data.decode()
    except Exception as e:
        raise ValueError(f"加密失败: {str(e)}")

def decrypt_sensitive_data(encrypted_data: str) -> str:
    """
    解密敏感数据
    
    Args:
        encrypted_data: 加密后的数据（base64编码）
        
    Returns:
        str: 解密后的原始数据
    """
    if not encrypted_data:
        return ""
    
    try:
        decrypted_data = cipher_suite.decrypt(encrypted_data.encode())
        return decrypted_data.decode()
    except Exception as e:
        raise ValueError(f"解密失败: {str(e)}")

def mask_sensitive_data(data: str, mask_char: str = '*', visible_chars: int = 4) -> str:
    """
    脱敏显示敏感数据
    
    Args:
        data: 原始数据
        mask_char: 用于脱敏的字符
        visible_chars: 保留可见的字符数（通常显示最后几位）
        
    Returns:
        str: 脱敏后的数据
    """
    if not data or len(data) <= visible_chars:
        return data
    
    masked_length = len(data) - visible_chars
    return mask_char * masked_length + data[-visible_chars:]
