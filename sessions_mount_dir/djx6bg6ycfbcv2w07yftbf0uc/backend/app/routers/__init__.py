from fastapi import APIRouter
from app.routers import auth, users, health

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/v1/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/v1/users", tags=["Users"])
api_router.include_router(health.router, prefix="/v1/health", tags=["Health"])
