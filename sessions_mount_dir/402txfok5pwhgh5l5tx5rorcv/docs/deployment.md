# 系统部署手册

## 1. 环境准备

### 1.1 系统要求
- 操作系统：Linux (Ubuntu 20.04+ 推荐) / macOS / Windows 10+
- Docker：20.10+
- Docker Compose：1.29+
- Git：2.25+
- Python：3.9+ (本地开发)
- Node.js：16+ (本地开发)

### 1.2 端口分配
- 前端服务：80 (HTTP)
- 后端服务：8000 (API)
- 数据库：5432 (PostgreSQL)
- Redis缓存：6379
- Nginx代理：5173
- Prometheus：9091
- Grafana：3000

## 2. 依赖安装

### 2.1 安装 Docker 和 Docker Compose

#### 本地开发环境准备
```bash
# 安装 Python 3.9+
# Ubuntu/Debian
sudo apt-get install python3.9 python3.9-venv python3.9-dev

# 安装 Node.js 16+
curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -
sudo apt-get install -y nodejs

# macOS
brew install python@3.9 node

# Windows
# 从官网下载安装包
# Python: https://www.python.org/downloads/
# Node.js: https://nodejs.org/
```

#### Ubuntu/Debian
```bash
# 更新包索引
sudo apt-get update

# 安装必要的包
sudo apt-get install \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# 添加 Docker 官方 GPG 密钥
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 设置稳定版仓库
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker Engine
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### macOS
```bash
# 使用 Homebrew 安装
brew install --cask docker
```

#### Windows
下载并安装 Docker Desktop：https://www.docker.com/products/docker-desktop

### 2.2 验证安装
```bash
docker --version
docker-compose --version
```

## 3. 项目部署

### 3.1 获取源代码
```bash
git clone <repository-url>
cd <project-directory>
```

### 3.2 配置环境变量
创建 `.env` 文件（可选，用于覆盖默认配置）：
```env
# 数据库配置
POSTGRES_DB=member_management
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password

# 后端配置
DATABASE_URL=postgresql://postgres:password@db:5432/member_management
REDIS_URL=redis://redis:6379
PYTHONPATH=/app
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:80,http://localhost:3000,http://localhost:5173

# 前端配置
VITE_API_URL=http://localhost:8000
VITE_ENV=development
NODE_ENV=development

# 监控配置
GF_SECURITY_ADMIN_PASSWORD=admin
```

### 3.3 构建和启动服务
```bash
# 构建并启动所有服务
docker-compose up -d --build

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

## 4. 数据库初始化

### 4.1 等待数据库就绪
```bash
# 检查数据库健康状态
docker-compose exec db pg_isready -U postgres
```

### 4.2 运行数据库迁移
```bash
# FastAPI 会自动创建表（通过 SQLAlchemy）
# 初始化元数据（如果需要）
docker-compose exec db psql -U postgres -d member_management -c "\dt"

# 手动运行迁移脚本（如果有）
docker-compose exec backend alembic upgrade head
```

### 4.3 验证数据库
```bash
# 连接数据库
docker-compose exec db psql -U postgres -d member_management

# 查看表结构
\dt

# 退出
\q
```

## 5. 应用启动验证

### 5.1 后端服务验证
```bash
# 检查后端健康状态
curl http://localhost:8000/health

# 测试 API 端点
curl http://localhost:8000/api/v1/members
curl http://localhost:8000/api/v1/courses

# 测试Redis缓存
curl http://localhost:8000/api/v1/cache/status

# 查看API文档
open http://localhost:8000/docs
```

### 5.2 前端服务验证
```bash
# 检查前端是否可访问
curl -I http://localhost

# 在浏览器中访问
http://localhost

# 通过Nginx代理访问
http://localhost:5173
```

### 5.3 端到端测试
1. 在浏览器中打开 http://localhost
2. 测试会员管理功能：
   - 创建新会员
   - 查询会员列表
   - 更新会员信息
   - 删除会员
3. 测试课程管理功能：
   - 创建新课程
   - 查看课程表
   - 预约课程
   - 取消预约
4. 验证缓存功能：
   - 检查课程列表加载速度
   - 验证缓存更新机制

## 6. 常见问题排查


### 6.1 Redis连接问题
```bash
# 检查Redis状态
docker-compose exec redis redis-cli ping

# 查看Redis日志
docker-compose logs redis

# 测试连接
docker-compose exec backend curl -f http://localhost:8000/health

# 检查Redis配置
docker-compose exec redis redis-cli config get *
```

### 6.2 服务无法启动
```bash
# 查看详细日志
docker-compose logs <service-name>

# 检查端口占用
sudo netstat -tulpn | grep <port>
```

### 6.3 数据库连接失败
```bash
# 检查数据库状态
docker-compose exec db pg_isready

# 验证连接字符串
echo $DATABASE_URL
```

