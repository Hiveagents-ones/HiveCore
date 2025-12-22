import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from concurrent.futures import ThreadPoolExecutor
import time

from app.main import app
from app.database import Base, get_db
from app.services.booking import BookingService
from app.services.billing import BillingService
from app.models import Booking

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_performance.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)

def test_concurrent_bookings(db):
    """测试并发预约的性能和正确性"""
    # 准备测试数据
    from app.models import Course, Member

    # 创建测试课程
    course = Course(name="Performance Test", type="group", schedule="2023-12-31 10:00", duration=60)
    db.add(course)
    db.commit()
    db.refresh(course)

    # 创建100个测试会员
    members = []
    for i in range(100):
        member = Member(name=f"Member {i}", phone=f"12345678{i:02d}", email=f"member{i}@test.com", join_date="2023-01-01")
        db.add(member)
        members.append(member)
    db.commit()

    # 并发预约测试
    booking_service = BookingService(db)

    def book_course(member_id, course_id):
        try:
            return booking_service.create_booking(member_id, course_id)
        except Exception as e:
            return str(e)

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(book_course, member.id, course.id) for member in members]
        results = [future.result() for future in futures]

    end_time = time.time()

    # 验证结果
    successful_bookings = [r for r in results if isinstance(r, Booking)]
    errors = [r for r in results if isinstance(r, str)]

    print(f"Total bookings: {len(results)}")
    print(f"Successful bookings: {len(successful_bookings)}")
    print(f"Errors: {len(errors)}")
    print(f"Execution time: {end_time - start_time:.2f} seconds")

    # 检查数据库中的实际预约数量
    db_bookings = booking_service.get_course_bookings(course.id)

    assert len(db_bookings) == len(successful_bookings)
    assert len(db_bookings) > 0  # 至少有一个预约成功

    # 验证数据一致性 - 确保所有预约记录都正确关联了会员和课程
    for booking in db_bookings:
        assert booking.member_id in [m.id for m in members]
        assert booking.course_id == course.id
        assert booking.status == "confirmed"

    # 验证没有重复预约
    booking_ids = [b.id for b in db_bookings]
    assert len(booking_ids) == len(set(booking_ids)), "存在重复预约"

    # 验证预约时间戳在合理范围内
    for booking in db_bookings:
        assert booking.created_at >= start_time
        assert booking.created_at <= end_time

    # 性能要求: 100个并发预约应该在5秒内完成
    assert (end_time - start_time) < 5

    # 输出性能指标
    print(f"Bookings per second: {len(successful_bookings)/(end_time - start_time):.2f}")

    """测试并发预约的性能和正确性"""
    # 准备测试数据
    from app.models import Course, Member
    
    # 创建测试课程
    course = Course(name="Performance Test", type="group", schedule="2023-12-31 10:00", duration=60)
    db.add(course)
    db.commit()
    db.refresh(course)
    
    # 创建100个测试会员
    members = []
    for i in range(100):
        member = Member(name=f"Member {i}", phone=f"12345678{i:02d}", email=f"member{i}@test.com", join_date="2023-01-01")
        db.add(member)
        members.append(member)
    db.commit()
    
    # 并发预约测试
    booking_service = BookingService(db)
    
    def book_course(member_id, course_id):
        try:
            return booking_service.create_booking(member_id, course_id)
        except Exception as e:
            return str(e)
    
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(book_course, member.id, course.id) for member in members]
        results = [future.result() for future in futures]
    
    end_time = time.time()
    
    # 验证结果
    successful_bookings = [r for r in results if isinstance(r, Booking)]
    errors = [r for r in results if isinstance(r, str)]
    
    print(f"Total bookings: {len(results)}")
    print(f"Successful bookings: {len(successful_bookings)}")
    print(f"Errors: {len(errors)}")
    print(f"Execution time: {end_time - start_time:.2f} seconds")
    
    # 检查数据库中的实际预约数量
    db_bookings = booking_service.get_course_bookings(course.id)
    
    assert len(db_bookings) == len(successful_bookings)
    assert len(db_bookings) > 0  # 至少有一个预约成功
    
    # 性能要求: 100个并发预约应该在5秒内完成
    assert (end_time - start_time) < 5
    
    # 输出性能指标
    print(f"Bookings per second: {len(successful_bookings)/(end_time - start_time):.2f}")

