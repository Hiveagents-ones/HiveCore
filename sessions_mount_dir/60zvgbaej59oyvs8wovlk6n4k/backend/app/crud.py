from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from . import models, schemas
from .security import encrypt_data, decrypt_data

from .models import PaymentStatus, NotificationType, NotificationStatus
from .models import Package, Payment, Notification

def get_member(db: Session, member_id: int) -> Optional[models.Member]:
    """获取单个会员信息"""
    member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if member:
        # 解密敏感信息返回
        member.phone = decrypt_data(member.phone)
        member.card_number = decrypt_data(member.card_number)
    return member

def get_member_by_phone(db: Session, phone: str) -> Optional[models.Member]:
    """通过手机号获取会员信息"""
    encrypted_phone = encrypt_data(phone)
    member = db.query(models.Member).filter(models.Member.phone == encrypted_phone).first()
    if member:
        # 解密敏感信息返回
        member.phone = decrypt_data(member.phone)
        member.card_number = decrypt_data(member.card_number)
    return member

def get_member_by_card_number(db: Session, card_number: str) -> Optional[models.Member]:
    """通过会员卡号获取会员信息"""
    encrypted_card_number = encrypt_data(card_number)
    member = db.query(models.Member).filter(models.Member.card_number == encrypted_card_number).first()
    if member:
        # 解密敏感信息返回
        member.phone = decrypt_data(member.phone)
        member.card_number = decrypt_data(member.card_number)
    return member

def get_members(db: Session, skip: int = 0, limit: int = 100) -> List[models.Member]:
    """获取会员列表"""
    members = db.query(models.Member).offset(skip).limit(limit).all()
    # 解密敏感信息
    for member in members:
        member.phone = decrypt_data(member.phone)
        member.card_number = decrypt_data(member.card_number)
    return members

