# 部署文档

## 目录

1. [环境配置](#环境配置)
2. [支付设置](#支付设置)
3. [监控说明](#监控说明)
4. [部署步骤](#部署步骤)
5. [维护操作](#维护操作)

## 环境配置

### 系统要求

- 操作系统: Linux (推荐 Ubuntu 20.04+)
- Docker: 20.10+
- Docker Compose: 2.0+
- 内存: 最小 4GB，推荐 8GB+
- 存储: 最小 20GB 可用空间

### 环境变量配置

创建 `.env` 文件并配置以下变量：

```bash
# 数据库配置
POSTGRES_DB=membership_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
DATABASE_URL=postgresql://postgres:your_secure_password@db:5432/membership_db

# 应用配置
SECRET_KEY=your_secret_key_here
DEBUG=false
ENVIRONMENT=production

# 支付配置
WECHAT_APP_ID=your_wechat_app_id
WECHAT_MCH_ID=your_wechat_mch_id
WECHAT_API_KEY=your_wechat_api_key
ALIPAY_APP_ID=your_alipay_app_id
ALIPAY_PRIVATE_KEY=your_alipay_private_key
ALIPAY_PUBLIC_KEY=your_alipay_public_key

# 监控配置
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_ADMIN_PASSWORD=your_grafana_password
```

## 支付设置

### 微信支付配置

1. 登录微信商户平台
2. 获取以下信息并更新到环境变量：
   - `WECHAT_APP_ID`
   - `WECHAT_MCH_ID`
   - `WECHAT_API_KEY`
3. 配置支付回调URL: `https://your-domain.com/api/payment/wechat/notify`

### 支付宝配置

1. 登录支付宝开放平台
2. 获取以下信息并更新到环境变量：
   - `ALIPAY_APP_ID`
   - `ALIPAY_PRIVATE_KEY`
   - `ALIPAY_PUBLIC_KEY`
3. 配置网关地址和回调URL: `https://your-domain.com/api/payment/alipay/notify`

### 线下支付配置

线下支付由管理员手动确认，无需额外配置。管理员可通过后台管理界面处理线下支付订单。

## 监控说明

### Prometheus 配置

Prometheus 已配置监控以下指标：

- 应用性能指标
- 数据库连接状态
- 支付成功率
- 会员续费统计

访问地址: `http://your-domain:9090`

### Grafana 仪表板

Grafana 预配置了以下仪表板：

1. **系统概览** - CPU、内存、磁盘使用情况
2. **应用性能** - API响应时间、错误率
3. **业务指标** - 支付成功率、会员续费趋势

访问地址: `http://your-domain:3000`
- 默认用户名: admin
- 密码: 环境变量中设置的 `GRAFANA_ADMIN_PASSWORD`

## 部署步骤

### 1. 克隆项目

```bash
git clone https://github.com/your-org/membership-system.git
cd membership-system
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入实际配置
```

### 3. 启动服务

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 4. 初始化数据库

```bash
# 运行数据库迁移
docker-compose exec backend alembic upgrade head

# 创建初始数据（可选）
docker-compose exec backend python scripts/init_data.py
```

### 5. 验证部署

1. 访问前端应用: `http://your-domain`
2. 访问API文档: `http://your-domain/docs`
3. 访问监控面板: `http://your-domain:3000`

## 维护操作

### 数据库备份

使用提供的备份脚本：

```bash
# 执行备份
./scripts/backup_db.sh

# 备份文件将保存在 backups/ 目录下
```

### 日志管理

```bash
# 查看应用日志
docker-compose logs -f backend

# 查看前端日志
docker-compose logs -f frontend

# 清理旧日志
docker system prune -f
```

### 更新部署

```bash
# 拉取最新代码
git pull origin main

# 重新构建并部署
docker-compose down
docker-compose up -d --build

# 运行数据库迁移（如果有）
docker-compose exec backend alembic upgrade head
```

### 扩容操作

```bash
# 扩展后端服务
docker-compose up -d --scale backend=3

# 扩展前端服务
docker-compose up -d --scale frontend=2
```

## 故障排查

### 常见问题

1. **支付回调失败**
   - 检查支付平台配置的回调URL是否正确
   - 确认服务器防火墙已开放相应端口
   - 查看支付服务日志: `docker-compose logs payment`

2. **数据库连接失败**
   - 检查数据库服务状态: `docker-compose ps db`
   - 验证数据库连接字符串配置
   - 查看数据库日志: `docker-compose logs db`

3. **前端无法访问后端API**
   - 检查网络配置和代理设置
   - 验证API服务是否正常运行
   - 查看浏览器控制台错误信息

### 性能优化

1. **数据库优化**
   - 定期执行 `VACUUM` 和 `ANALYZE`
   - 监控慢查询日志
   - 考虑添加适当的索引

2. **缓存策略**
   - 启用 Redis 缓存（如需要）
   - 配置适当的缓存过期时间
   - 监控缓存命中率

3. **负载均衡**
   - 使用 Nginx 进行负载均衡
   - 配置健康检查
   - 监控各节点负载情况

## 安全建议

1. 定期更新依赖包
2. 使用强密码和密钥
3. 启用 HTTPS
4. 配置防火墙规则
5. 定期备份数据
6. 监控异常访问日志

## 联系支持

如遇到部署问题，请联系：
- 技术支持: support@example.com
- 紧急联系: +86-xxx-xxxx-xxxx