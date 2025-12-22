from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@postgres/fitness_db?application_name=fitness_app_backend&options=-c%20statement_timeout%3D5000&connect_timeout=10"

# Configure connection pool settings with optimized parameters
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=20,  # Optimized for course booking concurrency
    max_overflow=10,  # Optimized for course booking peaks
    pool_timeout=10,  # Optimized timeout for course operations
    pool_pre_ping=True,  # Validate connections before use
    pool_recycle=1800,  # Recycle connections every 30 minutes
    pool_reset_on_return='rollback',  # Reset connections when returned to pool
    pool_use_lifo=True,  # Use LIFO to maximize connection reuse
    isolation_level="READ COMMITTED",  # Default isolation level
    connect_args={
        "connect_timeout": 10,
        "keepalives": 1,
        "keepalives_idle": 60,
        "keepalives_interval": 15,
        "keepalives_count": 5,
        "application_name": "fitness_app_backend"  # Identify connections in PG
        "statement_timeout": 5000,  # 5 second statement timeout for payment operations
        "idle_in_transaction_session_timeout": 30000,  # 30 second timeout for payment transactions
    },
    echo_pool=True,  # Enable pool logging for debugging
    echo=False,  # Disable SQL logging
    hide_parameters=True,  # Protect sensitive data in logs
    future=True  # Enable SQLAlchemy 2.0 compatibility
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  # Better for web applications
    twophase=False,  # Disable two-phase transactions
    info=None  # Additional execution options
)

Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get DB session optimized for payment operations
    Features:
    - Extended transaction timeouts for payment processing
    - Connection validation
    - Transaction isolation level control
    - Automatic connection cleanup
    """
    """
    Dependency function to get DB session optimized for course booking operations
    Features:
    - Connection validation
    - Transaction isolation level control
    - Automatic connection cleanup
    - Optimized timeouts for course operations
    """
    """
    Dependency function to get DB session with transaction management
    Optimized for payment operations with:
    - Connection validation
    - Transaction isolation level control
    - Automatic connection cleanup
    - Extended transaction timeouts
    """
    """
    Dependency function to get DB session with transaction management
    Yields:
        Session: SQLAlchemy database session
    
    Usage:
        with get_db() as db:
            # perform database operations
            db.commit()  # explicitly commit if needed
    """
    db = SessionLocal()
    # Set transaction isolation level for course booking operations
    db.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
        db.execute("SET idle_in_transaction_session_timeout = 30000")  # Extended timeout for payments
    try:
        yield db
        db.commit()  # Auto-commit if no exceptions
    except Exception as e:
        db.rollback()  # Rollback on error
        raise
    finally:
        db.close()

# Models
from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy import Enum
from sqlalchemy import CheckConstraint, Index  # For table constraints and indexes
from sqlalchemy import LargeBinary  # For encrypted fields

class Member(Base):
    
    # Add encrypted fields for sensitive member data
    encrypted_emergency_contact = Column(LargeBinary)
    emergency_contact_key_id = Column(String)  # Reference to encryption key used
    encrypted_medical_info = Column(LargeBinary)  # For storing sensitive medical data
    medical_info_key_id = Column(String)


class MemberPoints(Base):
    __tablename__ = "member_points"
    
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey('members.id'), nullable=False)
    points = Column(Integer, default=0, nullable=False)
    source = Column(String)  # e.g. 'checkin', 'booking', 'referral'
    reference_id = Column(Integer)  # ID of related entity
    expiry_date = Column(Date)
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_member_points_member', 'member_id'),
        Index('idx_member_points_expiry', 'expiry_date'),
        CheckConstraint('points >= 0', name='positive_points')
    )
    # Add encrypted fields for sensitive member data
    encrypted_emergency_contact = Column(LargeBinary)
    emergency_contact_key_id = Column(String)  # Reference to encryption key used
    encrypted_medical_info = Column(LargeBinary)  # For storing sensitive medical data
    medical_info_key_id = Column(String)
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    join_date = Column(Date, server_default=func.now())
    is_active = Column(Boolean, default=True)
    address = Column(String)
    emergency_contact = Column(String)
    birth_date = Column(Date)
    gender = Column(String)
    profile_image = Column(String)

class MemberCard(Base):
    __table_args__ = (
        # Add index for status and expiry date queries
        Index('idx_card_status_expiry', 'status', 'expiry_date'),
        {'sqlite_autoincrement': True}
    )
    __tablename__ = "member_cards"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    card_number = Column(String, unique=True, index=True)
    status = Column(String, default="active")  # active, expired, lost
    expiry_date = Column(Date)
    level_id = Column(Integer, ForeignKey("membership_levels.id"))

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    duration = Column(Integer)  # in minutes
    capacity = Column(Integer)

class CourseSchedule(Base):
    __table_args__ = (
        # Add index for frequently queried fields
        Index('idx_course_time', 'course_id', 'start_time'),
        # Check constraint to ensure end_time > start_time
        {'sqlite_autoincrement': True},
        CheckConstraint('end_time > start_time', name='check_time_validity')
    )
    __tablename__ = "course_schedules"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    coach_id = Column(Integer, ForeignKey("coaches.id"))

class CourseBooking(Base):
    __table_args__ = (
        # Ensure one member can't book same schedule twice
        {'sqlite_autoincrement': True},
        Index('idx_member_schedule', 'member_id', 'schedule_id', unique=True)
    )
    __tablename__ = "course_bookings"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    schedule_id = Column(Integer, ForeignKey("course_schedules.id"), nullable=False)
    booking_time = Column(DateTime, server_default=func.now())
    status = Column(String, default="confirmed")  # confirmed, cancelled, attended


    


class MembershipLevel(Base):
    __tablename__ = "membership_levels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String)
    benefits = Column(JSONB)  # Stores benefits as JSON
    min_points = Column(Integer, default=0)
    discount_rate = Column(Integer, default=0)  # Percentage
    monthly_fee = Column(Integer, nullable=False)


    
    is_active = Column(Boolean, default=True)
    certification = Column(String)
    bio = Column(String)
    hourly_rate = Column(Integer)
    profile_image = Column(String)
    # Add encrypted fields for sensitive coach data
    encrypted_bank_details = Column(LargeBinary)  # For payment information
    bank_details_key_id = Column(String)
    encrypted_id_document = Column(LargeBinary)  # For storing ID scans
    id_document_key_id = Column(String)
    


    """
    Model for tracking member payments with enhanced features
    """
    __tablename__ = "payments"
    __table_args__ = (
        # Index for efficient payment queries
        Index('idx_payment_member', 'member_id', 'payment_date'),
        # Index for status filtering
        Index('idx_payment_status', 'status'),
        # Index for payment method
        Index('idx_payment_method', 'payment_method')
    )

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    amount = Column(Integer, nullable=False)  # in cents
    payment_date = Column(DateTime, server_default=func.now())
    payment_method = Column(String, nullable=False)  # credit_card, wechat, alipay, cash
    status = Column(String, default="completed")  # pending, completed, failed, refunded
    transaction_id = Column(String, unique=True)
    description = Column(String)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    processed_by = Column(String)  # staff member who processed the payment
    notes = Column(String)
    metadata_ = Column(JSONB)  # Additional payment metadata

class Refund(Base):
    """
    Model for tracking payment refunds
    """
    """
    Model for tracking payment refunds
    """
    __tablename__ = "refunds"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False)
    amount = Column(Integer, nullable=False)  # in cents
    refund_date = Column(DateTime, server_default=func.now())
    reason = Column(String)
    status = Column(String, default="pending")  # pending, completed, failed
    processed_by = Column(String)  # staff member who processed the refund
    notes = Column(String)

class Invoice(Base):
    """
    Model for generating and tracking invoices
    """
    """
    Model for generating and tracking invoices
    """
    __tablename__ = "invoices"
    __table_args__ = (
        # Index for invoice number queries
        Index('idx_invoice_number', 'invoice_number', unique=True),
        # Index for member invoices
        Index('idx_invoice_member', 'member_id', 'issue_date')
    )

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    invoice_number = Column(String, unique=True, nullable=False)
    issue_date = Column(DateTime, server_default=func.now())
    due_date = Column(DateTime)
    total_amount = Column(Integer, nullable=False)  # in cents
    tax_amount = Column(Integer, default=0)
    status = Column(String, default="unpaid")  # unpaid, paid, cancelled
    items = Column(JSONB)  # Invoice line items
    notes = Column(String)
    billing_address = Column(String)
    tax_id = Column(String)  # Tax identification number
    pdf_path = Column(String)  # Path to generated PDF invoice
    """
    Model for tracking all database changes
    """
    
    operation_type = Column(String)  # system, manual
    ip_address = Column(String)  # Track source IP
    user_agent = Column(String)  # Track client info


    """
    Model for storing internationalization resources
    """
    __tablename__ = "i18n_resources"

    id = Column(Integer, primary_key=True, index=True)
    resource_key = Column(String, nullable=False, index=True)
    resource_value = Column(String, nullable=False)
    language_code = Column(String(5), nullable=False, index=True)  # e.g. 'en', 'zh-CN'
    resource_type = Column(String(20))  # e.g. 'label', 'message', 'error'
    context = Column(String)  # Additional context for the translation
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    __table_args__ = (
        # Ensure each translation is unique per language
        Index('idx_i18n_resource_unique', 'resource_key', 'language_code', unique=True),
        # Index for efficient lookups by resource type
        Index('idx_i18n_resource_type', 'resource_type')
    )
    """
    Model for storing dynamic fields that can be attached to various entities
    Supports encrypted field values when sensitive data is stored
    """
    __tablename__ = "dynamic_fields"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, nullable=False)  # e.g. 'member', 'course', 'coach'
    entity_id = Column(Integer, nullable=False)  # ID of the entity this field belongs to
    field_name = Column(String, nullable=False)
    field_type = Column(String, nullable=False)  # 'string', 'number', 'boolean', 'date', 'json'
    field_value = Column(String)
    encrypted_value = Column(LargeBinary)  # For storing encrypted field values
    encryption_key_id = Column(String)  # Reference to encryption key used
    field_json = Column(JSONB)  # For complex JSON data
    is_required = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    created_by = Column(String)  # User who created the field
    updated_by = Column(String)  # User who last updated the field

    __table_args__ = (
        # Index for efficient lookups by entity
        Index('idx_dynamic_field_entity', 'entity_type', 'entity_id'),
        # Ensure field names are unique per entity
        Index('idx_dynamic_field_unique', 'entity_type', 'entity_id', 'field_name', unique=True),
        # Index for frequently filtered fields
        Index('idx_dynamic_field_required', 'entity_type', 'is_required'),
        # Index for sorting
        Index('idx_dynamic_field_order', 'entity_type', 'display_order')
    )


class EncryptionKey(Base):
    """
    Model for managing encryption keys used to protect sensitive data
    """
    __tablename__ = "encryption_keys"

    id = Column(Integer, primary_key=True, index=True)
    key_id = Column(String, unique=True, nullable=False)  # Unique identifier for the key
    key_data = Column(LargeBinary, nullable=False)  # The actual encryption key
    algorithm = Column(String, nullable=False)  # e.g. 'AES-256'
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime)  # Optional key expiration
    is_active = Column(Boolean, default=True)  # Whether key is currently active
    description = Column(String)  # Optional description
    created_by = Column(String)  # Who created this key

    __table_args__ = (
        # Index for active keys
        Index('idx_encryption_key_active', 'is_active'),
        # Index for key expiration checks
        Index('idx_encryption_key_expiry', 'expires_at')
    )


class DynamicField(Base):
    """
    Model for storing dynamic field definitions that can be attached to various entities
    """
    __tablename__ = "dynamic_field_definitions"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, nullable=False)  # e.g. 'member', 'coach', 'course'
    field_name = Column(String, nullable=False)
    field_type = Column(String, nullable=False)  # e.g. 'string', 'number', 'date'
    display_name = Column(String)
    is_required = Column(Boolean, default=False)
    options = Column(JSONB)  # For fields with predefined options
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    __table_args__ = (
        Index('idx_dynamic_field_entity', 'entity_type', 'field_name'),
        CheckConstraint("field_type IN ('string', 'number', 'date', 'boolean', 'select')", name='valid_field_type')
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False)  # e.g. 'create', 'update', 'delete'
    entity_type = Column(String, nullable=False)  # e.g. 'member', 'booking'
    entity_id = Column(Integer, nullable=False)
    user_id = Column(Integer)  # Who performed the action
    user_type = Column(String)  # e.g. 'member', 'coach', 'admin'
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    ip_address = Column(String)
    user_agent = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (
        Index('idx_audit_log_entity', 'entity_type', 'entity_id'),
        Index('idx_audit_log_user', 'user_id', 'user_type'),
        Index('idx_audit_log_created', 'created_at')
    )
    __tablename__ = "dynamic_fields"
    
    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, nullable=False)  # e.g. 'member', 'coach', 'course'
    field_name = Column(String, nullable=False)
    field_type = Column(String, nullable=False)  # e.g. 'string', 'number', 'date'
    display_name = Column(String)
    is_required = Column(Boolean, default=False)
    options = Column(JSONB)  # For fields with predefined options
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    __table_args__ = (
        Index('idx_dynamic_field_entity', 'entity_type', 'field_name'),
        CheckConstraint("field_type IN ('string', 'number', 'date', 'boolean', 'select')", name='valid_field_type')
    )
    """
    Model for managing encryption keys used to protect sensitive data
    """
    __tablename__ = "encryption_keys"

    id = Column(Integer, primary_key=True, index=True)
    key_id = Column(String, unique=True, nullable=False)  # Unique identifier for the key
    key_data = Column(LargeBinary, nullable=False)  # The actual encryption key
    algorithm = Column(String, nullable=False)  # e.g. 'AES-256'
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime)  # Optional key expiration
    is_active = Column(Boolean, default=True)  # Whether key is currently active
    description = Column(String)  # Optional description
    created_by = Column(String)  # Who created this key

    __table_args__ = (
        # Index for active keys
        Index('idx_encryption_key_active', 'is_active'),
        # Index for key expiration checks
        Index('idx_encryption_key_expiry', 'expires_at')
    )
    """
    Model for storing internationalization resources
    """
    __tablename__ = "i18n_resources"

    id = Column(Integer, primary_key=True, index=True)
    resource_key = Column(String, nullable=False, index=True)
    resource_value = Column(String, nullable=False)
    language_code = Column(String(5), nullable=False, index=True)  # e.g. 'en', 'zh-CN'
    resource_type = Column(String(20))  # e.g. 'label', 'message', 'error'
    context = Column(String)  # Additional context for the translation
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    __table_args__ = (
        # Ensure each translation is unique per language
        Index('idx_i18n_resource_unique', 'resource_key', 'language_code', unique=True),
        # Index for efficient lookups by resource type
        Index('idx_i18n_resource_type', 'resource_type')
    )
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False)  # create, update, delete
    table_name = Column(String, nullable=False)
    record_id = Column(Integer, nullable=False)
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    changed_by = Column(String)  # Could be user_id or system
    changed_at = Column(DateTime, server_default=func.now())
    
    __tablename__ = "coaches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    specialization = Column(String)
    hire_date = Column(Date, server_default=func.now())


    

# Create all tables
Base.metadata.create_all(bind=engine)

def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get DB session with transaction management
    Optimized for payment operations with:
    - Connection validation
    - Transaction isolation level control
    - Automatic connection cleanup
    
    Yields:
        Session: SQLAlchemy database session

    Usage:
        with get_db() as db:
            # perform database operations
            db.commit()  # explicitly commit if needed
    """
    db = SessionLocal()
    try:
        # Test connection and set isolation level
        db.execute("SELECT 1")
        db.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
        yield db
        db.commit()  # Auto-commit if no exceptions
    except Exception as e:
        db.rollback()  # Rollback on error
        raise
    finally:
        db.expire_all()
        db.close()

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
class Coach(Base):
class CoachSchedule(Base):
    __tablename__ = "coach_schedules"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey('coaches.id'), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(String)  # e.g. "weekly", "biweekly"
    recurrence_end = Column(DateTime)  # End date for recurring schedules
    schedule_type = Column(String)  # regular, overtime, training
    max_bookings = Column(Integer)  # Maximum bookings allowed for this schedule
    location = Column(String)  # Location where the coach will be available
    status = Column(String, default="available")  # available, booked, unavailable, vacation
    notes = Column(String)  # Optional notes about the schedule
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    created_by = Column(String)  # User who created the schedule
    updated_by = Column(String)  # User who last updated the schedule

    __table_args__ = (
        Index('idx_coach_schedule_coach', 'coach_id'),
        Index('idx_coach_schedule_time', 'start_time', 'end_time'),
        Index('idx_coach_schedule_status', 'status'),
        Index('idx_coach_schedule_recurring', 'is_recurring', 'recurrence_end'),
        CheckConstraint('end_time > start_time', name='valid_time_range')
    )
    __tablename__ = "coaches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    specialization = Column(String)
    hire_date = Column(Date, server_default=func.now())
    is_active = Column(Boolean, default=True)
    certification = Column(String)
    bio = Column(String)
    hourly_rate = Column(Integer)
    profile_image = Column(String)
    # Add encrypted fields for sensitive coach data
    encrypted_bank_details = Column(LargeBinary)  # For payment information
    bank_details_key_id = Column(String)
    encrypted_id_document = Column(LargeBinary)  # For storing ID scans
    id_document_key_id = Column(String)

# [AUTO-APPENDED] Failed to replace, adding new code:
def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get DB session with transaction management
    Yields:
        Session: SQLAlchemy database session

    Usage:
        with get_db() as db:
            # perform database operations
            db.commit()  # explicitly commit if needed
    """
    db = SessionLocal()
    try:
        # Test connection and set isolation level
        db.execute("SELECT 1")
        db.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
        yield db
        db.commit()  # Auto-commit if no exceptions
    except Exception as e:
        db.rollback()  # Rollback on error
        raise
    finally:
        db.expire_all()
        db.close()

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False)  # e.g. 'create', 'update', 'delete'
    entity_type = Column(String, nullable=False)  # e.g. 'member', 'booking'
    entity_id = Column(Integer, nullable=False)
    user_id = Column(Integer)  # Who performed the action
    user_type = Column(String)  # e.g. 'member', 'coach', 'admin'
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    ip_address = Column(String)
    user_agent = Column(String)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index('idx_audit_log_entity', 'entity_type', 'entity_id'),
        Index('idx_audit_log_user', 'user_id', 'user_type'),
        Index('idx_audit_log_created', 'created_at')
    )