def create_member(db: Session, member: schemas.MemberCreate) -> models.Member:
    """创建新会员"""
    # 加密敏感信息
    encrypted_phone = encrypt_data(member.phone)
    encrypted_card_number = encrypt_data(member.card_number)
    
    db_member = models.Member(
        name=member.name,
        phone=encrypted_phone,
        card_number=encrypted_card_number,
        level=member.level,
        remaining_months=member.remaining_months,
        is_active=member.is_active
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    
    # 记录历史
    create_history(db, schemas.HistoryCreate(
        member_id=db_member.id,
        action="create",
        description=f"创建会员: {member.name}"
    ))
    
    return db_member

def update_member(db: Session, member_id: int, member: schemas.MemberUpdate) -> Optional[models.Member]:
    """更新会员信息"""
    db_member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not db_member:
        return None
    
    update_data = member.dict(exclude_unset=True)
    
    # 处理加密字段
    if 'phone' in update_data:
        update_data['phone'] = encrypt_data(update_data['phone'])
    if 'card_number' in update_data:
        update_data['card_number'] = encrypt_data(update_data['card_number'])
    
    for field, value in update_data.items():
        setattr(db_member, field, value)
    
    db.commit()
    db.refresh(db_member)
    
    # 记录历史
    create_history(db, schemas.HistoryCreate(
        member_id=member_id,
        action="update",
        description=f"更新会员信息: {member.name or db_member.name}"
    ))
    
    return db_member

def delete_member(db: Session, member_id: int) -> bool:
    """删除会员"""
    db_member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not db_member:
        return False
    
    # 记录历史
    create_history(db, schemas.HistoryCreate(
        member_id=member_id,
        action="delete",
        description=f"删除会员: {db_member.name}"
    ))
    
    db.delete(db_member)
    db.commit()
    return True

def create_history(db: Session, history: schemas.HistoryCreate) -> models.History:
    """创建历史记录"""
    db_history = models.History(**history.dict())
    db.add(db_history)
    db.commit()
    db.refresh(db_history)
    return db_history

def get_member_histories(db: Session, member_id: int, skip: int = 0, limit: int = 100) -> List[models.History]:
    """获取会员历史记录"""
    return db.query(models.History).filter(models.History.member_id == member_id).offset(skip).limit(limit).all()

def create_audit_log(db: Session, audit_log: schemas.AuditLogCreate) -> models.AuditLog:
    """创建审计日志"""
    db_audit_log = models.AuditLog(**audit_log.dict())
    db.add(db_audit_log)
    db.commit()
    db.refresh(db_audit_log)
    return db_audit_log

def get_audit_logs(db: Session, skip: int = 0, limit: int = 100) -> List[models.AuditLog]:
    """获取审计日志列表"""
    return db.query(models.AuditLog).offset(skip).limit(limit).all()

def sync_member_data(db: Session, member_id: int) -> Optional[models.Member]:
    """同步会员数据"""
    db_member = get_member(db, member_id)
    if not db_member:
        return None
    
    # 解密数据用于同步
    decrypted_phone = decrypt_data(db_member.phone)
    decrypted_card_number = decrypt_data(db_member.card_number)
    
    # 这里可以添加实际的同步逻辑，例如同步到其他系统
    # 示例：打印同步信息
    print(f"Syncing member {db_member.name} with phone {decrypted_phone} and card {decrypted_card_number}")
    
    # 记录同步历史
    create_history(db, schemas.HistoryCreate(
        member_id=member_id,
        action="sync",
        description=f"同步会员数据: {db_member.name}"
    ))
    
    return db_member

def get_active_members(db: Session, skip: int = 0, limit: int = 100) -> List[models.Member]:
    """获取活跃会员列表"""
    members = db.query(models.Member).filter(models.Member.is_active == True).offset(skip).limit(limit).all()
    # 解密敏感信息
    for member in members:
        member.phone = decrypt_data(member.phone)
        member.card_number = decrypt_data(member.card_number)
    return members

def get_members_by_level(db: Session, level: str, skip: int = 0, limit: int = 100) -> List[models.Member]:
    """根据会员等级获取会员列表"""
    members = db.query(models.Member).filter(models.Member.level == level).offset(skip).limit(limit).all()
    # 解密敏感信息
    for member in members:
        member.phone = decrypt_data(member.phone)
        member.card_number = decrypt_data(member.card_number)
    return members

def update_member_status(db: Session, member_id: int, is_active: bool) -> Optional[models.Member]:
    """更新会员状态"""
    db_member = get_member(db, member_id)
    if not db_member:
        return None
    
    db_member.is_active = is_active
    db.commit()
    db.refresh(db_member)
    
    # 记录历史
    create_history(db, schemas.HistoryCreate(
        member_id=member_id,
        action="status_update",
        description=f"更新会员状态为: {'激活' if is_active else '停用'}"
    ))
    
    return db_member

def extend_membership(db: Session, member_id: int, months: int) -> Optional[models.Member]:
    """延长会员会籍"""
    db_member = get_member(db, member_id)
    if not db_member:
        return None
    
    db_member.remaining_months += months
    db.commit()
    db.refresh(db_member)
    
    # 记录历史
    create_history(db, schemas.HistoryCreate(
        member_id=member_id,
        action="extend",
        description=f"延长会籍 {months} 个月"
    ))
    
    return db_member


def get_course(db: Session, course_id: int) -> Optional[models.Course]:
    """获取单个课程信息"""
    return db.query(models.Course).filter(models.Course.id == course_id).first()

def get_courses(db: Session, skip: int = 0, limit: int = 100, is_active: Optional[bool] = None) -> List[models.Course]:
    """获取课程列表（支持分页）"""
    query = db.query(models.Course)
    if is_active is not None:
        query = query.filter(models.Course.is_active == is_active)
    return query.offset(skip).limit(limit).all()

def create_course(db: Session, course: schemas.CourseCreate) -> models.Course:
    """创建新课程"""
    db_course = models.Course(**course.dict())
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course

def update_course(db: Session, course_id: int, course: schemas.CourseUpdate) -> Optional[models.Course]:
    """更新课程信息"""
    db_course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not db_course:
        return None
    
    update_data = course.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_course, field, value)
    
    db.commit()
    db.refresh(db_course)
    return db_course

def delete_course(db: Session, course_id: int) -> bool:
    """删除课程（软删除，设置为非活跃）"""
    db_course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not db_course:
        return False
    
    db_course.is_active = False
    db.commit()
    return True

def get_course_bookings(db: Session, course_id: int) -> List[models.Booking]:
    """获取课程的所有预约"""
    return db.query(models.Booking).filter(
        models.Booking.course_id == course_id,
        models.Booking.status == 'booked'
    ).all()

def get_course_available_slots(db: Session, course_id: int) -> int:
    """获取课程剩余名额"""
    course = get_course(db, course_id)
    if not course:
        return 0
    
    booked_count = db.query(models.Booking).filter(
        models.Booking.course_id == course_id,
        models.Booking.status == 'booked'
    ).count()
    
    return max(0, course.capacity - booked_count)

