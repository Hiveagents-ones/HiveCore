from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class MemberBase(BaseModel):
    name: str = Field(..., max_length=100)
    phone: str = Field(..., max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    birthday: Optional[datetime] = None
    gender: Optional[str] = Field(None, max_length=10)
    address: Optional[str] = None
    total_spent: float = Field(default=0.0)
    visit_count: int = Field(default=0)
    last_visit: Optional[datetime] = None
    is_active: bool = Field(default=True)

class MemberCreate(MemberBase):
    shop_id: int

class MemberUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    birthday: Optional[datetime] = None
    gender: Optional[str] = Field(None, max_length=10)
    address: Optional[str] = None
    total_spent: Optional[float] = None
    visit_count: Optional[int] = None
    last_visit: Optional[datetime] = None
    is_active: Optional[bool] = None

class Member(MemberBase):
    id: int
    shop_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class MemberTagBase(BaseModel):
    name: str = Field(..., max_length=50)
    color: Optional[str] = Field(None, max_length=7)

class MemberTagCreate(MemberTagBase):
    member_id: int
    shop_id: int

class MemberTag(MemberTagBase):
    id: int
    member_id: int
    shop_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class MemberNoteBase(BaseModel):
    content: str

class MemberNoteCreate(MemberNoteBase):
    member_id: int
    staff_id: int
    shop_id: int

class MemberNote(MemberNoteBase):
    id: int
    member_id: int
    staff_id: int
    shop_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ConsumptionBase(BaseModel):
    amount: float
    description: Optional[str] = None
    payment_method: Optional[str] = Field(None, max_length=50)

class ConsumptionCreate(ConsumptionBase):
    member_id: int

class Consumption(ConsumptionBase):
    id: int
    member_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class MemberWithDetails(Member):
    tags: List[MemberTag] = []
    notes: List[MemberNote] = []
    appointments: List[dict] = []  # Assuming Appointment schema will be defined elsewhere
    consumptions: List[Consumption] = []
    
    class Config:
        from_attributes = True

class MemberListResponse(BaseModel):
    members: List[MemberWithDetails]
    total: int
    page: int
    per_page: int
    
    class Config:
        from_attributes = True
