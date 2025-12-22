import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ..app.main import app
from ..app.database import get_db, Base
from ..app import crud, schemas

# Create an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the database tables
Base.metadata.create_all(bind=engine)

# Override the dependency to use the test database
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="module")
def test_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module")
def test_member(test_db):
    member_data = schemas.MemberCreate(
        name="Test Member",
        email="testmember@example.com",
        phone="1234567890",
        join_date="2023-01-01"
    )
    return crud.create_member(db=test_db, member=member_data)

def test_create_payment(test_member):
    payment_data = {
        "member_id": test_member.id,
        "amount": 100.00,
        "payment_date": "2023-06-01",
        "payment_method": "online",
        "status": "completed"
    }
    response = client.post("/payments/", json=payment_data)
    assert response.status_code == 201
    data = response.json()
    assert data["member_id"] == test_member.id
    assert data["amount"] == 100.00
    assert data["payment_method"] == "online"
    assert data["status"] == "completed"

def test_read_payment(test_member):
    # First create a payment
    payment_data = schemas.PaymentRecordCreate(
        member_id=test_member.id,
        amount=50.00,
        payment_date="2023-07-01",
        payment_method="offline",
        status="pending"
    )
    db = TestingSessionLocal()
    db_payment = crud.create_payment_record(db=db, payment=payment_data)
    db.close()

    # Then read it
    response = client.get(f"/payments/{db_payment.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == db_payment.id
    assert data["amount"] == 50.00

def test_read_payments_by_member(test_member):
    # Create multiple payments for the member
    db = TestingSessionLocal()
    crud.create_payment_record(db=db, payment=schemas.PaymentRecordCreate(
        member_id=test_member.id,
        amount=75.00,
        payment_date="2023-08-01",
        payment_method="online",
        status="completed"
    ))
    crud.create_payment_record(db=db, payment=schemas.PaymentRecordCreate(
        member_id=test_member.id,
        amount=25.00,
        payment_date="2023-09-01",
        payment_method="offline",
        status="completed"
    ))
    db.close()

    response = client.get(f"/payments/member/{test_member.id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert all(payment["member_id"] == test_member.id for payment in data)

def test_read_all_payments():
    response = client.get("/payments/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_update_payment(test_member):
    # Create a payment
    payment_data = schemas.PaymentRecordCreate(
        member_id=test_member.id,
        amount=100.00,
        payment_date="2023-10-01",
        payment_method="online",
        status="pending"
    )
    db = TestingSessionLocal()
    db_payment = crud.create_payment_record(db=db, payment=payment_data)
    db.close()

    # Update the payment
    update_data = {
        "amount": 120.00,
        "status": "completed"
    }
    response = client.put(f"/payments/{db_payment.id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == 120.00
    assert data["status"] == "completed"

def test_delete_payment(test_member):
    # Create a payment
    payment_data = schemas.PaymentRecordCreate(
        member_id=test_member.id,
        amount=200.00,
        payment_date="2023-11-01",
        payment_method="offline",
        status="completed"
    )
    db = TestingSessionLocal()
    db_payment = crud.create_payment_record(db=db, payment=payment_data)
    db.close()

    # Delete the payment
    response = client.delete(f"/payments/{db_payment.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == db_payment.id

    # Verify it's deleted
    response = client.get(f"/payments/{db_payment.id}")
    assert response.status_code == 404

def test_create_payment_member_not_found():
    payment_data = {
        "member_id": 9999,
        "amount": 100.00,
        "payment_date": "2023-12-01",
        "payment_method": "online",
        "status": "completed"
    }
    response = client.post("/payments/", json=payment_data)
    assert response.status_code == 404
    assert response.json()["detail"] == "Member not found"

def test_read_payment_not_found():
    response = client.get("/payments/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Payment record not found"

def test_read_payments_by_member_not_found():
    response = client.get("/payments/member/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Member not found"

def test_update_payment_not_found():
    update_data = {
        "amount": 150.00,
        "status": "completed"
    }
    response = client.put("/payments/9999", json=update_data)
    assert response.status_code == 404
    assert response.json()["detail"] == "Payment record not found"

def test_delete_payment_not_found():
    response = client.delete("/payments/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Payment record not found"
