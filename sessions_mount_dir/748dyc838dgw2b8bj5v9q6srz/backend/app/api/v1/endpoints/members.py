from fastapi import APIRouter, HTTPException, status
from ...schemas.member import MemberCreate, MemberResponse
from ...services.member import create_member

router = APIRouter(
    prefix="/members",
    tags=["members"],
)

@router.post(
    "/",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="注册新会员",
    description="通过手机号或邮箱注册新会员，生成会员卡",
)
async def register_member(member_data: MemberCreate):
    """
    注册新会员接口
    - **phone**: 手机号，需为11位数字
    - **email**: 邮箱，需符合格式
    """
    try:
        member = await create_member(member_data)
        return member
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )