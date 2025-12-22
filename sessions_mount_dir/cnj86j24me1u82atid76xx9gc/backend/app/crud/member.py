from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from ..models.member import Member
from ..core.rbac import check_permission, Permission
from ..core.audit import AuditService

class MemberCRUD:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)

    def create_member(self, 
                      member_data: Dict[str, Any], 
                      user_id: int,
                      ip_address: Optional[str] = None) -> Member:
        """
        创建新会员
        
        Args:
            member_data: 会员数据字典
            user_id: 操作用户ID
            ip_address: 操作来源IP地址
            
        Returns:
            Member: 创建的会员对象
        """
        # 权限检查
        if not check_permission(user_id, Permission.MEMBER_CREATE):
            raise PermissionError("No permission to create member")
            
        # 检查手机号和邮箱是否已存在
        existing = self.db.query(Member).filter(
            or_(Member.phone == member_data.get('phone'),
                Member.email == member_data.get('email'))
        ).first()
        
        if existing:
            raise ValueError("Phone or email already exists")
            
        member = Member(
            name=member_data['name'],
            phone=member_data['phone'],
            email=member_data['email'],
            membership_level=member_data.get('membership_level', 'basic'),
            remaining_membership=member_data.get('remaining_membership', 0.0),
            created_by=user_id,
            updated_by=user_id
        )
        
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        
        # 记录审计日志
        self.audit_service.log_member_action(
            user_id=user_id,
            action='create',
            member_id=member.id,
            details=member_data,
            ip_address=ip_address
        )
        
        return member

    def get_member(self, 
                   member_id: int, 
                   user_id: int,
                   ip_address: Optional[str] = None) -> Optional[Member]:
        """
        获取单个会员信息
        
        Args:
            member_id: 会员ID
            user_id: 操作用户ID
            ip_address: 操作来源IP地址
            
        Returns:
            Optional[Member]: 会员对象或None
        """
        # 权限检查
        if not check_permission(user_id, Permission.MEMBER_READ):
            raise PermissionError("No permission to read member")
            
        member = self.db.query(Member).filter(Member.id == member_id).first()
        
        if member:
            # 记录审计日志
            self.audit_service.log_member_action(
                user_id=user_id,
                action='view',
                member_id=member_id,
                ip_address=ip_address
            )
            
        return member

    def get_members(self, 
                    skip: int = 0, 
                    limit: int = 100,
                    user_id: int = None,
                    ip_address: Optional[str] = None,
                    filters: Optional[Dict[str, Any]] = None) -> List[Member]:
        """
        获取会员列表
        
        Args:
            skip: 跳过记录数
            limit: 返回记录数限制
            user_id: 操作用户ID
            ip_address: 操作来源IP地址
            filters: 过滤条件字典
            
        Returns:
            List[Member]: 会员列表
        """
        # 权限检查
        if not check_permission(user_id, Permission.MEMBER_READ):
            raise PermissionError("No permission to read members")
            
        query = self.db.query(Member)
        
        # 应用过滤条件
        if filters:
            if 'name' in filters:
                query = query.filter(Member.name.ilike(f"%{filters['name']}%"))
            if 'phone' in filters:
                query = query.filter(Member.phone.ilike(f"%{filters['phone']}%"))
            if 'email' in filters:
                query = query.filter(Member.email.ilike(f"%{filters['email']}%"))
            if 'membership_level' in filters:
                query = query.filter(Member.membership_level == filters['membership_level'])
            if 'is_active' in filters:
                query = query.filter(Member.is_active == filters['is_active'])
                
        members = query.offset(skip).limit(limit).all()
        
        # 记录审计日志
        self.audit_service.log_member_action(
            user_id=user_id,
            action='list',
            details={'filters': filters, 'skip': skip, 'limit': limit},
            ip_address=ip_address
        )
        
        return members

    def update_member(self, 
                      member_id: int, 
                      member_data: Dict[str, Any],
                      user_id: int,
                      ip_address: Optional[str] = None) -> Optional[Member]:
        """
        更新会员信息
        
        Args:
            member_id: 会员ID
            member_data: 更新数据字典
            user_id: 操作用户ID
            ip_address: 操作来源IP地址
            
        Returns:
            Optional[Member]: 更新后的会员对象或None
        """
        # 权限检查
        if not check_permission(user_id, Permission.MEMBER_UPDATE):
            raise PermissionError("No permission to update member")
            
        member = self.db.query(Member).filter(Member.id == member_id).first()
        
        if not member:
            return None
            
        # 检查手机号和邮箱唯一性
        if 'phone' in member_data:
            existing = self.db.query(Member).filter(
                and_(Member.phone == member_data['phone'],
                     Member.id != member_id)
            ).first()
            if existing:
                raise ValueError("Phone already exists")
                
        if 'email' in member_data:
            existing = self.db.query(Member).filter(
                and_(Member.email == member_data['email'],
                     Member.id != member_id)
            ).first()
            if existing:
                raise ValueError("Email already exists")
        
        # 更新字段
        for field, value in member_data.items():
            if hasattr(member, field):
                setattr(member, field, value)
                
        member.updated_by = user_id
        
        self.db.commit()
        self.db.refresh(member)
        
        # 记录审计日志
        self.audit_service.log_member_action(
            user_id=user_id,
            action='update',
            member_id=member_id,
            details=member_data,
            ip_address=ip_address
        )
        
        return member

    def delete_member(self, 
                      member_id: int, 
                      user_id: int,
                      ip_address: Optional[str] = None) -> bool:
        """
        删除会员（软删除）
        
        Args:
            member_id: 会员ID
            user_id: 操作用户ID
            ip_address: 操作来源IP地址
            
        Returns:
            bool: 是否成功删除
        """
        # 权限检查
        if not check_permission(user_id, Permission.MEMBER_DELETE):
            raise PermissionError("No permission to delete member")
            
        member = self.db.query(Member).filter(Member.id == member_id).first()
        
        if not member:
            return False
            
        member.is_active = False
        member.updated_by = user_id
        
        self.db.commit()
        
        # 记录审计日志
        self.audit_service.log_member_action(
            user_id=user_id,
            action='delete',
            member_id=member_id,
            ip_address=ip_address
        )
        
        return True

    def extend_membership(self, 
                         member_id: int, 
                         days: float,
                         user_id: int,
                         ip_address: Optional[str] = None) -> bool:
        """
        延长会员会籍
        
        Args:
            member_id: 会员ID
            days: 延长天数
            user_id: 操作用户ID
            ip_address: 操作来源IP地址
            
        Returns:
            bool: 是否成功延长
        """
        # 权限检查
        if not check_permission(user_id, Permission.MEMBER_UPDATE):
            raise PermissionError("No permission to update member")
            
        member = self.db.query(Member).filter(Member.id == member_id).first()
        
        if not member:
            return False
            
        member.extend_membership(days, user_id)
        self.db.commit()
        
        # 记录审计日志
        self.audit_service.log_member_action(
            user_id=user_id,
            action='extend_membership',
            member_id=member_id,
            details={'days': days},
            ip_address=ip_address
        )
        
        return True

    def consume_membership(self, 
                          member_id: int, 
                          days: float,
                          user_id: int,
                          ip_address: Optional[str] = None) -> bool:
        """
        消耗会员会籍
        
        Args:
            member_id: 会员ID
            days: 消耗天数
            user_id: 操作用户ID
            ip_address: 操作来源IP地址
            
        Returns:
            bool: 是否成功消耗
        """
        # 权限检查
        if not check_permission(user_id, Permission.MEMBER_UPDATE):
            raise PermissionError("No permission to update member")
            
        member = self.db.query(Member).filter(Member.id == member_id).first()
        
        if not member:
            return False
            
        success = member.consume_membership(days, user_id)
        
        if success:
            self.db.commit()
            
            # 记录审计日志
            self.audit_service.log_member_action(
                user_id=user_id,
                action='consume_membership',
                member_id=member_id,
                details={'days': days},
                ip_address=ip_address
            )
        
        return success

    def get_member_audit_logs(self, 
                             member_id: int, 
                             user_id: int,
                             limit: int = 100) -> List:
        """
        获取会员审计日志
        
        Args:
            member_id: 会员ID
            user_id: 操作用户ID
            limit: 返回记录数限制
            
        Returns:
            List: 审计日志列表
        """
        # 权限检查
        if not check_permission(user_id, Permission.MEMBER_READ):
            raise PermissionError("No permission to read member audit logs")
            
        return self.audit_service.get_member_audit_logs(member_id, limit)
