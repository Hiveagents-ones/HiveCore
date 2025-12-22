import pytest
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.rbac import check_permission, require_permission, require_any_permission
from backend.app.models.permission import User, Role, Permission

@pytest.fixture
def mock_db_session():
    """Mock database session fixture"""
    class MockSession:
        def query(self, model):
            return self
        
        def filter(self, condition):
            return self
        
        def first(self):
            return None
    
    return MockSession()

@pytest.fixture
def mock_superuser():
    """Mock superuser fixture"""
    user = User()
    user.is_superuser = True
    user.roles = []
    return user

@pytest.fixture
def mock_regular_user():
    """Mock regular user fixture"""
    user = User()
    user.is_superuser = False
    
    # Create mock role with permissions
    role = Role()
    role.is_active = True
    
    # Create mock permission
    permission = Permission()
    permission.code = "member:create"
    permission.is_active = True
    
    role.permissions = [permission]
    user.roles = [role]
    return user

@pytest.fixture
def mock_user_without_permissions():
    """Mock user without permissions fixture"""
    user = User()
    user.is_superuser = False
    user.roles = []
    return user

def test_check_permission_superuser(mock_superuser):
    """Test that superuser has all permissions"""
    assert check_permission(mock_superuser, "any:permission") is True
    assert check_permission(mock_superuser, "member:create") is True
    assert check_permission(mock_superuser, "nonexistent:permission") is True

def test_check_permission_regular_user(mock_regular_user):
    """Test that regular user has only assigned permissions"""
    assert check_permission(mock_regular_user, "member:create") is True
    assert check_permission(mock_regular_user, "member:update") is False
    assert check_permission(mock_regular_user, "admin:delete") is False

def test_check_permission_user_without_permissions(mock_user_without_permissions):
    """Test that user without permissions has no access"""
    assert check_permission(mock_user_without_permissions, "member:create") is False
    assert check_permission(mock_user_without_permissions, "any:permission") is False

@pytest.mark.asyncio
async def test_require_permission_success(mock_regular_user):
    """Test require_permission decorator with valid permission"""
    @require_permission("member:create")
    async def test_endpoint(current_user=None):
        return "success"
    
    result = await test_endpoint(current_user=mock_regular_user)
    assert result == "success"

@pytest.mark.asyncio
async def test_require_permission_failure(mock_regular_user):
    """Test require_permission decorator with invalid permission"""
    @require_permission("member:delete")
    async def test_endpoint(current_user=None):
        return "success"
    
    with pytest.raises(HTTPException) as exc_info:
        await test_endpoint(current_user=mock_regular_user)
    
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "Permission 'member:delete' required" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_require_permission_no_user():
    """Test require_permission decorator without user"""
    @require_permission("member:create")
    async def test_endpoint(current_user=None):
        return "success"
    
    with pytest.raises(HTTPException) as exc_info:
        await test_endpoint()
    
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Authentication required" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_require_any_permission_success(mock_regular_user):
    """Test require_any_permission decorator with one valid permission"""
    @require_any_permission(["member:create", "member:update"])
    async def test_endpoint(current_user=None):
        return "success"
    
    result = await test_endpoint(current_user=mock_regular_user)
    assert result == "success"

@pytest.mark.asyncio
async def test_require_any_permission_failure(mock_regular_user):
    """Test require_any_permission decorator with no valid permissions"""
    @require_any_permission(["member:update", "member:delete"])
    async def test_endpoint(current_user=None):
        return "success"
    
    with pytest.raises(HTTPException) as exc_info:
        await test_endpoint(current_user=mock_regular_user)
    
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

@pytest.mark.asyncio
async def test_require_any_permission_superuser(mock_superuser):
    """Test require_any_permission decorator with superuser"""
    @require_any_permission(["any:permission"])
    async def test_endpoint(current_user=None):
        return "success"
    
    result = await test_endpoint(current_user=mock_superuser)
    assert result == "success"

def test_permission_code_format():
    """Test that permission codes follow the expected format"""
    valid_codes = [
        "member:create",
        "member:update",
        "member:delete",
        "member:view",
        "admin:manage",
        "report:generate"
    ]
    
    for code in valid_codes:
        assert ":" in code
        assert len(code.split(":")) == 2
        assert code.split(":")[0].isalnum()
        assert code.split(":")[1].isalnum()
