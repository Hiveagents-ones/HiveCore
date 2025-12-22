#!/bin/bash

# 数据库备份脚本
# 用于备份PostgreSQL数据库

# 配置变量
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="membership_db"
DB_USER="postgres"
BACKUP_DIR="/var/backups/postgresql"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_backup_${DATE}.sql"
RETENTION_DAYS=7

# 创建备份目录（如果不存在）
mkdir -p ${BACKUP_DIR}

# 执行备份
echo "开始备份数据库: ${DB_NAME}"
PGPASSWORD=${DB_PASSWORD} pg_dump -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} > ${BACKUP_FILE}

# 检查备份是否成功
if [ $? -eq 0 ]; then
    echo "数据库备份成功: ${BACKUP_FILE}"
    
    # 压缩备份文件
    gzip ${BACKUP_FILE}
    echo "备份文件已压缩: ${BACKUP_FILE}.gz"
    
    # 清理旧备份
    echo "清理 ${RETENTION_DAYS} 天前的备份文件..."
    find ${BACKUP_DIR} -name "${DB_NAME}_backup_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete
    echo "清理完成"
else
    echo "数据库备份失败!"
    exit 1
fi

# 记录备份日志
echo "$(date): 数据库备份 ${DB_NAME} 完成" >> ${BACKUP_DIR}/backup.log

echo "备份脚本执行完成"
