from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, validator


class CoachBase(BaseModel):
    """教练基本信息模型"""
    name: str = Field(..., min_length=2, max_length=50, description="教练姓名")
    specialty: str = Field(..., min_length=2, max_length=100, description="专长领域")
    contact: str = Field(..., min_length=6, max_length=20, description="联系方式")


class CoachCreate(CoachBase):
    """创建教练数据模型"""
    pass


class CoachUpdate(BaseModel):
    """更新教练数据模型"""
    name: Optional[str] = Field(None, min_length=2, max_length=50, description="教练姓名")
    specialty: Optional[str] = Field(None, min_length=2, max_length=100, description="专长领域")
    contact: Optional[str] = Field(None, min_length=6, max_length=20, description="联系方式")


class CoachResponse(CoachBase):
    """教练响应数据模型"""
    id: int

    class Config:
        orm_mode = True


class ScheduleBase(BaseModel):
    """排班基础模型"""
    coach_id: int = Field(..., description="教练ID")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    course_id: Optional[int] = Field(None, description="关联课程ID")

    @validator('end_time')
    def validate_time_range(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError("结束时间必须晚于开始时间")
        return v


class ScheduleCreate(ScheduleBase):
    """创建排班数据模型"""
    pass


class ScheduleUpdate(BaseModel):
    """更新排班数据模型"""
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    course_id: Optional[int] = Field(None, description="关联课程ID")

    @validator('end_time')
    def validate_time_range(cls, v, values):
        if 'start_time' in values and v and values['start_time'] and v <= values['start_time']:
            raise ValueError("结束时间必须晚于开始时间")
        return v


class ScheduleResponse(ScheduleBase):


class ScheduleConflictCheck(BaseModel):
    """排班冲突检查模型"""
    coach_id: int = Field(..., description="教练ID")
    start_time: datetime = Field(..., description="检查开始时间")
    end_time: datetime = Field(..., description="检查结束时间")
    exclude_schedule_id: Optional[int] = Field(None, description="要排除的排班ID")

    @validator('end_time')
    def validate_time_range(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError("结束时间必须晚于开始时间")
        return v


class ScheduleBulkCreate(BaseModel):
    """批量创建排班模型"""
    coach_id: int = Field(..., description="教练ID")
    schedules: List[ScheduleCreate] = Field(..., min_items=1, description="排班列表")

    @validator('schedules')
    def validate_schedules(cls, v):
        # 检查批量排班是否有时间重叠
        sorted_schedules = sorted(v, key=lambda x: x.start_time)
        for i in range(len(sorted_schedules) - 1):
            if sorted_schedules[i].end_time > sorted_schedules[i + 1].start_time:
                raise ValueError(f"排班时间冲突: 第{i+1}个排班与第{i+2}个排班时间重叠")
        return v
    """排班响应数据模型"""
    id: int

    class Config:
        orm_mode = True