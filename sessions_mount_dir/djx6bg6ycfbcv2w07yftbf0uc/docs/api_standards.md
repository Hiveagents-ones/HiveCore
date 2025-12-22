# API 设计规范

## 概述

本文档定义了项目后端 API 的设计规范，包括 RESTful 原则、错误码定义、认证授权机制等。所有 API 接口都应遵循这些规范，以确保接口的一致性和可维护性。

## RESTful 原则

### 1. URL 设计

- 使用名词而非动词表示资源
- 使用复数形式表示资源集合
- 使用小写字母和连字符分隔单词
- 避免深层嵌套（建议不超过3层）

```
# 正确示例
GET    /api/v1/users          # 获取用户列表
POST   /api/v1/users          # 创建用户
GET    /api/v1/users/123      # 获取特定用户
PUT    /api/v1/users/123      # 更新用户
DELETE /api/v1/users/123      # 删除用户

# 错误示例
GET    /api/v1/getAllUsers    # 使用动词
GET    /api/v1/user/123       # 使用单数
GET    /api/v1/users/123/orders/456/items  # 嵌套过深
```

### 2. HTTP 方法

| 方法 | 用途 | 幂等性 | 安全性 |
|------|------|--------|--------|
| GET  | 获取资源 | 是 | 是 |
| POST | 创建资源 | 否 | 否 |
| PUT  | 完整更新资源 | 是 | 否 |
| PATCH | 部分更新资源 | 否 | 否 |
| DELETE | 删除资源 | 是 | 否 |

### 3. 状态码

#### 成功状态码
- `200 OK`: 请求成功
- `201 Created`: 资源创建成功
- `204 No Content`: 请求成功但无返回内容

#### 客户端错误
- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 未认证
- `403 Forbidden`: 无权限
- `404 Not Found`: 资源不存在
- `409 Conflict`: 资源冲突
- `422 Unprocessable Entity`: 请求格式正确但语义错误
- `429 Too Many Requests`: 请求频率超限

#### 服务器错误
- `500 Internal Server Error`: 服务器内部错误
- `502 Bad Gateway`: 网关错误
- `503 Service Unavailable`: 服务不可用

## 认证与授权

### 1. JWT 认证

所有需要认证的接口都应在请求头中包含 JWT token：

```
Authorization: Bearer <jwt_token>
```

JWT token 包含以下信息：
- `sub`: 用户ID
- `exp`: 过期时间
- `iat`: 签发时间
- `roles`: 用户角色列表

### 2. 权限控制

基于角色的访问控制（RBAC）：
- `admin`: 管理员，拥有所有权限
- `user`: 普通用户，拥有基本权限
- `guest`: 访客，只有只读权限

## 请求与响应格式

### 1. 请求格式

- 使用 JSON 格式
- Content-Type: `application/json`
- 时间格式: ISO 8601 (YYYY-MM-DDTHH:mm:ssZ)

### 2. 响应格式

所有 API 响应都应遵循统一格式：

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "timestamp": "2023-01-01T00:00:00Z"
}
```

#### 成功响应示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 123,
    "name": "John Doe",
    "email": "john@example.com"
  },
  "timestamp": "2023-01-01T00:00:00Z"
}
```

#### 错误响应示例

```json
{
  "code": 1001,
  "message": "User not found",
  "data": null,
  "timestamp": "2023-01-01T00:00:00Z"
}
```

## 错误码定义

### 通用错误码 (1000-1999)

| 错误码 | 描述 | HTTP状态码 |
|--------|------|------------|
| 1000 | 未知错误 | 500 |
| 1001 | 参数错误 | 400 |
| 1002 | 资源不存在 | 404 |
| 1003 | 权限不足 | 403 |
| 1004 | 未认证 | 401 |
| 1005 | 请求频率超限 | 429 |
| 1006 | 资源冲突 | 409 |

### 认证相关错误码 (2000-2999)

| 错误码 | 描述 | HTTP状态码 |
|--------|------|------------|
| 2000 | token无效 | 401 |
| 2001 | token过期 | 401 |
| 2002 | 用户名或密码错误 | 401 |
| 2003 | 账户被锁定 | 403 |
| 2004 | 账户未激活 | 403 |

### 业务错误码 (3000-3999)

| 错误码 | 描述 | HTTP状态码 |
|--------|------|------------|
| 3000 | 用户已存在 | 409 |
| 3001 | 邮箱已被使用 | 409 |
| 3002 | 密码强度不足 | 400 |
| 3003 | 验证码错误 | 400 |
| 3004 | 验证码已过期 | 400 |

## 分页规范

列表接口应支持分页，使用以下参数：

```
GET /api/v1/users?page=1&size=20&sort=created_at&order=desc
```

参数说明：
- `page`: 页码，从1开始，默认1
- `size`: 每页数量，默认20，最大100
- `sort`: 排序字段，默认创建时间
- `order`: 排序方向，asc或desc，默认desc

分页响应格式：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [],
    "total": 100,
    "page": 1,
    "size": 20,
    "pages": 5
  },
  "timestamp": "2023-01-01T00:00:00Z"
}
```

## 版本控制

API 版本通过 URL 路径控制：

```
/api/v1/users  # 版本1
/api/v2/users  # 版本2
```

版本规则：
- 主版本号：不兼容的API修改
- 次版本号：向下兼容的功能性新增
- 修订号：向下兼容的问题修正

## 国际化支持

API 支持多语言，通过请求头指定语言：

```
Accept-Language: zh-CN
```

支持的语言：
- `zh-CN`: 简体中文（默认）
- `en-US`: 英语
- `ja-JP`: 日语

错误消息将根据指定语言返回对应内容。

## 限流规范

为防止滥用，API 实施限流策略：

- 普通用户：100 请求/分钟
- 认证用户：1000 请求/分钟
- 管理员：无限制

超出限制时返回 429 状态码。

## 监控与日志

所有 API 请求都会记录以下信息：
- 请求路径和方法
- 请求参数
- 响应状态码
- 处理时间
- 用户ID（如果已认证）
- IP地址

## 最佳实践

1. **幂等性**：GET、PUT、DELETE 操作应该是幂等的
2. **缓存**：合理使用 HTTP 缓存头
3. **安全**：敏感数据传输使用 HTTPS
4. **文档**：使用 OpenAPI/Swagger 自动生成文档
5. **测试**：所有接口必须有单元测试和集成测试

## 示例代码

### FastAPI 实现

```python
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.security import get_current_user
from app.schemas.response import Response

router = APIRouter()

@router.get("/users/{user_id}", response_model=Response)
async def get_user(
    user_id: int,
    current_user = Depends(get_current_user)
):
    """获取用户信息"""
    if user_id != current_user.id and "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return Response(
        code=0,
        message="success",
        data=user.dict()
    )
```

### 错误处理

```python
from app.core.exceptions import APIException
from app.schemas.response import Response

@router.exception_handler(APIException)
async def api_exception_handler(request, exc: APIException):
    return Response(
        code=exc.code,
        message=exc.message,
        data=None
    )
```

## 参考资源

- [REST API Design Guide](https://restfulapi.net/)
- [JWT Handbook](https://jwt.io/introduction/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenAPI Specification](https://swagger.io/specification/)

## 更新日志

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0.0 | 2023-01-01 | 初始版本 |
| 1.1.0 | 2023-02-01 | 添加国际化支持 |
| 1.2.0 | 2023-03-01 | 添加限流规范 |