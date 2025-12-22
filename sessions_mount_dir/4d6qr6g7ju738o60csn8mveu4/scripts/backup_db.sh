#!/bin/bash

# 数据库备份脚本
# 用于每日定时备份 PostgreSQL 数据库

# 配置变量
DB_NAME="gym_db"
DB_USER="gym_user"
DB_PASSWORD="gym_password"
DB_HOST="localhost"
DB_PORT="5432"
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_backup_${DATE}.sql"
RETENTION_DAYS=7

# 创建备份目录
mkdir -p ${BACKUP_DIR}

# 执行备份
PGPASSWORD=${DB_PASSWORD} pg_dump -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} > ${BACKUP_FILE}

# 检查备份是否成功
if [ $? -eq 0 ]; then
    echo "数据库备份成功: ${BACKUP_FILE}"
    
    # 压缩备份文件
    gzip ${BACKUP_FILE}
    echo "备份文件已压缩: ${BACKUP_FILE}.gz"
    
    # 删除超过保留期的备份文件
    find ${BACKUP_DIR} -name "${DB_NAME}_backup_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
    echo "已删除超过 ${RETENTION_DAYS} 天的备份文件"
else
    echo "数据库备份失败"
    exit 1
fi

# 添加到 crontab 的示例（每日凌晨2点执行）
# 0 2 * * * /path/to/scripts/backup_db.sh
