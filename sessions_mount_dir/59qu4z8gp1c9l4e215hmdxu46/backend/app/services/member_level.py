from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..database import Member, MemberCard, CourseBooking, MembershipLevel, Course


class MemberLevelService:
    """
    会员等级计算服务
    
    提供会员等级计算和管理的相关功能
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_member_level(self, member_id: int) -> Optional[int]:
        """
        计算会员等级
        
        根据会员的活跃度和消费行为计算会员等级
        
        Args:
            member_id: 会员ID
            
        Returns:
            会员等级ID，如果无法计算则返回None
        """
        # 获取会员基本信息
        member = self.db.query(Member).filter(Member.id == member_id).first()
        if not member:
            return None
            
        # 获取会员卡信息
        member_card = self.db.query(MemberCard).filter(
            MemberCard.member_id == member_id,
            MemberCard.status == 'active'
        ).first()
        
        if not member_card:
            return None
            
        # 如果会员卡已有等级，直接返回
        if member_card.level_id:
            return member_card.level_id
            
        # 计算会员活跃度（课程参与次数）
        course_count = self.db.query(CourseBooking).filter(
            CourseBooking.member_id == member_id,
            CourseBooking.status == 'attended'
        ).count()
        
        # 计算会员加入时长（月）
        join_months = (date.today().year - member.join_date.year) * 12 + \
                     (date.today().month - member.join_date.month)
        
        # 简单规则：根据课程参与次数和加入时长确定等级
        if course_count >= 20 and join_months >= 12:
            level = self.db.query(MembershipLevel).filter(
                MembershipLevel.name == 'Gold'
            ).first()
        elif course_count >= 10 and join_months >= 6:
            level = self.db.query(MembershipLevel).filter(
                MembershipLevel.name == 'Silver'
            ).first()
        else:
            level = self.db.query(MembershipLevel).filter(
                MembershipLevel.name == 'Basic'
            ).first()
            
        return level.id if level else None
    
    def update_member_level(self, member_id: int) -> bool:
        """
        更新会员等级
        
        根据计算规则更新会员的等级
        
        Args:
            member_id: 会员ID
            
        Returns:
            是否成功更新
        """
        level_id = self.calculate_member_level(member_id)
        if not level_id:
            return False
            
        member_card = self.db.query(MemberCard).filter(
            MemberCard.member_id == member_id,
            MemberCard.status == 'active'
        ).first()
        
        if not member_card:
            return False
            
        member_card.level_id = level_id
        self.db.commit()
        return True
    
    def get_member_level_details(self, member_id: int) -> Optional[dict]:
        """
        获取会员等级详情

        Args:
            member_id: 会员ID

        Returns:
            包含会员等级详情的字典，如果无法获取则返回None
            {
                'level_id': int,
                'level_name': str,
                'benefits': str
            }
        """
        member_card = self.db.query(MemberCard).filter(
            MemberCard.member_id == member_id,
            MemberCard.status == 'active'
        ).first()

        if not member_card or not member_card.level_id:
            return None

        level = self.db.query(MembershipLevel).filter(
            MembershipLevel.id == member_card.level_id
        ).first()

        if not level:
            return None

        return {
            'level_id': level.id,
            'level_name': level.name,
            'benefits': level.benefits
        }

    def can_book_course(self, member_id: int, course_id: int) -> bool:
        """
        检查会员是否有权限预约指定课程
        
        Args:
            member_id: 会员ID
            course_id: 课程ID
            
        Returns:
            是否有预约权限
        """
        # 获取会员等级详情
        level_info = self.get_member_level_details(member_id)
        if not level_info:
            return False
            
        # 获取课程信息
        course = self.db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return False
            
        # 检查会员等级是否满足课程要求
        if level_info['level_name'] == 'Basic' and course.required_level != 'Basic':
            return False
        elif level_info['level_name'] == 'Silver' and course.required_level == 'Gold':
            return False
            
        return True
        
    def get_booking_limit(self, member_id: int) -> int:
        """
        获取会员的课程预约上限
        
        Args:
            member_id: 会员ID
            
        Returns:
            可预约课程数量上限
        """
        level_info = self.get_member_level_details(member_id)
        if not level_info:
            return 1
            
        # 根据会员等级返回不同的预约上限
        if level_info['level_name'] == 'Gold':
            return 10
        elif level_info['level_name'] == 'Silver':
            return 5
        else:
            return 2
        """
        获取会员等级详情
        
        Args:
            member_id: 会员ID
            
        Returns:
            包含会员等级详情的字典，如果无法获取则返回None
            {
                'level_id': int,
                'level_name': str,
                'benefits': str
            }
        """
        member_card = self.db.query(MemberCard).filter(
            MemberCard.member_id == member_id,
            MemberCard.status == 'active'
        ).first()
        
        if not member_card or not member_card.level_id:
            return None
            
        level = self.db.query(MembershipLevel).filter(
            MembershipLevel.id == member_card.level_id
        ).first()
        
        if not level:
            return None
            
        return {
            'level_id': level.id,
            'level_name': level.name,
            'benefits': level.benefits
        }

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
    def calculate_member_level(self, member_id: int) -> Optional[int]:
        """
        计算会员等级

        根据会员的活跃度、消费行为和最近活动时间计算会员等级

        Args:
            member_id: 会员ID

        Returns:
            会员等级ID，如果无法计算则返回None
        """
        # 获取会员基本信息
        member = self.db.query(Member).filter(Member.id == member_id).first()
        if not member:
            return None

        # 获取会员卡信息
        member_card = self.db.query(MemberCard).filter(
            MemberCard.member_id == member_id,
            MemberCard.status == 'active'
        ).first()

        if not member_card:
            return None

        # 如果会员卡已有等级，直接返回
        if member_card.level_id:
            return member_card.level_id

        # 计算会员活跃度（最近3个月的课程参与次数）
        three_months_ago = date.today() - timedelta(days=90)
        recent_course_count = self.db.query(CourseBooking).filter(
            CourseBooking.member_id == member_id,
            CourseBooking.status == 'attended',
            CourseBooking.booking_time >= three_months_ago
        ).count()

        # 计算会员加入时长（月）
        join_months = (date.today().year - member.join_date.year) * 12 + \
                     (date.today().month - member.join_date.month)

        # 改进规则：考虑最近活跃度和总活跃度
        if (recent_course_count >= 8 or recent_course_count >= 5 and join_months >= 12):
            level = self.db.query(MembershipLevel).filter(
                MembershipLevel.name == 'Gold'
            ).first()
        elif (recent_course_count >= 4 or recent_course_count >= 2 and join_months >= 6):
            level = self.db.query(MembershipLevel).filter(
                MembershipLevel.name == 'Silver'
            ).first()
        else:
            level = self.db.query(MembershipLevel).filter(
                MembershipLevel.name == 'Basic'
            ).first()

        return level.id if level else None

# [AUTO-APPENDED] Failed to replace, adding new code:
    def can_book_course(self, member_id: int, course_id: int) -> bool:
        """
        检查会员是否有权限预约指定课程

        Args:
            member_id: 会员ID
            course_id: 课程ID

        Returns:
            是否有预约权限
        """
        # 获取会员等级详情
        level_info = self.get_member_level_details(member_id)
        if not level_info:
            return False

        # 获取课程信息
        course = self.db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return False

        # 检查课程是否对会员等级开放
        required_level = course.required_level
        if required_level == 'Gold' and level_info['level_name'] != 'Gold':
            return False
        elif required_level == 'Silver' and level_info['level_name'] == 'Basic':
            return False
            
        # 检查会员当前预约数量是否已达上限
        current_bookings = self.db.query(CourseBooking).filter(
            CourseBooking.member_id == member_id,
            CourseBooking.status.in_(['booked', 'attended'])
        ).count()
        
        if current_bookings >= self.get_booking_limit(member_id):
            return False

        return True

# [AUTO-APPENDED] Failed to replace, adding new code:
    def get_booking_limit(self, member_id: int) -> int:
        """
        获取会员的课程预约上限

        Args:
            member_id: 会员ID

        Returns:
            可预约课程数量上限
        """
        level_info = self.get_member_level_details(member_id)
        if not level_info:
            return 3  # 默认3节课

        # 根据会员等级返回不同的预约上限
        if level_info['level_name'] == 'Gold':
            return 15  # 金牌会员可预约15节课
        elif level_info['level_name'] == 'Silver':
            return 8   # 银牌会员可预约8节课
        else:
            return 3    # 普通会员可预约3节课

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
    def calculate_member_level(self, member_id: int) -> Optional[int]:
        """
        计算会员等级

        根据会员的活跃度和消费行为计算会员等级

        Args:
            member_id: 会员ID

        Returns:
            会员等级ID，如果无法计算则返回None
        """
        # 获取会员基本信息
        member = self.db.query(Member).filter(Member.id == member_id).first()
        if not member:
            return None

        # 获取会员卡信息
        member_card = self.db.query(MemberCard).filter(
            MemberCard.member_id == member_id,
            MemberCard.status == 'active'
        ).first()

        if not member_card:
            return None

        # 如果会员卡已有等级，直接返回
        if member_card.level_id:
            return member_card.level_id

        # 计算会员活跃度（最近3个月的课程参与次数）
        three_months_ago = date.today() - timedelta(days=90)
        recent_course_count = self.db.query(CourseBooking).filter(
            CourseBooking.member_id == member_id,
            CourseBooking.status == 'attended',
            CourseBooking.booking_time >= three_months_ago
        ).count()

        # 计算会员加入时长（月）
        join_months = (date.today().year - member.join_date.year) * 12 + \
                     (date.today().month - member.join_date.month)

        # 改进规则：考虑最近活跃度和总活跃度
        if (recent_course_count >= 8 or recent_course_count >= 5 and join_months >= 12):
            level = self.db.query(MembershipLevel).filter(
                MembershipLevel.name == 'Gold'
            ).first()
        elif (recent_course_count >= 4 or recent_course_count >= 2 and join_months >= 6):
            level = self.db.query(MembershipLevel).filter(
                MembershipLevel.name == 'Silver'
            ).first()
        else:
            level = self.db.query(MembershipLevel).filter(
                MembershipLevel.name == 'Basic'
            ).first()

        return level.id if level else None

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
    def calculate_member_level(self, member_id: int) -> Optional[int]:
        """
        计算会员等级

        根据会员的活跃度和消费行为计算会员等级

        Args:
            member_id: 会员ID

        Returns:
            会员等级ID，如果无法计算则返回None
        """
        # 获取会员基本信息
        member = self.db.query(Member).filter(Member.id == member_id).first()
        if not member:
            return None

        # 获取会员卡信息
        member_card = self.db.query(MemberCard).filter(
            MemberCard.member_id == member_id,
            MemberCard.status == 'active'
        ).first()

        if not member_card:
            return None

        # 如果会员卡已有等级，直接返回
        if member_card.level_id:
            return member_card.level_id

        # 计算会员活跃度（最近3个月的课程参与次数）
        three_months_ago = date.today() - timedelta(days=90)
        recent_course_count = self.db.query(CourseBooking).filter(
            CourseBooking.member_id == member_id,
            CourseBooking.status == 'attended',
            CourseBooking.booking_time >= three_months_ago
        ).count()

        # 计算总课程参与次数
        total_course_count = self.db.query(CourseBooking).filter(
            CourseBooking.member_id == member_id,
            CourseBooking.status == 'attended'
        ).count()

        # 计算会员加入时长（月）
        join_months = (date.today().year - member.join_date.year) * 12 + \
                     (date.today().month - member.join_date.month)

        # 改进规则：考虑最近活跃度和总活跃度
        if (recent_course_count >= 8 or total_course_count >= 20) and join_months >= 6:
            level = self.db.query(MembershipLevel).filter(
                MembershipLevel.name == 'Gold'
            ).first()
        elif (recent_course_count >= 4 or total_course_count >= 10) and join_months >= 3:
            level = self.db.query(MembershipLevel).filter(
                MembershipLevel.name == 'Silver'
            ).first()
        else:
            level = self.db.query(MembershipLevel).filter(
                MembershipLevel.name == 'Basic'
            ).first()

        return level.id if level else None