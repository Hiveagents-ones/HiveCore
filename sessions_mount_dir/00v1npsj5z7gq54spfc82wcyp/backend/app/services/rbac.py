from enum import Enum
from typing import Dict, List, Optional
from fastapi import Depends, HTTPException, status
from .database import get_db
from sqlalchemy.orm import Session


class Role(str, Enum):
    """Defines available roles in the system"""
    ADMIN = "admin"
    MANAGER = "manager"
    STAFF = "staff"
    MEMBER = "member"


class Permission(str, Enum):
    """Defines available permissions in the system"""
    # Payment related permissions
    # Payment report permissions
    # Payment related permissions
    VIEW_PAYMENT_REPORTS = "view_payment_reports"
    GENERATE_PAYMENT_REPORTS = "generate_payment_reports"
    VIEW_PAYMENTS = "view_payments"
    CREATE_PAYMENTS = "create_payments"
    GENERATE_REPORTS = "generate_reports"
    
    # Financial management permissions
    VIEW_FINANCIAL_RECORDS = "view_financial_records"
    MANAGE_FINANCIAL_RECORDS = "manage_financial_records"
    PROCESS_REFUNDS = "process_refunds"
    
    # Member related permissions
    VIEW_MEMBERS = "view_members"
    MANAGE_MEMBERS = "manage_members"
    
    # Payment management permissions
    MANAGE_PAYMENTS = "manage_payments"
    
    # Course related permissions
    VIEW_COURSES = "view_courses"
    MANAGE_COURSES = "manage_courses"
    
    # Coach related permissions
    VIEW_COACHES = "view_coaches"
    MANAGE_SCHEDULES = "manage_schedules"
    # Course booking permissions
    BOOK_COURSES = "book_courses"
    CANCEL_BOOKINGS = "cancel_bookings"
    MANAGE_BOOKINGS = "manage_bookings"


# Role to permission mapping
ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    Role.ADMIN: [
        Permission.VIEW_PAYMENTS,
        Permission.CREATE_PAYMENTS,
        Permission.GENERATE_REPORTS,
        Permission.VIEW_PAYMENT_REPORTS,
        Permission.GENERATE_PAYMENT_REPORTS,
        Permission.MANAGE_PAYMENTS,
        Permission.VIEW_MEMBERS,
        Permission.MANAGE_MEMBERS,
        Permission.VIEW_COURSES,
        Permission.BOOK_COURSES,
        Permission.MANAGE_COURSES,
        Permission.VIEW_COACHES,
        Permission.MANAGE_BOOKINGS,
        Permission.CANCEL_BOOKINGS,
        Permission.MANAGE_SCHEDULES,
        Permission.VIEW_FINANCIAL_RECORDS,
        Permission.MANAGE_FINANCIAL_RECORDS,
        Permission.PROCESS_REFUNDS
    ],
    Role.MANAGER: [
        Permission.VIEW_PAYMENTS,
        Permission.CREATE_PAYMENTS,
        Permission.GENERATE_REPORTS,
        Permission.VIEW_PAYMENT_REPORTS,
        Permission.GENERATE_PAYMENT_REPORTS,
        Permission.MANAGE_PAYMENTS,
        Permission.VIEW_MEMBERS,
        Permission.MANAGE_MEMBERS,
        Permission.VIEW_COURSES,
        Permission.BOOK_COURSES,
        Permission.VIEW_COACHES,
        Permission.MANAGE_SCHEDULES,
        Permission.VIEW_FINANCIAL_RECORDS
    ],
    Role.STAFF: [
        Permission.VIEW_PAYMENTS,
        Permission.CREATE_PAYMENTS,
        Permission.VIEW_PAYMENT_REPORTS,
        Permission.VIEW_MEMBERS,
        Permission.VIEW_COURSES,
        Permission.BOOK_COURSES,
        Permission.VIEW_COACHES
    ],
    Role.MEMBER: [
        Permission.VIEW_PAYMENTS,
        Permission.VIEW_COURSES,
        Permission.BOOK_COURSES,
        Permission.VIEW_COACHES
    ]
}


def has_permission(required_permission: Permission, user_role: Role) -> bool:
    """Check if a user role has the required permission"""
    return required_permission in ROLE_PERMISSIONS.get(user_role, [])


def check_permission(
    required_permission: Permission,
    user_role: Optional[Role] = None,
    db: Session = Depends(get_db)
):
    """Dependency to check if user has required permission"""
    if user_role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    if not has_permission(required_permission, user_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )


# Payment specific permission checks
payment_permissions = {
    "view_payment_reports": check_permission(Permission.VIEW_PAYMENT_REPORTS),
    "generate_payment_reports": check_permission(Permission.GENERATE_PAYMENT_REPORTS),
    "manage_payments": check_permission(Permission.MANAGE_PAYMENTS),
    "view_payments": check_permission(Permission.VIEW_PAYMENTS),
    "create_payments": check_permission(Permission.CREATE_PAYMENTS),
    "generate_reports": check_permission(Permission.GENERATE_REPORTS)
}
# Course booking specific permission checks
course_booking_permissions = {
    "book_courses": check_permission(Permission.BOOK_COURSES),
    "cancel_bookings": check_permission(Permission.CANCEL_BOOKINGS),
    "manage_bookings": check_permission(Permission.MANAGE_BOOKINGS),
}
# Financial management specific permission checks
financial_permissions = {
    "view_financial_records": check_permission(Permission.VIEW_FINANCIAL_RECORDS),
    "manage_financial_records": check_permission(Permission.MANAGE_FINANCIAL_RECORDS),
    "process_refunds": check_permission(Permission.PROCESS_REFUNDS)
}