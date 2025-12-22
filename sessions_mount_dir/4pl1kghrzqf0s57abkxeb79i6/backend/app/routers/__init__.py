from fastapi import APIRouter
from . import members

api_router = APIRouter()

api_router.include_router(members.router, prefix="/members", tags=["members"])
