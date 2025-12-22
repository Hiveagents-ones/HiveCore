from typing import List, Optional
from sqlalchemy.orm import Session
from ..models.rbac import User, Role, Permission
from ..core.rbac import RBAC

class RBACService:
    def __init__(self, db: Session):
        self.db = db
        self.rbac = RBAC(db)

    def create_role(self, name: str, description: Optional[str] = None) -> Role:
        """Create a new role"""
        existing_role = self.db.query(Role).filter(Role.name == name).first()
        if existing_role:
            raise ValueError(f"Role '{name}' already exists")
        
        role = Role(name=name, description=description)
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role

    def create_permission(self, resource: str, action: str, description: Optional[str] = None) -> Permission:
        """Create a new permission"""
        existing_permission = self.db.query(Permission).filter(
            Permission.resource == resource,
            Permission.action == action
        ).first()
        if existing_permission:
            raise ValueError(f"Permission '{resource}:{action}' already exists")
        
        permission = Permission(resource=resource, action=action, description=description)
        self.db.add(permission)
        self.db.commit()
        self.db.refresh(permission)
        return permission

    def assign_role_to_user(self, user_id: int, role_name: str) -> bool:
        """Assign a role to a user"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with id {user_id} not found")
        
        role = self.db.query(Role).filter(Role.name == role_name).first()
        if not role:
            raise ValueError(f"Role '{role_name}' not found")
        
        if role not in user.roles:
            user.roles.append(role)
            self.db.commit()
        return True

    def remove_role_from_user(self, user_id: int, role_name: str) -> bool:
        """Remove a role from a user"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with id {user_id} not found")
        
        role = self.db.query(Role).filter(Role.name == role_name).first()
        if not role:
            raise ValueError(f"Role '{role_name}' not found")
        
        if role in user.roles:
            user.roles.remove(role)
            self.db.commit()
        return True

    def assign_permission_to_role(self, role_name: str, resource: str, action: str) -> bool:
        """Assign a permission to a role"""
        role = self.db.query(Role).filter(Role.name == role_name).first()
        if not role:
            raise ValueError(f"Role '{role_name}' not found")
        
        permission = self.db.query(Permission).filter(
            Permission.resource == resource,
            Permission.action == action
        ).first()
        if not permission:
            raise ValueError(f"Permission '{resource}:{action}' not found")
        
        if permission not in role.permissions:
            role.permissions.append(permission)
            self.db.commit()
        return True

    def remove_permission_from_role(self, role_name: str, resource: str, action: str) -> bool:
        """Remove a permission from a role"""
        role = self.db.query(Role).filter(Role.name == role_name).first()
        if not role:
            raise ValueError(f"Role '{role_name}' not found")
        
        permission = self.db.query(Permission).filter(
            Permission.resource == resource,
            Permission.action == action
        ).first()
        if not permission:
            raise ValueError(f"Permission '{resource}:{action}' not found")
        
        if permission in role.permissions:
            role.permissions.remove(permission)
            self.db.commit()
        return True

    def get_user_roles(self, user_id: int) -> List[str]:
        """Get all roles for a user"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return []
        return [role.name for role in user.roles]

    def get_role_permissions(self, role_name: str) -> List[str]:
        """Get all permissions for a role"""
        role = self.db.query(Role).filter(Role.name == role_name).first()
        if not role:
            return []
        return [f"{p.resource}:{p.action}" for p in role.permissions]

    def get_all_roles(self) -> List[Role]:
        """Get all roles"""
        return self.db.query(Role).all()

    def get_all_permissions(self) -> List[Permission]:
        """Get all permissions"""
        return self.db.query(Permission).all()

    def initialize_default_roles(self):
        """Initialize default roles and permissions"""
        # Create default roles
        user_role = self.create_role("user", "Regular user")
        merchant_role = self.create_role("merchant", "Merchant user")
        admin_role = self.create_role("admin", "Administrator")

        # Create default permissions
        # User permissions
        self.create_permission("profile", "read", "Read user profile")
        self.create_permission("profile", "update", "Update user profile")
        
        # Merchant permissions
        self.create_permission("product", "create", "Create product")
        self.create_permission("product", "read", "Read product")
        self.create_permission("product", "update", "Update product")
        self.create_permission("product", "delete", "Delete product")
        self.create_permission("order", "read", "Read orders")
        
        # Admin permissions
        self.create_permission("user", "read", "Read any user")
        self.create_permission("user", "update", "Update any user")
        self.create_permission("user", "delete", "Delete any user")
        self.create_permission("role", "manage", "Manage roles")
        self.create_permission("permission", "manage", "Manage permissions")
        self.create_permission("system", "admin", "System administration")

        # Assign permissions to roles
        # User role permissions
        self.assign_permission_to_role("user", "profile", "read")
        self.assign_permission_to_role("user", "profile", "update")
        
        # Merchant role permissions (includes user permissions)
        self.assign_permission_to_role("merchant", "profile", "read")
        self.assign_permission_to_role("merchant", "profile", "update")
        self.assign_permission_to_role("merchant", "product", "create")
        self.assign_permission_to_role("merchant", "product", "read")
        self.assign_permission_to_role("merchant", "product", "update")
        self.assign_permission_to_role("merchant", "product", "delete")
        self.assign_permission_to_role("merchant", "order", "read")
        
        # Admin role permissions (includes all permissions)
        for permission in self.get_all_permissions():
            self.assign_permission_to_role("admin", permission.resource, permission.action)
