from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy import Float
from sqlalchemy import Enum
from .database import Base
from enum import Enum as PyEnum
from sqlalchemy.sql import func


class CourseStatus(PyEnum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    ARCHIVED = 'archived'
    DRAFT = 'draft'
    PENDING_REVIEW = 'pending_review'


class CourseType(Base):
    """课程类型数据模型"""
    __tablename__ = 'course_types'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, comment='课程类型名称')
    description = Column(String(255), comment='课程类型描述')
    is_active = Column(Boolean, default=True, comment='是否启用')
    status = Column(Enum(CourseStatus), default=CourseStatus.ACTIVE, comment='课程状态')
    color_code = Column(String(7), default='#2196F3', comment='颜色代码')
    duration = Column(Integer, nullable=False, comment='课程时长(分钟)')
    max_capacity = Column(Integer, nullable=False, comment='最大参与人数')
    min_booking_hours = Column(Integer, default=2, comment='最少提前预约小时数')
    cancellation_hours = Column(Integer, default=1, comment='最少提前取消小时数')
    allow_booking = Column(Boolean, default=True, comment='是否允许预约')
    booking_window_days = Column(Integer, default=7, comment='可预约天数范围')
    refund_policy = Column(String(50), default='flexible', comment='退款政策: flexible/strict/non_refundable')
    display_order = Column(Integer, default=0, comment='显示排序')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment='创建时间')
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment='更新时间')
    created_by = Column(String(50), comment='创建人')
    updated_by = Column(String(50), comment='更新人')
    price = Column(Float, default=0.0, comment='课程价格')
version = Column(Integer, default=1, comment='版本号')

    def __repr__(self):
    def can_transition_to(self, new_status):
        """检查状态转换是否合法"""
        transitions = {
            CourseStatus.DRAFT: [CourseStatus.PENDING_REVIEW, CourseStatus.ARCHIVED],
            CourseStatus.PENDING_REVIEW: [CourseStatus.ACTIVE, CourseStatus.ARCHIVED],
            CourseStatus.ACTIVE: [CourseStatus.INACTIVE, CourseStatus.ARCHIVED],
            CourseStatus.INACTIVE: [CourseStatus.ACTIVE, CourseStatus.ARCHIVED],
            CourseStatus.ARCHIVED: []
        }
        return new_status in transitions.get(self.status, [])
        return f'<CourseType {self.name} (ID:{self.id})>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status.value if self.status else None,
            'color_code': self.color_code,
            'duration': self.duration,
            'max_capacity': self.max_capacity,
            'price': self.price,
            'display_order': self.display_order
            'version': self.version,
        }