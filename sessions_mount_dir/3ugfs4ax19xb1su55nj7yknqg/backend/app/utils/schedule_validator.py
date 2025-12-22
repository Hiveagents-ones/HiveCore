from datetime import datetime, time
from typing import List, Optional
from pydantic import BaseModel, validator

from ..models import Coach, CourseSchedule


class ScheduleValidator:
    """
    教练排班规则验证工具类
    """
    
    MIN_START_TIME = time(8, 0)  # 最早开始时间: 8:00
    MAX_END_TIME = time(22, 0)   # 最晚结束时间: 22:00
    MAX_HOURS_PER_DAY = 10       # 每天最多工作小时数
    MIN_BREAK_HOURS = 1          # 两个班次之间最少休息小时数
    
    @classmethod
    def validate_single_schedule(cls, schedule: 'ScheduleCreate') -> bool:
        """
        验证单个排班时间是否有效
        
        Args:
            schedule: 排班数据
            
        Returns:
            bool: 是否有效
        """
        # 验证时间范围
        if schedule.start_time.time() < cls.MIN_START_TIME:
            return False
            
        if schedule.end_time.time() > cls.MAX_END_TIME:
            return False
            
        # 验证时长合理性
        duration = (schedule.end_time - schedule.start_time).total_seconds() / 3600
        if duration <= 0 or duration > 4:  # 单次排班最长4小时
            return False
            
        return True
    
    @classmethod
    def validate_coach_schedules(cls, coach_id: int, new_schedule: 'ScheduleCreate', 
                                existing_schedules: List[CourseSchedule]) -> bool:
        """
        验证教练的排班是否冲突
        
        Args:
            coach_id: 教练ID
            new_schedule: 新排班数据
            existing_schedules: 教练已有的排班列表
            
        Returns:
            bool: 是否有效
        """
        # 1. 验证单个排班有效性
        if not cls.validate_single_schedule(new_schedule):
            return False
            
        # 2. 验证排班日期是否已有排班
        same_day_schedules = [
            s for s in existing_schedules 
            if s.start_time.date() == new_schedule.start_time.date()
        ]
        
        # 3. 验证每日总时长
        total_hours = sum(
            (s.end_time - s.start_time).total_seconds() / 3600 
            for s in same_day_schedules
        )
        new_duration = (new_schedule.end_time - new_schedule.start_time).total_seconds() / 3600
        
        if total_hours + new_duration > cls.MAX_HOURS_PER_DAY:
            return False
            
        # 4. 验证排班时间是否重叠
        for schedule in same_day_schedules:
            if (
                (new_schedule.start_time < schedule.end_time) and 
                (new_schedule.end_time > schedule.start_time)
            ):
                return False
                
            # 验证休息时间是否足够
            time_between = abs((new_schedule.start_time - schedule.end_time).total_seconds() / 3600)
            if 0 < time_between < cls.MIN_BREAK_HOURS:
                return False
                
        return True


class ScheduleCreate(BaseModel):
    """
    排班创建数据模型
    """
    coach_id: int
    course_id: int
    start_time: datetime
    end_time: datetime
    
    @validator('end_time')
    def validate_times(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('结束时间必须晚于开始时间')
        return v