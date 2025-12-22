from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.coach import Coach


class ScheduleService:
    """
    教练排班服务
    处理教练排班相关的业务逻辑
    """

    @staticmethod
    def get_coach_schedule(db: Session, coach_id: int) -> Optional[Dict]:
        """
        获取指定教练的排班信息
        :param db: 数据库会话
        :param coach_id: 教练ID
        :return: 排班信息字典或None
        """
        coach = db.query(Coach).filter(Coach.id == coach_id).first()
        return coach.schedule if coach else None

    @staticmethod
    def update_coach_schedule(db: Session, coach_id: int, schedule_data: Dict) -> bool:
        """
        更新教练排班信息
        :param db: 数据库会话
        :param coach_id: 教练ID
        :param schedule_data: 新的排班数据
        :return: 是否更新成功
        """
        coach = db.query(Coach).filter(Coach.id == coach_id).first()
        if not coach:
            return False

        coach.schedule = schedule_data
        db.commit()
        db.refresh(coach)
        return True

    @staticmethod
    def add_work_day(db: Session, coach_id: int, date: str, shift: str) -> bool:
        """
        添加工作日期和班次
        :param db: 数据库会话
        :param coach_id: 教练ID
        :param date: 日期字符串 (YYYY-MM-DD)
        :param shift: 班次 (早/中/晚)
        :return: 是否添加成功
        """
        try:
            datetime.strptime(date, '%Y-%m-%d')  # 验证日期格式
        except ValueError:
            return False

        coach = db.query(Coach).filter(Coach.id == coach_id).first()
        if not coach:
            return False

        schedule = coach.schedule or {"work_days": [], "shifts": []}
        
        if date not in schedule["work_days"]:
            schedule["work_days"].append(date)
            schedule["shifts"].append(shift)
            coach.schedule = schedule
            db.commit()
            return True
        return False

    @staticmethod
    def remove_work_day(db: Session, coach_id: int, date: str) -> bool:
        """
        移除工作日期
        :param db: 数据库会话
        :param coach_id: 教练ID
        :param date: 日期字符串 (YYYY-MM-DD)
        :return: 是否移除成功
        """
        coach = db.query(Coach).filter(Coach.id == coach_id).first()
        if not coach or not coach.schedule:
            return False

        try:
            index = coach.schedule["work_days"].index(date)
            del coach.schedule["work_days"][index]
            del coach.schedule["shifts"][index]
            db.commit()
            return True
        except ValueError:
            return False

    @staticmethod
    def get_available_coaches(db: Session, date: str) -> List[Dict]:
        """
        获取指定日期可用的教练列表
        :param db: 数据库会话
        :param date: 日期字符串 (YYYY-MM-DD)
        :return: 可用教练列表
        """
        coaches = db.query(Coach).all()
        available_coaches = []
        
        for coach in coaches:
            if coach.schedule and date in coach.schedule.get("work_days", []):
                index = coach.schedule["work_days"].index(date)
                shift = coach.schedule["shifts"][index]
                available_coaches.append({
                    "id": coach.id,
                    "name": coach.name,
                    "shift": shift
                })
        
        return available_coaches