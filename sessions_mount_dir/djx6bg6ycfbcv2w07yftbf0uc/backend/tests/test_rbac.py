import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db, Base
from app.models.rbac import User, Role, Permission
from app.services.rbac_service import RBACService
from app.schemas.rbac import UserCreate, RoleCreate, PermissionCreate, RoleAssignment

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def rbac_service(db_session):
    """Create RBAC service instance"""
    return RBACService(db_session)


@pytest.fixture(scope="function")
def sample_permissions(db_session):
    """Create sample permissions"""
    permissions = [
        Permission(name="read_users", resource="users", action="read"),
        Permission(name="write_users", resource="users", action="write"),
        Permission(name="delete_users", resource="users", action="delete"),
        Permission(name="read_products", resource="products", action="read"),
        Permission(name="write_products", resource="products", action="write"),
    ]
    
    for perm in permissions:
        db_session.add(perm)
    db_session.commit()
    
    return permissions


@pytest.fixture(scope="function")
def sample_roles(db_session, sample_permissions):
    """Create sample roles"""
    roles = [
        Role(name="user", description="Regular user"),
        Role(name="merchant", description="Merchant user"),
        Role(name="admin", description="Administrator"),
    ]
    
    for role in roles:
        db_session.add(role)
    db_session.commit()
    
    # Assign permissions to roles
    roles[0].permissions = [sample_permissions[0], sample_permissions[3]]  # user: read_users, read_products
    roles[1].permissions = [sample_permissions[0], sample_permissions[3], sample_permissions[4]]  # merchant: + write_products
    roles[2].permissions = sample_permissions  # admin: all permissions
    
    db_session.commit()
    return roles


@pytest.fixture(scope="function")
def sample_users(db_session, sample_roles):
    """Create sample users"""
    users = [
        User(username="user1", email="user1@example.com", hashed_password="pass1"),
        User(username="merchant1", email="merchant1@example.com", hashed_password="pass2"),
        User(username="admin1", email="admin1@example.com", hashed_password="pass3"),
    ]
    
    for user in users:
        db_session.add(user)
    db_session.commit()
    
    # Assign roles to users
    users[0].roles = [sample_roles[0]]  # user1 -> user
    users[1].roles = [sample_roles[1]]  # merchant1 -> merchant
    users[2].roles = [sample_roles[2]]  # admin1 -> admin
    
    db_session.commit()
    return users


class TestRBACService:
    """Test RBAC service methods"""
    
    def test_create_user(self, rbac_service):
        """Test user creation"""
        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            password="testpass"
        )
        user = rbac_service.create_user(user_data)
        
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.id is not None
    
    def test_create_role(self, rbac_service):
        """Test role creation"""
        role_data = RoleCreate(
            name="testrole",
            description="Test role"
        )
        role = rbac_service.create_role(role_data)
        
        assert role.name == "testrole"
        assert role.description == "Test role"
        assert role.id is not None
    
    def test_create_permission(self, rbac_service):
        """Test permission creation"""
        perm_data = PermissionCreate(
            name="test_perm",
            resource="test",
            action="read"
        )
        permission = rbac_service.create_permission(perm_data)
        
        assert permission.name == "test_perm"
        assert permission.resource == "test"
        assert permission.action == "read"
        assert permission.id is not None
    
    def test_assign_roles_to_user(self, rbac_service, sample_users, sample_roles):
        """Test role assignment to user"""
        user = sample_users[0]
        role_ids = [role.id for role in sample_roles[:2]]
        
        updated_user = rbac_service.assign_roles_to_user(user.id, role_ids)
        
        assert len(updated_user.roles) == 2
        assert set(role.id for role in updated_user.roles) == set(role_ids)
    
    def test_assign_permissions_to_role(self, rbac_service, sample_roles, sample_permissions):
        """Test permission assignment to role"""
        role = sample_roles[0]
        perm_ids = [perm.id for perm in sample_permissions[:2]]
        
        updated_role = rbac_service.assign_permissions_to_role(role.id, perm_ids)
        
        assert len(updated_role.permissions) == 2
        assert set(perm.id for perm in updated_role.permissions) == set(perm_ids)


class TestRBACAPI:
    """Test RBAC API endpoints"""
    
    def test_create_user_endpoint(self):
        """Test user creation endpoint"""
        response = client.post(
            "/rbac/users/",
            json={
                "username": "apiuser",
                "email": "api@example.com",
                "password": "apipass"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "apiuser"
        assert data["email"] == "api@example.com"
    
    def test_get_user_endpoint(self, sample_users):
        """Test get user endpoint"""
        user = sample_users[0]
        response = client.get(f"/rbac/users/{user.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user.id
        assert data["username"] == user.username
        assert "roles" in data
    
    def test_create_role_endpoint(self):
        """Test role creation endpoint"""
        response = client.post(
            "/rbac/roles/",
            json={
                "name": "apirole",
                "description": "API test role"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "apirole"
        assert data["description"] == "API test role"
    
    def test_assign_roles_to_user_endpoint(self, sample_users, sample_roles):
        """Test role assignment endpoint"""
        user = sample_users[0]
        role_ids = [role.id for role in sample_roles[:2]]
        
        response = client.post(
            f"/rbac/users/{user.id}/roles",
            json={
                "user_id": user.id,
                "role_ids": role_ids
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["roles"]) == 2
        assert set(role["id"] for role in data["roles"]) == set(role_ids)
    
    def test_check_permission_endpoint(self, sample_users):
        """Test permission check endpoint"""
        user = sample_users[0]  # user with 'user' role
        
        response = client.post(
            "/rbac/check-permission",
            json={
                "user_id": user.id,
                "resource": "users",
                "action": "read"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_permission"] is True
        
        # Test permission user doesn't have
        response = client.post(
            "/rbac/check-permission",
            json={
                "user_id": user.id,
                "resource": "users",
                "action": "delete"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_permission"] is False


class TestRBACCore:
    """Test RBAC core functionality"""
    
    def test_get_user_permissions(self, sample_users):
        """Test getting user permissions"""
        from app.core.rbac import RBAC
        
        db = TestingSessionLocal()
        rbac = RBAC(db)
        
        # Test regular user permissions
        user = sample_users[0]
        permissions = rbac.get_user_permissions(user.id)
        
        assert "users:read" in permissions
        assert "products:read" in permissions
        assert "users:delete" not in permissions
        
        db.close()
    
    def test_has_permission(self, sample_users):
        """Test permission checking"""
        from app.core.rbac import RBAC
        
        db = TestingSessionLocal()
        rbac = RBAC(db)
        
        # Test regular user
        user = sample_users[0]
        assert rbac.has_permission(user.id, "users", "read") is True
        assert rbac.has_permission(user.id, "users", "delete") is False
        
        # Test admin
        admin = sample_users[2]
        assert rbac.has_permission(admin.id, "users", "delete") is True
        
        db.close()
    
    def test_has_role(self, sample_users):
        """Test role checking"""
        from app.core.rbac import RBAC
        
        db = TestingSessionLocal()
        rbac = RBAC(db)
        
        # Test regular user
        user = sample_users[0]
        assert rbac.has_role(user.id, "user") is True
        assert rbac.has_role(user.id, "admin") is False
        
        # Test admin
        admin = sample_users[2]
        assert rbac.has_role(admin.id, "admin") is True
        
        db.close()


if __name__ == "__main__":
    pytest.main([__file__])
