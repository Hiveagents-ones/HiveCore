# 健身房会员管理系统

## 项目概述

本项目是一个现代化的健身房会员管理系统，支持会员注册、会员卡管理等核心功能。系统采用前后端分离架构，提供友好的用户界面和高效的后端服务。

## 技术栈

- **前端**: Vue 3 + Vite + Pinia + Vue Router
- **后端**: Python + FastAPI + SQLAlchemy
- **数据库**: PostgreSQL
- **部署**: Docker + Docker Compose
- **国际化**: Vue I18n

## 项目结构

```
.
├── backend/                 # 后端服务
│   └── app/
│       ├── core/           # 核心模块
│       │   └── security.py # 安全相关
│       ├── models.py       # 数据模型
│       ├── routers/        # 路由
│       │   └── register.py # 注册路由
│       ├── schemas.py      # 数据模式
│       └── main.py         # 应用入口
├── frontend/               # 前端应用
│   └── src/
│       ├── services/       # API服务
│       │   └── api.js      # API接口
│       ├── stores/         # 状态管理
│       │   └── register.js # 注册状态
│       ├── locales/        # 国际化
│       │   ├── zh.json     # 中文语言包
│       │   └── en.json     # 英文语言包
│       └── views/          # 页面组件
│           └── RegisterView.vue # 注册页面
├── scripts/                # 脚本文件
│   └── backup_db.sh       # 数据库备份
├── docker-compose.yml      # Docker编排
└── README.md              # 项目文档
```

## 快速开始

### 环境要求

- Docker 20.10+
- Docker Compose 2.0+
- Node.js 18+ (开发环境)
- Python 3.9+ (开发环境)

### 安装与运行

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd gym-member-system
   ```

2. **使用Docker Compose启动服务**
   ```bash
   docker-compose up -d
   ```

3. **访问应用**
   - 前端应用: http://localhost:3000
   - 后端API: http://localhost:8000
   - API文档: http://localhost:8000/docs

### 开发环境设置

#### 后端开发

1. **安装依赖**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，配置数据库连接等
   ```

3. **运行开发服务器**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

#### 前端开发

1. **安装依赖**
   ```bash
   cd frontend
   npm install
   ```

2. **配置环境变量**
   ```bash
   cp .env.example .env.local
   # 编辑 .env.local 文件，配置API地址等
   ```

3. **运行开发服务器**
   ```bash
   npm run dev
   ```

## 功能说明

### 会员注册 (R1)

新用户可以通过系统注册成为健身房会员，功能包括：

- 收集用户基本信息（姓名、手机号、身份证号）
- 支持选择会员卡类型（月卡、季卡、年卡）
- 自动生成唯一的会员ID
- 表单验证和错误提示
- 多语言支持（中文/英文）

#### API接口

- **POST** `/api/register` - 会员注册
  ```json
  {
    "name": "张三",
    "phone": "13800138000",
    "id_card": "110101199001011234",
    "card_type": "monthly"
  }
  ```

#### 前端组件

- `RegisterView.vue` - 注册页面主组件
- `register.js` - Pinia状态管理
- `api.js` - API服务封装

## 测试

### 后端测试

```bash
cd backend
pytest tests/ -v
```

### 前端测试

```bash
cd frontend
npm run test
```

### E2E测试

```bash
npm run test:e2e
```

## 部署

### 生产环境部署

1. **构建镜像**
   ```bash
   docker-compose -f docker-compose.prod.yml build
   ```

2. **启动服务**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

### 数据库备份

使用提供的备份脚本：

```bash
./scripts/backup_db.sh
```

## 验收标准

### R1 会员注册功能验收

- [ ] 用户可以填写姓名、手机号、身份证号
- [ ] 用户可以选择会员卡类型（月卡、季卡、年卡）
- [ ] 表单验证：手机号格式、身份证号格式
- [ ] 注册成功后显示会员ID
- [ ] 支持中英文切换
- [ ] 响应式设计，适配移动端
- [ ] API响应时间 < 500ms
- [ ] 数据持久化存储

## 维护与监控

### 日志查看

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 健康检查

- 后端健康检查: `GET /health`
- 数据库连接检查: `GET /health/db`

## 常见问题

### Q: 如何重置数据库？

A: 使用以下命令：
```bash
docker-compose down -vdocker-compose up -d
```

### Q: 如何添加新的会员卡类型？

A: 需要修改以下文件：
1. `backend/app/models.py` - 添加新的卡类型
2. `frontend/src/locales/zh.json` 和 `en.json` - 添加翻译
3. `frontend/src/views/RegisterView.vue` - 更新UI选项

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

- 项目维护者: [Your Name](mailto:your.email@example.com)
- 项目地址: [GitHub Repository](https://github.com/your-username/gym-member-system)

## 更新日志

### v1.0.0 (2024-01-01)
- 初始版本发布
- 实现会员注册功能
- 支持多语言
- Docker化部署
