from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ....database import get_db
from ....models.coach import Coach as CoachModel
from ....schemas.coach import Coach, CoachCreate, CoachUpdate, CoachList

router = APIRouter()

@router.post("/", response_model=Coach)
def create_coach(coach: CoachCreate, db: Session = Depends(get_db)):
    """创建新教练"""
    db_coach = db.query(CoachModel).filter(CoachModel.email == coach.email).first()
    if db_coach:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    db_coach = CoachModel(**coach.dict())
    db.add(db_coach)
    db.commit()
    db.refresh(db_coach)
    return db_coach

@router.get("/", response_model=CoachList)
def list_coaches(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """获取教练列表"""
    query = db.query(CoachModel)
    
    if is_active is not None:
        query = query.filter(CoachModel.is_active == is_active)
    
    total = query.count()
    coaches = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return CoachList(
        coaches=coaches,
        total=total,
        page=page,
        per_page=per_page
    )

@router.get("/{coach_id}", response_model=Coach)
def get_coach(coach_id: int, db: Session = Depends(get_db)):
    """获取单个教练详情"""
    coach = db.query(CoachModel).filter(CoachModel.id == coach_id).first()
    if not coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    return coach

@router.put("/{coach_id}", response_model=Coach)
def update_coach(coach_id: int, coach_update: CoachUpdate, db: Session = Depends(get_db)):
    """更新教练信息"""
    db_coach = db.query(CoachModel).filter(CoachModel.id == coach_id).first()
    if not db_coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    
    update_data = coach_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_coach, field, value)
    
    db.commit()
    db.refresh(db_coach)
    return db_coach

@router.delete("/{coach_id}")
def delete_coach(coach_id: int, db: Session = Depends(get_db)):
    """删除教练"""
    db_coach = db.query(CoachModel).filter(CoachModel.id == coach_id).first()
    if not db_coach:
        raise HTTPException(status_code=404, detail="Coach not found")
    
    db.delete(db_coach)
    db.commit()
    return {"message": "Coach deleted successfully"}