### 6.4 前端无法访问后端

### 6.5 数据库迁移失败
```bash
# 检查数据库连接
docker-compose exec db pg_isready -U postgres

# 查看迁移日志
docker-compose logs backend | grep -i migration

# 重置数据库（谨慎操作）
docker-compose down -v
docker-compose up -d db
# 等待数据库就绪后重新运行迁移
```
1. 检查 `VITE_API_URL` 配置
2. 确认后端服务健康状态
3. 检查网络连接
4. 验证CORS配置
5. 检查Nginx代理配置

## 7. 维护操作

### 7.1 更新应用
```bash
# 拉取最新代码
git pull

# 重新构建和部署
docker-compose up -d --build
```

### 7.2 备份数据库
```bash
# 创建备份
docker-compose exec db pg_dump -U postgres member_management > backup.sql

# 恢复备份
docker-compose exec -T db psql -U postgres member_management < backup.sql
```

### 7.3 停止服务
```bash
# 停止所有服务
docker-compose down

# 停止并删除卷（谨慎操作）
docker-compose down -v
```

## 8. 监控和日志

### 8.1 实时监控
```bash
# 监控所有服务
docker-compose logs -f

# 监控特定服务
docker-compose logs -f <service-name>
```

### 8.2 资源使用情况
```bash
# 查看容器资源使用
docker stats

# 查看磁盘使用
docker system df

# 清理未使用的资源
docker system prune -a
```

### 8.3 Prometheus 和 Grafana 监控
```bash
# 访问 Prometheus
http://localhost:9091

# 访问 Grafana (默认账号: admin/admin)
http://localhost:3000

# 查看 Prometheus 目标
curl http://localhost:9091/api/v1/targets
```

## 9. 安全注意事项

1. 修改默认数据库密码
2. 使用 HTTPS（生产环境）
3. 定期更新基础镜像
4. 限制数据库访问权限
5. 启用防火墙规则
6. Redis安全配置
   - 设置Redis密码认证
   - 禁用危险命令
   - 限制网络访问
7. FastAPI 安全配置
   - 启用 OAuth2 认证
   - 配置 JWT 认证
   - 设置 CORS 策略
   - 启用请求限流
   - 使用中间件进行审计日志
8. 监控安全
   - 修改 Grafana 默认密码
   - 限制 Prometheus 访问
9. 数据脱敏
   - 敏感数据加密存储
   - API响应数据脱敏
   - 日志敏感信息过滤

## 10. 性能优化建议

1. 调整 FastAPI 数据库连接池配置
2. 配置 Nginx 缓存和负载均衡
3. 启用 Gzip 压缩
4. 使用 CDN 加速静态资源
5. 定期清理 Docker 镜像和卷
6. Redis缓存优化
   - 合理设置过期时间
   - 使用 Redis 连接池
   - 监控内存使用
   - 使用 Redis 集群（生产环境）
7. PostgreSQL 优化
   - 创建适当索引
   - 定期执行 VACUUM
   - 调整 shared_buffers 等参数
   - 使用连接池
8. FastAPI 应用优化
   - 启用异步处理（async/await）
   - 使用 SQLAlchemy 分页
   - 配置合适的 Uvicorn 参数
   - 启用 Prometheus 监控
9. 前端优化
   - 使用 Vue 3 组合式 API
   - 启用 Vite 构建优化
   - 实现虚拟滚动
   - 使用懒加载
10. 数据库查询优化
    - 使用查询优化
    - 避免 N+1 查询
    - 使用数据库视图
    - 实现读写分离

---

**部署完成后，请确保所有功能正常运行，并保存此文档供后续维护参考。**

## 11. 开发环境配置

### 11.1 本地开发设置
```bash
# 后端开发环境
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端开发环境
cd frontend
npm install
npm run dev
```

### 11.2 代码质量工具
```bash
# 后端代码检查
pip install black flake8 mypy
black .
flake8 .
mypy .

# 前端代码检查
npm run lint
npm run type-check
```

### 11.3 测试
```bash
# 后端测试
cd backend
pytest -v

# 前端测试
cd frontend
npm run test
```

## 12. 生产环境部署

### 12.1 环境变量配置
```env
# 生产环境配置
ENVIRONMENT=production
DATABASE_URL=postgresql://user:password@db:5432/production_db
REDIS_URL=redis://redis:6379/0
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# SSL配置
SSL_CERT_PATH=/etc/ssl/certs/cert.pem
SSL_KEY_PATH=/etc/ssl/private/key.pem
```

### 12.2 负载均衡配置
```nginx
# nginx.conf 示例
upstream backend {
    server backend1:8000;
    server backend2:8000;
}

server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;
    
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 12.3 监控和告警
```yaml
# prometheus.yml 告警规则
groups:
- name: alert_rules
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
```

---

**部署完成后，请确保所有功能正常运行，并保存此文档供后续维护参考。**