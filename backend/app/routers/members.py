from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..models import member as models
from ..schemas import member as schemas
from ..database import get_db

router = APIRouter()

@router.get("/profile", response_model=schemas.MemberProfile)
async def get_member_profile(db: Session = Depends(get_db)):
    # 实际项目中应从认证信息中获取会员ID
    member_id = 1  # 示例ID
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member

@router.put("/profile", response_model=schemas.MemberProfile)
async def update_member_profile(profile: schemas.MemberProfileUpdate, db: Session = Depends(get_db)):
    # 实际项目中应从认证信息中获取会员ID
    member_id = 1  # 示例ID
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    update_data = profile.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(member, key, value)

    db.add(member)
    db.commit()
    db.refresh(member)
    return member