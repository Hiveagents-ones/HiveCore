# 健身房会员注册系统

## 项目概述

本项目是一个基于现代Web技术栈的健身房会员注册系统，支持新用户注册、会员套餐选择和在线支付功能。

## 技术架构

### 前端技术栈
- Vue 3 - 渐进式JavaScript框架
- Vite - 现代前端构建工具
- Pinia - Vue状态管理库
- Vue Router - Vue官方路由管理器
- Element Plus - Vue 3 UI组件库

### 后端技术栈
- Python - 编程语言
- FastAPI - 现代Web框架
- SQLAlchemy - Python SQL工具包
- Pydantic - 数据验证库

### 数据库
- PostgreSQL - 关系型数据库

### 部署与监控
- Docker - 容器化部署
- Nginx - 反向代理服务器
- Prometheus + Grafana - 监控系统

## 项目结构

```
.
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   └── RegisterView.vue    # 注册页面组件
│   │   ├── stores/
│   │   │   └── register.js         # 注册状态管理
│   │   ├── services/
│   │   │   └── api.js              # API服务封装
│   │   ├── router/
│   │   │   └── index.js            # 路由配置
│   │   └── main.js                 # 前端入口文件
├── backend/
│   └── app/
│       ├── main.py                 # 后端入口文件
│       ├── models.py               # 数据库模型
│       ├── schemas.py              # Pydantic模式
│       ├── routers/
│       │   └── register.py         # 注册路由
│       └── core/
│           └── config.py           # 配置文件
├── docker-compose.yml              # Docker编排文件
└── README.md                       # 项目说明文档
```

## 快速开始

### 环境要求

- Node.js >= 16.0.0
- Python >= 3.8
- PostgreSQL >= 12
- Docker >= 20.10
- Docker Compose >= 1.29

### 本地开发

1. 克隆项目
```bash
git clone <repository-url>
cd gym-member-registration
```

2. 启动数据库
```bash
docker-compose up -d postgres
```

3. 后端启动
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. 前端启动
```bash
cd frontend
npm install
npm run dev
```

5. 访问应用
- 前端: http://localhost:5173
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

### Docker部署

1. 构建并启动所有服务
```bash
docker-compose up -d
```

2. 查看服务状态
```bash
docker-compose ps
```

3. 查看日志
```bash
docker-compose logs -f
```

## API接口

### 注册接口

**POST** `/api/register`

请求体:
```json
{
  "name": "张三",
  "phone": "13800138000",
  "id_card": "110101199001011234",
  "package_id": 1,
  "payment_method": "wechat"
}
```

响应:
```json
{
  "id": 1,
  "name": "张三",
  "phone": "13800138000",
  "id_card": "110101199001011234",
  "package_id": 1,
  "payment_method": "wechat",
  "status": "active",
  "created_at": "2023-01-01T00:00:00"
}
```

## 核心功能

### 会员注册流程
1. 用户填写个人信息（姓名、手机号、身份证号）
2. 选择会员套餐
3. 选择支付方式
4. 完成支付
5. 注册成功

### 数据验证
- 前端使用Element Plus表单验证
- 后端使用Pydantic进行数据验证
- 数据库层面确保数据完整性

## 监控与日志

- Prometheus指标: http://localhost:9090
- Grafana仪表盘: http://localhost:3000
- 应用日志: 通过docker-compose logs查看

## 配置说明

### 环境变量

创建`.env`文件:
```
# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/gym_db

# JWT配置
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 支付配置
WECHAT_APP_ID=your-wechat-app-id
WECHAT_APP_SECRET=your-wechat-app-secret
```

### 数据库初始化

```bash
cd backend
python -m app.models
```

## 常见问题

### Q: 如何添加新的会员套餐？
A: 直接在数据库的`packages`表中插入新记录即可。

### Q: 如何修改支付方式？
A: 在`backend/app/core/config.py`中修改`PAYMENT_METHODS`配置。

### Q: 如何扩展新的注册字段？
A: 需要同时修改:
- `frontend/src/views/RegisterView.vue` - 添加表单字段
- `frontend/src/stores/register.js` - 添加状态
- `backend/app/models.py` - 添加数据库字段
- `backend/app/schemas.py` - 添加验证模式

## 贡献指南

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

## 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

- 项目维护者: [Your Name](mailto:your.email@example.com)
- 项目地址: [GitHub Repository](https://github.com/your-username/gym-member-registration)

## 更新日志

### v1.0.0 (2023-01-01)
- 初始版本发布
- 实现会员注册核心功能
- 支持微信和支付宝支付
- 完成Docker部署配置