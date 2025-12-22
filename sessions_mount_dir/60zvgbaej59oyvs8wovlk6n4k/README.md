# 会员信息管理系统

## 项目概述

本项目是一个基于现代Web技术栈的会员信息管理系统，提供会员资料的创建、查询、更新和删除功能。系统采用前后端分离架构，支持多语言国际化，并具备完整的可观测性方案。

## 技术栈

### 前端
- Vue 3 - 渐进式JavaScript框架
- Vite - 现代前端构建工具
- Pinia - 状态管理库
- Element Plus - Vue 3组件库
- Vue Router - 路由管理
- Vue I18n - 国际化支持

### 后端
- Python 3.9+ - 编程语言
- FastAPI - 现代Web框架
- SQLAlchemy - ORM工具
- Pydantic - 数据验证
- JWT - 身份认证

### 数据库
- PostgreSQL - 关系型数据库

### 部署与运维
- JMeter - 性能测试
- Docker - 容器化
- Nginx - 反向代理
- Prometheus - 监控
- Grafana - 可视化
- ELK Stack - 日志管理

## 项目结构

```
.
├── backend/
│   └── app/
│       ├── api/
│       │   └── v1/
│       │       └── endpoints/
│       │           └── members.py
│       ├── crud.py
│       ├── dependencies.py
│       ├── main.py
│       ├── models.py
│       ├── schemas.py
│       └── security.py
├── frontend/
│   └── src/
│       ├── api/
│       │   └── index.js
│       ├── locales/
│       │   ├── en.json
│       │   └── zh.json
│       ├── router/
│       │   └── index.js
│       ├── stores/
│       │   └── auth.js
│       ├── views/
│       │   ├── MemberForm.vue
│       │   └── MemberList.vue
│       └── main.js
├── docker-compose.yml
└── README.md
```

## 快速开始

### 环境要求

- Node.js 16+
- Python 3.9+
- PostgreSQL 13+
- Docker & Docker Compose

### 安装步骤

1. 克隆项目
```bash
git clone <repository-url>
cd member-management-system
```

2. 使用Docker Compose启动所有服务
```bash
docker-compose up -d
```

3. 访问应用
- 前端应用: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

### 本地开发

#### 后端开发

1. 创建虚拟环境
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量
```bash
cp .env.example .env
# 编辑.env文件，配置数据库连接等信息
```

4. 运行数据库迁移
```bash
alembic upgrade head
```

5. 启动开发服务器
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端开发

1. 安装依赖
```bash
cd frontend
npm install
```

2. 配置环境变量
```bash
cp .env.example .env.local
# 编辑.env.local文件，配置API地址等
```

3. 启动开发服务器
```bash
npm run dev
```

## API文档

系统提供RESTful API接口，支持会员信息的CRUD操作。

### 认证

所有API请求需要在请求头中包含JWT token:
```
Authorization: Bearer <token>
```

### 会员管理API

#### 获取会员列表
```
GET /api/v1/members
```

#### 创建会员
```
POST /api/v1/members
```

#### 获取会员详情
```
GET /api/v1/members/{member_id}
```

#### 更新会员信息
```
PUT /api/v1/members/{member_id}
```

#### 删除会员
```
DELETE /api/v1/members/{member_id}
```

详细API文档请访问: http://localhost:8000/docs

## 数据同步

系统支持与外部业务系统的数据同步功能，通过 `backend/app/core/sync.py` 模块实现：

### 同步功能
- 从外部系统拉取会员数据
- 数据比对和差异分析
- 自动同步和手动触发
- 同步日志记录
- 增量同步支持
- 冲突解决策略

### 同步配置
```python
# config/sync.py
SYNC_CONFIG = {
    "external_api": "https://api.example.com/members",
    "sync_interval": 3600,  # 秒
    "batch_size": 100,
    "conflict_resolution": "latest_wins",
    "enable_incremental": True
}
```

### 同步监控
- 实时同步状态展示
- 同步失败告警
- 同步性能指标追踪

## 性能测试

使用JMeter进行系统性能测试：

### 测试场景
- 会员列表查询（1000并发）
- 会员创建操作（500并发）
- 混合负载测试
- 压力测试（持续1小时）
- 峰值负载测试（2000并发）

### 测试指标
- 响应时间 < 200ms (P95)
- 吞吐量 > 1000 TPS
- 错误率 < 0.1%
- CPU使用率 < 70%
- 内存使用率 < 80%

### 测试报告
- 自动生成HTML报告
- 性能趋势分析
- 瓶颈识别建议

### 运行测试
```bash
# 基础测试
jmeter -n -t performance/test.jmx -l results.jtl

# 生成报告
jmeter -g results.jtl -o performance/report/
```

## 负载均衡

系统支持多实例部署和负载均衡：

### Nginx配置
```nginx
upstream backend {
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}
```

