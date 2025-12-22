from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json

from sqlalchemy.orm import Session
from sqlalchemy import func

from .models.coach import Coach, CoachLeave
from .models.course import Course


class SchedulingService:
    """
    教练排班服务，包含自动排班算法和冲突检测功能
    """

    def __init__(self, db: Session):
        self.db = db

    def get_available_coaches(self, start_time: datetime, end_time: datetime) -> List[Coach]:
        """
        获取在指定时间段内可用的教练列表
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            可用教练列表
        """
        # 1. 获取所有在职教练
        active_coaches = self.db.query(Coach).filter(Coach.status == True).all()
        
        # 2. 过滤掉请假的教练
        available_coaches = []
        for coach in active_coaches:
            # 检查教练是否有请假
            leave_conflict = self.db.query(CoachLeave).filter(
                CoachLeave.coach_id == coach.id,
                CoachLeave.status == 'approved',
                CoachLeave.start_date <= end_time,
                CoachLeave.end_date >= start_time
            ).first()
            
            if not leave_conflict:
                available_coaches.append(coach)
        
        return available_coaches

    def auto_assign_coach(self, course_data: Dict) -> Optional[Coach]:
        """
        新增自动分配算法逻辑：
        1. 优先考虑教练资质匹配度
        2. 考虑教练当前工作量
        3. 考虑教练的工作时间偏好
        """
        """
        自动分配教练算法
        
        Args:
            course_data: 课程信息，包含开始时间、结束时间、课程类型等
            
        Returns:
            分配的教练对象，如果没有可用教练则返回None
        """
        start_time = course_data['start_time']
        end_time = course_data['end_time']
        course_type = course_data.get('type', 'general')
        
        # 1. 获取可用教练
        available_coaches = self.get_available_coaches(start_time, end_time)
        
        if not available_coaches:
            return None
        
        # 2. 根据教练资质和课程类型匹配
        qualified_coaches = []
        for coach in available_coaches:
            if self._is_coach_qualified(coach, course_type):
                qualified_coaches.append(coach)
        
        if not qualified_coaches:
            return None
        
        # 3. 根据教练当前工作量排序（最少课程的优先）
        # 获取每个教练在当前日期的课程数
        current_date = start_time.date()
        from .models.course import Course  # 避免循环导入
        
        # 查询教练当天已有课程数
        subquery = self.db.query(
            Course.coach_id,
            func.count(Course.id).label('course_count')
        ).filter(
            func.date(Course.start_time) == current_date
        ).group_by(Course.coach_id).subquery()
        
        # 为每个教练添加课程数信息（如果没有则为0）
        coaches_with_load = []
        for coach in qualified_coaches:
            course_count = self.db.query(subquery.c.course_count).filter(
                subquery.c.coach_id == coach.id
            ).scalar() or 0
            
            # 检查是否超过每日最大课程数
            if coach.max_courses_per_day and course_count >= coach.max_courses_per_day:
                continue
                
            coaches_with_load.append({
                'coach': coach,
                'course_count': course_count
            })
        
        if not coaches_with_load:
            return None
            
        # 按课程数升序排序
        sorted_coaches = sorted(coaches_with_load, key=lambda x: x['course_count'])
        return sorted_coaches[0]['coach']
    
    def _is_coach_qualified(self, coach: Coach, course_type: str) -> bool:
        """
        检查教练是否有资质教授特定类型的课程
        
        Args:
            coach: 教练对象
            course_type: 课程类型
            
        Returns:
            bool: 是否有资质
        """
        # 简单实现：检查教练的专业领域是否包含课程类型
        # 实际项目中应该更复杂的资质检查逻辑
        return course_type.lower() in (coach.specialty or '').lower()
    
    def check_schedule_conflict(self, coach_id: int, start_time: datetime, end_time: datetime) -> bool:
        """
        检查教练在指定时间段是否有排班冲突
        
        Args:
            coach_id: 教练ID
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            bool: 是否有冲突
        """
        """
        检查教练在指定时间段是否有排班冲突
        
        Args:
            coach_id: 教练ID
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            bool: 是否有冲突
        """
        # 1. 检查请假冲突
        leave_conflict = self.db.query(CoachLeave).filter(
            CoachLeave.coach_id == coach_id,
            CoachLeave.status == 'approved',
            CoachLeave.start_date <= end_time,
            CoachLeave.end_date >= start_time
        ).first()
        
        if leave_conflict:
            return True
        
        # 2. 检查已有课程排班冲突
        from .models.course import Course
        course_conflict = self.db.query(Course).filter(
            Course.coach_id == coach_id,
            Course.start_time <= end_time,
            Course.end_time >= start_time
        ).first()
        
        if course_conflict:
            return True
            
        # 3. 检查是否在工作时间内
        coach = self.db.query(Coach).filter(Coach.id == coach_id).first()
        if coach and coach.working_hours:
            try:
                work_start, work_end = coach.working_hours.split('-')
                work_start_time = datetime.strptime(work_start.strip(), '%H:%M').time()
                work_end_time = datetime.strptime(work_end.strip(), '%H:%M').time()
                
                if start_time.time() < work_start_time or end_time.time() > work_end_time:
                    return True
            except (ValueError, AttributeError):
                pass
        
        return False
    
    def get_coach_schedule(self, coach_id: int, start_date: datetime, end_date: datetime) -> Dict:
        """
        获取教练的排班表
        
        Args:
            coach_id: 教练ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            排班表字典
        """
        coach = self.db.query(Coach).filter(Coach.id == coach_id).first()
        if not coach:
            return {}
        
        # 1. 获取教练的基本工作时间
        schedule = {
            'coach_id': coach.id,
            'coach_name': coach.name,
            'working_hours': coach.working_hours,
            'max_courses_per_day': coach.max_courses_per_day,
            'schedule': {}
        }
        
        # 2. 获取请假信息
        leaves = self.db.query(CoachLeave).filter(
            CoachLeave.coach_id == coach_id,
            CoachLeave.status == 'approved',
            CoachLeave.end_date >= start_date,
            CoachLeave.start_date <= end_date
        ).all()
        
        for leave in leaves:
            schedule['schedule'][leave.start_date.date().isoformat()] = {
                'type': 'leave',
                'start_time': leave.start_date,
                'end_time': leave.end_date,
                'reason': leave.reason
            }
        
        # 3. TODO: 获取课程安排
        # 需要后续实现从数据库中获取教练的课程安排
        
        return schedule

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
    def auto_assign_coach(self, course_data: Dict) -> Optional[Coach]:
        """
        自动分配教练算法
        
        算法逻辑：
        1. 获取时间段内可用教练
        2. 根据教练资质和课程类型匹配
        3. 根据教练当前工作量排序（最少课程的优先）
        4. 检查教练每日最大课程数限制

        Args:
            course_data: 课程信息，包含开始时间、结束时间、课程类型等

        Returns:
            分配的教练对象，如果没有可用教练则返回None
        """

# [AUTO-APPENDED] Failed to replace, adding new code:
    def _is_coach_qualified(self, coach: Coach, course_type: str) -> bool:
        """
        检查教练是否有资质教授特定类型的课程
        
        实现逻辑：
        1. 检查教练的专业领域是否包含课程类型
        2. 检查教练的认证资质是否匹配课程要求

        Args:
            coach: 教练对象
            course_type: 课程类型

        Returns:
            bool: 是否有资质
        """
        # 简单实现：检查教练的专业领域是否包含课程类型
        # 实际项目中应该更复杂的资质检查逻辑
        return course_type.lower() in (coach.specialty or '').lower()