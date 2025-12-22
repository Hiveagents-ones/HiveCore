from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base

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

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    roles = relationship('Role', secondary=user_roles, back_populates='users')

class Role(Base):
    __tablename__ = 'roles'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    users = relationship('User', secondary=user_roles, back_populates='roles')
    permissions = relationship('Permission', secondary=role_permissions, back_populates='roles')

class Permission(Base):
    __tablename__ = 'permissions'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    resource = Column(String(100), nullable=False)  # e.g., 'user', 'product', 'order'
    action = Column(String(50), nullable=False)    # e.g., 'create', 'read', 'update', 'delete'
    description = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    roles = relationship('Role', secondary=role_permissions, back_populates='permissions')

# Default roles and permissions initialization
def init_default_roles(session):
    # Create default permissions
    permissions = [
        Permission(name='user:create', resource='user', action='create', description='Create new users'),
        Permission(name='user:read', resource='user', action='read', description='Read user information'),
        Permission(name='user:update', resource='user', action='update', description='Update user information'),
        Permission(name='user:delete', resource='user', action='delete', description='Delete users'),
        Permission(name='product:create', resource='product', action='create', description='Create new products'),
        Permission(name='product:read', resource='product', action='read', description='Read product information'),
        Permission(name='product:update', resource='product', action='update', description='Update product information'),
        Permission(name='product:delete', resource='product', action='delete', description='Delete products'),
        Permission(name='order:create', resource='order', action='create', description='Create new orders'),
        Permission(name='order:read', resource='order', action='read', description='Read order information'),
        Permission(name='order:update', resource='order', action='update', description='Update order information'),
        Permission(name='order:delete', resource='order', action='delete', description='Delete orders'),
    ]
    
    # Create default roles
    roles = [
        Role(name='user', description='Regular user with basic permissions'),
        Role(name='merchant', description='Merchant with product and order management permissions'),
        Role(name='admin', description='Administrator with full system access'),
    ]
    
    # Add permissions to session if they don't exist
    for perm in permissions:
        if not session.query(Permission).filter_by(name=perm.name).first():
            session.add(perm)
    
    # Add roles to session if they don't exist
    for role in roles:
        if not session.query(Role).filter_by(name=role.name).first():
            session.add(role)
    
    session.commit()
    
    # Assign permissions to roles
    user_role = session.query(Role).filter_by(name='user').first()
    merchant_role = session.query(Role).filter_by(name='merchant').first()
    admin_role = session.query(Role).filter_by(name='admin').first()
    
    # User permissions
    user_permissions = ['user:read', 'product:read', 'order:create', 'order:read']
    for perm_name in user_permissions:
        perm = session.query(Permission).filter_by(name=perm_name).first()
        if perm and perm not in user_role.permissions:
            user_role.permissions.append(perm)
    
    # Merchant permissions (includes all user permissions)
    merchant_permissions = user_permissions + ['product:create', 'product:read', 'product:update', 'order:update']
    for perm_name in merchant_permissions:
        perm = session.query(Permission).filter_by(name=perm_name).first()
        if perm and perm not in merchant_role.permissions:
            merchant_role.permissions.append(perm)
    
    # Admin permissions (all permissions)
    all_permissions = session.query(Permission).all()
    for perm in all_permissions:
        if perm not in admin_role.permissions:
            admin_role.permissions.append(perm)
    
    session.commit()
