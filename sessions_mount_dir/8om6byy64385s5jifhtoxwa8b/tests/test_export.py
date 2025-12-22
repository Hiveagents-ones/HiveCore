import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.main import app
from backend.app.core.database import get_db, Base
from backend.app.models.member import Member
from backend.app.schemas.member import MemberCreate
import json
import io
import pandas as pd

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="function")
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def sample_members(test_db):
    db = TestingSessionLocal()
    members = [
        Member(
            name="张三",
            phone="13800138000",
            card_number="M001",
            level="VIP",
            remaining_classes=10,
            valid_until="2024-12-31"
        ),
        Member(
            name="李四",
            phone="13900139000",
            card_number="M002",
            level="普通",
            remaining_classes=5,
            valid_until="2024-06-30"
        ),
        Member(
            name="王五",
            phone="13700137000",
            card_number="M003",
            level="黄金",
            remaining_classes=20,
            valid_until="2025-01-31"
        )
    ]
    for member in members:
        db.add(member)
    db.commit()
    db.close()
    return members

class TestMemberExport:
    """会员信息导出功能测试"""
    
    def test_export_members_csv(self, sample_members):
        """测试导出会员信息为CSV格式"""
        response = client.get("/api/v1/members/export?format=csv")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment; filename=members.csv" in response.headers["content-disposition"]
        
        # 验证CSV内容
        csv_content = response.content.decode("utf-8")
        assert "姓名" in csv_content
        assert "联系方式" in csv_content
        assert "会员卡号" in csv_content
        assert "会员等级" in csv_content
        assert "剩余课时" in csv_content
        assert "有效期" in csv_content
        assert "张三" in csv_content
        assert "李四" in csv_content
        assert "王五" in csv_content
    
    def test_export_members_excel(self, sample_members):
        """测试导出会员信息为Excel格式"""
        response = client.get("/api/v1/members/export?format=excel")
        assert response.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers["content-type"]
        assert "attachment; filename=members.xlsx" in response.headers["content-disposition"]
        
        # 验证Excel内容
        excel_data = io.BytesIO(response.content)
        df = pd.read_excel(excel_data)
        assert len(df) == 3
        assert "姓名" in df.columns
        assert "联系方式" in df.columns
        assert "会员卡号" in df.columns
        assert "会员等级" in df.columns
        assert "剩余课时" in df.columns
        assert "有效期" in df.columns
        assert "张三" in df["姓名"].values
        assert "李四" in df["姓名"].values
        assert "王五" in df["姓名"].values
    
    def test_export_members_json(self, sample_members):
        """测试导出会员信息为JSON格式"""
        response = client.get("/api/v1/members/export?format=json")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "attachment; filename=members.json" in response.headers["content-disposition"]
        
        # 验证JSON内容
        json_data = response.json()
        assert isinstance(json_data, list)
        assert len(json_data) == 3
        
        member_names = [m["name"] for m in json_data]
        assert "张三" in member_names
        assert "李四" in member_names
        assert "王五" in member_names
        
        # 验证字段完整性
        for member in json_data:
            assert "name" in member
            assert "phone" in member
            assert "card_number" in member
            assert "level" in member
            assert "remaining_classes" in member
            assert "valid_until" in member
    
    def test_export_filtered_members(self, sample_members):
        """测试导出筛选后的会员信息"""
        # 测试按会员等级筛选
        response = client.get("/api/v1/members/export?format=csv&level=VIP")
        assert response.status_code == 200
        csv_content = response.content.decode("utf-8")
        assert "张三" in csv_content
        assert "李四" not in csv_content
        assert "王五" not in csv_content
        
        # 测试按剩余课时筛选
        response = client.get("/api/v1/members/export?format=csv&min_classes=10")
        assert response.status_code == 200
        csv_content = response.content.decode("utf-8")
        assert "张三" in csv_content
        assert "李四" not in csv_content
        assert "王五" in csv_content
    
    def test_export_empty_database(self, test_db):
        """测试导出空数据库"""
        response = client.get("/api/v1/members/export?format=csv")
        assert response.status_code == 200
        csv_content = response.content.decode("utf-8")
        # 应该只包含标题行
        lines = csv_content.strip().split("\n")
        assert len(lines) == 1
        assert "姓名" in lines[0]
    
    def test_export_invalid_format(self, sample_members):
        """测试无效的导出格式"""
        response = client.get("/api/v1/members/export?format=pdf")
        assert response.status_code == 400
        assert "format" in response.json()["detail"].lower()
    
    def test_export_with_authentication(self, sample_members):
        """测试需要认证的导出功能"""
        # 未认证请求
        response = client.get("/api/v1/members/export?format=csv")
        assert response.status_code == 401
        
        # 使用认证token
        token = "Bearer test_token"
        headers = {"Authorization": token}
        response = client.get("/api/v1/members/export?format=csv", headers=headers)
        assert response.status_code == 200
    
    def test_export_large_dataset(self, test_db):
        """测试导出大量数据"""
        # 创建1000个测试会员
        db = TestingSessionLocal()
        for i in range(1000):
            member = Member(
                name=f"会员{i}",
                phone=f"138{i:010d}",
                card_number=f"M{i:04d}",
                level="普通",
                remaining_classes=10,
                valid_until="2024-12-31"
            )
            db.add(member)
        db.commit()
        db.close()
        
        # 测试导出
        response = client.get("/api/v1/members/export?format=csv")
        assert response.status_code == 200
        csv_content = response.content.decode("utf-8")
        lines = csv_content.strip().split("\n")
        # 1000行数据 + 1行标题
        assert len(lines) == 1001
    
    def test_export_with_special_characters(self, test_db):
        """测试包含特殊字符的会员信息导出"""
        db = TestingSessionLocal()
        member = Member(
            name="测试会员,包含\"特殊\"字符",
            phone="13800138000",
            card_number="M001",
            level="VIP",
            remaining_classes=10,
            valid_until="2024-12-31"
        )
        db.add(member)
        db.commit()
        db.close()
        
        response = client.get("/api/v1/members/export?format=csv")
        assert response.status_code == 200
        csv_content = response.content.decode("utf-8")
        assert "测试会员" in csv_content
        # 确保特殊字符被正确转义
        assert '"测试会员,包含\"特殊\"字符"' in csv_content
