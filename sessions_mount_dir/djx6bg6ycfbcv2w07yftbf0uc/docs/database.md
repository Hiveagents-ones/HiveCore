# 数据库设计文档

## 概述

本文档描述了健身房管理系统的数据库设计，主要包含会员表（members）的详细说明。

## 会员表（members）

### 表结构

| 字段名 | 数据类型 | 约束 | 描述 |
|--------|----------|------|------|
| id | Integer | PRIMARY KEY, AUTO_INCREMENT | 主键，自增ID |
| member_id | String(20) | UNIQUE, NOT NULL, INDEX | 会员唯一标识符 |
| name | String(100) | NOT NULL | 会员姓名 |
| phone | String(20) | UNIQUE, NOT NULL, INDEX | 手机号码 |
| id_card | String(18) | UNIQUE, NOT NULL, INDEX | 身份证号 |
| email | String(100) | UNIQUE, INDEX, NULLABLE | 电子邮箱 |
| address | String(255) | NULLABLE | 联系地址 |
| registration_date | DateTime(timezone) | NOT NULL, DEFAULT=now() | 注册日期 |
| status | Boolean | NOT NULL, DEFAULT=True | 会员状态（True: active, False: inactive） |
| created_at | DateTime(timezone) | NOT NULL, DEFAULT=now() | 创建时间 |
| updated_at | DateTime(timezone) | NOT NULL, DEFAULT=now(), ONUPDATE=now() | 更新时间 |

### 索引

| 索引名 | 字段 | 类型 |
|--------|------|------|
| idx_member_phone | phone | B-tree |
| idx_member_id_card | id_card | B-tree |
| idx_member_email | email | B-tree |
| idx_member_status | status | B-tree |

### 字段说明

- **id**: 主键，自增整数，用于唯一标识每条记录
- **member_id**: 业务层面的会员ID，格式为字符串，长度不超过20个字符
- **name**: 会员真实姓名，长度不超过100个字符
- **phone**: 手机号码，长度不超过20个字符，用于接收通知和验证
- **id_card**: 身份证号码，长度为18个字符，用于实名认证
- **email**: 电子邮箱，长度不超过100个字符，可选字段
- **address**: 联系地址，长度不超过255个字符，可选字段
- **registration_date**: 会员注册时间，带时区的时间戳
- **status**: 会员状态，True表示活跃会员，False表示非活跃会员
- **created_at**: 记录创建时间，带时区的时间戳
- **updated_at**: 记录最后更新时间，带时区的时间戳

### 业务规则

1. 会员注册时必须提供姓名、手机号和身份证号
2. 手机号和身份证号在系统中必须唯一
3. 会员ID由系统自动生成，保证唯一性
4. 新注册的会员默认状态为活跃（True）
5. 所有时间字段都使用UTC时区存储

### 示例数据

```sql
INSERT INTO members (member_id, name, phone, id_card, email, address, status) VALUES
('M20230001', '张三', '13800138000', '110101199001011234', 'zhangsan@example.com', '北京市朝阳区', true),
('M20230002', '李四', '13900139000', '110101199002022345', 'lisi@example.com', '上海市浦东新区', true),
('M20230003', '王五', '13700137000', '110101199003033456', NULL, '广州市天河区', false);
```

### 相关文件

- 后端模型定义: `backend/app/models.py`
- 后端数据模式: `backend/app/schemas.py`
- 注册路由: `backend/app/routers/register.py`

## 版本历史

| 版本 | 日期 | 修改内容 | 修改人 |
|------|------|----------|--------|
| 1.0 | 2023-12-01 | 初始版本，创建会员表结构 | 交付工程师 |