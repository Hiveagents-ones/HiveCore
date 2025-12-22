import os
from cryptography.fernet import Fernet
from typing import Optional, Union

# 从环境变量获取加密密钥，如果不存在则生成一个新的
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
if not ENCRYPTION_KEY:
    # 在生产环境中，应该通过安全的方式生成并存储密钥
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    print("Warning: No encryption key found in environment variables. A new key has been generated.")
    print(f"Please set this key in your environment: ENCRYPTION_KEY={ENCRYPTION_KEY}")

# 创建Fernet实例
cipher_suite = Fernet(ENCRYPTION_KEY.encode())

def encrypt_sensitive_data(data: Union[str, int, None]) -> Optional[str]:
    """
    加密敏感数据
    
    Args:
        data: 需要加密的数据（字符串、整数或None）
    
    Returns:
        加密后的字符串，如果输入为None则返回None
    """
    if data is None:
        return None
    
    # 将数据转换为字符串
    str_data = str(data)
    
    # 加密数据
    encrypted_data = cipher_suite.encrypt(str_data.encode())
    
    # 返回加密后的字符串
    return encrypted_data.decode()

def decrypt_sensitive_data(encrypted_data: Optional[str]) -> Optional[str]:
    """
    解密敏感数据
    
    Args:
        encrypted_data: 加密后的字符串
    
    Returns:
        解密后的原始数据，如果输入为None则返回None
    """
    if encrypted_data is None:
        return None
    
    try:
        # 解密数据
        decrypted_data = cipher_suite.decrypt(encrypted_data.encode())
        
        # 返回解密后的字符串
        return decrypted_data.decode()
    except Exception as e:
        # 如果解密失败，记录错误并返回None
        print(f"Error decrypting data: {e}")
        return None

def get_encryption_key() -> str:
    """
    获取当前使用的加密密钥
    
    Returns:
        加密密钥字符串
    """
    return ENCRYPTION_KEY

# 敏感字段列表，用于标识哪些字段需要加密
SENSITIVE_FIELDS = {
    'phone',
    'email',
    'address',
    'id_card',
    'bank_account',
    'emergency_contact',
    'wechat',
    'qq',
}

def is_sensitive_field(field_name: str) -> bool:
    """
    检查字段是否为敏感字段
    
    Args:
        field_name: 字段名称
    
    Returns:
        如果是敏感字段返回True，否则返回False
    """
    return field_name.lower() in SENSITIVE_FIELDS
