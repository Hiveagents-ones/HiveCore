# 支付模块 API 文档

## 概述

本文档详细说明了支付模块的 API 接口，包括订单创建、支付处理、订阅管理和交易历史等功能。

## 基础信息

- **Base URL**: `https://yourdomain.com/api/v1`
- **认证方式**: Bearer Token
- **数据格式**: JSON
- **字符编码**: UTF-8

## 支付方式

系统支持以下支付方式：
- `ALIPAY`: 支付宝
- `WECHAT`: 微信支付
- `STRIPE`: Stripe 信用卡支付

## 接口列表

### 1. 订单管理

#### 1.1 创建订单

**接口地址**: `POST /orders`

**请求参数**:
```json
{
  "membership_plan_id": "uuid",
  "payment_method": "ALIPAY|WECHAT|STRIPE",
  "amount": 99.99,
  "currency": "CNY|USD|EUR",
  "expires_at": "2024-12-31T23:59:59Z",
  "is_renewal": false
}
```

**响应示例**:
```json
{
  "id": "uuid",
  "membership_plan_id": "uuid",
  "payment_method": "ALIPAY",
  "amount": 99.99,
  "currency": "CNY",
  "status": "PENDING",
  "created_at": "2024-01-01T00:00:00Z",
  "expires_at": "2024-12-31T23:59:59Z",
  "is_renewal": false
}
```

#### 1.2 处理支付

**接口地址**: `POST /pay`

**请求参数**:
```json
{
  "order_id": "uuid",
  "return_url": "https://yourdomain.com/payment/success",
  "cancel_url": "https://yourdomain.com/payment/cancel"
}
```

**响应示例**:
```json
{
  "payment_url": "https://payment.gateway.com/pay/xyz",
  "payment_id": "pay_123456",
  "status": "PENDING"
}
```

### 2. 订阅管理

#### 2.1 获取订阅计划

**接口地址**: `GET /subscription/plans`

**响应示例**:
```json
[
  {
    "id": 1,
    "name": "基础版",
    "description": "适合个人用户",
    "type": "MONTHLY",
    "price": 29.99,
    "currency": "CNY",
    "duration_days": 30,
    "features": ["功能A", "功能B"]
  },
  {
    "id": 2,
    "name": "专业版",
    "description": "适合团队使用",
    "type": "YEARLY",
    "price": 299.99,
    "currency": "CNY",
    "duration_days": 365,
    "features": ["功能A", "功能B", "功能C"]
  }
]
```

#### 2.2 获取订阅状态

**接口地址**: `GET /subscription/status`

**响应示例**:
```json
{
  "status": "ACTIVE",
  "plan": {
    "id": 1,
    "name": "基础版",
    "type": "MONTHLY"
  },
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-02-01T00:00:00Z",
  "auto_renew": true,
  "days_remaining": 15,
  "is_active": true
}
```

#### 2.3 创建订阅

**接口地址**: `POST /subscription/subscribe`

**请求参数**:
```json
{
  "plan_id": 1,
  "payment_method": "ALIPAY"
}
```

**响应示例**:
```json
{
  "subscription_id": "uuid",
  "order_id": "uuid",
  "payment_url": "https://payment.gateway.com/pay/xyz",
  "status": "PENDING"
}
```

### 3. 支付回调

#### 3.1 支付宝回调

**接口地址**: `POST /payment/callback/alipay`

**请求参数**: 支付宝异步通知参数

**响应**: `success`

#### 3.2 微信支付回调

**接口地址**: `POST /payment/callback/wechat`

**请求参数**: 微信支付异步通知参数

**响应**: XML 格式成功响应

#### 3.3 Stripe Webhook

**接口地址**: `POST /payment/callback/stripe`

**请求参数**: Stripe Webhook 事件

**响应**: `200 OK`

### 4. 交易历史

#### 4.1 获取交易列表

**接口地址**: `GET /transactions`

**查询参数**:
- `page`: 页码 (默认: 1)
- `limit`: 每页数量 (默认: 20)
- `status`: 订单状态筛选
- `start_date`: 开始日期
- `end_date`: 结束日期

**响应示例**:
```json
{
  "total": 100,
  "page": 1,
  "limit": 20,
  "items": [
    {
      "id": "uuid",
      "amount": 99.99,
      "currency": "CNY",
      "status": "COMPLETED",
      "payment_method": "ALIPAY",
      "created_at": "2024-01-01T00:00:00Z",
      "completed_at": "2024-01-01T00:05:00Z"
    }
  ]
}
```

## 错误码说明

| 错误码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未授权访问 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 500 | 服务器内部错误 |

## 状态说明

### 订单状态 (OrderStatus)
- `PENDING`: 待支付
- `PROCESSING`: 处理中
- `COMPLETED`: 已完成
- `FAILED`: 失败
- `CANCELLED`: 已取消
- `REFUNDED`: 已退款

### 订阅状态 (SubscriptionStatus)
- `ACTIVE`: 活跃
- `EXPIRED`: 已过期
- `CANCELLED`: 已取消
- `SUSPENDED`: 已暂停

## 安全说明

1. 所有支付相关接口都需要 HTTPS
2. 支付回调需要验证签名
3. 敏感信息需要加密存储
4. 支付日志需要完整记录

## 测试环境

- **测试地址**: `https://test.yourdomain.com/api/v1`
- **测试账号**: 联系开发团队获取
- **测试支付**: 使用沙箱环境进行测试

## 更新日志

### v1.0.0 (2024-01-01)
- 初始版本发布
- 支持支付宝、微信支付、Stripe
- 实现基础订阅功能

### v1.1.0 (2024-02-01)
- 添加退款功能
- 优化支付流程
- 增加交易历史查询
