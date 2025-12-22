# 活动管理模块 API 文档

## 概述

本文档详细描述了活动管理模块的所有接口，包括请求参数、响应格式和权限要求。

## 基础信息

- **基础路径**: `/api/activities`
- **认证方式**: Bearer Token (JWT)
- **权限要求**: 需要商家认证

## 接口列表

### 1. 创建活动

**接口地址**: `POST /api/activities/`

**描述**: 创建新的健身活动

**权限要求**: 需要商家认证，且只能为自己创建活动

**请求参数**:

```json
{
  "merchant_id": "integer",
  "name": "string",
  "description": "string",
  "start_time": "datetime",
  "end_time": "datetime",
  "location": "string",
  "rules": "string",
  "rewards": "string",
  "max_participants": "integer",
  "status": "string",
  "is_active": "boolean"
}
```

**响应格式**:

```json
{
  "id": "integer",
  "merchant_id": "integer",
  "name": "string",
  "description": "string",
  "start_time": "datetime",
  "end_time": "datetime",
  "location": "string",
  "rules": "string",
  "rewards": "string",
  "max_participants": "integer",
  "status": "string",
  "is_active": "boolean",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

**状态码**:
- 201: 创建成功
- 403: 无权限创建活动
- 409: 活动时间冲突

### 2. 获取活动列表

**接口地址**: `GET /api/activities/`

**描述**: 获取当前商家的活动列表

**权限要求**: 需要商家认证

**查询参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| status | string | 否 | 活动状态 (draft/published/cancelled/completed) |
| is_active | boolean | 否 | 是否激活 |
| skip | integer | 否 | 跳过记录数 (默认0) |
| limit | integer | 否 | 返回记录数 (默认100，最大100) |

**响应格式**:

```json
[
  {
    "id": "integer",
    "merchant_id": "integer",
    "name": "string",
    "description": "string",
    "start_time": "datetime",
    "end_time": "datetime",
    "location": "string",
    "rules": "string",
    "rewards": "string",
    "max_participants": "integer",
    "status": "string",
    "is_active": "boolean",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
]
```

### 3. 获取活动详情

**接口地址**: `GET /api/activities/{activity_id}`

**描述**: 获取指定活动的详细信息

**权限要求**: 需要商家认证，且只能查看自己的活动

**路径参数**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| activity_id | integer | 活动ID |

**响应格式**:

```json
{
  "id": "integer",
  "merchant_id": "integer",
  "name": "string",
  "description": "string",
  "start_time": "datetime",
  "end_time": "datetime",
  "location": "string",
  "rules": "string",
  "rewards": "string",
  "max_participants": "integer",
  "status": "string",
  "is_active": "boolean",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

**状态码**:
- 200: 获取成功
- 404: 活动不存在
- 403: 无权限查看该活动

### 4. 更新活动

**接口地址**: `PUT /api/activities/{activity_id}`

**描述**: 更新指定活动的信息

**权限要求**: 需要商家认证，且只能更新自己的活动

**路径参数**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| activity_id | integer | 活动ID |

**请求参数**:

```json
{
  "name": "string",
  "description": "string",
  "start_time": "datetime",
  "end_time": "datetime",
  "location": "string",
  "rules": "string",
  "rewards": "string",
  "max_participants": "integer",
  "status": "string",
  "is_active": "boolean"
}
```

**响应格式**:

```json
{
  "id": "integer",
  "merchant_id": "integer",
  "name": "string",
  "description": "string",
  "start_time": "datetime",
  "end_time": "datetime",
  "location": "string",
  "rules": "string",
  "rewards": "string",
  "max_participants": "integer",
  "status": "string",
  "is_active": "boolean",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

**状态码**:
- 200: 更新成功
- 404: 活动不存在
- 403: 无权限更新该活动
- 409: 活动时间冲突

### 5. 删除活动

**接口地址**: `DELETE /api/activities/{activity_id}`

**描述**: 删除指定的活动

**权限要求**: 需要商家认证，且只能删除自己的活动

**路径参数**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| activity_id | integer | 活动ID |

**响应格式**:

```json
{
  "message": "Activity deleted successfully"
}
```

**状态码**:
- 200: 删除成功
- 404: 活动不存在
- 403: 无权限删除该活动

## 数据模型

### Activity (活动)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | integer | 活动ID (主键) |
| merchant_id | integer | 商家ID (外键) |
| name | string | 活动名称 |
| description | string | 活动描述 |
| start_time | datetime | 开始时间 |
| end_time | datetime | 结束时间 |
| location | string | 活动地点 |
| rules | string | 活动规则 |
| rewards | string | 活动奖励 |
| max_participants | integer | 最大参与人数 |
| status | string | 活动状态 (draft/published/cancelled/completed) |
| is_active | boolean | 是否激活 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

### Merchant (商家)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | integer | 商家ID (主键) |
| name | string | 商家名称 |
| email | string | 邮箱 |
| is_active | boolean | 是否激活 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

## 错误码说明

| 错误码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 422 | 请求参数验证失败 |
| 500 | 服务器内部错误 |

## 示例

### 创建活动示例

**请求**:

```bash
curl -X POST "https://api.example.com/api/activities/" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": 1,
    "name": "晨跑活动",
    "description": "每天早上6点晨跑",
    "start_time": "2024-01-01T06:00:00",
    "end_time": "2024-01-01T07:00:00",
    "location": "中央公园",
    "rules": "准时参加，穿运动装",
    "rewards": "积分奖励",
    "max_participants": 30,
    "status": "draft",
    "is_active": true
  }'
```

**响应**:

```json
{
  "id": 1,
  "merchant_id": 1,
  "name": "晨跑活动",
  "description": "每天早上6点晨跑",
  "start_time": "2024-01-01T06:00:00",
  "end_time": "2024-01-01T07:00:00",
  "location": "中央公园",
  "rules": "准时参加，穿运动装",
  "rewards": "积分奖励",
  "max_participants": 30,
  "status": "draft",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

### 获取活动列表示例

**请求**:

```bash
curl -X GET "https://api.example.com/api/activities/?status=published&limit=10" \
  -H "Authorization: Bearer <token>"
```

**响应**:

```json
[
  {
    "id": 1,
    "merchant_id": 1,
    "name": "晨跑活动",
    "description": "每天早上6点晨跑",
    "start_time": "2024-01-01T06:00:00",
    "end_time": "2024-01-01T07:00:00",
    "location": "中央公园",
    "rules": "准时参加，穿运动装",
    "rewards": "积分奖励",
    "max_participants": 30,
    "status": "published",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

## 注意事项

1. 所有接口都需要在请求头中包含有效的 JWT Token
2. 商家只能操作自己创建的活动
3. 活动时间不能与已有活动冲突
4. 删除活动为软删除，实际数据不会从数据库中移除
5. 所有时间字段均使用 ISO 8601 格式
6. 分页查询最大限制为100条记录