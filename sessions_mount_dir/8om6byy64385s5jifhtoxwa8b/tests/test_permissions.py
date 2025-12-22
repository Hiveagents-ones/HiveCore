import pytest
from fastapi import HTTPException
from app.core.rbac import Role, Permission, RBAC, require_permission
from unittest.mock import AsyncMock, patch


class TestRBAC:
    """测试基于角色的访问控制功能"""

    def test_admin_permissions(self):
        """测试管理员权限"""
        admin_permissions = Role.ADMIN.permissions
        assert Permission.MEMBER_CREATE in admin_permissions
        assert Permission.MEMBER_READ in admin_permissions
        assert Permission.MEMBER_UPDATE in admin_permissions
        assert Permission.MEMBER_DELETE in admin_permissions
        assert Permission.USER_MANAGE in admin_permissions
        assert Permission.ROLE_MANAGE in admin_permissions
        assert Permission.SYSTEM_CONFIG in admin_permissions

    def test_manager_permissions(self):
        """测试经理权限"""
        manager_permissions = Role.MANAGER.permissions
        assert Permission.MEMBER_CREATE in manager_permissions
        assert Permission.MEMBER_READ in manager_permissions
        assert Permission.MEMBER_UPDATE in manager_permissions
        assert Permission.MEMBER_DELETE in manager_permissions
        assert Permission.USER_MANAGE not in manager_permissions
        assert Permission.ROLE_MANAGE not in manager_permissions
        assert Permission.SYSTEM_CONFIG not in manager_permissions

    def test_staff_permissions(self):
        """测试员工权限"""
        staff_permissions = Role.STAFF.permissions
        assert Permission.MEMBER_READ in staff_permissions
        assert Permission.MEMBER_UPDATE in staff_permissions
        assert Permission.MEMBER_CREATE not in staff_permissions
        assert Permission.MEMBER_DELETE not in staff_permissions

    def test_member_permissions(self):
        """测试会员权限"""
        member_permissions = Role.MEMBER.permissions
        assert Permission.MEMBER_READ in member_permissions
        assert Permission.MEMBER_UPDATE not in member_permissions
        assert Permission.MEMBER_CREATE not in member_permissions
        assert Permission.MEMBER_DELETE not in member_permissions

    def test_has_permission(self):
        """测试权限检查"""
        assert RBAC.has_permission(Role.ADMIN, Permission.MEMBER_CREATE)
        assert RBAC.has_permission(Role.MANAGER, Permission.MEMBER_CREATE)
        assert not RBAC.has_permission(Role.STAFF, Permission.MEMBER_CREATE)
        assert not RBAC.has_permission(Role.MEMBER, Permission.MEMBER_CREATE)

    def test_has_any_permission(self):
        """测试任一权限检查"""
        assert RBAC.has_any_permission(Role.STAFF, [Permission.MEMBER_READ, Permission.MEMBER_CREATE])
        assert not RBAC.has_any_permission(Role.MEMBER, [Permission.MEMBER_CREATE, Permission.MEMBER_DELETE])

    def test_has_all_permissions(self):
        """测试所有权限检查"""
        assert RBAC.has_all_permissions(Role.ADMIN, [Permission.MEMBER_READ, Permission.MEMBER_CREATE])
        assert not RBAC.has_all_permissions(Role.STAFF, [Permission.MEMBER_READ, Permission.MEMBER_CREATE])

    def test_check_permission_success(self):
        """测试权限检查成功"""
        # 不应该抛出异常
        RBAC.check_permission(Role.ADMIN, Permission.MEMBER_CREATE)
        RBAC.check_permission(Role.MANAGER, Permission.MEMBER_READ)

    def test_check_permission_failure(self):
        """测试权限检查失败"""
        with pytest.raises(HTTPException) as exc_info:
            RBAC.check_permission(Role.MEMBER, Permission.MEMBER_DELETE)
        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in str(exc_info.value.detail)

    def test_get_user_permissions(self):
        """测试获取用户权限列表"""
        admin_perms = RBAC.get_user_permissions(Role.ADMIN)
        assert "member:create" in admin_perms
        assert "member:read" in admin_perms
        assert "member:update" in admin_perms
        assert "member:delete" in admin_perms
        assert "user:manage" in admin_perms
        assert "role:manage" in admin_perms
        assert "system:config" in admin_perms

        member_perms = RBAC.get_user_permissions(Role.MEMBER)
        assert len(member_perms) == 1
        assert "member:read" in member_perms

    @pytest.mark.asyncio
    async def test_require_permission_decorator(self):
        """测试权限装饰器"""
        mock_user = AsyncMock()
        mock_user.role = "admin"

        @require_permission(Permission.MEMBER_CREATE)
        async def test_function():
            return "success"

        with patch('app.core.rbac.get_current_user', return_value=mock_user):
            result = await test_function()
            assert result == "success"

    @pytest.mark.asyncio
    async def test_require_permission_decorator_failure(self):
        """测试权限装饰器失败"""
        mock_user = AsyncMock()
        mock_user.role = "member"

        @require_permission(Permission.MEMBER_DELETE)
        async def test_function():
            return "success"

        with patch('app.core.rbac.get_current_user', return_value=mock_user):
            with pytest.raises(HTTPException) as exc_info:
                await test_function()
            assert exc_info.value.status_code == 403
            assert "Insufficient permissions" in str(exc_info.value.detail)

    def test_role_enum_values(self):
        """测试角色枚举值"""
        assert Role.ADMIN.value == "admin"
        assert Role.MANAGER.value == "manager"
        assert Role.STAFF.value == "staff"
        assert Role.MEMBER.value == "member"

    def test_permission_enum_values(self):
        """测试权限枚举值"""
        assert Permission.MEMBER_CREATE.value == "member:create"
        assert Permission.MEMBER_READ.value == "member:read"
        assert Permission.MEMBER_UPDATE.value == "member:update"
        assert Permission.MEMBER_DELETE.value == "member:delete"
        assert Permission.USER_MANAGE.value == "user:manage"
        assert Permission.ROLE_MANAGE.value == "role:manage"
        assert Permission.SYSTEM_CONFIG.value == "system:config"
