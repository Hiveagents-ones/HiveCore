# 支付模块设计文档

## 概述

支付模块是系统的核心组件之一，负责处理会员的会籍购买、续费、升级等交易，并记录支付历史。该模块支持多种支付方式，包括信用卡、支付宝、微信支付等。

## 架构设计

### 技术栈

- **前端**: Vue 3 + Vite + Pinia + Vue Router
- **后端**: FastAPI + SQLAlchemy + Alembic
- **数据库**: PostgreSQL
- **部署**: Docker + Nginx

### 模块结构

```
backend/
├── app/
│   ├── core/
│   │   └── payment_gateway.py    # 支付网关核心逻辑
│   ├── models/
│   │   └── payment.py            # 支付数据模型
│   ├── crud/
│   │   └── payment.py            # 支付CRUD操作
│   ├── schemas/
│   │   └── payment.py            # 支付数据模式
│   └── api/v1/endpoints/
│       └── payments.py           # 支付API端点

frontend/
├── src/
│   ├── api/
│   │   └── payment.js            # 前端支付API调用
│   ├── views/
│   │   ├── Payment.vue           # 支付页面
│   │   └── PaymentHistory.vue    # 支付历史页面
│   ├── stores/
│   │   └── payment.js            # 支付状态管理
│   └── locales/
│       ├── zh.json               # 中文国际化
│       └── en.json               # 英文国际化

tests/
├── test_payment_api.py            # 支付API测试
├── security/
│   └── payment_security_test.py  # 支付安全测试
└── performance/
    └── payment_load_test.py      # 支付性能测试
```

## API说明

### 支付相关API

#### 1. 创建支付订单

**端点**: `POST /api/v1/payments/create`

**请求体**:
```json
{
  "amount": 100.00,
  "currency": "CNY",
  "payment_method": "alipay",
  "order_id": "ORD123456",
  "user_id": "USER123"
}
```

**响应**:
```json
{
  "payment_id": "PAY123456",
  "payment_url": "https://payment.gateway.com/pay/PAY123456",
  "status": "pending"
}
```

#### 2. 查询支付状态

**端点**: `GET /api/v1/payments/{payment_id}/status`

**响应**:
```json
{
  "payment_id": "PAY123456",
  "status": "success",
  "paid_at": "2023-10-01T12:00:00Z",
  "amount": 100.00
}
```

#### 3. 获取支付历史

**端点**: `GET /api/v1/payments/history?user_id={user_id}&page={page}&size={size}`

**响应**:
```json
{
  "total": 10,
  "page": 1,
  "size": 5,
  "payments": [
    {
      "payment_id": "PAY123456",
      "amount": 100.00,
      "status": "success",
      "created_at": "2023-10-01T12:00:00Z"
    }
  ]
}
```

## 部署指南

### 环境要求

- Docker 20.10+
- Docker Compose 2.0+
- PostgreSQL 13+
- Nginx 1.20+

### 部署步骤

1. **克隆项目代码**
   ```bash
   git clone https://github.com/your-org/payment-module.git
   cd payment-module
   ```

2. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，配置数据库连接、支付网关密钥等
   ```

3. **启动服务**
   ```bash
   docker-compose up -d
   ```

4. **初始化数据库**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

5. **验证部署**
   - 访问 `http://localhost:8080` 查看前端页面
   - 访问 `http://localhost:8000/docs` 查看API文档

### 监控与日志

- **日志路径**: `/var/log/payment-module`
- **监控指标**: Prometheus + Grafana
- **告警配置**: Alertmanager

## 安全考虑

1. **支付数据加密**: 所有敏感支付数据在传输和存储时均需加密
2. **防重放攻击**: 每个支付请求包含唯一的时间戳和随机数
3. **权限控制**: 严格的API访问权限控制
4. **审计日志**: 记录所有支付操作的详细日志

## 测试

### 运行测试

```bash
# 运行所有测试
docker-compose exec backend pytest

# 运行特定测试
docker-compose exec backend pytest tests/test_payment_api.py
```

### 测试覆盖率

目标测试覆盖率: 90%+

## 维护

### 数据库迁移

```bash
# 创建新迁移
docker-compose exec backend alembic revision --autogenerate -m "Add new payment field"

# 应用迁移
docker-compose exec backend alembic upgrade head
```

### 回滚

```bash
# 回滚到上一个版本
docker-compose exec backend alembic downgrade -1
```

## 常见问题

### Q: 如何添加新的支付方式？
A: 需要在 `backend/app/core/payment_gateway.py` 中添加新的支付网关实现，并在前端添加相应的支付选项。

### Q: 支付失败如何处理？
A: 系统会自动重试3次，如果仍然失败，会将订单状态标记为失败，并通知用户重新支付。

### Q: 如何处理退款？
A: 通过 `POST /api/v1/payments/{payment_id}/refund` 端点发起退款请求，系统会调用相应支付网关的退款接口。

## 版本历史

- v1.0.0: 初始版本，支持基本的支付功能
- v1.1.0: 添加微信支付支持
- v1.2.0: 优化支付流程，提升性能

## 联系方式

如有问题或建议，请联系开发团队: dev-team@example.com