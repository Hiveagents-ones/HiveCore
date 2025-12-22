import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime
import io
import csv

from backend.app.main import app
from backend.app.core.database import get_db, Base
from backend.app.models.user import User
from backend.app.models.member import Member
from backend.app.core.rbac import create_access_token

# 测试数据库配置
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建测试数据库表
Base.metadata.create_all(bind=engine)

# 测试客户端
client = TestClient(app)

# 覆盖依赖
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def test_db():
    db = TestingSessionLocal()
    try:
        # 创建测试用户
        test_user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
            is_active=True,
            permissions=["member:export"]
        )
        db.add(test_user)
        
        # 创建测试会员
        test_members = [
            Member(
                name="张三",
                phone="13800138000",
                email="zhangsan@example.com",
                level="VIP",
                points=1000,
                remaining_membership=12,
                is_active=True,
                notes="测试会员1"
            ),
            Member(
                name="李四",
                phone="13900139000",
                email="lisi@example.com",
                level="普通",
                points=500,
                remaining_membership=6,
                is_active=False,
                notes="测试会员2"
            )
        ]
        
        for member in test_members:
            db.add(member)
        
        db.commit()
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module")
def auth_headers():
    access_token = create_access_token(data={"sub": "testuser"})
    return {"Authorization": f"Bearer {access_token}"}

def test_export_members_success(test_db, auth_headers):
    """测试成功导出会员数据"""
    response = client.get(
        "/api/v1/export/members",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert "attachment" in response.headers["content-disposition"]
    
    # 验证CSV内容
    csv_content = response.content.decode('utf-8-sig')
    csv_reader = csv.reader(io.StringIO(csv_content))
    rows = list(csv_reader)
    
    # 验证表头
    expected_headers = [
        "ID",
        "姓名",
        "手机号",
        "邮箱",
        "会员等级",
        "积分",
        "剩余会籍(月)",
        "是否激活",
        "创建时间",
        "更新时间",
        "备注"
    ]
    assert rows[0] == expected_headers
    
    # 验证数据行数
    assert len(rows) == 3  # 表头 + 2条数据
    
    # 验证第一条数据
    assert rows[1][1] == "张三"
    assert rows[1][4] == "VIP"
    assert rows[1][7] == "是"
    
    # 验证第二条数据
    assert rows[2][1] == "李四"
    assert rows[2][4] == "普通"
    assert rows[2][7] == "否"

def test_export_members_with_filters(test_db, auth_headers):
    """测试带筛选条件的导出"""
    response = client.get(
        "/api/v1/export/members?level=VIP&is_active=true",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    
    csv_content = response.content.decode('utf-8-sig')
    csv_reader = csv.reader(io.StringIO(csv_content))
    rows = list(csv_reader)
    
    # 应该只有一条VIP且激活的记录
    assert len(rows) == 2  # 表头 + 1条数据
    assert rows[1][1] == "张三"
    assert rows[1][4] == "VIP"

def test_export_members_no_data(test_db, auth_headers):
    """测试没有符合条件数据的情况"""
    response = client.get(
        "/api/v1/export/members?level=钻石",
        headers=auth_headers
    )
    
    assert response.status_code == 404
    assert "没有找到符合条件的会员数据" in response.json()["detail"]

def test_export_members_unauthorized():
    """测试未授权访问"""
    response = client.get("/api/v1/export/members")
    
    assert response.status_code == 401

def test_export_members_no_permission(test_db):
    """测试无权限访问"""
    # 创建没有导出权限的用户
    user = User(
        username="nopermuser",
        email="noperm@example.com",
        hashed_password="hashed_password",
        is_active=True,
        permissions=[]
    )
    db = TestingSessionLocal()
    db.add(user)
    db.commit()
    db.close()
    
    access_token = create_access_token(data={"sub": "nopermuser"})
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = client.get(
        "/api/v1/export/members",
        headers=headers
    )
    
    assert response.status_code == 403

def test_export_members_pagination(test_db, auth_headers):
    """测试分页导出"""
    response = client.get(
        "/api/v1/export/members?skip=1&limit=1",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    
    csv_content = response.content.decode('utf-8-sig')
    csv_reader = csv.reader(io.StringIO(csv_content))
    rows = list(csv_reader)
    
    # 应该只有一条记录（跳过第一条，取一条）
    assert len(rows) == 2  # 表头 + 1条数据
    assert rows[1][1] == "李四"

def test_export_members_limit_validation(test_db, auth_headers):
    """测试导出数量限制验证"""
    # 测试超过最大限制
    response = client.get(
        "/api/v1/export/members?limit=10001",
        headers=auth_headers
    )
    
    assert response.status_code == 422
    
    # 测试最小限制
    response = client.get(
        "/api/v1/export/members?limit=0",
        headers=auth_headers
    )
    
    assert response.status_code == 422

def test_export_members_filename_format(test_db, auth_headers):
    """测试导出文件名格式"""
    response = client.get(
        "/api/v1/export/members",
        headers=auth_headers
    )
    
    content_disposition = response.headers["content-disposition"]
    assert "attachment; filename=" in content_disposition
    
    # 验证文件名格式: members_export_YYYYMMDD_HHMMSS.csv
    filename = content_disposition.split("filename=")[1].strip('"')
    assert filename.startswith("members_export_")
    assert filename.endswith(".csv")
    
    # 验证时间戳格式
    timestamp = filename.replace("members_export_", "").replace(".csv", "")
    datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
