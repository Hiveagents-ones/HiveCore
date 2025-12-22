from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from .... import crud, schemas, models
from ....database import get_db

router = APIRouter()

@router.get("/", response_model=List[schemas.Reminder])
def read_reminders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    reminders = crud.get_reminders(db, skip=skip, limit=limit)
    return reminders

@router.post("/", response_model=schemas.Reminder)
def create_reminder(reminder: schemas.ReminderCreate, db: Session = Depends(get_db)):
    return crud.create_reminder(db=db, reminder=reminder)

@router.get("/{reminder_id}", response_model=schemas.Reminder)
def read_reminder(reminder_id: int, db: Session = Depends(get_db)):
    db_reminder = crud.get_reminder(db, reminder_id=reminder_id)
    if db_reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return db_reminder

@router.put("/{reminder_id}", response_model=schemas.Reminder)
def update_reminder(reminder_id: int, reminder: schemas.ReminderUpdate, db: Session = Depends(get_db)):
    db_reminder = crud.update_reminder(db, reminder_id=reminder_id, reminder=reminder)
    if db_reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return db_reminder

@router.delete("/{reminder_id}", response_model=schemas.Reminder)
def delete_reminder(reminder_id: int, db: Session = Depends(get_db)):
    db_reminder = crud.delete_reminder(db, reminder_id=reminder_id)
    if db_reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return db_reminder

@router.get("/member/{member_id}", response_model=List[schemas.Reminder])
def read_reminders_by_member(member_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    reminders = crud.get_reminders_by_member(db, member_id=member_id, skip=skip, limit=limit)
    return reminders
