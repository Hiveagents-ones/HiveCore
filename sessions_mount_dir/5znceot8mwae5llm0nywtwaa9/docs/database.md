# 数据库设计文档

## 概述

本文档描述了会员续费流程系统的数据库设计，包括表结构、索引和关系说明。数据库使用 PostgreSQL，并通过 SQLAlchemy 进行 ORM 映射。

## 表结构

### 1. members (会员表)

存储会员的基本信息和会员状态。

| 字段名 | 类型 | 约束 | 描述 |
|--------|------|------|------|
| id | Integer | PRIMARY KEY, AUTO_INCREMENT | 会员唯一标识 |
| username | String(50) | UNIQUE, NOT NULL, INDEX | 用户名 |
| email | String(100) | UNIQUE, NOT NULL, INDEX | 邮箱地址 |
| password_hash | String(255) | NOT NULL | 密码哈希 |
| is_active | Boolean | DEFAULT TRUE | 账户是否激活 |
| is_vip | Boolean | DEFAULT FALSE | 是否为VIP会员 |
| vip_expire_at | DateTime | NULLABLE | VIP到期时间 |
| created_at | DateTime | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DateTime | DEFAULT CURRENT_TIMESTAMP ON UPDATE | 更新时间 |

#### 索引
- `PRIMARY KEY` (id)
- `UNIQUE INDEX` (username)
- `UNIQUE INDEX` (email)
- `INDEX` (idx_member_vip_status) ON (is_vip, vip_expire_at)

### 2. packages (套餐表)

存储会员套餐信息。

| 字段名 | 类型 | 约束 | 描述 |
|--------|------|------|------|
| id | Integer | PRIMARY KEY, AUTO_INCREMENT | 套餐唯一标识 |
| name | String(100) | NOT NULL | 套餐名称 |
| description | Text | NULLABLE | 套餐描述 |
| price | Numeric(10,2) | NOT NULL | 套餐价格 |
| duration_days | Integer | NOT NULL | 套餐有效期（天） |
| is_active | Boolean | DEFAULT TRUE | 套餐是否可用 |
| created_at | DateTime | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DateTime | DEFAULT CURRENT_TIMESTAMP ON UPDATE | 更新时间 |

#### 索引
- `PRIMARY KEY` (id)
- `INDEX` (idx_package_active_price) ON (is_active, price)

### 3. payments (支付记录表)

存储会员的支付记录。

| 字段名 | 类型 | 约束 | 描述 |
|--------|------|------|------|
| id | Integer | PRIMARY KEY, AUTO_INCREMENT | 支付记录唯一标识 |
| member_id | Integer | FOREIGN KEY (members.id), NOT NULL | 会员ID |
| package_id | Integer | FOREIGN KEY (packages.id), NOT NULL | 套餐ID |
| amount | Numeric(10,2) | NOT NULL | 支付金额 |
| payment_method | String(50) | NOT NULL | 支付方式 (wechat, alipay等) |
| payment_status | String(50) | DEFAULT 'pending' | 支付状态 (pending, success, failed) |
| transaction_id | String(100) | UNIQUE, NULLABLE | 第三方交易ID |
| paid_at | DateTime | NULLABLE | 支付完成时间 |
| created_at | DateTime | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DateTime | DEFAULT CURRENT_TIMESTAMP ON UPDATE | 更新时间 |

#### 索引
- `PRIMARY KEY` (id)
- `INDEX` (idx_payment_member_status) ON (member_id, payment_status)
- `UNIQUE INDEX` (idx_payment_transaction) ON (transaction_id)

## 关系说明

### 1. members 与 payments
- 一个会员可以有多条支付记录 (1:N)
- 通过 `payments.member_id` 外键关联 `members.id`

### 2. packages 与 payments
- 一个套餐可以有多条支付记录 (1:N)
- 通过 `payments.package_id` 外键关联 `packages.id`

### 3. members 与 packages
- 间接关系，通过 `payments` 表关联
- 一个会员可以购买多个不同的套餐

## 数据库初始化

```sql
-- 创建数据库
CREATE DATABASE membership_renewal;

-- 使用数据库
\c membership_renewal;

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

## 数据迁移

数据库迁移文件位于 `backend/alembic/versions/` 目录下，使用 Alembic 进行版本管理。

```bash
# 生成迁移文件
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head
```

## 性能优化

1. **索引优化**
   - 为常用查询字段创建索引
   - 复合索引优化多条件查询

2. **查询优化**
   - 使用 JOIN 替代子查询
   - 避免 N+1 查询问题

3. **缓存策略**
   - 使用 Redis 缓存热点数据
   - 缓存会员状态和套餐信息

## 备份策略

1. **定期备份**
   - 每日全量备份
   - 每小时增量备份

2. **备份存储**
   - 本地存储
   - 云存储备份

## 监控指标

1. **性能指标**
   - 查询响应时间
   - 数据库连接数

2. **业务指标**
   - 支付成功率
   - 会员续费率

## 安全考虑

1. **数据加密**
   - 密码哈希存储
   - 敏感数据加密

2. **访问控制**
   - 数据库用户权限控制
   - SQL 注入防护

## 版本历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0.0 | 2023-01-01 | 初始版本 |
| 1.1.0 | 2023-02-01 | 添加支付状态索引 |
| 1.2.0 | 2023-03-01 | 优化会员状态查询 |