# RBAC系统设计文档

## 概述

本文档描述了基于角色的访问控制（RBAC）系统的设计与实现。该系统定义了用户、商家、管理员三种角色，并为不同角色分配不同的API访问权限。

## 技术栈

- FastAPI
- SQLAlchemy
- Redis
- Pydantic
- pytest

## 系统架构

### 核心组件

1. **模型层** (`backend/app/models/rbac.py`)
   - 定义用户、角色、权限的数据模型
   - 实现用户-角色、角色-权限的多对多关系

2. **核心逻辑** (`backend/app/core/rbac.py`)
   - 实现权限检查的核心逻辑
   - 提供权限验证装饰器

3. **服务层** (`backend/app/services/rbac_service.py`)
   - 封装RBAC相关的业务逻辑
   - 提供角色和权限管理的服务接口

4. **数据模式** (`backend/app/schemas/rbac.py`)
   - 定义请求和响应的数据结构
   - 实现数据验证和序列化

5. **路由层** (`backend/app/routers/rbac.py`)
   - 提供RBAC管理的API端点
   - 实现角色和权限的CRUD操作

6. **中间件** (`backend/app/middleware/rbac_middleware.py`)
   - 实现请求级别的权限检查
   - 集成到FastAPI应用中

7. **测试** (`backend/tests/test_rbac.py`)
   - 提供完整的单元测试和集成测试

8. **数据库迁移** (`backend/alembic/versions/add_rbac_tables.py`)
   - 创建RBAC相关的数据库表

## 角色定义

### 1. 用户 (User)
- 基础角色
- 可以访问公开API
- 可以管理自己的资源

### 2. 商家 (Merchant)
- 继承用户权限
- 可以管理店铺信息
- 可以查看订单数据

### 3. 管理员 (Admin)
- 继承所有权限
- 可以管理所有用户和角色
- 可以访问系统管理功能

## 权限矩阵

| 功能模块 | 用户 | 商家 | 管理员 |
|---------|------|------|--------|
| 查看公开信息 | ✓ | ✓ | ✓ |
| 管理个人资料 | ✓ | ✓ | ✓ |
| 管理店铺 | ✗ | ✓ | ✓ |
| 查看订单 | 自己 | 自己店铺 | 所有 |
| 管理用户 | ✗ | ✗ | ✓ |
| 管理角色 | ✗ | ✗ | ✓ |
| 系统设置 | ✗ | ✗ | ✓ |

## API端点

### 角色管理
- `GET /api/v1/roles` - 获取所有角色
- `POST /api/v1/roles` - 创建新角色
- `PUT /api/v1/roles/{role_id}` - 更新角色
- `DELETE /api/v1/roles/{role_id}` - 删除角色

### 权限管理
- `GET /api/v1/permissions` - 获取所有权限
- `POST /api/v1/permissions` - 创建新权限
- `PUT /api/v1/permissions/{permission_id}` - 更新权限
- `DELETE /api/v1/permissions/{permission_id}` - 删除权限

### 用户角色分配
- `GET /api/v1/users/{user_id}/roles` - 获取用户角色
- `POST /api/v1/users/{user_id}/roles` - 分配角色给用户
- `DELETE /api/v1/users/{user_id}/roles/{role_id}` - 移除用户角色

## 使用示例

### 1. 权限装饰器使用

```python
from backend.app.core.rbac import require_permission

@router.get("/protected")
@require_permission("read_sensitive_data")
async def protected_endpoint():
    return {"message": "Access granted"}
```

### 2. 中间件集成

```python
from backend.app.middleware.rbac_middleware import RBACMiddleware

app = FastAPI()
app.add_middleware(RBACMiddleware)
```

### 3. 服务层调用

```python
from backend.app.services.rbac_service import RBACService

rbac_service = RBACService()
has_permission = await rbac_service.check_permission(user_id, "manage_users")
```

## 数据库设计

### 表结构

1. **users** - 用户表
2. **roles** - 角色表
3. **permissions** - 权限表
4. **user_roles** - 用户角色关联表
5. **role_permissions** - 角色权限关联表

### 关系
- 用户与角色：多对多关系
- 角色与权限：多对多关系

## 缓存策略

使用Redis缓存用户权限信息，提高权限检查性能：
- 缓存键：`user_permissions:{user_id}`
- 缓存时间：30分钟
- 缓存失效：用户角色变更时主动清除

## 安全考虑

1. **权限最小化原则**：每个角色只授予必要的权限
2. **权限继承**：高级角色自动继承低级角色权限
3. **权限检查**：所有敏感操作必须进行权限验证
4. **审计日志**：记录所有权限相关的操作

## 测试覆盖

测试文件 `backend/tests/test_rbac.py` 包含：
- 权限检查逻辑测试
- 角色分配测试
- API端点权限测试
- 中间件集成测试

## 部署说明

1. 运行数据库迁移：
   ```bash
   alembic upgrade head
   ```

2. 初始化基础角色和权限数据

3. 确保Redis服务正常运行

4. 配置环境变量：
   ```env
   REDIS_URL=redis://localhost:6379
   ```

## 维护指南

1. 添加新角色：通过API或直接操作数据库
2. 添加新权限：更新权限表并分配给相应角色
3. 修改权限：更新权限定义并清除相关缓存
4. 监控权限使用：定期检查权限分配情况

## 版本历史

- v1.0.0 - 初始版本，实现基础RBAC功能
- v1.1.0 - 添加权限继承机制
- v1.2.0 - 优化缓存策略

## 相关文档

- [FastAPI官方文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy文档](https://docs.sqlalchemy.org/)
- [Redis文档](https://redis.io/documentation)