# 会员信息管理系统部署指南

本文档详细说明了如何部署会员信息管理系统，包括环境准备、依赖安装、配置设置和启动步骤。

## 目录

- [系统要求](#系统要求)
- [环境准备](#环境准备)
- [后端部署](#后端部署)
- [前端部署](#前端部署)
- [数据库设置](#数据库设置)
- [定时任务配置](#定时任务配置)
- [备份与恢复](#备份与恢复)
- [监控与日志](#监控与日志)
- [故障排除](#故障排除)

## 系统要求

### 硬件要求

- CPU: 2核心以上
- 内存: 4GB以上
- 存储: 20GB以上可用空间

### 软件要求

- 操作系统: Linux (推荐Ubuntu 20.04+), macOS, Windows 10+
- Docker: 20.10+
- Docker Compose: 1.29+
- Node.js: 16+ (用于本地开发)
- Python: 3.9+ (用于本地开发)
- PostgreSQL: 13+ (如果不使用Docker)

## 环境准备

### 1. 克隆项目

```bash
git clone https://github.com/your-org/member-management-system.git
cd member-management-system
```

### 2. 创建环境变量文件

```bash
# 后端环境变量
cp backend/.env.example backend/.env

# 前端环境变量
cp frontend/.env.example frontend/.env
```

### 3. 编辑环境变量

编辑 `backend/.env` 文件，设置以下变量:

```env
# 数据库配置
DATABASE_URL=postgresql://username:password@localhost:5432/member_management

# JWT配置
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 其他配置
DEBUG=False
LOG_LEVEL=INFO
```

编辑 `frontend/.env` 文件，设置以下变量:

```env
# API地址
VITE_API_BASE_URL=http://localhost:8000/api/v1

# 其他配置
VITE_APP_TITLE=会员信息管理系统
```

## 后端部署

### 使用Docker部署 (推荐)

1. 构建后端Docker镜像:

```bash
cd backend
docker build -t member-management-backend .
```

2. 运行后端容器:

```bash
docker run -d \
  --name member-backend \
  -p 8000:8000 \
  --env-file .env \
  member-management-backend
```

### 本地部署

1. 安装依赖:

```bash
cd backend
pip install -r requirements.txt
```

2. 初始化数据库:

```bash
alembic upgrade head
```

3. 启动后端服务:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 前端部署

### 使用Docker部署 (推荐)

1. 构建前端Docker镜像:

```bash
cd frontend
docker build -t member-management-frontend .
```

2. 运行前端容器:

```bash
docker run -d \
  --name member-frontend \
  -p 80:80 \
  member-management-frontend
```

### 本地部署

1. 安装依赖:

```bash
cd frontend
npm install
```

2. 构建生产版本:

```bash
npm run build
```

3. 使用Web服务器托管构建文件:

```bash
# 使用nginx
sudo cp -r dist/* /var/www/html/

# 或者使用简单的HTTP服务器
npm install -g serve
serve -s dist -l 80
```

## 数据库设置

### 使用Docker部署PostgreSQL

1. 启动PostgreSQL容器:

```bash
docker run -d \
  --name member-postgres \
  -e POSTGRES_USER=member_user \
  -e POSTGRES_PASSWORD=member_password \
  -e POSTGRES_DB=member_management \
  -p 5432:5432 \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:13
```

2. 更新后端环境变量中的数据库URL:

```env
DATABASE_URL=postgresql://member_user:member_password@localhost:5432/member_management
```

### 本地安装PostgreSQL

1. 安装PostgreSQL:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql
brew services start postgresql

# Windows
# 下载并安装PostgreSQL官方安装包
```

2. 创建数据库和用户:

```bash
sudo -u postgres psql
CREATE DATABASE member_management;
CREATE USER member_user WITH PASSWORD 'member_password';
GRANT ALL PRIVILEGES ON DATABASE member_management TO member_user;
\q
```

3. 更新后端环境变量中的数据库URL:

```env
DATABASE_URL=postgresql://member_user:member_password@localhost:5432/member_management
```

## 定时任务配置

系统使用Celery处理异步任务，如数据导出。以下是配置步骤:

### 1. 启动Redis (作为Celery消息代理)

```bash
docker run -d --name member-redis -p 6379:6379 redis:6-alpine
```

### 2. 启动Celery Worker

```bash
cd backend
celery -A app.core.celery worker --loglevel=info
```

### 3. 启动Celery Beat (定时任务调度器)

```bash
cd backend
celery -A app.core.celery beat --loglevel=info
```

### 4. 配置定时任务

编辑 `backend/app/core/celery.py` 文件，添加或修改定时任务:

```python
from celery.schedules import crontab

# 示例: 每天凌晨2点执行数据备份
beat_schedule = {
    'daily-backup': {
        'task': 'app.tasks.backup_data',
        'schedule': crontab(hour=2, minute=0),
    },
}
```

## 备份与恢复

系统提供了备份和恢复脚本，位于 `scripts/` 目录下。

### 数据备份

使用 `scripts/backup.sh` 脚本进行数据备份:

```bash
# 设置执行权限
chmod +x scripts/backup.sh

# 执行备份
./scripts/backup.sh
```

备份文件将保存在 `backups/` 目录下，文件名格式为 `backup_YYYYMMDD_HHMMSS.sql`。

### 数据恢复

使用 `scripts/restore.sh` 脚本进行数据恢复:

```bash
# 设置执行权限
chmod +x scripts/restore.sh

# 执行恢复 (指定备份文件)
./scripts/restore.sh backups/backup_20230101_120000.sql
```

### 自动备份配置

可以通过Cron配置自动备份:

```bash
# 编辑Cron任务
crontab -e

# 添加以下行，每天凌晨3点执行备份
0 3 * * * /path/to/member-management-system/scripts/backup.sh
```

## 监控与日志

### 日志配置

后端日志配置在 `backend/app/core/logging.py` 文件中:

```python
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler('logs/app.log', maxBytes=10485760, backupCount=5),
            logging.StreamHandler()
        ]
    )
```

日志文件保存在 `backend/logs/` 目录下。

### 监控配置

可以使用以下工具监控系统状态:

1. **Prometheus + Grafana**: 用于系统指标监控
2. **ELK Stack**: 用于日志聚合和分析
3. **Sentry**: 用于错误追踪

### 健康检查端点

系统提供了健康检查端点:

```bash
# 后端健康检查
curl http://localhost:8000/health

# 前端健康检查
curl http://localhost/health
```

## 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库服务是否运行
   - 验证数据库URL配置是否正确
   - 确认数据库用户权限

2. **前端无法访问后端API**
   - 检查后端服务是否运行
   - 验证API地址配置是否正确
   - 检查防火墙设置

3. **Celery任务不执行**
   - 检查Redis服务是否运行
   - 验证Celery Worker是否启动
   - 检查任务队列配置

4. **备份失败**
   - 检查数据库连接
   - 验证备份目录权限
   - 检查磁盘空间

### 日志分析

查看应用日志:

```bash
# 后端日志
tail -f backend/logs/app.log

# Docker容器日志
docker logs member-backend
docker logs member-frontend
docker logs member-postgres
```

### 性能优化

1. **数据库优化**
   - 定期执行VACUUM和ANALYZE
   - 适当调整PostgreSQL配置参数
   - 为常用查询添加索引

2. **后端优化**
   - 使用连接池
   - 启用API缓存
   - 优化查询语句

3. **前端优化**
   - 启用Gzip压缩
   - 使用CDN加速静态资源
   - 实现代码分割和懒加载

## 安全建议

1. **定期更新依赖**
   - 定期检查并更新系统依赖
   - 使用安全扫描工具检查漏洞

2. **访问控制**
   - 实施强密码策略
   - 启用双因素认证
   - 限制API访问频率

3. **数据保护**
   - 加密敏感数据
   - 定期备份数据
   - 实施数据访问审计

## 更新与维护

### 系统更新

1. 获取最新代码:

```bash
git pull origin main
```

2. 更新后端:

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
```

3. 更新前端:

```bash
cd frontend
npm install
npm run build
```

4. 重启服务:

```bash
docker-compose restart
```

### 定期维护

1. **每周任务**
   - 检查系统日志
   - 监控系统性能
   - 验证备份完整性

2. **每月任务**
   - 更新系统依赖
   - 清理旧日志文件
   - 审查用户权限

3. **每季度任务**
   - 全面系统安全审计
   - 性能基准测试
   - 灾难恢复演练

## 联系支持

如果在部署过程中遇到问题，请联系技术支持团队:

- 邮箱: support@example.com
- 电话: +1 (123) 456-7890
- 在线支持: https://support.example.com

---

本文档最后更新于: 2023-01-01