def create_booking(db: Session, booking: schemas.BookingCreate) -> Optional[models.Booking]:
    """创建预约"""
    # 检查会员是否存在且活跃
    member = get_member(db, booking.member_id)
    if not member or not member.is_active:
        return None
    
    # 检查课程是否存在且活跃
    course = get_course(db, booking.course_id)
    if not course or not course.is_active:
        return None
    
    # 检查是否已经预约过该课程
    existing_booking = db.query(models.Booking).filter(
        models.Booking.member_id == booking.member_id,
        models.Booking.course_id == booking.course_id,
        models.Booking.status == 'booked'
    ).first()
    if existing_booking:
        return None
    
    # 检查课程是否还有余量
    if get_course_available_slots(db, booking.course_id) <= 0:
        return None
    
    db_booking = models.Booking(**booking.dict())
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    
    # 记录历史
    create_history(db, schemas.HistoryCreate(
        member_id=booking.member_id,
        action="book_course",
        description=f"预约课程: {course.name}"
    ))
    
    return db_booking

def cancel_booking(db: Session, booking_id: int) -> Optional[models.Booking]:
    """取消预约"""
    db_booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not db_booking or db_booking.status != 'booked':
        return None
    
    db_booking.status = 'cancelled'
    db.commit()
    db.refresh(db_booking)
    
    # 记录历史
    create_history(db, schemas.HistoryCreate(
        member_id=db_booking.member_id,
        action="cancel_booking",
        description=f"取消预约课程: {db_booking.course.name}"
    ))
    
    return db_booking

def get_member_bookings(db: Session, member_id: int, status: Optional[str] = None) -> List[models.Booking]:
    """获取会员的预约列表"""
    query = db.query(models.Booking).filter(models.Booking.member_id == member_id)
    if status:
        query = query.filter(models.Booking.status == status)
    return query.all()

def complete_booking(db: Session, booking_id: int) -> Optional[models.Booking]:
    """完成预约"""
    db_booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not db_booking or db_booking.status != 'booked':
        return None
    
    db_booking.status = 'completed'
    db.commit()
    db.refresh(db_booking)
    
    # 记录历史
    create_history(db, schemas.HistoryCreate(
        member_id=db_booking.member_id,
        action="complete_booking",
        description=f"完成课程: {db_booking.course.name}"
    ))
    
    return db_booking


def create_payment(db: Session, payment: schemas.PaymentCreate) -> models.Payment:
    """创建支付记录"""
    db_payment = models.Payment(**payment.dict())
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment

def get_payment(db: Session, payment_id: int) -> Optional[models.Payment]:
    """获取支付记录"""
    return db.query(models.Payment).filter(models.Payment.id == payment_id).first()

def get_member_payments(db: Session, member_id: int, skip: int = 0, limit: int = 100) -> List[models.Payment]:
    """获取会员支付记录"""
    return db.query(models.Payment).filter(models.Payment.member_id == member_id).offset(skip).limit(limit).all()

def update_payment_status(db: Session, payment_id: int, status: PaymentStatus) -> Optional[models.Payment]:
    """更新支付状态"""
    db_payment = get_payment(db, payment_id)
    if not db_payment:
        return None
    
    db_payment.status = status
    db.commit()
    db.refresh(db_payment)
    return db_payment

def create_package(db: Session, package: schemas.PackageCreate) -> models.Package:
    """创建套餐"""
    db_package = models.Package(**package.dict())
    db.add(db_package)
    db.commit()
    db.refresh(db_package)
    return db_package

def get_packages(db: Session, skip: int = 0, limit: int = 100) -> List[models.Package]:
    """获取套餐列表"""
    return db.query(models.Package).filter(models.Package.is_active == True).offset(skip).limit(limit).all()

def get_package(db: Session, package_id: int) -> Optional[models.Package]:
    """获取单个套餐"""
    return db.query(models.Package).filter(models.Package.id == package_id).first()

def update_package(db: Session, package_id: int, package: schemas.PackageUpdate) -> Optional[models.Package]:
    """更新套餐"""
    db_package = get_package(db, package_id)
    if not db_package:
        return None
    
    update_data = package.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_package, field, value)
    
    db.commit()
    db.refresh(db_package)
    return db_package

def create_notification(db: Session, notification: schemas.NotificationCreate) -> models.Notification:
    """创建通知"""
    db_notification = models.Notification(**notification.dict())
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification

def get_member_notifications(db: Session, member_id: int, skip: int = 0, limit: int = 100) -> List[models.Notification]:
    """获取会员通知列表"""
    return db.query(models.Notification).filter(models.Notification.member_id == member_id).offset(skip).limit(limit).all()

def update_notification_status(db: Session, notification_id: int, status: NotificationStatus) -> Optional[models.Notification]:
    """更新通知状态"""
    db_notification = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not db_notification:
        return None
    
    db_notification.status = status
    db.commit()
    db.refresh(db_notification)
    return db_notification

