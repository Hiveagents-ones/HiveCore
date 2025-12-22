#!/bin/bash

# 自动化部署脚本
# 用于构建镜像、运行容器和执行数据库迁移

set -e

# 颜色输出
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

# 检查Docker和Docker Compose是否安装
check_dependencies() {
    log_info "检查依赖..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    log_info "依赖检查完成"
}

# 构建镜像
build_images() {
    log_info "构建Docker镜像..."
    
    # 构建后端镜像
    log_info "构建后端镜像..."
    docker-compose build backend
    
    # 构建前端镜像
    log_info "构建前端镜像..."
    docker-compose build frontend
    
    log_info "镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    # 启动数据库
    log_info "启动数据库..."
    docker-compose up -d db
    
    # 等待数据库就绪
    log_info "等待数据库就绪..."
    sleep 10
    
    # 执行数据库迁移
    log_info "执行数据库迁移..."
    docker-compose run --rm backend alembic upgrade head
    
    # 启动后端服务
    log_info "启动后端服务..."
    docker-compose up -d backend
    
    # 启动前端服务
    log_info "启动前端服务..."
    docker-compose up -d frontend
    
    # 启动监控服务
    log_info "启动监控服务..."
    docker-compose up -d prometheus grafana
    
    log_info "所有服务启动完成"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    # 检查后端健康状态
    log_info "检查后端健康状态..."
    for i in {1..30}; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            log_info "后端服务健康检查通过"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "后端服务健康检查失败"
            exit 1
        fi
        sleep 2
    done
    
    # 检查前端健康状态
    log_info "检查前端健康状态..."
    for i in {1..30}; do
        if curl -f http://localhost:3000 &> /dev/null; then
            log_info "前端服务健康检查通过"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "前端服务健康检查失败"
            exit 1
        fi
        sleep 2
    done
    
    log_info "健康检查完成"
}

# 显示服务状态
show_status() {
    log_info "服务状态:"
    docker-compose ps
    
    log_info "服务访问地址:"
    echo "前端: http://localhost:3000"
    echo "后端API: http://localhost:8000"
    echo "API文档: http://localhost:8000/docs"
    echo "Prometheus: http://localhost:9090"
    echo "Grafana: http://localhost:3001 (admin/admin)"
}

# 主函数
main() {
    log_info "开始部署会员信息管理系统..."
    
    check_dependencies
    build_images
    start_services
    health_check
    show_status
    
    log_info "部署完成！"
}

# 执行主函数
main "$@"
