#!/bin/bash

# 数据库恢复脚本
# 用于从备份文件恢复PostgreSQL数据库

# 配置变量
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="membership_db"
DB_USER="postgres"
BACKUP_DIR="/var/backups/postgresql"

# 检查是否提供了备份文件参数
if [ $# -eq 0 ]; then
    echo "错误: 请提供备份文件路径"
    echo "用法: $0 <备份文件路径>"
    echo "示例: $0 ${BACKUP_DIR}/${DB_NAME}_backup_20231201_120000.sql.gz"
    exit 1
fi

BACKUP_FILE=$1

# 检查备份文件是否存在
if [ ! -f "${BACKUP_FILE}" ]; then
    echo "错误: 备份文件不存在: ${BACKUP_FILE}"
    exit 1
fi

# 确认恢复操作
read -p "警告: 此操作将覆盖现有数据库 '${DB_NAME}'。是否继续? (y/N): " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "操作已取消"
    exit 0
fi

# 创建临时目录
temp_dir=$(mktemp -d)
trap "rm -rf ${temp_dir}" EXIT

# 解压备份文件（如果是压缩的）
if [[ ${BACKUP_FILE} == *.gz ]]; then
    echo "解压备份文件..."
    gunzip -c "${BACKUP_FILE}" > "${temp_dir}/restore.sql"
    restore_file="${temp_dir}/restore.sql"
else
    restore_file="${BACKUP_FILE}"
fi

# 执行恢复
echo "开始恢复数据库: ${DB_NAME}"
PGPASSWORD=${DB_PASSWORD} psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} < "${restore_file}"

# 检查恢复是否成功
if [ $? -eq 0 ]; then
    echo "数据库恢复成功!"
    
    # 记录恢复日志
    echo "$(date): 数据库恢复 ${DB_NAME} 完成，使用备份文件: ${BACKUP_FILE}" >> ${BACKUP_DIR}/restore.log
else
    echo "数据库恢复失败!"
    exit 1
fi

echo "恢复脚本执行完成"