def get_expiring_members(db: Session, days: int = 30) -> List[models.Member]:
    """获取即将到期的会员"""
    from datetime import timedelta
    expiry_date = datetime.now() + timedelta(days=days)
    return db.query(models.Member).filter(
        models.Member.remaining_months <= 1,
        models.Member.is_active == True
    ).all()

def process_membership_renewal(db: Session, member_id: int, package_id: int, payment_method: str = 'stripe') -> Optional[dict]:
    """处理会员续费流程"""
    member = get_member(db, member_id)
    if not member:
        return None

    package = get_package(db, package_id)
    if not package or not package.is_active:
        return None

    # 创建支付记录
    payment = create_payment(db, schemas.PaymentCreate(
        member_id=member_id,
        amount=package.price,
        payment_method=payment_method,
        status=PaymentStatus.PENDING,
        description=f"续费套餐: {package.name}"
    ))

    # 这里应该调用支付网关处理支付
    # 示例代码，实际需要集成Stripe/Adyen
    try:
        # 模拟支付成功
        payment_status = PaymentStatus.COMPLETED
        update_payment_status(db, payment.id, payment_status)

        # 更新会员会籍
        member.remaining_months += package.duration_months
        db.commit()

        # 记录历史
        create_history(db, schemas.HistoryCreate(
            member_id=member_id,
            action="renewal",
            description=f"续费套餐: {package.name}, 时长: {package.duration_months}个月"
        ))

        # 发送续费成功通知
        create_notification(db, schemas.NotificationCreate(
            member_id=member_id,
            type=NotificationType.EMAIL,
            title="续费成功",
            content=f"您的会员已成功续费{package.duration_months}个月",
            status=NotificationStatus.PENDING
        ))

        return {
            "success": True,
            "payment_id": payment.id,
            "new_expiry": member.remaining_months
        }
    except Exception as e:
        update_payment_status(db, payment.id, PaymentStatus.FAILED)
        return {
            "success": False,
            "error": str(e),
            "payment_id": payment.id
        }

def get_renewal_history(db: Session, member_id: int, skip: int = 0, limit: int = 100) -> List[models.Payment]:
    """获取会员续费历史"""
    return db.query(models.Payment).filter(
        models.Payment.member_id == member_id,
        models.Payment.status == PaymentStatus.COMPLETED,
        models.Payment.description.like('%续费%')
    ).offset(skip).limit(limit).all()

def send_expiry_reminders(db: Session, days_threshold: int = 30) -> int:
    """发送到期提醒通知"""
    expiring_members = get_expiring_members(db, days_threshold)
    count = 0

    for member in expiring_members:
        # 检查是否已发送过提醒
        existing_notification = db.query(models.Notification).filter(
            models.Notification.member_id == member.id,
            models.Notification.type == NotificationType.EMAIL,
            models.Notification.title == "会籍到期提醒",
            models.Notification.created_at > datetime.now() - timedelta(days=7)
        ).first()

        if not existing_notification:
            create_notification(db, schemas.NotificationCreate(
                member_id=member.id,
                type=NotificationType.EMAIL,
                title="会籍到期提醒",
                content=f"您的会员会籍将在{member.remaining_months}个月后到期，请及时续费",
                status=NotificationStatus.PENDING
            ))
            count += 1

    return count

def get_member_stats(db: Session) -> dict:
    """获取会员统计信息"""
    total_members = db.query(models.Member).count()
    active_members = db.query(models.Member).filter(models.Member.is_active == True).count()
    expiring_members = len(get_expiring_members(db))
    
    # 按等级统计
    level_stats = db.query(
        models.Member.level,
        db.func.count(models.Member.id).label('count')
    ).group_by(models.Member.level).all()
    
    return {
        'total_members': total_members,
        'active_members': active_members,
        'expiring_members': expiring_members,
        'level_distribution': {stat.level: stat.count for stat in level_stats}
    }

def bulk_update_members(db: Session, member_ids: List[int], update_data: dict) -> List[models.Member]:
    """批量更新会员信息"""
    members = db.query(models.Member).filter(models.Member.id.in_(member_ids)).all()
    
    # 处理加密字段
    if 'phone' in update_data:
        update_data['phone'] = encrypt_data(update_data['phone'])
    if 'card_number' in update_data:
        update_data['card_number'] = encrypt_data(update_data['card_number'])
    
    for member in members:
        for field, value in update_data.items():
            setattr(member, field, value)
        
        # 记录历史
        create_history(db, schemas.HistoryCreate(
            member_id=member.id,
            action="bulk_update",
            description=f"批量更新会员信息: {member.name}"
        ))
    
    db.commit()
    return members

