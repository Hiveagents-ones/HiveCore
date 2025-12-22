from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from .routers import members, courses, coaches, payments, schedules, billing
from .database import engine, Base, get_db
from sqlalchemy.orm import Session
from . import models

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="会员管理系统 API",
    description="会员信息管理系统的后端API接口",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
app.include_router(
    billing.router,
    prefix="/api/v1/billing",
    tags=["billing"],
    dependencies=[Depends(get_db)]
)
    members.router,
    prefix="/api/v1/members",
    tags=["members"],
    dependencies=[Depends(get_db)]
)

@app.get("/api/v1/members/{member_id}/payments")
async def get_member_payments(member_id: int, db: Session = Depends(get_db)):
    """
    获取指定会员的支付记录
    
    Args:
        member_id: 会员ID
        
    Returns:
        该会员的所有支付记录
    """
    return payments.router.get_member_payments(member_id, db)

app.include_router(
    courses.router,
    prefix="/api/v1/courses",
    tags=["courses"],
    dependencies=[Depends(get_db)]
)

app.include_router(
    coaches.router,
    prefix="/api/v1/coaches",
    tags=["coaches"],
    dependencies=[Depends(get_db)]
)

app.include_router(
    payments.router,
    prefix="/api/v1/payments",
    tags=["payments"],
    dependencies=[Depends(get_db)]
)

@app.get("/")
def root():
    return {"message": "会员管理系统API服务运行中"}