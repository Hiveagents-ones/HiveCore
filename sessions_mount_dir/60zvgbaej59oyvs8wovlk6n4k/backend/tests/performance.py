from locust import HttpUser, task, between, events
import random
import json
import time
from collections import defaultdict

class MemberAPITestUser(HttpUser):
    wait_time = between(1, 3)  # Standard wait time for realistic load

    def on_start(self):
        """Initialize user session"""
        # Login to get token
        response = self.client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "testpass"
        })
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}

    @task(3)
    def get_member_list(self):
        """Test member list endpoint"""
        self.client.get("/api/v1/members", headers=self.headers)

    @task(2)
    def get_member_detail(self):
        """Test member detail endpoint"""
        member_id = random.randint(1, 1000)
        self.client.get(f"/api/v1/members/{member_id}", headers=self.headers)

    @task(1)
    def get_payment_history(self):
        """Test payment history endpoint"""
        member_id = random.randint(1, 1000)
        self.client.get(f"/api/v1/payments/member/{member_id}", headers=self.headers)


class ReportAPITestUser(HttpUser):
    wait_time = between(1, 3)  # Standard wait time for realistic load

    def on_start(self):
        """Initialize user session"""
        # Login to get token
        response = self.client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "testpass"
        })
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}

    @task(3)
    def get_member_list(self):
        """Test member list endpoint"""
        self.client.get("/api/v1/members", headers=self.headers)

    @task(2)
    def get_member_detail(self):
        """Test member detail endpoint"""
        member_id = random.randint(1, 1000)
        self.client.get(f"/api/v1/members/{member_id}", headers=self.headers)

    @task(1)
    def create_member(self):
        """Test member creation endpoint"""
        member_data = {
            "name": f"Test User {random.randint(1, 10000)}",
            "phone": f"1{random.randint(1000000000, 9999999999)}",
            "card_number": f"CARD{random.randint(100000, 999999)}",
            "level": random.choice(["bronze", "silver", "gold", "platinum"]),
            "membership_months": random.randint(1, 36)
        }
        self.client.post("/api/v1/members", json=member_data, headers=self.headers)

    @task(1)
    def update_member(self):
        """Test member update endpoint"""
        member_id = random.randint(1, 1000)
        update_data = {
            "name": f"Updated User {random.randint(1, 10000)}",
            "level": random.choice(["bronze", "silver", "gold", "platinum"])
        }
        self.client.put(f"/api/v1/members/{member_id}", json=update_data, headers=self.headers)

    @task(1)
    def delete_member(self):
        """Test member deletion endpoint"""
        member_id = random.randint(1, 1000)
        self.client.delete(f"/api/v1/members/{member_id}", headers=self.headers)

    @task(3)
    def generate_report(self):
        """Test report generation endpoint"""
        report_type = random.choice(["monthly", "quarterly", "annual"])
        self.client.get(f"/api/v1/reports/{report_type}", headers=self.headers)

    @task(2)
    def get_report_history(self):
        """Test report history endpoint"""
        self.client.get("/api/v1/reports/history", headers=self.headers)

    @task(1)
    def download_report(self):
        """Test report download endpoint"""
        report_id = random.randint(1, 1000)
        self.client.get(f"/api/v1/reports/{report_id}/download", headers=self.headers), headers=self.headers)


# Performance metrics tracking
stats = {
    "requests": defaultdict(list),
    "response_times": defaultdict(list),
    "errors": defaultdict(int)
}

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    stats["requests"][name].append(request_type)
    stats["response_times"][name].append(response_time)
    if exception:
        stats["errors"][name] += 1
    
    # Log slow requests
    if response_time > 500:
        print(f"Slow request detected: {name} took {response_time}ms")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("\n=== Performance Test Results ===")
    print(f"{'Endpoint':<30} {'Requests':<10} {'Avg RT(ms)':<12} {'95th %ile':<12} {'Errors':<10}")
    print("-" * 80)

    for endpoint in stats["response_times"]:
        total_requests = len(stats["response_times"][endpoint])
        avg_response_time = sum(stats["response_times"][endpoint]) / total_requests
        sorted_times = sorted(stats["response_times"][endpoint])
        p95_index = int(0.95 * total_requests)
        p95_response_time = sorted_times[p95_index] if p95_index < total_requests else sorted_times[-1]
        errors = stats["errors"][endpoint]

        print(f"{endpoint:<30} {total_requests:<10} {avg_response_time:<12.2f} {p95_response_time:<12.2f} {errors:<10}")

        # R1.5 Standard validation
        if avg_response_time > 200:
            print(f"  ⚠️  WARNING: Average response time exceeds 200ms for {endpoint}")
        if p95_response_time > 500:
            print(f"  ⚠️  WARNING: 95th percentile exceeds 500ms for {endpoint}")
        if errors > 0:
            print(f"  ❌ ERROR: {errors} errors occurred for {endpoint}")

    print("\n=== R1.5 Standard Validation ===")
    print("✅ All endpoints meet R1.5 performance standards" if all(
        sum(stats["response_times"][endpoint]) / len(stats["response_times"][endpoint]) <= 200 and
        sorted(stats["response_times"][endpoint])[int(0.95 * len(stats["response_times"][endpoint]))] <= 500 and
        stats["errors"][endpoint] == 0
        for endpoint in stats["response_times"]
    ) else "❌ Some endpoints do not meet R1.5 standards")


if __name__ == "__main__":
    import os
    # Run tests for all APIs
    print("Starting performance tests for Member API (1000 concurrent users)...")
    os.system("locust -f performance.py MemberAPITestUser --host=http://localhost:8000 --users=1000 --spawn-rate=100 --run-time=120s --headless")
    print("\nStarting performance tests for Payment API (1000 concurrent users)...")
    os.system("locust -f performance.py PaymentAPITestUser --host=http://localhost:8000 --users=1000 --spawn-rate=100 --run-time=120s --headless")
    print("\nStarting performance tests for Report API (1000 concurrent users)...")
    os.system("locust -f performance.py ReportAPITestUser --host=http://localhost:8000 --users=1000 --spawn-rate=100 --run-time=120s --headless")
    def create_member(self):
        """Test member creation endpoint"""
        member_data = {
            "name": f"Test User {random.randint(1, 10000)}",
            "phone": f"1{random.randint(1000000000, 9999999999)}",
            "card_number": f"CARD{random.randint(100000, 999999)}",
            "level": random.choice(["bronze", "silver", "gold", "platinum"]),
            "membership_months": random.randint(1, 36)
        }
        self.client.post("/api/v1/members", json=member_data, headers=self.headers)

    @task(1)
    def update_member(self):
        """Test member update endpoint"""
        member_id = random.randint(1, 1000)
        update_data = {
            "name": f"Updated User {random.randint(1, 10000)}",
            "level": random.choice(["bronze", "silver", "gold", "platinum"])
        }
        self.client.put(f"/api/v1/members/{member_id}", json=update_data, headers=self.headers)

    @task(1)
    def delete_member(self):
        """Test member deletion endpoint"""
        member_id = random.randint(1, 1000)
        self.client.delete(f"/api/v1/members/{member_id}", headers=self.headers)


class PaymentAPITestUser(HttpUser):
    wait_time = between(0.1, 0.5)  # Reduced wait time for higher concurrency

    def on_start(self):
        """Initialize user session"""
        # Login to get token
        response = self.client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "testpass"
        })
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}

    @task(3)
    def initiate_payment(self):
        """Test payment initiation endpoint"""
        payment_data = {
            "member_id": random.randint(1, 1000),
            "amount": round(random.uniform(10.0, 500.0), 2),
            "months": random.randint(1, 12)
        }
        self.client.post("/api/v1/payments", json=payment_data, headers=self.headers)

    @task(2)
    def confirm_payment(self):
        """Test payment confirmation endpoint"""
        # Simulate payment confirmation with a test payment intent ID
        confirm_data = {
            "payment_intent_id": f"pi_test_{random.randint(1000000000000000, 9999999999999999)}",
            "status": "succeeded"
        }
        self.client.post("/api/v1/payments/confirm", json=confirm_data, headers=self.headers)

    @task(1)
    def get_payment_history(self):
        """Test payment history endpoint"""
        member_id = random.randint(1, 1000)
        self.client.get(f"/api/v1/payments?member_id={member_id}", headers=self.headers)
    wait_time = between(1, 3)
    
    def on_start(self):
        """Initialize user session"""
        # Login to get token
        response = self.client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "testpass"
        })
        if response.status_code == 200:
            self.token = response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}
    
    @task(3)
    def get_member_list(self):
        """Test member list endpoint"""
        self.client.get("/api/v1/members", headers=self.headers)
    
    @task(2)
    def get_member_detail(self):
        """Test member detail endpoint"""
        member_id = random.randint(1, 1000)
        self.client.get(f"/api/v1/members/{member_id}", headers=self.headers)
    
    @task(1)
    def create_member(self):
        """Test member creation endpoint"""
        member_data = {
            "name": f"Test User {random.randint(1, 10000)}",
            "phone": f"1{random.randint(1000000000, 9999999999)}",
            "card_number": f"CARD{random.randint(100000, 999999)}",
            "level": random.choice(["bronze", "silver", "gold", "platinum"]),
            "membership_months": random.randint(1, 36)
        }
        self.client.post("/api/v1/members", json=member_data, headers=self.headers)
    
    @task(1)
    def update_member(self):
        """Test member update endpoint"""
        member_id = random.randint(1, 1000)
        update_data = {
            "name": f"Updated User {random.randint(1, 10000)}",
            "level": random.choice(["bronze", "silver", "gold", "platinum"])
        }
        self.client.put(f"/api/v1/members/{member_id}", json=update_data, headers=self.headers)
    
    @task(1)
    def delete_member(self):
        """Test member deletion endpoint"""
        member_id = random.randint(1, 1000)
        self.client.delete(f"/api/v1/members/{member_id}", headers=self.headers)

