import pytest
from app.core.security import SecurityManager
from app.core.config import settings


class TestSecurityManager:
    """安全功能管理器测试类"""

    def setup_method(self):
        """测试前初始化"""
        self.security = SecurityManager()

    def test_encrypt_decrypt_payment_info(self):
        """测试支付信息加密和解密"""
        payment_data = {
            "card_number": "4111111111111111",
            "expiry": "12/25",
            "cvv": "123",
            "amount": 100.00
        }

        # 加密
        encrypted = self.security.encrypt_payment_info(payment_data)
        assert isinstance(encrypted, str)
        assert encrypted != str(payment_data)

        # 解密
        decrypted = self.security.decrypt_payment_info(encrypted)
        assert decrypted == payment_data

    def test_hash_password(self):
        """测试密码哈希"""
        password = "test_password_123"
        hashed, salt = self.security.hash_password(password)

        assert isinstance(hashed, str)
        assert isinstance(salt, str)
        assert len(hashed) == 64  # SHA256 hex length
        assert len(salt) == 32  # 16 bytes = 32 hex chars

        # 使用相同密码和盐值应该得到相同哈希
        hashed2, _ = self.security.hash_password(password, salt)
        assert hashed == hashed2

    def test_verify_password(self):
        """测试密码验证"""
        password = "test_password_123"
        hashed, salt = self.security.hash_password(password)

        # 正确密码应该验证通过
        assert self.security.verify_password(password, hashed, salt) is True

        # 错误密码应该验证失败
        assert self.security.verify_password("wrong_password", hashed, salt) is False

    def test_sanitize_sql_input(self):
        """测试SQL输入清理"""
        # 测试危险字符清理
        dangerous_input = "'; DROP TABLE users; --"
        cleaned = self.security.sanitize_sql_input(dangerous_input)
        assert "'" not in cleaned
        assert ";" not in cleaned
        assert "--" not in cleaned
        assert "DROP" in cleaned  # 保留非危险字符

        # 测试正常输入
        normal_input = "normal username"
        cleaned = self.security.sanitize_sql_input(normal_input)
        assert cleaned == "normal username"

    def test_generate_secure_token(self):
        """测试安全令牌生成"""
        token = self.security.generate_secure_token()
        assert isinstance(token, str)
        assert len(token) == 32

        # 测试自定义长度
        token_16 = self.security.generate_secure_token(16)
        assert len(token_16) == 16

        # 多次生成应该得到不同的令牌
        token2 = self.security.generate_secure_token()
        assert token != token2

    def test_encryption_with_custom_key(self):
        """测试使用自定义密钥的加密"""
        # 临时设置加密密钥
        original_key = settings.ENCRYPTION_KEY
        settings.ENCRYPTION_KEY = "test_encryption_key_123"

        try:
            security_with_key = SecurityManager()
            payment_data = {"test": "data"}

            encrypted = security_with_key.encrypt_payment_info(payment_data)
            decrypted = security_with_key.decrypt_payment_info(encrypted)
            assert decrypted == payment_data
        finally:
            # 恢复原始设置
            settings.ENCRYPTION_KEY = original_key

    def test_password_hashing_security(self):
        """测试密码哈希的安全性"""
        password = "my_secure_password"
        hashed1, salt1 = self.security.hash_password(password)
        hashed2, salt2 = self.security.hash_password(password)

        # 相同密码应该生成不同的哈希（因为盐值不同）
        assert hashed1 != hashed2
        assert salt1 != salt2

        # 但都应该能验证通过
        assert self.security.verify_password(password, hashed1, salt1) is True
        assert self.security.verify_password(password, hashed2, salt2) is True

    def test_sql_injection_prevention(self):
        """测试SQL注入防护"""
        injection_attempts = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM passwords --",
            "1'; EXEC xp_cmdshell('dir'); --"
        ]

        for injection in injection_attempts:
            cleaned = self.security.sanitize_sql_input(injection)
            # 确保危险字符被移除
            assert "'" not in cleaned
            assert ";" not in cleaned
            assert "--" not in cleaned
            assert "/*" not in cleaned
            assert "*/" not in cleaned
            assert "xp_" not in cleaned
            assert "sp_" not in cleaned
