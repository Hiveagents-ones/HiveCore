import os
import sys
import time
import asyncio
import aiohttp
import statistics
from typing import List, Dict, Any
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.security import create_access_token
from app.core.config import settings


class PerformanceTest:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.results: List[Dict[str, Any]] = []
        self.auth_token = None
        self.test_user = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123"
        }

    async def setup(self):
        """Setup test environment"""
        async with aiohttp.ClientSession() as session:
            # Register test user
            async with session.post(
                f"{self.base_url}/api/v1/auth/register",
                json=self.test_user
            ) as resp:
                if resp.status not in [200, 201]:
                    print(f"Failed to register test user: {await resp.text()}")
                    return False

            # Login to get token
            async with session.post(
                f"{self.base_url}/api/v1/auth/login",
                json={
                    "username": self.test_user["username"],
                    "password": self.test_user["password"]
                }
            ) as resp:
                if resp.status != 200:
                    print(f"Failed to login: {await resp.text()}")
                    return False
                
                data = await resp.json()
                self.auth_token = data.get("access_token")
                return True

    async def make_request(self, session: aiohttp.ClientSession, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a single request and measure response time"""
        headers = kwargs.pop("headers", {})
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        start_time = time.time()
        try:
            async with session.request(
                method,
                f"{self.base_url}{endpoint}",
                headers=headers,
                **kwargs
            ) as resp:
                response_time = (time.time() - start_time) * 1000  # Convert to ms
                
                result = {
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": resp.status,
                    "response_time": response_time,
                    "timestamp": datetime.utcnow().isoformat(),
                    "success": resp.status < 400
                }
                
                # Read response body for additional metrics
                try:
                    response_data = await resp.json()
                    result["response_size"] = len(str(response_data))
                except:
                    result["response_size"] = 0
                
                return result
        except Exception as e:
            return {
                "endpoint": endpoint,
                "method": method,
                "status_code": 0,
                "response_time": (time.time() - start_time) * 1000,
                "timestamp": datetime.utcnow().isoformat(),
                "success": False,
                "error": str(e)
            }

    async def run_load_test(self, endpoint: str, method: str = "GET", concurrent_users: int = 10, total_requests: int = 100, **kwargs):
        """Run load test for a specific endpoint"""
        print(f"\nRunning load test for {method} {endpoint}")
        print(f"Concurrent users: {concurrent_users}, Total requests: {total_requests}")
        
        connector = aiohttp.TCPConnector(limit=concurrent_users)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = []
            requests_per_user = total_requests // concurrent_users
            
            for _ in range(concurrent_users):
                for _ in range(requests_per_user):
                    task = self.make_request(session, method, endpoint, **kwargs)
                    tasks.append(task)
            
            # Execute all requests
            results = await asyncio.gather(*tasks)
            self.results.extend(results)
            
            # Calculate metrics
            response_times = [r["response_time"] for r in results if r["success"]]
            success_rate = sum(1 for r in results if r["success"]) / len(results) * 100
            
            if response_times:
                avg_response_time = statistics.mean(response_times)
                p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
                p99_response_time = statistics.quantiles(response_times, n=100)[98]  # 99th percentile
                min_response_time = min(response_times)
                max_response_time = max(response_times)
            else:
                avg_response_time = p95_response_time = p99_response_time = 0
                min_response_time = max_response_time = 0
            
            print(f"\nResults for {method} {endpoint}:")
            print(f"  Success Rate: {success_rate:.2f}%")
            print(f"  Average Response Time: {avg_response_time:.2f}ms")
            print(f"  P95 Response Time: {p95_response_time:.2f}ms")
            print(f"  P99 Response Time: {p99_response_time:.2f}ms")
            print(f"  Min Response Time: {min_response_time:.2f}ms")
            print(f"  Max Response Time: {max_response_time:.2f}ms")
            print(f"  Total Requests: {len(results)}")
            print(f"  Successful Requests: {sum(1 for r in results if r['success'])}")
            
            # Check if P95 meets requirements (typically < 500ms)
            if p95_response_time > 500:
                print(f"  WARNING: P95 response time ({p95_response_time:.2f}ms) exceeds 500ms threshold!")
            else:
                print(f"  PASS: P95 response time ({p95_response_time:.2f}ms) is within acceptable limits")

    async def run_all_tests(self):
        """Run performance tests for all key endpoints"""
        print("Starting Performance Tests")
        print("=" * 50)
        
        # Setup test environment
        if not await self.setup():
            print("Failed to setup test environment")
            return
        
        # Test endpoints
        test_cases = [
            {"endpoint": "/api/v1/health", "method": "GET", "concurrent_users": 20, "total_requests": 200},
            {"endpoint": "/api/v1/auth/me", "method": "GET", "concurrent_users": 10, "total_requests": 100},
            {"endpoint": "/api/v1/users", "method": "GET", "concurrent_users": 5, "total_requests": 50},
            {"endpoint": "/api/v1/auth/refresh", "method": "POST", "concurrent_users": 10, "total_requests": 100},
        ]
        
        for test_case in test_cases:
            await self.run_load_test(**test_case)
            await asyncio.sleep(2)  # Brief pause between tests
        
        # Generate summary report
        self.generate_summary_report()

    def generate_summary_report(self):
        """Generate a summary report of all tests"""
        print("\n" + "=" * 50)
        print("PERFORMANCE TEST SUMMARY")
        print("=" * 50)
        
        # Group results by endpoint
        endpoint_results = {}
        for result in self.results:
            key = f"{result['method']} {result['endpoint']}"
            if key not in endpoint_results:
                endpoint_results[key] = []
            endpoint_results[key].append(result)
        
        all_passed = True
        for endpoint, results in endpoint_results.items():
            response_times = [r["response_time"] for r in results if r["success"]]
            success_rate = sum(1 for r in results if r["success"]) / len(results) * 100
            
            if response_times:
                p95 = statistics.quantiles(response_times, n=20)[18]
                status = "PASS" if p95 <= 500 else "FAIL"
                if status == "FAIL":
                    all_passed = False
                
                print(f"\n{endpoint}:")
                print(f"  Success Rate: {success_rate:.2f}%")
                print(f"  P95 Response Time: {p95:.2f}ms [{status}]")
        
        print("\n" + "=" * 50)
        if all_passed:
            print("OVERALL RESULT: ALL TESTS PASSED")
        else:
            print("OVERALL RESULT: SOME TESTS FAILED")
        print("=" * 50)


async def main():
    """Main entry point"""
    tester = PerformanceTest()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())