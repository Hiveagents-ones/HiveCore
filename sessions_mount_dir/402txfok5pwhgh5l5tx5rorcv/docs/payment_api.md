# 支付API文档

## 概述

支付API提供会员在线支付会费、私教课费用和课程预约费用的功能。系统支持支付宝和微信支付，并记录每笔交易的详细信息。

## 基础信息

- **Base URL**: `/api/v1/payments`
- **认证方式**: Bearer Token
- **数据格式**: JSON

## API端点

### 1. 创建支付订单

**POST** `/api/v1/payments/`

创建一个新的支付订单。

#### 请求参数

```json
{
  "member_id": 1,
  "amount": 100.00,
  "type": "membership",
  "description": "月度会员费"
}
```

#### 响应示例

```json
{
  "id": 1,
  "member_id": 1,
  "amount": 100.00,
  "type": "membership",
  "status": "pending",
  "transaction_id": "txn_123456",
  "description": "月度会员费",
  "created_at": "2023-01-01T00:00:00Z"
}
```

#### 错误响应

- `404 Not Found`: 会员不存在
- `400 Bad Request`: 支付创建失败

### 2. 支付回调处理

**POST** `/api/v1/payments/callback/{payment_provider}`

处理支付平台（支付宝/微信）的回调通知。

#### 路径参数

- `payment_provider`: 支付提供商（`alipay` 或 `wechat`）

#### 请求参数

支付平台回调的原始数据（JSON格式）

#### 响应示例

```json
{
  "status": "success",
  "payment_id": 1
}
```

#### 错误响应

- `404 Not Found`: 支付记录不存在
- `400 Bad Request`: 回调处理失败

### 3. 查询支付记录

**GET** `/api/v1/payments/`

获取支付记录列表，支持按会员ID筛选。

#### 查询参数

- `member_id` (可选): 会员ID

#### 响应示例

```json
[
  {
    "id": 1,
    "member_id": 1,
    "amount": 100.00,
    "type": "membership",
    "status": "success",
    "transaction_id": "txn_123456",
    "description": "月度会员费",
    "created_at": "2023-01-01T00:00:00Z"
  }
]
```

## 数据模型

### Payment

| 字段 | 类型 | 描述 |
|------|------|------|
| id | integer | 支付记录ID |
| member_id | integer | 会员ID |
| amount | float | 支付金额 |
| type | string | 支付类型（membership/course/private） |
| status | string | 支付状态（pending/success/failed） |
| transaction_id | string | 第三方交易ID |
| description | string | 支付描述 |
| created_at | datetime | 创建时间 |

## 支付状态说明

- `pending`: 待支付
- `success`: 支付成功
- `failed`: 支付失败

## 支付类型说明

- `membership`: 会员费
- `course`: 课程费用
- `private`: 私教课费用

## 安全说明

1. 所有API请求需要包含有效的认证token
2. 支付回调需要验证签名
3. 敏感信息（如交易ID）需要加密存储

## 错误码说明

| 错误码 | 描述 |
|--------|------|
| 404 | 资源不存在 |
| 400 | 请求参数错误 |
| 500 | 服务器内部错误 |

## 示例代码

### JavaScript (前端)

```javascript
// 创建支付订单
const createPayment = async (paymentData) => {
  const response = await fetch('/api/v1/payments/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(paymentData)
  });
  return response.json();
};

// 查询支付记录
const getPayments = async (memberId) => {
  const url = memberId ? `/api/v1/payments/?member_id=${memberId}` : '/api/v1/payments/';
  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
};
```

### Python (后端)

```python
# 使用requests库调用API
import requests

def create_payment(payment_data):
    response = requests.post(
        'http://localhost:8000/api/v1/payments/',
        json=payment_data,
        headers={'Authorization': f'Bearer {token}'}
    )
    return response.json()

def get_payments(member_id=None):
    url = 'http://localhost:8000/api/v1/payments/'
    if member_id:
        url += f'?member_id={member_id}'
    response = requests.get(
        url,
        headers={'Authorization': f'Bearer {token}'}
    )
    return response.json()
```

## 更新日志

- v1.0.0 (2023-01-01): 初始版本，支持基本的支付功能
- v1.1.0 (2023-02-01): 添加支付回调处理
- v1.2.0 (2023-03-01): 增加交易历史查询功能