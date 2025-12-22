from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from ..models.coach import Coach
from ..database import get_db

class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        credentials: HTTPAuthorizationCredentials = await super(JWTBearer, self).__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
            return credentials.credentials
        else:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")



    """
    检查当前用户是否有权限访问教练数据
    :param request: FastAPI请求对象
    :param coach_id: 要访问的教练ID
    :return: 是否有权限
    """
    db = next(get_db())
    
    # 获取当前用户ID (假设从JWT中解析)
    current_user_id = request.state.user_id
    
    # 如果是管理员，直接放行
    if request.state.is_admin:
        return True
    
    # 检查是否是教练本人
    coach = db.query(Coach).filter(Coach.id == coach_id).first()
    if coach and coach.id == current_user_id:
        return True
    
    return False


def coach_data_permission(request: Request, coach_id: int) -> bool:



def coach_schedule_permission(request: Request, coach_id: int) -> bool:
    """
    检查排班管理权限
    :param request: FastAPI请求对象
    :param coach_id: 教练ID
    :return: 是否有权限
    """
    # 管理员有全部权限
    if request.state.is_admin:
        return True
    
    # 教练只能管理自己的排班
    if request.state.user_id == coach_id:
        return True
    
    return False