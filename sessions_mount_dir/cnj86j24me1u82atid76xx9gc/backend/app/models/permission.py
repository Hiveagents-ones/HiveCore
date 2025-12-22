from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base

# Association table for many-to-many relationship between roles and permissions
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id'), primary_key=True)
)

# Association table for many-to-many relationship between users and roles
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True)
)

class Permission(Base):
    __tablename__ = 'permissions'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, comment='Permission name')
    code = Column(String(50), unique=True, nullable=False, comment='Permission code')
    description = Column(String(255), nullable=True, comment='Permission description')
    resource = Column(String(100), nullable=False, comment='Resource type')
    action = Column(String(50), nullable=False, comment='Action type')
    is_active = Column(Boolean, default=True, comment='Whether the permission is active')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment='Creation time')
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment='Last update time')

    # Relationships
    roles = relationship('Role', secondary=role_permissions, back_populates='permissions')

class Role(Base):
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, comment='Role name')
    code = Column(String(50), unique=True, nullable=False, comment='Role code')
    description = Column(String(255), nullable=True, comment='Role description')
    is_active = Column(Boolean, default=True, comment='Whether the role is active')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment='Creation time')
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment='Last update time')

    # Relationships
    permissions = relationship('Permission', secondary=role_permissions, back_populates='roles')
    users = relationship('User', secondary=user_roles, back_populates='roles')

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, comment='Username')
    email = Column(String(255), unique=True, nullable=False, comment='Email address')
    hashed_password = Column(String(255), nullable=False, comment='Hashed password')
    is_active = Column(Boolean, default=True, comment='Whether the user is active')
    is_superuser = Column(Boolean, default=False, comment='Whether the user is a superuser')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment='Creation time')
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment='Last update time')
    last_login = Column(DateTime(timezone=True), nullable=True, comment='Last login time')

    # Relationships
    roles = relationship('Role', secondary=user_roles, back_populates='users')
    audit_logs = relationship('AuditLog', back_populates='user')

    def has_permission(self, permission_code: str) -> bool:
        """Check if user has a specific permission"""
        if self.is_superuser:
            return True
        
        for role in self.roles:
            if not role.is_active:
                continue
            for permission in role.permissions:
                if permission.is_active and permission.code == permission_code:
                    return True
        return False

    def has_role(self, role_code: str) -> bool:
        """Check if user has a specific role"""
        if self.is_superuser:
            return True
        
        for role in self.roles:
            if role.is_active and role.code == role_code:
                return True
        return False

    def get_permissions(self) -> list:
        """Get all permissions for the user"""
        if self.is_superuser:
            return ['*']
        
        permissions = set()
        for role in self.roles:
            if not role.is_active:
                continue
            for permission in role.permissions:
                if permission.is_active:
                    permissions.add(permission.code)
        return list(permissions)

    def get_roles(self) -> list:
        """Get all active roles for the user"""
        if self.is_superuser:
            return ['superuser']
        
        roles = []
        for role in self.roles:
            if role.is_active:
                roles.append(role.code)
        return roles