import pytest
from fastapi import HTTPException
from jose import jwt, JWTError
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from app.core.security import (
    create_access_token,
    verify_password,
    get_password_hash,
    get_current_user,
    get_current_active_user,
    encrypt_sensitive_data,
    decrypt_sensitive_data,
)
from app.models.user import User
from app.core.config import settings


class TestSecurity:
    """Test security-related functions"""

    def test_create_access_token(self):
        """Test JWT token creation"""
        user_id = 123
        token = create_access_token(subject=user_id)
        
        # Verify token can be decoded
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] == str(user_id)
        assert "exp" in payload
        
        # Test with custom expiration
        expires_delta = timedelta(hours=2)
        token_with_exp = create_access_token(subject=user_id, expires_delta=expires_delta)
        payload_with_exp = jwt.decode(token_with_exp, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        exp_time = datetime.fromtimestamp(payload_with_exp["exp"])
        expected_time = datetime.utcnow() + expires_delta
        assert abs((exp_time - expected_time).total_seconds()) < 60  # Allow 60 seconds tolerance

    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        # Verify hash is different from original password
        assert hashed != password
        
        # Verify password can be verified against hash
        assert verify_password(password, hashed) is True
        
        # Verify wrong password fails verification
        assert verify_password("wrong_password", hashed) is False

    @pytest.mark.asyncio
    async def test_get_current_user_success(self):
        """Test successful user authentication"""
        # Create mock user
        mock_user = User(
            id=1,
            email="test@example.com",
            is_active=True,
            hashed_password=get_password_hash("password")
        )
        
        # Create valid token
        token = create_access_token(subject=mock_user.id)
        
        # Mock database session
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user
        
        # Test authentication
        with patch('app.core.security.get_db', return_value=mock_db):
            user = await get_current_user(token, mock_db)
            assert user.id == mock_user.id
            assert user.email == mock_user.email

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test authentication with invalid token"""
        invalid_token = "invalid.token.here"
        mock_db = Mock()
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(invalid_token, mock_db)
        
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_nonexistent_user(self):
        """Test authentication with valid token but non-existent user"""
        token = create_access_token(subject=999)  # Non-existent user ID
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token, mock_db)
        
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_active_user_success(self):
        """Test getting active user"""
        mock_user = User(
            id=1,
            email="test@example.com",
            is_active=True,
            hashed_password=get_password_hash("password")
        )
        
        user = await get_current_active_user(mock_user)
        assert user.id == mock_user.id
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_get_current_active_user_inactive(self):
        """Test getting inactive user raises exception"""
        mock_user = User(
            id=1,
            email="test@example.com",
            is_active=False,
            hashed_password=get_password_hash("password")
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(mock_user)
        
        assert exc_info.value.status_code == 400
        assert "Inactive user" in str(exc_info.value.detail)

    def test_encrypt_decrypt_sensitive_data(self):
        """Test sensitive data encryption/decryption"""
        # Note: These are placeholder implementations
        # In production, use proper encryption
        sensitive_data = "sensitive_information"
        
        encrypted = encrypt_sensitive_data(sensitive_data)
        assert encrypted == sensitive_data  # Placeholder returns same data
        
        decrypted = decrypt_sensitive_data(encrypted)
        assert decrypted == sensitive_data

    def test_token_expiration(self):
        """Test token expiration behavior"""
        # Create token that expires in the past
        past_delta = timedelta(minutes=-1)
        expired_token = create_access_token(subject=123, expires_delta=past_delta)
        
        # Verify expired token raises JWTError
        with pytest.raises(JWTError):
            jwt.decode(expired_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    def test_password_hash_uniqueness(self):
        """Test that same password generates different hashes"""
        password = "same_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    @pytest.mark.asyncio
    async def test_get_current_user_malformed_token(self):
        """Test authentication with malformed token"""
        malformed_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"  # Incomplete JWT
        mock_db = Mock()
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(malformed_token, mock_db)
        
        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)

    def test_token_payload_structure(self):
        """Test JWT token payload structure"""
        user_id = "test_user_123"
        token = create_access_token(subject=user_id)
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # Verify required fields
        assert "exp" in payload
        assert "sub" in payload
        assert payload["sub"] == user_id
        
        # Verify no extra fields
        assert len(payload.keys()) == 2
