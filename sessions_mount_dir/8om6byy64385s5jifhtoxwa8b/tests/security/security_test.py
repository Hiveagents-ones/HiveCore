import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from fastapi import HTTPException
from cryptography.fernet import Fernet
import ssl

from backend.app.core.security import (
    create_access_token,
    verify_password,
    get_password_hash,
    DataEncryption,
    HTTPSConfig,
    encryption
)
from backend.app.core.config import settings


class TestPasswordSecurity:
    """密码安全测试"""

    def test_password_hashing(self):
        """测试密码哈希"""
        password = "test_password_123"
        hashed = get_password_hash(password)
        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("wrong_password", hashed)

    def test_password_verification(self):
        """测试密码验证"""
        password = "secure_password"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True
        assert verify_password(password, hashed) is True  # 多次验证


class TestTokenSecurity:
    """令牌安全测试"""

    def test_create_access_token(self):
        """测试访问令牌创建"""
        subject = "test_user"
        token = create_access_token(subject)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expiry(self):
        """测试带过期时间的访问令牌"""
        subject = "test_user"
        expires_delta = timedelta(minutes=30)
        token = create_access_token(subject, expires_delta)
        assert isinstance(token, str)

    def test_create_access_token_default_expiry(self):
        """测试默认过期时间的访问令牌"""
        subject = "test_user"
        token = create_access_token(subject)
        assert isinstance(token, str)


class TestDataEncryption:
    """数据加密测试"""

    def setup_method(self):
        """测试前准备"""
        self.test_key = Fernet.generate_key()
        self.encryption = DataEncryption(self.test_key)

    def test_encrypt_decrypt_data(self):
        """测试数据加密和解密"""
        original_data = "sensitive_member_info"
        encrypted = self.encryption.encrypt(original_data)
        decrypted = self.encryption.decrypt(encrypted)
        assert original_data == decrypted
        assert encrypted != original_data

    def test_encrypt_empty_data(self):
        """测试空数据加密"""
        empty_data = ""
        encrypted = self.encryption.encrypt(empty_data)
        assert encrypted == empty_data

    def test_decrypt_empty_data(self):
        """测试空数据解密"""
        empty_data = ""
        decrypted = self.encryption.decrypt(empty_data)
        assert decrypted == empty_data

    def test_decrypt_invalid_data(self):
        """测试解密无效数据"""
        invalid_data = "invalid_encrypted_data"
        with pytest.raises(HTTPException) as exc_info:
            self.encryption.decrypt(invalid_data)
        assert exc_info.value.status_code == 400
        assert "Invalid encrypted data" in str(exc_info.value.detail)

    def test_global_encryption_instance(self):
        """测试全局加密实例"""
        test_data = "member_contact_info"
        encrypted = encryption.encrypt(test_data)
        decrypted = encryption.decrypt(encrypted)
        assert test_data == decrypted


class TestHTTPSConfig:
    """HTTPS配置测试"""

    @patch('ssl.create_default_context')
    def test_create_ssl_context_success(self, mock_create_context):
        """测试成功创建SSL上下文"""
        mock_context = MagicMock()
        mock_create_context.return_value = mock_context
        
        certfile = "/path/to/cert.pem"
        keyfile = "/path/to/key.pem"
        
        result = HTTPSConfig.create_ssl_context(certfile, keyfile)
        
        mock_create_context.assert_called_once_with(ssl.Purpose.CLIENT_AUTH)
        mock_context.load_cert_chain.assert_called_once_with(certfile=certfile, keyfile=keyfile)
        assert result == mock_context

    @patch('ssl.create_default_context')
    def test_create_ssl_context_failure(self, mock_create_context):
        """测试创建SSL上下文失败"""
        mock_create_context.return_value = MagicMock()
        mock_create_context.return_value.load_cert_chain.side_effect = Exception("Certificate error")
        
        with pytest.raises(HTTPException) as exc_info:
            HTTPSConfig.create_ssl_context("invalid_cert.pem", "invalid_key.pem")
        
        assert exc_info.value.status_code == 500
        assert "Failed to load SSL certificate" in str(exc_info.value.detail)

    def test_get_ssl_protocol_version(self):
        """测试获取SSL协议版本"""
        version = HTTPSConfig.get_ssl_protocol_version()
        assert version == ssl.TLSVersion.TLSv1_2


class TestSecurityIntegration:
    """安全功能集成测试"""

    def test_member_data_encryption_flow(self):
        """测试会员数据加密流程"""
        member_data = {
            "name": "张三",
            "phone": "13800138000",
            "card_number": "VIP001"
        }
        
        # 加密敏感信息
        encrypted_phone = encryption.encrypt(member_data["phone"])
        encrypted_card = encryption.encrypt(member_data["card_number"])
        
        # 验证加密后的数据不同
        assert encrypted_phone != member_data["phone"]
        assert encrypted_card != member_data["card_number"]
        
        # 解密验证
        decrypted_phone = encryption.decrypt(encrypted_phone)
        decrypted_card = encryption.decrypt(encrypted_card)
        
        assert decrypted_phone == member_data["phone"]
        assert decrypted_card == member_data["card_number"]

    def test_token_and_encryption_integration(self):
        """测试令牌和加密集成"""
        user_id = "member_123"
        
        # 创建访问令牌
        token = create_access_token(user_id)
        assert token
        
        # 加密用户敏感信息
        sensitive_info = "member_sensitive_data"
        encrypted_info = encryption.encrypt(sensitive_info)
        
        # 解密验证
        decrypted_info = encryption.decrypt(encrypted_info)
        assert decrypted_info == sensitive_info
