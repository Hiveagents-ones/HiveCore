#!/bin/bash

# Docker Compose部署脚本，用于快速启动本地开发环境
# 使用方法: ./scripts/docker-deploy.sh [start|stop|restart|logs|status]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目配置
PROJECT_NAME="member-management"
COMPOSE_FILE="docker-compose.yml"
BACKEND_IMAGE="${PROJECT_NAME}-backend:latest"
FRONTEND_IMAGE="${PROJECT_NAME}-frontend:latest"
DB_IMAGE="postgres:15-alpine"
DB_NAME="member_db"
DB_USER="member_user"
DB_PASSWORD="member_pass"
DB_PORT="5432"
BACKEND_PORT="8000"
FRONTEND_PORT="3000"

# 函数：打印带颜色的消息
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 函数：检查Docker和Docker Compose是否安装
check_dependencies() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装，请先安装Docker"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi

    print_message "依赖检查通过"
}

# 函数：创建docker-compose.yml文件
create_compose_file() {
    if [ ! -f "$COMPOSE_FILE" ]; then
        print_message "创建docker-compose.yml文件"
        cat > "$COMPOSE_FILE" <<EOF
version: '3.8'

services:
  db:
    image: ${DB_IMAGE}
    container_name: ${PROJECT_NAME}-db
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "${DB_PORT}:${DB_PORT}"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - ${PROJECT_NAME}-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: .
      dockerfile: Dockerfile
    image: ${BACKEND_IMAGE}
    container_name: ${PROJECT_NAME}-backend
    environment:
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@db:${DB_PORT}/${DB_NAME}
      SECRET_KEY: your-secret-key-here
      ALGORITHM: HS256
      ACCESS_TOKEN_EXPIRE_MINUTES: 30
    ports:
      - "${BACKEND_PORT}:${BACKEND_PORT}"
    depends_on:
      db:
        condition: service_healthy
    networks:
      - ${PROJECT_NAME}-network
    volumes:
      - ./backend:/app/backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    image: ${FRONTEND_IMAGE}
    container_name: ${PROJECT_NAME}-frontend
    ports:
      - "${FRONTEND_PORT}:${FRONTEND_PORT}"
    depends_on:
      - backend
    networks:
      - ${PROJECT_NAME}-network
    volumes:
      - ./frontend:/app/frontend
    command: npm run dev

volumes:
  postgres_data:

networks:
  ${PROJECT_NAME}-network:
    driver: bridge
EOF
        print_message "docker-compose.yml文件创建成功"
    else
        print_message "docker-compose.yml文件已存在"
    fi
}

# 函数：创建前端Dockerfile
create_frontend_dockerfile() {
    FRONTEND_DOCKERFILE="frontend/Dockerfile"
    if [ ! -f "$FRONTEND_DOCKERFILE" ]; then
        print_message "创建前端Dockerfile"
        mkdir -p frontend
        cat > "$FRONTEND_DOCKERFILE" <<EOF
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
EOF
        print_message "前端Dockerfile创建成功"
    else
        print_message "前端Dockerfile已存在"
    fi
}

# 函数：创建前端package.json
create_frontend_package_json() {
    FRONTEND_PACKAGE="frontend/package.json"
    if [ ! -f "$FRONTEND_PACKAGE" ]; then
        print_message "创建前端package.json"
        mkdir -p frontend
        cat > "$FRONTEND_PACKAGE" <<EOF
{
  "name": "member-management-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.3.4",
    "vue-router": "^4.2.4",
    "pinia": "^2.1.6",
    "element-plus": "^2.3.9",
    "axios": "^1.4.0",
    "@element-plus/icons-vue": "^2.1.0",
    "vue-i18n": "^9.2.2"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^4.2.3",
    "vite": "^4.4.5",
    "sass": "^1.64.2"
  }
}
EOF
        print_message "前端package.json创建成功"
    else
        print_message "前端package.json已存在"
    fi
}

# 函数：创建后端requirements.txt
create_backend_requirements() {
    BACKEND_REQUIREMENTS="backend/requirements.txt"
    if [ ! -f "$BACKEND_REQUIREMENTS" ]; then
        print_message "创建后端requirements.txt"
        mkdir -p backend
        cat > "$BACKEND_REQUIREMENTS" <<EOF
fastapi==0.101.0
uvicorn[standard]==0.23.2
sqlalchemy==2.0.19
psycopg2-binary==2.9.7
pydantic==2.1.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
alembic==1.11.1
python-dotenv==1.0.0
EOF
        print_message "后端requirements.txt创建成功"
    else
        print_message "后端requirements.txt已存在"
    fi
}

# 函数：启动服务
start_services() {
    print_message "启动服务..."
    docker-compose up -d
    print_message "服务启动成功"
    print_message "前端地址: http://localhost:${FRONTEND_PORT}"
    print_message "后端API: http://localhost:${BACKEND_PORT}"
    print_message "API文档: http://localhost:${BACKEND_PORT}/docs"
}

# 函数：停止服务
stop_services() {
    print_message "停止服务..."
    docker-compose down
    print_message "服务已停止"
}

# 函数：重启服务
restart_services() {
    print_message "重启服务..."
    docker-compose restart
    print_message "服务已重启"
}

# 函数：查看日志
show_logs() {
    docker-compose logs -f
}

# 函数：查看服务状态
show_status() {
    docker-compose ps
}

# 主函数
main() {
    check_dependencies
    create_compose_file
    create_frontend_dockerfile
    create_frontend_package_json
    create_backend_requirements

    case "${1:-start}" in
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        logs)
            show_logs
            ;;
        status)
            show_status
            ;;
        *)
            echo "使用方法: $0 {start|stop|restart|logs|status}"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
