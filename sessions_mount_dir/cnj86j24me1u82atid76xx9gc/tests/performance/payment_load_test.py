import asyncio
import time
import uuid
from typing import List
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import get_db
from backend.app.main import app
from backend.app.models.payment import PaymentOrder, PaymentMethod
from backend.app.schemas.payment import PaymentOrderCreate

# Test database setup
SQLALCHEMY_DATABASE_URL = "postgresql://test:test@localhost/test_db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

class PaymentLoadTest:
    """Payment API load testing suite"""
    
    def __init__(self):
        self.base_url = "/api/v1/payments"
        self.test_user_id = uuid.uuid4()
        self.results = {
            "create_order": [],
            "get_order": [],
            "initiate_payment": []
        }
    
    def create_test_order(self) -> dict:
        """Create a test payment order"""
        order_data = {
            "user_id": str(self.test_user_id),
            "amount": 99.99,
            "currency": "USD",
            "payment_method": PaymentMethod.STRIPE,
            "description": "Test load payment"
        }
        return order_data
    
    def measure_response_time(self, endpoint: str, method: str = "GET", data: dict = None) -> float:
        """Measure response time for an API endpoint"""
        start_time = time.time()
        
        if method == "POST":
            response = client.post(endpoint, json=data)
        else:
            response = client.get(endpoint)
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        return response_time, response.status_code
    
    def run_concurrent_requests(self, endpoint: str, method: str, data: dict = None, num_requests: int = 100) -> List[float]:
        """Run concurrent requests and measure response times"""
        response_times = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for _ in range(num_requests):
                if method == "POST":
                    future = executor.submit(self.measure_response_time, endpoint, method, data)
                else:
                    future = executor.submit(self.measure_response_time, endpoint, method)
                futures.append(future)
            
            for future in futures:
                response_time, status_code = future.result()
                response_times.append(response_time)
        
        return response_times
    
    def test_create_order_load(self, num_requests: int = 100):
        """Test load for creating payment orders"""
        print(f"\nTesting create order endpoint with {num_requests} concurrent requests...")
        
        order_data = self.create_test_order()
        response_times = self.run_concurrent_requests(
            f"{self.base_url}/orders",
            "POST",
            order_data,
            num_requests
        )
        
        self.results["create_order"] = response_times
        self.print_statistics("Create Order", response_times)
    
    def test_get_order_load(self, num_requests: int = 100):
        """Test load for retrieving payment orders"""
        print(f"\nTesting get order endpoint with {num_requests} concurrent requests...")
        
        # First create an order to test with
        order_data = self.create_test_order()
        create_response = client.post(f"{self.base_url}/orders", json=order_data)
        order_id = create_response.json()["id"]
        
        response_times = self.run_concurrent_requests(
            f"{self.base_url}/orders/{order_id}",
            "GET",
            num_requests=num_requests
        )
        
        self.results["get_order"] = response_times
        self.print_statistics("Get Order", response_times)
    
    def test_initiate_payment_load(self, num_requests: int = 100):
        """Test load for initiating payment"""
        print(f"\nTesting initiate payment endpoint with {num_requests} concurrent requests...")
        
        # Create an order first
        order_data = self.create_test_order()
        create_response = client.post(f"{self.base_url}/orders", json=order_data)
        order_id = create_response.json()["id"]
        
        response_times = self.run_concurrent_requests(
            f"{self.base_url}/orders/{order_id}/pay",
            "POST",
            num_requests=num_requests
        )
        
        self.results["initiate_payment"] = response_times
        self.print_statistics("Initiate Payment", response_times)
    
    def print_statistics(self, test_name: str, response_times: List[float]):
        """Print performance statistics"""
        if not response_times:
            print(f"No data for {test_name}")
            return
        
        avg_time = sum(response_times) / len(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        p95_time = sorted(response_times)[int(len(response_times) * 0.95)]
        
        print(f"\n{test_name} Performance Statistics:")
        print(f"  Average Response Time: {avg_time:.2f} ms")
        print(f"  Min Response Time: {min_time:.2f} ms")
        print(f"  Max Response Time: {max_time:.2f} ms")
        print(f"  95th Percentile: {p95_time:.2f} ms")
        print(f"  Total Requests: {len(response_times)}")
        print(f"  Requests/Second: {len(response_times) / (sum(response_times) / 1000):.2f}")
    
    def run_full_test_suite(self, num_requests: int = 100):
        """Run the complete load test suite"""
        print("Starting Payment API Load Test Suite")
        print("=" * 50)
        
        self.test_create_order_load(num_requests)
        self.test_get_order_load(num_requests)
        self.test_initiate_payment_load(num_requests)
        
        print("\n" + "=" * 50)
        print("Load Test Suite Completed")

if __name__ == "__main__":
    # Initialize and run load tests
    load_test = PaymentLoadTest()
    
    # Run with 100 concurrent requests
    load_test.run_full_test_suite(num_requests=100)
    
    # Optionally run with different load levels
    # load_test.run_full_test_suite(num_requests=500)
    # load_test.run_full_test_suite(num_requests=1000)
