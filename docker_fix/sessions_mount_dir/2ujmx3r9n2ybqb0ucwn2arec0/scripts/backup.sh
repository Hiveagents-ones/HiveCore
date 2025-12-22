#!/bin/bash

# Backup script for PostgreSQL database in Docker environment
# This script creates a backup of the gym_db database

# Set variables
BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="gym_db_backup_${TIMESTAMP}.sql"
CONTAINER_NAME="$(docker-compose ps -q db)"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Check if the database container is running
if [ -z "$CONTAINER_NAME" ]; then
    echo "Error: Database container is not running"
    exit 1
fi

# Create backup
echo "Creating backup of gym_db database..."
docker exec $CONTAINER_NAME pg_dump -U gym_user -d gym_db > "${BACKUP_DIR}/${BACKUP_FILE}"

# Check if backup was successful
if [ $? -eq 0 ]; then
    echo "Backup created successfully: ${BACKUP_DIR}/${BACKUP_FILE}"
    
    # Compress the backup file
    gzip "${BACKUP_DIR}/${BACKUP_FILE}"
    echo "Backup compressed: ${BACKUP_DIR}/${BACKUP_FILE}.gz"
    
    # Remove backups older than 7 days
    find $BACKUP_DIR -name "gym_db_backup_*.sql.gz" -mtime +7 -delete
    echo "Old backups removed"
else
    echo "Error: Backup failed"
    exit 1
fi

exit 0