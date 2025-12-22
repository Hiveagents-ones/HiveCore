from pydantic import BaseModel
from datetime import date

class MemberCardBase(BaseModel):
    member_id: int
    card_type: str
    expiry_date: date

class MemberCardCreate(MemberCardBase):
    status: str

class MemberCardUpdate(BaseModel):
    status: str | None = None
    expiry_date: date | None = None

class MemberCardResponse(MemberCardBase):
    id: int
    status: str

    class Config:
        orm_mode = True