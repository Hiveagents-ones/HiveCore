import asyncio
import aiohttp
import time
from typing import List, Dict
import statistics
import json
from datetime import datetime, timedelta

# Test configuration
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"
NUM_USERS = 50
REQUESTS_PER_USER = 10
TEST_DURATION = 60  # seconds

# Test data
TEST_COURSE_ID = 1
TEST_USER_CREDENTIALS = [
    {"username": f"testuser{i}", "password": "testpass123"}
    for i in range(NUM_USERS)
]

class BookingLoadTest:
    def __init__(self):
        self.results: List[float] = []
        self.errors: List[Dict] = []
        self.success_count = 0
        self.error_count = 0
        self.auth_tokens: Dict[str, str] = {}

    async def setup_session(self) -> aiohttp.ClientSession:
        """Create and configure aiohttp session"""
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
        return aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={"Content-Type": "application/json"}
        )

    async def authenticate_user(self, session: aiohttp.ClientSession, credentials: Dict) -> str:
        """Authenticate user and return access token"""
        if credentials["username"] in self.auth_tokens:
            return self.auth_tokens[credentials["username"]]

        auth_url = f"{BASE_URL}{API_PREFIX}/auth/login"
        async with session.post(auth_url, json=credentials) as response:
            if response.status == 200:
                data = await response.json()
                token = data.get("access_token")
                self.auth_tokens[credentials["username"]] = token
                return token
            else:
                raise Exception(f"Authentication failed for {credentials['username']}")

    async def make_booking_request(self, session: aiohttp.ClientSession, user_token: str) -> float:
        """Make a single booking request and return response time"""
        booking_url = f"{BASE_URL}{API_PREFIX}/bookings"
        headers = {"Authorization": f"Bearer {user_token}"}
        booking_data = {
            "course_id": TEST_COURSE_ID,
            "booking_time": (datetime.now() + timedelta(days=1)).isoformat()
        }

        start_time = time.time()
        try:
            async with session.post(booking_url, json=booking_data, headers=headers) as response:
                await response.text()  # Consume response
                end_time = time.time()
                response_time = end_time - start_time

                if response.status == 201:
                    self.success_count += 1
                else:
                    self.error_count += 1
                    self.errors.append({
                        "status": response.status,
                        "error": await response.text(),
                        "timestamp": datetime.now().isoformat()
                    })

                return response_time
        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time
            self.error_count += 1
            self.errors.append({
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            return response_time

    async def user_simulation(self, session: aiohttp.ClientSession, credentials: Dict) -> None:
        """Simulate a single user making multiple booking requests"""
        try:
            user_token = await self.authenticate_user(session, credentials)
            
            for _ in range(REQUESTS_PER_USER):
                response_time = await self.make_booking_request(session, user_token)
                self.results.append(response_time)
                await asyncio.sleep(0.1)  # Small delay between requests

        except Exception as e:
            self.error_count += 1
            self.errors.append({
                "error": f"User simulation failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })

    async def run_load_test(self) -> Dict:
        """Execute the load test"""
        print(f"Starting load test with {NUM_USERS} users, {REQUESTS_PER_USER} requests each")
        start_time = time.time()

        async with await self.setup_session() as session:
            tasks = [
                self.user_simulation(session, credentials)
                for credentials in TEST_USER_CREDENTIALS
            ]
            await asyncio.gather(*tasks)

        end_time = time.time()
        total_duration = end_time - start_time

        # Calculate statistics
        if self.results:
            avg_response_time = statistics.mean(self.results)
            min_response_time = min(self.results)
            max_response_time = max(self.results)
            median_response_time = statistics.median(self.results)
            p95_response_time = sorted(self.results)[int(len(self.results) * 0.95)]
        else:
            avg_response_time = min_response_time = max_response_time = median_response_time = p95_response_time = 0

        total_requests = self.success_count + self.error_count
        success_rate = (self.success_count / total_requests * 100) if total_requests > 0 else 0
        requests_per_second = total_requests / total_duration if total_duration > 0 else 0

        test_results = {
            "test_configuration": {
                "num_users": NUM_USERS,
                "requests_per_user": REQUESTS_PER_USER,
                "total_requests": total_requests,
                "test_duration_seconds": total_duration
            },
            "performance_metrics": {
                "requests_per_second": round(requests_per_second, 2),
                "success_rate_percent": round(success_rate, 2),
                "response_times": {
                    "average_ms": round(avg_response_time * 1000, 2),
                    "minimum_ms": round(min_response_time * 1000, 2),
                    "maximum_ms": round(max_response_time * 1000, 2),
                    "median_ms": round(median_response_time * 1000, 2),
                    "p95_ms": round(p95_response_time * 1000, 2)
                }
            },
            "error_summary": {
                "total_errors": self.error_count,
                "error_rate_percent": round((self.error_count / total_requests * 100) if total_requests > 0 else 0, 2),
                "sample_errors": self.errors[:5]  # First 5 errors for review
            },
            "timestamp": datetime.now().isoformat()
        }

        return test_results

    def print_results(self, results: Dict) -> None:
        """Print formatted test results"""
        print("\n" + "="*60)
        print("LOAD TEST RESULTS")
        print("="*60)
        
        config = results["test_configuration"]
        metrics = results["performance_metrics"]
        errors = results["error_summary"]
        
        print(f"\nTest Configuration:")
        print(f"  - Users: {config['num_users']}")
        print(f"  - Requests per User: {config['requests_per_user']}")
        print(f"  - Total Requests: {config['total_requests']}")
        print(f"  - Test Duration: {config['test_duration_seconds']:.2f} seconds")
        
        print(f"\nPerformance Metrics:")
        print(f"  - Requests/Second: {metrics['requests_per_second']}")
        print(f"  - Success Rate: {metrics['success_rate_percent']}%")
        print(f"  - Average Response Time: {metrics['response_times']['average_ms']} ms")
        print(f"  - Median Response Time: {metrics['response_times']['median_ms']} ms")
        print(f"  - 95th Percentile: {metrics['response_times']['p95_ms']} ms")
        print(f"  - Min/Max Response Time: {metrics['response_times']['minimum_ms']}/{metrics['response_times']['maximum_ms']} ms")
        
        print(f"\nError Summary:")
        print(f"  - Total Errors: {errors['total_errors']}")
        print(f"  - Error Rate: {errors['error_rate_percent']}%")
        
        if errors['sample_errors']:
            print(f"\nSample Errors:")
            for i, error in enumerate(errors['sample_errors'], 1):
                print(f"  {i}. {error.get('status', 'N/A')}: {error.get('error', 'Unknown error')[:100]}...")
        
        print("\n" + "="*60)

async def main():
    """Main test execution function"""
    test = BookingLoadTest()
    results = await test.run_load_test()
    test.print_results(results)
    
    # Save results to file
    with open("booking_load_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results saved to: booking_load_test_results.json")

if __name__ == "__main__":
    asyncio.run(main())
