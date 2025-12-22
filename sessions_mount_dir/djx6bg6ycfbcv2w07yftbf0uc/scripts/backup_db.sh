#!/bin/bash

# 数据库备份脚本
# 实现每日备份和定时清理

# 配置变量
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="membership_db"
DB_USER="postgres"
DB_PASSWORD="postgres"
BACKUP_DIR="/var/backups/postgresql"
RETENTION_DAYS=7
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql"
LOG_FILE="/var/log/postgresql/backup.log"

# 创建备份目录
mkdir -p ${BACKUP_DIR}

# 记录日志
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> ${LOG_FILE}
}

# 执行备份
log "开始数据库备份: ${DB_NAME}"

# 使用pg_dump备份
PGPASSWORD=${DB_PASSWORD} pg_dump -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} > ${BACKUP_FILE} 2>> ${LOG_FILE}

if [ $? -eq 0 ]; then
    log "备份成功: ${BACKUP_FILE}"
    
    # 压缩备份文件
    gzip ${BACKUP_FILE}
    log "备份文件已压缩: ${BACKUP_FILE}.gz"
    
    # 清理旧备份
    log "开始清理 ${RETENTION_DAYS} 天前的备份文件"
    find ${BACKUP_DIR} -name "${DB_NAME}_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete
    log "清理完成"
else
    log "备份失败，请检查错误日志"
    exit 1
fi

# 验证备份文件大小
BACKUP_SIZE=$(stat -c%s "${BACKUP_FILE}.gz")
if [ ${BACKUP_SIZE} -gt 0 ]; then
    log "备份文件验证通过，大小: ${BACKUP_SIZE} 字节"
else
    log "警告: 备份文件大小为0"
fi

log "备份任务完成"
exit 0