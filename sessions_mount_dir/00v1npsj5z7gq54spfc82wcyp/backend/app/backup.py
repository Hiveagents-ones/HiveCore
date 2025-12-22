import os
import json
import datetime
from pathlib import Path
from typing import Optional

import redis
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from prometheus_client import Summary
from fastapi import BackgroundTasks

from .database import get_db
from .schemas.member import MemberCreate, MemberUpdate
from .routers.members import get_member, get_members, create_member, update_member, delete_member
from .services.sync import sync_to_redis
from .models.member import Member
from .monitoring import backup_metrics

router = APIRouter()

# Prometheus metrics
BACKUP_TIME = Summary('backup_processing_seconds', 'Time spent processing backup')

# Redis connection
redis_client = redis.Redis(host='localhost', port=6379, db=0)
# Scheduler for automated backups
scheduler = BackgroundScheduler()

BACKUP_DIR = Path("backups")
BACKUP_DIR.mkdir(exist_ok=True)
# Backup schedule configuration
BACKUP_SCHEDULE = "0 2 * * *"  # Daily at 2 AM


def generate_backup_filename() -> str:
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"backup_{now}.json"


@BACKUP_TIME.time()
def backup_members_data(db: Session = Depends(get_db)) -> str:
    """
    Backup all members data to a JSON file and Redis
    Returns the backup file path
    """
    try:
        members = get_members(db=db)
        member_data = [member.__dict__ for member in members]
        
        # Remove SQLAlchemy internal attributes
        for member in member_data:
            member.pop('_sa_instance_state', None)
        
        # Generate backup file
        backup_file = BACKUP_DIR / generate_backup_filename()
        with open(backup_file, 'w') as f:
            json.dump(member_data, f, indent=2, default=str)
        
        # Sync to Redis
        sync_to_redis(member_data)
        
        # Update metrics
        backup_metrics.labels(status='success').inc()
        
        return str(backup_file)
    except Exception as e:
        backup_metrics.labels(status='failed').inc()
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")


def restore_members_data(backup_file: str, db: Session = Depends(get_db)) -> str:

    try:
        if not os.path.exists(backup_file):
            raise HTTPException(status_code=404, detail="Backup file not found")

        with open(backup_file, 'r') as f:
            member_data = json.load(f)

        # Clear existing data (in a real system, you might want to archive instead)
        db.query(Member).delete()
        db.commit()

        # Restore members
        for member in member_data:
            create_member(MemberCreate(**member), db=db)

        # Sync to Redis
        sync_to_redis(member_data)

        return f"Successfully restored {len(member_data)} members from backup"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")


def schedule_backup_job():
    """
    Schedule the automated backup job
    """

    """
    Schedule the automated backup job
    """
    if not scheduler.running:
        scheduler.start()
        
    scheduler.add_job(
        backup_members_data,
        trigger=CronTrigger.from_crontab(BACKUP_SCHEDULE),
        args=[Depends(get_db)],
        name="daily_members_backup",
        replace_existing=True
    )
    """
    Restore members data from a backup file
    Returns status message
    """
    try:
        if not os.path.exists(backup_file):
            raise HTTPException(status_code=404, detail="Backup file not found")
            
        with open(backup_file, 'r') as f:
            member_data = json.load(f)
        
        # Clear existing data (in a real system, you might want to archive instead)
        db.query(Member).delete()
        db.commit()
        
        # Restore members
        for member in member_data:
            create_member(MemberCreate(**member), db=db)
        
        # Sync to Redis
        sync_to_redis(member_data)
        
        return f"Successfully restored {len(member_data)} members from backup"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")


@router.get("/backup")
def create_backup(db: Session = Depends(get_db)):
    """
    Create a backup of all members data
    """
    backup_file = backup_members_data(db=db)
    return {"status": "success", "backup_file": backup_file}


@router.post("/restore")
def restore_backup(backup_file: str, db: Session = Depends(get_db)):
    """
    Restore members data from a backup file
    """
    result = restore_members_data(backup_file, db=db)
    return {"status": "success", "message": result}


@router.get("/backup/jobs")
@router.get("/backup/schedule")
def get_backup_schedule():
    """
    Get current backup schedule configuration
    """
    return {
        "status": "success",
        "schedule": BACKUP_SCHEDULE,
        "next_run_time": str(scheduler.get_job("daily_members_backup").next_run_time) if scheduler.get_job("daily_members_backup") else "Not scheduled"
    }
@router.post("/backup/run-now")
def run_backup_now(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Schedule a backup to run immediately in background
    """
    background_tasks.add_task(backup_members_data, db=db)
    return {"status": "success", "message": "Backup scheduled to run in background"}
def list_backup_jobs():
@router.get("/backup/list")
def list_available_backups():
    """
    List all available backup files
    """
    backups = []
    for file in BACKUP_DIR.glob("backup_*.json"):
        backups.append({
            "name": file.name,
            "size": file.stat().st_size,
            "modified": datetime.datetime.fromtimestamp(file.stat().st_mtime).isoformat()
        })
    return {"backups": sorted(backups, key=lambda x: x["modified"], reverse=True)}
    """
    List all scheduled backup jobs
    """
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": str(job.next_run_time),
            "trigger": str(job.trigger)
        })
    return {"jobs": jobs}


@router.post("/backup/trigger-now")
def trigger_backup_now_sync(db: Session = Depends(get_db)):
    """
    Trigger backup immediately
    """
    backup_file = backup_members_data(db=db)
    return {"status": "success", "backup_file": backup_file, "message": "Backup triggered successfully"}


@router.post("/backup/schedule")
def configure_backup_schedule(cron_expression: str):
    """
    Update the backup schedule
    """
    global BACKUP_SCHEDULE
    try:
        # Validate cron expression
        CronTrigger.from_crontab(cron_expression)
        BACKUP_SCHEDULE = cron_expression
        
        # Reschedule the job
        schedule_backup_job()
        
        return {"status": "success", "message": f"Backup schedule updated to: {cron_expression}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid cron expression: {str(e)}")
def restore_backup(backup_file: str, db: Session = Depends(get_db)):
    """
    Restore members data from a backup file
    """
    result = restore_members_data(backup_file, db=db)
    return {"status": "success", "message": result}


# Start the backup scheduler when the module loads
schedule_backup_job()