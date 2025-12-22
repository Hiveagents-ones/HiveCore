from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, courses, members, bookings, statistics

app = FastAPI(
    title="商家端API",
    description="提供商家端数据统计和管理功能的API服务",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(courses.router, prefix="/api/courses", tags=["课程管理"])
app.include_router(members.router, prefix="/api/members", tags=["会员管理"])
app.include_router(bookings.router, prefix="/api/bookings", tags=["预约管理"])
app.include_router(statistics.router, prefix="/api/statistics", tags=["数据统计"])

@app.get("/")
async def root():
    return {"message": "商家端API服务正在运行"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
