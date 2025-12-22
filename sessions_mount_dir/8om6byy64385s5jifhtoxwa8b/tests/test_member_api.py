import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db, Base
from app.main import app
from app.models.member import Member
from app.schemas.member import MemberCreate, MemberUpdate

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
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


class TestMemberAPI:
    """会员API测试类"""

    def test_create_member(self):
        """测试创建会员"""
        member_data = {
            "name": "张三",
            "phone": "13800138000",
            "email": "zhangsan@example.com",
            "member_card_number": "M001",
            "member_level": "basic",
            "remaining_classes": 10,
            "expiry_date": "2024-12-31"
        }
        response = client.post("/api/v1/members/", json=member_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == member_data["name"]
        assert data["phone"] == member_data["phone"]
        assert data["email"] == member_data["email"]
        assert data["member_card_number"] == member_data["member_card_number"]
        assert data["member_level"] == member_data["member_level"]
        assert data["remaining_classes"] == member_data["remaining_classes"]
        assert "id" in data

    def test_get_member(self):
        """测试获取单个会员信息"""
        # 先创建一个会员
        member_data = {
            "name": "李四",
            "phone": "13900139000",
            "email": "lisi@example.com",
            "member_card_number": "M002",
            "member_level": "silver",
            "remaining_classes": 20,
            "expiry_date": "2024-12-31"
        }
        create_response = client.post("/api/v1/members/", json=member_data)
        member_id = create_response.json()["id"]

        # 获取会员信息
        response = client.get(f"/api/v1/members/{member_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == member_id
        assert data["name"] == member_data["name"]

    def test_get_nonexistent_member(self):
        """测试获取不存在的会员"""
        response = client.get("/api/v1/members/99999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Member not found"

    def test_update_member(self):
        """测试更新会员信息"""
        # 先创建一个会员
        member_data = {
            "name": "王五",
            "phone": "13700137000",
            "email": "wangwu@example.com",
            "member_card_number": "M003",
            "member_level": "gold",
            "remaining_classes": 30,
            "expiry_date": "2024-12-31"
        }
        create_response = client.post("/api/v1/members/", json=member_data)
        member_id = create_response.json()["id"]

        # 更新会员信息
        update_data = {
            "name": "王五修改",
            "member_level": "platinum",
            "remaining_classes": 40
        }
        response = client.put(f"/api/v1/members/{member_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["member_level"] == update_data["member_level"]
        assert data["remaining_classes"] == update_data["remaining_classes"]
        # 未更新的字段应保持原值
        assert data["phone"] == member_data["phone"]

    def test_delete_member(self):
        """测试注销会员"""
        # 先创建一个会员
        member_data = {
            "name": "赵六",
            "phone": "13600136000",
            "email": "zhaoliu@example.com",
            "member_card_number": "M004",
            "member_level": "basic",
            "remaining_classes": 5,
            "expiry_date": "2024-12-31"
        }
        create_response = client.post("/api/v1/members/", json=member_data)
        member_id = create_response.json()["id"]

        # 删除会员
        response = client.delete(f"/api/v1/members/{member_id}")
        assert response.status_code == 204

        # 验证会员已被删除
        get_response = client.get(f"/api/v1/members/{member_id}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_member(self):
        """测试删除不存在的会员"""
        response = client.delete("/api/v1/members/99999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Member not found"

    def test_list_members(self):
        """测试查询会员列表"""
        # 创建多个会员
        members = [
            {
                "name": "会员A",
                "phone": "13500135001",
                "email": "membera@example.com",
                "member_card_number": "M005",
                "member_level": "basic",
                "remaining_classes": 10,
                "expiry_date": "2024-12-31"
            },
            {
                "name": "会员B",
                "phone": "13500135002",
                "email": "memberb@example.com",
                "member_card_number": "M006",
                "member_level": "silver",
                "remaining_classes": 20,
                "expiry_date": "2024-12-31"
            },
            {
                "name": "会员C",
                "phone": "13500135003",
                "email": "memberc@example.com",
                "member_card_number": "M007",
                "member_level": "gold",
                "remaining_classes": 30,
                "expiry_date": "2024-12-31"
            }
        ]

        for member in members:
            client.post("/api/v1/members/", json=member)

        # 获取所有会员
        response = client.get("/api/v1/members/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert len(data["items"]) >= 3

    def test_list_members_with_filters(self):
        """测试带过滤条件的会员查询"""
        # 创建测试会员
        member_data = {
            "name": "测试会员",
            "phone": "13500135999",
            "email": "test@example.com",
            "member_card_number": "M008",
            "member_level": "platinum",
            "remaining_classes": 50,
            "expiry_date": "2024-12-31"
        }
        client.post("/api/v1/members/", json=member_data)

        # 按姓名过滤
        response = client.get("/api/v1/members/?name=测试会员")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0
        assert all(item["name"] == "测试会员" for item in data["items"])

        # 按会员等级过滤
        response = client.get("/api/v1/members/?member_level=platinum")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0
        assert all(item["member_level"] == "platinum" for item in data["items"])

        # 按手机号过滤
        response = client.get("/api/v1/members/?phone=13500135999")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0
        assert all(item["phone"] == "13500135999" for item in data["items"])

    def test_list_members_pagination(self):
        """测试会员列表分页"""
        # 创建多个会员
        for i in range(15):
            member_data = {
                "name": f"分页测试{i}",
                "phone": f"13500135{i:02d}",
                "email": f"page{i}@example.com",
                "member_card_number": f"M{i:03d}",
                "member_level": "basic",
                "remaining_classes": 10,
                "expiry_date": "2024-12-31"
            }
            client.post("/api/v1/members/", json=member_data)

        # 测试第一页
        response = client.get("/api/v1/members/?page=1&size=5")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 5
        assert len(data["items"]) == 5

        # 测试第二页
        response = client.get("/api/v1/members/?page=2&size=5")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["size"] == 5
        assert len(data["items"]) == 5

    def test_member_validation(self):
        """测试会员数据验证"""
        # 测试无效的会员等级
        invalid_member = {
            "name": "测试",
            "phone": "13800138000",
            "email": "test@example.com",
            "member_card_number": "M999",
            "member_level": "invalid_level",
            "remaining_classes": 10,
            "expiry_date": "2024-12-31"
        }
        response = client.post("/api/v1/members/", json=invalid_member)
        assert response.status_code == 422

        # 测试无效的手机号
        invalid_member = {
            "name": "测试",
            "phone": "123",
            "email": "test@example.com",
            "member_card_number": "M999",
            "member_level": "basic",
            "remaining_classes": 10,
            "expiry_date": "2024-12-31"
        }
        response = client.post("/api/v1/members/", json=invalid_member)
        assert response.status_code == 422

        # 测试无效的邮箱
        invalid_member = {
            "name": "测试",
            "phone": "13800138000",
            "email": "invalid_email",
            "member_card_number": "M999",
            "member_level": "basic",
            "remaining_classes": 10,
            "expiry_date": "2024-12-31"
        }
        response = client.post("/api/v1/members/", json=invalid_member)
        assert response.status_code == 422