# Performance metrics tracking
stats = {
    "requests": defaultdict(list),
    "response_times": defaultdict(list),
    "errors": defaultdict(int)
}

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    stats["requests"][name].append(request_type)
    stats["response_times"][name].append(response_time)
    if exception:
        stats["errors"][name] += 1

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("\n=== Performance Test Results ===")
    print(f"{'Endpoint':<30} {'Requests':<10} {'Avg RT(ms)':<12} {'95th %ile':<12} {'Errors':<10}")
    print("-" * 80)
    
    for endpoint in stats["response_times"]:
        total_requests = len(stats["response_times"][endpoint])
        avg_response_time = sum(stats["response_times"][endpoint]) / total_requests
        sorted_times = sorted(stats["response_times"][endpoint])
        p95_index = int(0.95 * total_requests)
        p95_response_time = sorted_times[p95_index] if p95_index < total_requests else sorted_times[-1]
        errors = stats["errors"][endpoint]
        
        print(f"{endpoint:<30} {total_requests:<10} {avg_response_time:<12.2f} {p95_response_time:<12.2f} {errors:<10}")
        
        # R1.5 Standard validation
        if avg_response_time > 200:
            print(f"  ⚠️  WARNING: Average response time exceeds 200ms for {endpoint}")
        if p95_response_time > 500:
            print(f"  ⚠️  WARNING: 95th percentile exceeds 500ms for {endpoint}")
        if errors > 0:
            print(f"  ❌ ERROR: {errors} errors occurred for {endpoint}")
    
    print("\n=== R1.5 Standard Validation ===")
    print("✅ All endpoints meet R1.5 performance standards" if all(
        sum(stats["response_times"][endpoint]) / len(stats["response_times"][endpoint]) <= 200 and
        sorted(stats["response_times"][endpoint])[int(0.95 * len(stats["response_times"][endpoint]))] <= 500 and
        stats["errors"][endpoint] == 0
        for endpoint in stats["response_times"]
    ) else "❌ Some endpoints do not meet R1.5 standards")


if __name__ == "__main__":
    import os
    import sys
    
    # Validate test parameters
    if len(sys.argv) > 1:
        try:
            users = int(sys.argv[1])
            spawn_rate = min(100, users // 10)  # Safe spawn rate
            run_time = "120s"
        except ValueError:
            users = 1000
            spawn_rate = 100
            run_time = "120s"
    else:
        users = 1000
        spawn_rate = 100
        run_time = "120s"
    
    host = "http://localhost:8000"
    
    # Run tests for all API classes
    test_classes = ["MemberAPITestUser", "PaymentAPITestUser", "ReportAPITestUser"]
    
    for test_class in test_classes:
        print(f"\nStarting performance tests for {test_class} ({users} concurrent users)...")
        cmd = f"locust -f performance.py {test_class} --host={host} --users={users} --spawn-rate={spawn_rate} --run-time={run_time} --headless"
        print(f"Running: {cmd}")
        result = os.system(cmd)
        if result != 0:
            print(f"⚠️  Warning: Test for {test_class} exited with code {result}")