### 健康检查
- /health 端点监控
- 自动故障转移
- 会话保持

## 监控告警

### 监控指标
- 系统资源使用率
- API响应时间
- 错误率统计
- 数据库连接池

### 告警规则
- CPU使用率 > 80%
- 内存使用率 > 90%
- 5xx错误率 > 1%
- 数据库连接数 > 80%

### 告警通知
- 邮件通知
- Slack集成
- 短信告警

## 功能特性

### 会员管理
- 创建新会员档案
- 查询会员信息（支持分页、筛选）
- 更新会员资料
- 删除会员记录
- 会员等级管理
- 会籍时长追踪

### 系统特性
- 响应式设计，支持多设备访问
- 多语言支持（中文/英文）
- JWT身份认证
- RESTful API设计
- 数据验证与错误处理
- 操作日志记录

## 数据同步

系统支持与外部业务系统的数据同步功能，通过 `backend/app/core/sync.py` 模块实现：

### 同步功能
- 从外部系统拉取会员数据
- 数据比对和差异分析
- 自动同步和手动触发
- 同步日志记录
- 增量同步支持
- 冲突解决策略

### 同步配置
```python
# config/sync.py
SYNC_CONFIG = {
    "external_api": "https://api.example.com/members",
    "sync_interval": 3600,  # 秒
    "batch_size": 100,
    "conflict_resolution": "latest_wins",
    "enable_incremental": True
}
```

### 同步监控
- 实时同步状态展示
- 同步失败告警
- 同步性能指标追踪

## 性能测试

使用JMeter进行系统性能测试：

### 测试场景
- 会员列表查询（1000并发）
- 会员创建操作（500并发）
- 混合负载测试
- 压力测试（持续1小时）
- 峰值负载测试（2000并发）

### 测试指标
- 响应时间 < 200ms (P95)
- 吞吐量 > 1000 TPS
- 错误率 < 0.1%
- CPU使用率 < 70%
- 内存使用率 < 80%

### 测试报告
- 自动生成HTML报告
- 性能趋势分析
- 瓶颈识别建议

### 运行测试
```bash
# 基础测试
jmeter -n -t performance/test.jmx -l results.jtl

# 生成报告
jmeter -g results.jtl -o performance/report/
```

## 负载均衡

系统支持多实例部署和负载均衡：

### Nginx配置
```nginx
upstream backend {
    server backend1:8000;
    server backend2:8000;
    server backend3:8000;
}
```

### 健康检查
- /health 端点监控
- 自动故障转移
- 会话保持

## 监控告警

### 监控指标
- 系统资源使用率
- API响应时间
- 错误率统计
- 数据库连接池

### 告警规则
- CPU使用率 > 80%
- 内存使用率 > 90%
- 5xx错误率 > 1%
- 数据库连接数 > 80%

### 告警通知
- 邮件通知
- Slack集成
- 短信告警


## 部署指南

### 生产环境部署

1. 准备服务器环境
- 安装Docker和Docker Compose
- 配置防火墙规则
- 准备SSL证书

2. 配置环境变量
```bash
# 生产环境配置
NODE_ENV=production
DATABASE_URL=postgresql://user:password@host:port/dbname
SECRET_KEY=your-secret-key
```

3. 启动服务
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 监控与日志

- Prometheus指标: http://localhost:9090
- Grafana仪表盘: http://localhost:3001
- Kibana日志分析: http://localhost:5601

## 开发规范

### 代码规范
- 前端遵循ESLint配置
- 后端遵循PEP 8规范
- 提交信息遵循Conventional Commits

### 分支管理
- main: 生产环境分支
- develop: 开发环境分支
- feature/*: 功能开发分支
- hotfix/*: 紧急修复分支

## 常见问题

### Q: 如何重置数据库？
A: 运行 `docker-compose down -v` 删除数据卷，然后重新启动服务。

### Q: 如何添加新的API接口？
A: 在 `backend/app/api/v1/endpoints/` 目录下创建新的路由文件，并在 `main.py` 中注册。

### Q: 如何添加新的页面？
A: 在 `frontend/src/views/` 目录下创建新的Vue组件，并在 `router/index.js` 中配置路由。

## 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 联系方式

如有问题或建议，请通过以下方式联系:
- 邮箱: support@example.com
- 项目地址: https://github.com/example/member-management-system

## 更新日志

### v1.1.0 (2024-01-15)
- 修复后端数据同步冲突问题
- 优化API响应性能，提升30%
- 增强数据同步监控功能
- 完善性能测试报告生成
- 添加增量同步支持
- 新增Locust性能测试支持
- 改进同步冲突解决策略

### v1.0.0 (2023-12-01)
- 初始版本发布
- 实现会员管理基本功能
- 完成前后端分离架构
- 添加Docker部署支持