if __name__ == "__main__":
    pytest.main(["-v", "test_booking.py"])

def test_concurrent_payments(db):
    """测试并发支付的性能和正确性"""
    # 准备测试数据
    from app.models import Member

    # 创建100个测试会员
    members = []
    for i in range(100):
        member = Member(name=f"Member {i}", phone=f"12345678{i:02d}", email=f"member{i}@test.com", join_date="2023-01-01")
        db.add(member)
        members.append(member)
    db.commit()

    # 并发支付测试
    billing_service = BillingService(db)

    def make_payment(member_id, amount):
        try:
            return billing_service.process_payment(member_id, amount, "credit_card")
        except Exception as e:
            return str(e)

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(make_payment, member.id, 100) for member in members]
        results = [future.result() for future in futures]

    end_time = time.time()

    # 验证结果
    successful_payments = [r for r in results if isinstance(r, dict) and 'payment_id' in r]
    errors = [r for r in results if isinstance(r, str)]

    print(f"Total payments: {len(results)}")
    print(f"Successful payments: {len(successful_payments)}")
    print(f"Errors: {len(errors)}")
    print(f"Execution time: {end_time - start_time:.2f} seconds")

    # 检查数据库中的实际支付数量
    db_payments = billing_service.get_payments()

    assert len(db_payments) == len(successful_payments)
    assert len(db_payments) > 0  # 至少有一个支付成功
    
    # 验证数据一致性 - 确保所有支付记录都正确关联了会员
    for payment in db_payments:
        assert payment.member_id in [m.id for m in members]
        assert payment.amount == 100
        assert payment.payment_method == "credit_card"
    
    # 验证没有重复支付
    payment_ids = [p.id for p in db_payments]
    assert len(payment_ids) == len(set(payment_ids)), "存在重复支付"

    # 性能要求: 100个并发支付应该在5秒内完成
    assert (end_time - start_time) < 5

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
    # 检查数据库中的实际预约数量
    db_bookings = booking_service.get_course_bookings(course.id)

    assert len(db_bookings) == len(successful_bookings)
    assert len(db_bookings) > 0  # 至少有一个预约成功
    
    # 验证数据一致性 - 确保所有预约记录都正确关联了会员和课程
    for booking in db_bookings:
        assert booking.member_id in [m.id for m in members]
        assert booking.course_id == course.id
        assert booking.status == "confirmed"
    
    # 验证没有重复预约
    booking_ids = [b.id for b in db_bookings]
    assert len(booking_ids) == len(set(booking_ids)), "存在重复预约"

# [AUTO-APPENDED] Failed to insert:
    
    # 验证预约时间戳在合理范围内
    for booking in db_bookings:
        assert booking.created_at >= start_time
        assert booking.created_at <= end_time

# ========== AUTO-APPENDED CODE (编辑失败自动追加) ==========
# [AUTO-APPENDED] Failed to replace, adding new code:
    # 检查数据库中的实际预约数量
    db_bookings = booking_service.get_course_bookings(course.id)

    assert len(db_bookings) == len(successful_bookings)
    assert len(db_bookings) > 0  # 至少有一个预约成功

    # 验证数据一致性 - 确保所有预约记录都正确关联了会员和课程
    for booking in db_bookings:
        assert booking.member_id in [m.id for m in members]
        assert booking.course_id == course.id
        assert booking.status == "confirmed"

    # 验证没有重复预约
    booking_ids = [b.id for b in db_bookings]
    assert len(booking_ids) == len(set(booking_ids)), "存在重复预约"

    # 验证预约时间戳在合理范围内
    for booking in db_bookings:
        assert booking.created_at >= start_time
        assert booking.created_at <= end_time

    # 性能要求: 100个并发预约应该在5秒内完成
    assert (end_time - start_time) < 5