#!/bin/bash

# 数据库自动备份脚本
# 使用方法: ./backup.sh [环境名称]
# 示例: ./backup.sh production

# 配置参数
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="member_management"
DB_USER="postgres"
BACKUP_DIR="../backups"
DATE=$(date +%Y%m%d_%H%M%S)
ENVIRONMENT=${1:-development}

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份文件名
BACKUP_FILE="$BACKUP_DIR/backup_${ENVIRONMENT}_${DATE}.sql"

# 执行备份
echo "开始备份数据库..."
PGPASSWORD=$POSTGRES_PASSWORD pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME > $BACKUP_FILE

# 检查备份是否成功
if [ $? -eq 0 ]; then
    echo "数据库备份成功: $BACKUP_FILE"
    
    # 压缩备份文件
    gzip $BACKUP_FILE
    echo "备份文件已压缩: ${BACKUP_FILE}.gz"
    
    # 清理7天前的备份文件
    find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete
    echo "已清理7天前的备份文件"
else
    echo "数据库备份失败!"
    exit 1
fi

# 备份配置文件
echo "备份配置文件..."
cp ../docker-compose.yml $BACKUP_DIR/docker-compose_${ENVIRONMENT}_${DATE}.yml
cp ../nginx.conf $BACKUP_DIR/nginx_${ENVIRONMENT}_${DATE}.conf

echo "备份完成!"
