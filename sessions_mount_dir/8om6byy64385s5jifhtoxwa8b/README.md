# 会员信息管理系统

## 项目简介

本项目是一个基于 Vue 3 和 FastAPI 的会员信息管理系统，提供会员档案的创建、查询、更新和删除功能。系统采用前后端分离架构，支持现代化的 Web 开发实践。

## 功能特性

- ✅ 会员档案管理（CRUD）
  - 创建新会员
  - 查询会员信息
  - 更新会员资料
  - 删除会员记录
- ✅ 会员信息字段
  - 姓名
  - 联系方式
  - 会员等级
  - 剩余会籍
- ✅ 响应式界面设计
- ✅ RESTful API 接口
- ✅ 数据库迁移管理
- ✅ 权限管理系统（RBAC）
- ✅ 操作审计日志
- ✅ 数据导出功能
- ✅ 多语言支持（中文/英文）
- ✅ 数据备份与恢复

## 技术栈

### 前端
- Vue 3 - 渐进式 JavaScript 框架
- Vite - 现代化前端构建工具
- Pinia - Vue 状态管理库
- Vue Router - Vue 官方路由管理器
- Element Plus - Vue 3 组件库
- Vue I18n - Vue 国际化插件

### 后端
- Python - 编程语言
- FastAPI - 现代、快速的 Web 框架
- SQLAlchemy - Python SQL 工具包和 ORM
- Pydantic - 数据验证库
- Alembic - 数据库迁移工具
- Celery - 分布式任务队列（用于异步导出）

### 数据库
- PostgreSQL - 开源对象关系数据库系统

## 项目结构

```
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       └── endpoints/
│   │   │           └── members.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── models/
│   │   │   └── member.py
│   │   ├── schemas/
│   │   │   └── member.py
│   │   ├── crud/
│   │   │   └── member.py
│   │   └── main.py
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── member.js
│   │   ├── views/
│   │   │   ├── MemberList.vue
│   │   │   └── MemberForm.vue
│   │   └── ...
├── alembic.ini

├── scripts/
│   ├── backup.sh
│   └── restore.sh
├── docs/
│   ├── deployment.md
│   └── backup-restore.md
├── tests/
│   ├── test_permissions.py
│   ├── test_export.py
│   └── test_member_api.py
├── docker-compose.yml
└── README.md
```

## 快速开始

### 环境要求

- Node.js >= 16.0.0
- Python >= 3.8
- PostgreSQL >= 12

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd member-management-system
   ```

2. **后端设置**
   ```bash
   cd backend
   
   # 创建虚拟环境
   python -m venv venv
   
   # 激活虚拟环境
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   
   # 安装依赖
   pip install -r requirements.txt
   ```

3. **数据库设置**
   ```bash
   # 创建数据库
   createdb member_management
   
   # 运行数据库迁移
   alembic upgrade head
   ```

4. **前端设置**
   ```bash
   cd frontend
   
   # 安装依赖
   npm install
   ```

### 运行项目

1. **启动后端服务**
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **启动前端服务**
   ```bash
   cd frontend
   npm run dev
   ```

3. **访问应用**
   - 前端界面: http://localhost:5173
   - 后端 API 文档: http://localhost:8000/docs

## API 接口

### 会员管理接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/v1/members/ | 获取会员列表 |
| GET | /api/v1/members/{id} | 获取单个会员信息 |
| POST | /api/v1/members/ | 创建新会员 |
| PUT | /api/v1/members/{id} | 更新会员信息 |
| DELETE | /api/v1/members/{id} | 删除会员 |

| GET | /api/v1/export/members | 导出会员数据 |
| GET | /api/v1/audit/logs | 获取审计日志 |

### 请求示例

#### 创建会员
```json
POST /api/v1/members/
{
  "name": "张三",
  "contact": "13800138000",
  "level": "VIP",
  "remaining_membership": 365
}
```

#### 更新会员
```json
PUT /api/v1/members/1
{
  "name": "张三",
  "contact": "13900139000",
  "level": "SVIP",
  "remaining_membership": 730
}
```

## 部署指南

### 生产环境部署

1. **后端部署**
   ```bash
   # 安装生产依赖
   pip install gunicorn
   
   # 启动生产服务器
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
   ```

2. **前端部署**
   ```bash
   # 构建生产版本
   npm run build
   
   # 部署 dist 目录到 Web 服务器
   ```

3. **数据库配置**
   - 修改 `backend/app/core/config.py` 中的数据库连接字符串
   - 运行 `alembic upgrade head` 更新数据库结构

### Docker 部署

```dockerfile
# Dockerfile 示例
FROM python:3.9

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .

CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

## 开发指南

### 添加新功能

1. **后端**
   - 在 `backend/app/models/` 中定义数据模型
   - 在 `backend/app/schemas/` 中定义 Pydantic 模型
   - 在 `backend/app/crud/` 中实现数据库操作
   - 在 `backend/app/api/v1/endpoints/` 中创建 API 端点

2. **前端**
   - 在 `frontend/src/api/` 中添加 API 调用
   - 在 `frontend/src/views/` 中创建页面组件
   - 在 `frontend/src/router/` 中配置路由

### 代码规范

- 后端遵循 PEP 8 Python 代码规范
- 前端遵循 Vue 3 官方风格指南
- 使用 ESLint 和 Prettier 格式化前端代码
- 使用 Black 格式化后端代码

## 常见问题

### Q: 如何修改数据库连接配置？
A: 编辑 `backend/app/core/config.py` 文件中的 `DATABASE_URL` 变量。

### Q: 如何添加新的会员字段？
A: 
1. 修改 `backend/app/models/member.py` 中的 Member 模型
2. 更新 `backend/app/schemas/member.py` 中的 Pydantic 模型
3. 运行 `alembic revision --autogenerate -m "描述"` 生成迁移
4. 运行 `alembic upgrade head` 应用迁移

### Q: 如何自定义 API 前缀？
A: 修改 `backend/app/main.py` 中的 APIRouter 配置。

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 邮箱: support@example.com
- 项目地址: https://github.com/example/member-management-system

## 更新日志

### v1.0.0 (2024-01-01)
- 初始版本发布
- 实现会员 CRUD 功能
- 完成前后端基础架构
