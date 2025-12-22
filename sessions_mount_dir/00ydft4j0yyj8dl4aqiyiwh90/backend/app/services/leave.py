from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ..models.coach import Coach, CoachLeave


class LeaveService:
    """
    教练请假服务，实现两级审批流程
    """

    @staticmethod
    def create_leave_request(
        db: Session,
        coach_id: int,
        start_date: datetime,
        end_date: datetime,
        reason: str
    ) -> CoachLeave:
        """
        创建请假申请
        :param db: 数据库会话
        :param coach_id: 教练ID
        :param start_date: 开始时间
        :param end_date: 结束时间
        :param reason: 请假原因
        :return: 创建的请假记录
        """
        leave = CoachLeave(
            coach_id=coach_id,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            status='pending'
        )
        db.add(leave)
        db.commit()
        db.refresh(leave)
        return leave

    @staticmethod
    def get_leave_requests(db: Session, coach_id: Optional[int] = None) -> list[CoachLeave]:
        """
        获取请假申请列表
        :param db: 数据库会话
        :param coach_id: 可选，教练ID
        :return: 请假申请列表
        """
        query = db.query(CoachLeave)
        if coach_id:
            query = query.filter(CoachLeave.coach_id == coach_id)
        return query.all()

    @staticmethod
    def get_leave_request(db: Session, leave_id: int) -> Optional[CoachLeave]:
        """
        获取单个请假申请
        :param db: 数据库会话
        :param leave_id: 请假ID
        :return: 请假记录或None
        """
        return db.query(CoachLeave).filter(CoachLeave.id == leave_id).first()

    @staticmethod
    def approve_leave_request(db: Session, leave_id: int, approver_level: int = 1) -> Optional[CoachLeave]:
        """
        审批请假申请
        :param db: 数据库会话
        :param leave_id: 请假ID
        :param approver_level: 审批级别 (1: 初级审批, 2: 最终审批)
        :return: 更新后的请假记录或None
        """
        leave = db.query(CoachLeave).filter(CoachLeave.id == leave_id).first()
        if not leave:
            return None

        if approver_level == 1:
            leave.status = 'first_approved'
        elif approver_level == 2:
            leave.status = 'approved'

        db.commit()
        db.refresh(leave)
        return leave

    @staticmethod
    def reject_leave_request(db: Session, leave_id: int) -> Optional[CoachLeave]:
        """
        拒绝请假申请
        :param db: 数据库会话
        :param leave_id: 请假ID
        :return: 更新后的请假记录或None
        """
        leave = db.query(CoachLeave).filter(CoachLeave.id == leave_id).first()
        if not leave:
            return None

        leave.status = 'rejected'
        db.commit()
        db.refresh(leave)
        return leave

    @staticmethod
    def check_leave_conflict(
        db: Session,
        coach_id: int,
        start_date: datetime,
        end_date: datetime,
        exclude_leave_id: Optional[int] = None
    ) -> bool:
        """
        检查请假时间冲突
        :param db: 数据库会话
        :param coach_id: 教练ID
        :param start_date: 开始时间
        :param end_date: 结束时间
        :param exclude_leave_id: 要排除的请假ID（用于更新请假时检查冲突）
        :return: 是否存在冲突
        """
        query = db.query(CoachLeave).filter(
            CoachLeave.coach_id == coach_id,
            CoachLeave.status.in_(['pending', 'first_approved', 'approved']),
            (
                (CoachLeave.start_date <= end_date) &
                (CoachLeave.end_date >= start_date)
            )
        )

        if exclude_leave_id:
            query = query.filter(CoachLeave.id != exclude_leave_id)

        return query.count() > 0