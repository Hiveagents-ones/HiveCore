#!/bin/bash

# 数据库备份脚本
# 实现每日全量备份并加密存储

# 配置变量
DB_NAME="member_management"
DB_USER="postgres"
DB_HOST="localhost"
DB_PORT="5432"
BACKUP_DIR="/var/backups/postgresql"
ENCRYPT_KEY_FILE="/etc/backup/encrypt.key"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_backup_${DATE}.sql"
ENCRYPTED_FILE="${BACKUP_FILE}.enc"
LOG_FILE="/var/log/backup.log"

# 创建备份目录
mkdir -p ${BACKUP_DIR}

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> ${LOG_FILE}
}

# 检查加密密钥文件
if [ ! -f ${ENCRYPT_KEY_FILE} ]; then
    log "ERROR: 加密密钥文件不存在: ${ENCRYPT_KEY_FILE}"
    exit 1
fi

# 开始备份
log "开始数据库备份: ${DB_NAME}"

# 执行备份
if pg_dump -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} > ${BACKUP_FILE}; then
    log "数据库备份成功: ${BACKUP_FILE}"
    
    # 加密备份文件
    if openssl enc -aes-256-cbc -salt -in ${BACKUP_FILE} -out ${ENCRYPTED_FILE} -pass file:${ENCRYPT_KEY_FILE}; then
        log "备份文件加密成功: ${ENCRYPTED_FILE}"
        
        # 删除未加密的备份文件
        rm -f ${BACKUP_FILE}
        
        # 清理旧备份
        find ${BACKUP_DIR} -name "${DB_NAME}_backup_*.sql.enc" -mtime +${RETENTION_DAYS} -delete
        log "清理 ${RETENTION_DAYS} 天前的旧备份文件"
        
        log "备份流程完成"
    else
        log "ERROR: 备份文件加密失败"
        rm -f ${BACKUP_FILE}
        exit 1
    fi
else
    log "ERROR: 数据库备份失败"
    exit 1
fi

exit 0