def search_members(db: Session, keyword: str, skip: int = 0, limit: int = 100) -> List[models.Member]:
    """搜索会员"""
    # 解密数据进行搜索
    all_members = db.query(models.Member).all()
    results = []
    
    for member in all_members:
        decrypted_phone = decrypt_data(member.phone)
        decrypted_card_number = decrypt_data(member.card_number)
        
        if (keyword.lower() in member.name.lower() or
            keyword in decrypted_phone or
            keyword in decrypted_card_number or
            keyword.lower() in member.level.lower()):
            results.append(member)
    
    return results[skip:skip+limit]

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
def update_member(db: Session, member_id: int, member: schemas.MemberUpdate) -> Optional[models.Member]:
    """更新会员信息"""
    db_member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not db_member:
        return None

    update_data = member.dict(exclude_unset=True)

    # 处理加密字段
    if 'phone' in update_data:
        update_data['phone'] = encrypt_data(update_data['phone'])
    if 'card_number' in update_data:
        update_data['card_number'] = encrypt_data(update_data['card_number'])

    for field, value in update_data.items():
        setattr(db_member, field, value)

    db.commit()
    db.refresh(db_member)

    # 记录历史
    create_history(db, schemas.HistoryCreate(
        member_id=member_id,
        action="update",
        description=f"更新会员信息: {member.name or db_member.name}"
    ))

    # 解密敏感信息返回
    db_member.phone = decrypt_data(db_member.phone)
    db_member.card_number = decrypt_data(db_member.card_number)
    
    return db_member

# [AUTO-APPENDED] Failed to replace, adding new code:
def update_member_status(db: Session, member_id: int, is_active: bool) -> Optional[models.Member]:
    """更新会员状态"""
    db_member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not db_member:
        return None

    db_member.is_active = is_active
    db.commit()
    db.refresh(db_member)

    # 记录历史
    create_history(db, schemas.HistoryCreate(
        member_id=member_id,
        action="status_update",
        description=f"更新会员状态: {'激活' if is_active else '停用'}"
    ))

    # 解密敏感信息返回
    db_member.phone = decrypt_data(db_member.phone)
    db_member.card_number = decrypt_data(db_member.card_number)
    
    return db_member

# [AUTO-APPENDED] Failed to replace, adding new code:
def extend_membership(db: Session, member_id: int, months: int) -> Optional[models.Member]:
    """延长会员会籍"""
    db_member = db.query(models.Member).filter(models.Member.id == member_id).first()
    if not db_member:
        return None

    db_member.remaining_months += months
    db.commit()
    db.refresh(db_member)

    # 记录历史
    create_history(db, schemas.HistoryCreate(
        member_id=member_id,
        action="extend",
        description=f"延长会籍 {months} 个月"
    ))

    # 解密敏感信息返回
    db_member.phone = decrypt_data(db_member.phone)
    db_member.card_number = decrypt_data(db_member.card_number)
    
    return db_member

# [AUTO-APPENDED] Failed to replace, adding new code:
def bulk_update_members(db: Session, member_ids: List[int], update_data: dict) -> List[models.Member]:
    """批量更新会员信息"""
    members = db.query(models.Member).filter(models.Member.id.in_(member_ids)).all()

    # 处理加密字段
    if 'phone' in update_data:
        update_data['phone'] = encrypt_data(update_data['phone'])
    if 'card_number' in update_data:
        update_data['card_number'] = encrypt_data(update_data['card_number'])

    for member in members:
        for field, value in update_data.items():
            setattr(member, field, value)

        # 记录历史
        create_history(db, schemas.HistoryCreate(
            member_id=member.id,
            action="bulk_update",
            description=f"批量更新会员信息: {member.name}"
        ))

    db.commit()
    
    # 解密敏感信息返回
    for member in members:
        member.phone = decrypt_data(member.phone)
        member.card_number = decrypt_data(member.card_number)
    
    return members

# [AUTO-APPENDED] Failed to replace, adding new code:
def search_members(db: Session, keyword: str, skip: int = 0, limit: int = 100) -> List[models.Member]:
    """搜索会员"""
    # 解密数据进行搜索
    all_members = db.query(models.Member).all()
    results = []

    for member in all_members:
        decrypted_phone = decrypt_data(member.phone)
        decrypted_card_number = decrypt_data(member.card_number)

        if (keyword.lower() in member.name.lower() or
            keyword in decrypted_phone or
            keyword in decrypted_card_number or
            keyword.lower() in member.level.lower()):
            # 解密敏感信息返回
            member.phone = decrypted_phone
            member.card_number = decrypted_card_number
            results.append(member)

    return results[skip:skip+limit]