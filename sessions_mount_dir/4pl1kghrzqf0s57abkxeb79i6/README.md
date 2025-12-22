# 健身房会员管理系统

## 项目简介

本项目是一个现代化的健身房会员管理系统，旨在提供全面的会员管理、课程预约、教练排班和收费管理功能。系统采用前后端分离架构，提供高效、稳定、易用的管理体验。

## 功能特性

### 会员管理 (R1)
- 完整的会员信息管理（姓名、性别、年龄、联系方式）
- 会员卡类型管理（月卡、季卡、年卡等）
- 会员状态跟踪（活跃、冻结、过期）
- 入场记录管理
- 健身目标设定与跟踪
- 会员信息的增删改查操作
- 批量导入导出功能
- 会员卡续费和升级操作

### 课程管理
- 课程信息维护
- 课程类型分类
- 课程预约管理
- 预约记录查询

### 教练管理
- 教练信息管理
- 排班计划制定
- 请假调班处理

### 收费管理
- 多种收费方式支持
- 收费记录管理
- 退款处理

## 技术栈

### 前端
- **Vue 3** - 渐进式JavaScript框架
- **Vite** - 快速构建工具
- **Pinia** - 状态管理
- **Vue Router** - 路由管理
- **Element Plus** - UI组件库

### 后端
- **FastAPI** - 现代化Python Web框架
- **SQLAlchemy** - ORM框架
- **Pydantic** - 数据验证
- **Alembic** - 数据库迁移工具

### 数据库
- **PostgreSQL** - 关系型数据库

### 部署与监控
- **Docker** - 容器化部署
- **Nginx** - 反向代理
- **Prometheus** - 监控系统
- **Grafana** - 监控可视化
- **Python logging + Loki** - 日志管理

## 项目结构

```
.
├── backend/
│   └── app/
│       ├── main.py              # 后端入口文件
│       ├── database.py          # 数据库配置
│       ├── models.py            # 数据模型
│       ├── schemas.py           # Pydantic模型
│       ├── core/
│       │   ├── security.py      # 安全相关
│       │   └── config.py        # 配置管理
│       └── routers/
│           ├── __init__.py      # 路由初始化
│           ├── members.py       # 会员管理路由
│           ├── courses.py       # 课程管理路由
│           ├── coaches.py       # 教练管理路由
│           ├── payments.py      # 收费管理路由
│           └── reports.py       # 报表管理路由
├── frontend/
│   └── src/
│       ├── main.js              # 前端入口
│       ├── router/
│       │   └── index.js         # 路由配置
│       ├── stores/
│       │   └── member.js        # 会员状态管理
│       ├── api/
│       │   └── member.js        # 会员API接口
│       ├── views/
│       │   ├── MemberList.vue   # 会员列表页面
│       │   └── MemberDetail.vue # 会员详情页面
│       └── components/
│           └── MemberCardRenew.vue # 会员卡续费组件
├── docker-compose.yml           # Docker编排文件
└── README.md                    # 项目说明文档
```

## API 接口

### 会员管理
- `GET /api/v1/members` - 获取会员列表
- `POST /api/v1/members` - 创建新会员
- `PUT /api/v1/members/{member_id}` - 更新会员信息
- `DELETE /api/v1/members/{member_id}` - 删除会员
- `POST /api/v1/members/batch` - 批量导入会员
- `GET /api/v1/members/batch` - 批量导出会员
- `POST /api/v1/members/{member_id}/renew` - 会员卡续费

### 课程管理
- `GET /api/v1/courses` - 获取课程列表
- `POST /api/v1/courses` - 创建新课程
- `PUT /api/v1/courses/{course_id}` - 更新课程信息
- `DELETE /api/v1/courses/{course_id}` - 删除课程
- `POST /api/v1/courses/{course_id}/book` - 预约课程
- `DELETE /api/v1/courses/{course_id}/book` - 取消预约
- `GET /api/v1/courses/{course_id}/bookings` - 获取课程预约记录

### 教练管理
- `GET /api/v1/coaches/schedules` - 获取教练排班
- `POST /api/v1/coaches/schedules` - 创建排班
- `PUT /api/v1/coaches/schedules/{schedule_id}` - 更新排班
- `DELETE /api/v1/coaches/schedules/{schedule_id}` - 删除排班
- `POST /api/v1/coaches/{coach_id}/leave` - 教练请假
- `PUT /api/v1/coaches/{coach_id}/leave` - 调班处理

### 收费管理
- `GET /api/v1/payments` - 获取收费记录
- `POST /api/v1/payments` - 创建收费记录
- `PUT /api/v1/payments/{payment_id}` - 更新收费记录
- `POST /api/v1/payments/refund` - 退款处理

## 快速开始

### 环境要求
- Docker & Docker Compose
- Node.js 16+
- Python 3.9+
- PostgreSQL 13+

### 使用 Docker 部署

1. 克隆项目
```bash
git clone <repository-url>
cd gym-management-system
```

2. 启动服务
```bash
docker-compose up -d
```

3. 访问应用
- 前端应用: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

### 本地开发

#### 后端开发

1. 安装依赖
```bash
cd backend
pip install -r requirements.txt
```

2. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库连接等信息
```

3. 初始化数据库
```bash
alembic upgrade head
```

4. 启动开发服务器
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端开发

1. 安装依赖
```bash
cd frontend
npm install
```

2. 启动开发服务器
```bash
npm run dev
```

## 部署指南

### 生产环境部署

1. 准备服务器环境
- 安装 Docker 和 Docker Compose
- 配置防火墙规则
- 准备 SSL 证书

2. 配置环境变量
```bash
# 生产环境配置
cp .env.example .env.production
# 编辑生产环境配置
```

3. 构建和部署
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

4. 配置 Nginx
```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 监控和日志

### 监控配置
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001

### 日志查看
```bash
# 查看应用日志
docker-compose logs -f app

# 查看Nginx日志
docker-compose logs -f nginx
```

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 联系方式

- 项目维护者: [Your Name]
- 邮箱: [your.email@example.com]
- 项目地址: [https://github.com/yourusername/gym-management-system]

## 更新日志

### v1.0.0 (2024-01-01)
- 初始版本发布
- 实现会员管理核心功能
- 完成基础课程管理
- 添加收费管理模块

### v1.1.0 (计划中)
- 增加移动端支持
- 优化批量操作性能
- 添加数据报表功能
- 完善权限管理系统