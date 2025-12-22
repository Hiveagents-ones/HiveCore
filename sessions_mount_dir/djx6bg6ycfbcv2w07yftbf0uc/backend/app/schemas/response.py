from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar('T')

class BaseResponse(BaseModel, Generic[T]):
    """统一API响应格式"""
    success: bool = Field(..., description="请求是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[T] = Field(None, description="响应数据")
    code: int = Field(200, description="业务状态码")
    timestamp: Optional[str] = Field(None, description="响应时间戳")

class ErrorResponse(BaseModel):
    """错误响应格式"""
    success: bool = Field(False, description="请求是否成功")
    message: str = Field(..., description="错误消息")
    error_code: str = Field(..., description="错误代码")
    details: Optional[dict] = Field(None, description="错误详情")
    timestamp: Optional[str] = Field(None, description="响应时间戳")

class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应格式"""
    success: bool = Field(True, description="请求是否成功")
    message: str = Field("操作成功", description="响应消息")
    data: list[T] = Field(..., description="数据列表")
    pagination: dict = Field(..., description="分页信息")
    code: int = Field(200, description="业务状态码")
    timestamp: Optional[str] = Field(None, description="响应时间戳")

class SuccessResponse(BaseModel):
    """简单成功响应格式"""
    success: bool = Field(True, description="请求是否成功")
    message: str = Field("操作成功", description="响应消息")
    code: int = Field(200, description="业务状态码")
    timestamp: Optional[str] = Field(None, description="响应时间戳")
