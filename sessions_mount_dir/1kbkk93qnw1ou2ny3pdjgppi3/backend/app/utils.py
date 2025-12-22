import uuid
import string
import secrets
from cryptography.fernet import Fernet
import os

# 加密密钥，实际项目中应从环境变量或安全配置中心加载
# WARNING: 不要将此密钥提交到版本控制系统
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key().decode())
cipher_suite = Fernet(ENCRYPTION_KEY.encode())


def generate_unique_member_id() -> str:
    """
    生成一个格式化的、唯一的会员ID。
    格式：M-{16个字符的十六进制字符串}
    示例：M-1a2b3c4d5e6f7g8h
    """
    # 生成16字节的随机数，并将其转换为十六进制字符串
    random_bytes = secrets.token_bytes(16)
    hex_str = random_bytes.hex()
    formatted_id = f"M-{hex_str.upper()}"
    return formatted_id


def encrypt_sensitive_data(data: str) -> str:
    """
    加密敏感数据（如身份证号）。
    Args:
        data: 需要加密的字符串。
    Returns:
        加密后的字符串 (UTF-8 编码)。
    """
    if not isinstance(data, str):
        data = str(data)
    encrypted_data = cipher_suite.encrypt(data.encode('utf-8'))
    return encrypted_data.decode('utf-8')


def decrypt_sensitive_data(encrypted_data: str) -> str:
    """
    解密敏感数据。
    Args:
        encrypted_data: 加密的字符串 (UTF-8 编码)。
    Returns:
        解密后的原始字符串。
    """
    if not isinstance(encrypted_data, str):
        encrypted_data = str(encrypted_data)
    decrypted_data = cipher_suite.decrypt(encrypted_data.encode('utf-8'))
    return decrypted_data.decode('utf-8')
