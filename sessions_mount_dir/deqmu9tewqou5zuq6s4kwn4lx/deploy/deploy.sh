#!/bin/bash

# 自动化部署脚本
# 用于部署会籍续费与支付系统

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查必要的命令
check_dependencies() {
    log_info "检查系统依赖..."
    
    commands=("docker" "docker-compose" "git" "node" "npm")
    
    for cmd in "${commands[@]}"; do
        if ! command -v $cmd &> /dev/null; then
            log_error "$cmd 未安装，请先安装 $cmd"
            exit 1
        fi
    done
    
    log_info "所有依赖检查通过"
}

# 设置环境变量
setup_env() {
    log_info "设置环境变量..."
    
    # 创建 .env 文件（如果不存在）
    if [ ! -f .env ]; then
        cat > .env << EOF
# 数据库配置
POSTGRES_DB=membership_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_password

# Redis配置
REDIS_PASSWORD=redis_password

# JWT配置
SECRET_KEY=your-super-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 应用配置
ENVIRONMENT=production
DEBUG=false

# 监控配置
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
EOF
        log_warn "已创建默认 .env 文件，请根据需要修改配置"
    fi
}

# 构建前端
build_frontend() {
    log_info "构建前端应用..."
    
    cd frontend
    
    # 安装依赖
    npm ci
    
    # 构建生产版本
    npm run build
    
    cd ..
    
    log_info "前端构建完成"
}

# 启动服务
start_services() {
    log_info "启动所有服务..."
    
    # 使用 docker-compose 启动服务
    docker-compose up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 30
    
    # 检查服务状态
    if docker-compose ps | grep -q "Up"; then
        log_info "所有服务已成功启动"
    else
        log_error "部分服务启动失败"
        docker-compose logs
        exit 1
    fi
}

# 运行数据库迁移
run_migrations() {
    log_info "运行数据库迁移..."
    
    # 等待数据库就绪
    until docker-compose exec -T postgres pg_isready -U $POSTGRES_USER; do
        log_info "等待数据库启动..."
        sleep 2
    done
    
    # 运行迁移（假设使用 Alembic）
    docker-compose exec -T backend alembic upgrade head
    
    log_info "数据库迁移完成"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    # 检查后端 API
    if curl -f http://localhost:8000/health &> /dev/null; then
        log_info "后端 API 健康检查通过"
    else
        log_error "后端 API 健康检查失败"
        exit 1
    fi
    
    # 检查前端
    if curl -f http://localhost:5173 &> /dev/null; then
        log_info "前端健康检查通过"
    else
        log_error "前端健康检查失败"
        exit 1
    fi
    
    # 检查监控服务
    if curl -f http://localhost:9090 &> /dev/null; then
        log_info "Prometheus 健康检查通过"
    else
        log_warn "Prometheus 健康检查失败"
    fi
    
    if curl -f http://localhost:3000 &> /dev/null; then
        log_info "Grafana 健康检查通过"
    else
        log_warn "Grafana 健康检查失败"
    fi
}

# 主函数
main() {
    log_info "开始部署会籍续费与支付系统..."
    
    check_dependencies
    setup_env
    build_frontend
    start_services
    run_migrations
    health_check
    
    log_info "部署完成！"
    log_info "前端地址: http://localhost:5173"
    log_info "后端 API: http://localhost:8000"
    log_info "Prometheus: http://localhost:9090"
    log_info "Grafana: http://localhost:3000"
    log_info "默认 Grafana 用户名/密码: admin/admin"
}

# 执行主函数
main "$@"
