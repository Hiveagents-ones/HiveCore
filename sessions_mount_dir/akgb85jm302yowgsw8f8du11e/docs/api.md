# API 接口文档

## 概述

本文档描述了会员和支付相关的 API 接口，包括会员状态查询、支付订单创建等功能。

## 基础信息

- 基础URL: `https://api.example.com`
- API版本: v1
- 数据格式: JSON
- 字符编码: UTF-8

## 认证方式

所有需要认证的接口都需要在请求头中包含认证信息：

```
Authorization: Bearer <token>
```

## 会员相关接口

### 1. 获取会员状态

**接口地址：** `GET /membership/status`

**接口描述：** 获取指定会员的当前会员状态信息

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| member_id | int | 是 | 会员ID |

**响应示例：**

```json
{
  "member_id": 123,
  "is_vip": true,
  "vip_expire_at": "2024-12-31T23:59:59Z",
  "days_remaining": 30
}
```

**响应字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| member_id | int | 会员ID |
| is_vip | bool | 是否为VIP会员 |
| vip_expire_at | string | VIP到期时间（ISO 8601格式） |
| days_remaining | int | 剩余天数（非VIP时为null） |

### 2. 清除会员缓存

**接口地址：** `POST /membership/clear-cache`

**接口描述：** 清除指定会员或所有会员的缓存数据

**请求参数：**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| member_id | int | 否 | 会员ID（不传则清除所有） |

**响应示例：**

```json
{
  "message": "Cache cleared successfully"
}
```

## 支付相关接口

### 1. 创建支付订单

**接口地址：** `POST /payment/create`

**接口描述：** 创建会员续费支付订单

**请求头：**

```
Authorization: Bearer <token>
Content-Type: application/json
```

**请求参数：**

```json
{
  "plan_id": 1,
  "payment_method": "wechat"
}
```

**请求字段说明：**

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| plan_id | int | 是 | 套餐ID |
| payment_method | string | 是 | 支付方式（wechat/alipay） |

**响应示例：**

```json
{
  "success": true,
  "message": "支付订单创建成功",
  "payment_url": "https://pay.example.com/xxxx",
  "order_id": "PAY_123_1640995200"
}
```

**响应字段说明：**

| 字段名 | 类型 | 说明 |
|--------|------|------|
| success | bool | 是否成功 |
| message | string | 响应消息 |
| payment_url | string | 支付链接 |
| order_id | string | 订单号 |

## 错误码说明

| 错误码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未授权访问 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 安全规范

1. 所有敏感数据传输必须使用HTTPS
2. 支付相关接口需要有效的认证token
3. 支付回调需要进行签名验证
4. 敏感信息（如密钥）不应出现在日志中
5. 接口访问需要进行频率限制

## 数据模型

### MembershipStatusResponse

```json
{
  "member_id": "integer",
  "is_vip": "boolean",
  "vip_expire_at": "string (datetime)",
  "days_remaining": "integer (nullable)"
}
```

### RenewalRequest

```json
{
  "plan_id": "integer",
  "payment_method": "string (enum: wechat, alipay)"
}
```

### RenewalResponse

```json
{
  "success": "boolean",
  "message": "string",
  "payment_url": "string (nullable)",
  "order_id": "string"
}
```

## 注意事项

1. 会员状态接口有5分钟的缓存
2. 支付订单创建后需要在30分钟内完成支付
3. VIP到期后会自动更新会员状态
4. 支付成功后会自动延长会员有效期
5. 建议定期清除缓存以确保数据一致性