import pytest
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from jose import jwt
from app.core.security import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token,
    get_current_user,
    TokenPayload,
    Token,
)
from fastapi.security import HTTPAuthorizationCredentials


class TestPasswordHashing:
    def test_get_password_hash(self):
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert hashed != password
        assert hashed.startswith("$2b$")

    def test_verify_password(self):
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False


class TestTokenCreation:
    def test_create_access_token(self):
        data = {"sub": "testuser", "scopes": ["read", "write"]}
        token = create_access_token(data)
        assert isinstance(token, str)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "testuser"
        assert payload["scopes"] == ["read", "write"]
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_create_access_token_with_expiry(self):
        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=60)
        token = create_access_token(data, expires_delta)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = datetime.fromtimestamp(payload["exp"])
        iat = datetime.fromtimestamp(payload["iat"])
        assert (exp - iat).seconds // 60 == 60

    def test_create_refresh_token(self):
        data = {"sub": "testuser", "scopes": ["read"]}
        token = create_refresh_token(data)
        assert isinstance(token, str)
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "testuser"
        assert payload["scopes"] == ["read"]
        assert payload["type"] == "refresh"
        assert "exp" in payload
        assert "iat" in payload


class TestTokenVerification:
    def test_verify_valid_token(self):
        data = {"sub": "testuser", "scopes": ["read"]}
        token = create_access_token(data)
        payload = verify_token(token)
        
        assert isinstance(payload, TokenPayload)
        assert payload.sub == "testuser"
        assert payload.scopes == ["read"]
        assert payload.type == "access"

    def test_verify_invalid_token(self):
        invalid_token = "invalid.token.here"
        with pytest.raises(HTTPException) as exc_info:
            verify_token(invalid_token)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Could not validate credentials" in str(exc_info.value.detail)

    def test_verify_expired_token(self):
        data = {"sub": "testuser"}
        expired_delta = timedelta(minutes=-1)
        token = create_access_token(data, expired_delta)
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetCurrentUser:
    def test_get_current_user_valid_token(self):
        data = {"sub": "testuser", "scopes": ["read", "write"]}
        token = create_access_token(data)
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        payload = get_current_user(credentials)
        assert isinstance(payload, TokenPayload)
        assert payload.sub == "testuser"
        assert payload.scopes == ["read", "write"]
        assert payload.type == "access"

    def test_get_current_user_invalid_token(self):
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid.token.here"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_expired_token(self):
        data = {"sub": "testuser"}
        expired_delta = timedelta(minutes=-1)
        token = create_access_token(data, expired_delta)
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(credentials)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestTokenModel:
    def test_token_model(self):
        token = Token(
            access_token="access_token_value",
            refresh_token="refresh_token_value",
            token_type="bearer"
        )
        assert token.access_token == "access_token_value"
        assert token.refresh_token == "refresh_token_value"
        assert token.token_type == "bearer"


class TestTokenPayloadModel:
    def test_token_payload_model(self):
        payload = TokenPayload(
            sub="testuser",
            scopes=["read", "write"],
            exp=1234567890,
            iat=1234567880,
            type="access"
        )
        assert payload.sub == "testuser"
        assert payload.scopes == ["read", "write"]
        assert payload.exp == 1234567890
        assert payload.iat == 1234567880
        assert payload.type == "access"

    def test_token_payload_model_optional_fields(self):
        payload = TokenPayload()
        assert payload.sub is None
        assert payload.scopes == []
        assert payload.exp is None
        assert payload.iat is None
        assert payload.type is None
