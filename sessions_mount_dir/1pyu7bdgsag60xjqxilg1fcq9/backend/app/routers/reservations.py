from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..models.reservation import Reservation
from ..database import get_db

router = APIRouter(
    prefix="/api/v1/reservations",
    tags=["reservations"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_model=List[dict])
async def get_reservations(db: Session = Depends(get_db)):
    """获取所有预约记录"""
    reservations = db.query(Reservation).all()
    return [{
        "id": r.id,
        "member_id": r.member_id,
        "course_id": r.course_id,
        "status": r.status,
        "created_at": r.created_at,
        "updated_at": r.updated_at
    } for r in reservations]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_reservation(
    member_id: int,
    course_id: int,
    db: Session = Depends(get_db)
):
    """创建新的课程预约"""
    reservation = Reservation(
        member_id=member_id,
        course_id=course_id,
        status="pending"
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return {"id": reservation.id, "status": "success"}


@router.put("/{reservation_id}")
async def update_reservation_status(
    reservation_id: int,
    status: str,
    db: Session = Depends(get_db)
):
    """更新预约状态 (pending/confirmed/cancelled)"""
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found"
        )
    
    reservation.status = status
    db.commit()
    db.refresh(reservation)
    return {"id": reservation.id, "status": "updated"}


@router.delete("/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reservation(
    reservation_id: int,
    db: Session = Depends(get_db)
):
    """删除预约记录"""
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found"
        )
    
    db.delete(reservation)
    db.commit()
    return