# 备份与恢复指南

本文档描述了如何对会员信息管理系统的数据库进行备份和恢复操作。

## 概述

系统使用 PostgreSQL 作为主数据库，我们提供了自动化脚本来简化备份和恢复流程。这些脚本位于 `scripts/` 目录下。

## 备份

### 自动备份

系统通过 cron 任务定期执行自动备份。默认配置为每天凌晨 2 点执行一次备份。

要设置自动备份，请将以下行添加到 crontab 中：

```bash
0 2 * * * /path/to/your/project/scripts/backup.sh
```

### 手动备份

您也可以手动执行备份脚本：

```bash
./scripts/backup.sh
```

### 备份脚本说明

备份脚本 `scripts/backup.sh` 执行以下操作：

1. 连接到 PostgreSQL 数据库
2. 创建数据库的完整转储
3. 压缩备份文件
4. 删除超过 7 天的旧备份
5. 记录操作日志

#### 配置

备份脚本的配置位于脚本顶部，您可以根据需要修改：

```bash
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="membership_db"
DB_USER="postgres"
BACKUP_DIR="/var/backups/postgresql"
RETENTION_DAYS=7
```

#### 环境变量

脚本需要 `DB_PASSWORD` 环境变量来连接数据库。请确保在执行脚本前设置此变量：

```bash
export DB_PASSWORD="your_password"
```

## 恢复

### 恢复步骤

1. 确保您有备份文件
2. 执行恢复脚本

```bash
./scripts/restore.sh /path/to/backup/file.sql.gz
```

### 恢复脚本说明

恢复脚本 `scripts/restore.sh` 执行以下操作：

1. 验证备份文件存在
2. 确认恢复操作
3. 解压备份文件（如果需要）
4. 恢复数据库
5. 记录操作日志

#### 安全注意事项

- 恢复操作会覆盖现有数据库，请谨慎操作
- 脚本会在执行前要求确认
- 建议在恢复前先备份当前数据库

## 备份文件管理

### 备份文件位置

默认备份文件存储在 `/var/backups/postgresql/` 目录下。

### 备份文件命名

备份文件按以下格式命名：

```
membership_db_backup_YYYYMMDD_HHMMSS.sql.gz
```

### 备份文件清理

备份脚本会自动删除超过保留期（默认 7 天）的旧备份文件。

## 日志

### 备份日志

备份操作日志记录在 `/var/backups/postgresql/backup.log` 文件中。

### 恢复日志

恢复操作日志记录在 `/var/backups/postgresql/restore.log` 文件中。

## 故障排除

### 常见问题

1. **权限错误**：确保脚本有执行权限
   ```bash
   chmod +x scripts/backup.sh scripts/restore.sh
   ```

2. **连接失败**：检查数据库连接参数和密码

3. **磁盘空间不足**：确保备份目录有足够空间

4. **恢复失败**：检查备份文件完整性

### 获取帮助

如果遇到问题，请检查日志文件以获取详细错误信息。

## 最佳实践

1. 定期验证备份文件的完整性
2. 定期测试恢复流程
3. 将备份文件存储在多个位置（本地和远程）
4. 根据业务需求调整备份频率和保留期
5. 监控备份任务的执行状态

## 相关文档

- [部署指南](deployment.md)
- [数据库架构](../backend/app/models/)