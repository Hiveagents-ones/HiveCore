import asyncio
import aiohttp
import time
from typing import List, Dict
import statistics
from datetime import datetime

# Load test configuration
BASE_URL = "http://localhost:8000"
CONCURRENT_USERS = 1000
TEST_DURATION = 60  # seconds
ENDPOINTS = [
    {"path": "/api/v1/memberships", "method": "GET", "weight": 40},
    {"path": "/api/v1/payments", "method": "POST", "weight": 30},
    {"path": "/api/v1/renewals", "method": "POST", "weight": 20},
    {"path": "/api/v1/history", "method": "GET", "weight": 10}
]

class LoadTester:
    def __init__(self):
        self.results: List[Dict] = []
        self.errors: List[Dict] = []
        self.start_time = None
        self.end_time = None

    async def single_request(self, session: aiohttp.ClientSession, endpoint: Dict) -> Dict:
        """Execute a single request and return metrics"""
        start = time.time()
        status = None
        error = None
        
        try:
            if endpoint["method"] == "GET":
                async with session.get(f"{BASE_URL}{endpoint['path']}") as response:
                    status = response.status
                    await response.text()
            else:  # POST
                payload = {
                    "member_id": f"test_member_{int(time.time() * 1000) % 1000}",
                    "amount": 100.0,
                    "payment_method": "online"
                }
                async with session.post(
                    f"{BASE_URL}{endpoint['path']}",
                    json=payload
                ) as response:
                    status = response.status
                    await response.text()
                    
        except Exception as e:
            error = str(e)
            
        end = time.time()
        
        return {
            "endpoint": endpoint["path"],
            "method": endpoint["method"],
            "status_code": status,
            "response_time": (end - start) * 1000,  # in ms
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def user_session(self, user_id: int):
        """Simulate a user session with multiple requests"""
        async with aiohttp.ClientSession() as session:
            while time.time() - self.start_time < TEST_DURATION:
                # Select endpoint based on weight
                endpoint = self.select_weighted_endpoint()
                result = await self.single_request(session, endpoint)
                result["user_id"] = user_id
                
                if result["error"]:
                    self.errors.append(result)
                else:
                    self.results.append(result)
                    
                # Small delay between requests
                await asyncio.sleep(0.1)

    def select_weighted_endpoint(self) -> Dict:
        """Select endpoint based on configured weights"""
        total_weight = sum(ep["weight"] for ep in ENDPOINTS)
        r = statistics.randint(1, total_weight)
        
        current_weight = 0
        for endpoint in ENDPOINTS:
            current_weight += endpoint["weight"]
            if r <= current_weight:
                return endpoint
        return ENDPOINTS[0]

    async def run_test(self):
        """Execute the load test with concurrent users"""
        print(f"Starting load test with {CONCURRENT_USERS} concurrent users")
        print(f"Test duration: {TEST_DURATION} seconds")
        print(f"Target URL: {BASE_URL}")
        
        self.start_time = time.time()
        
        # Create tasks for all concurrent users
        tasks = [
            asyncio.create_task(self.user_session(user_id))
            for user_id in range(CONCURRENT_USERS)
        ]
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks)
        
        self.end_time = time.time()
        
    def generate_report(self) -> Dict:
        """Generate comprehensive test report"""
        if not self.results:
            return {"error": "No successful requests recorded"}
            
        response_times = [r["response_time"] for r in self.results]
        status_codes = {}
        endpoint_stats = {}
        
        for result in self.results:
            # Count status codes
            status = result["status_code"]
            status_codes[status] = status_codes.get(status, 0) + 1
            
            # Group by endpoint
            ep = result["endpoint"]
            if ep not in endpoint_stats:
                endpoint_stats[ep] = {
                    "count": 0,
                    "response_times": [],
                    "errors": 0
                }
            endpoint_stats[ep]["count"] += 1
            endpoint_stats[ep]["response_times"].append(result["response_time"])
            
        # Calculate endpoint statistics
        for ep in endpoint_stats:
            times = endpoint_stats[ep]["response_times"]
            endpoint_stats[ep]["avg_response_time"] = statistics.mean(times)
            endpoint_stats[ep]["min_response_time"] = min(times)
            endpoint_stats[ep]["max_response_time"] = max(times)
            endpoint_stats[ep]["p95_response_time"] = statistics.quantiles(times, n=20)[18] if len(times) > 20 else max(times)
            
        total_duration = self.end_time - self.start_time
        requests_per_second = len(self.results) / total_duration if total_duration > 0 else 0
        
        report = {
            "test_summary": {
                "total_requests": len(self.results),
                "total_errors": len(self.errors),
                "error_rate": len(self.errors) / (len(self.results) + len(self.errors)) * 100,
                "duration_seconds": total_duration,
                "requests_per_second": requests_per_second,
                "concurrent_users": CONCURRENT_USERS
            },
            "response_time_stats": {
                "avg_ms": statistics.mean(response_times),
                "min_ms": min(response_times),
                "max_ms": max(response_times),
                "p50_ms": statistics.median(response_times),
                "p95_ms": statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else max(response_times),
                "p99_ms": statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else max(response_times)
            },
            "status_code_distribution": status_codes,
            "endpoint_breakdown": endpoint_stats,
            "errors": self.errors[:10]  # First 10 errors
        }
        
        return report

async def main():
    """Main test execution function"""
    tester = LoadTester()
    await tester.run_test()
    report = tester.generate_report()
    
    # Print report
    print("\n" + "="*50)
    print("LOAD TEST REPORT")
    print("="*50)
    
    summary = report["test_summary"]
    print(f"\nTotal Requests: {summary['total_requests']}")
    print(f"Total Errors: {summary['total_errors']}")
    print(f"Error Rate: {summary['error_rate']:.2f}%")
    print(f"Duration: {summary['duration_seconds']:.2f} seconds")
    print(f"Requests/sec: {summary['requests_per_second']:.2f}")
    
    rt_stats = report["response_time_stats"]
    print(f"\nResponse Times (ms):")
    print(f"  Average: {rt_stats['avg_ms']:.2f}")
    print(f"  Min: {rt_stats['min_ms']:.2f}")
    print(f"  Max: {rt_stats['max_ms']:.2f}")
    print(f"  50th percentile: {rt_stats['p50_ms']:.2f}")
    print(f"  95th percentile: {rt_stats['p95_ms']:.2f}")
    print(f"  99th percentile: {rt_stats['p99_ms']:.2f}")
    
    print(f"\nStatus Code Distribution:")
    for code, count in report["status_code_distribution"].items():
        print(f"  {code}: {count}")
    
    print(f"\nEndpoint Breakdown:")
    for endpoint, stats in report["endpoint_breakdown"].items():
        print(f"  {endpoint}:")
        print(f"    Requests: {stats['count']}")
        print(f"    Avg Response Time: {stats['avg_response_time']:.2f}ms")
        print(f"    P95 Response Time: {stats['p95_response_time']:.2f}ms")
    
    if report["errors"]:
        print(f"\nSample Errors:")
        for error in report["errors"]:
            print(f"  {error['endpoint']} - {error['error']}")
    
    # Performance criteria check
    print("\n" + "="*50)
    print("PERFORMANCE CRITERIA CHECK")
    print("="*50)
    
    # Check if performance meets criteria
    criteria_met = True
    
    if rt_stats['p95_ms'] > 500:
        print("\u274c P95 response time > 500ms")
        criteria_met = False
    else:
        print("\u2705 P95 response time <= 500ms")
        
    if summary['error_rate'] > 1:
        print("\u274c Error rate > 1%")
        criteria_met = False
    else:
        print("\u2705 Error rate <= 1%")
        
    if summary['requests_per_second'] < 100:
        print("\u274c Requests/sec < 100")
        criteria_met = False
    else:
        print("\u2705 Requests/sec >= 100")
    
    if criteria_met:
        print("\n\u2705 ALL PERFORMANCE CRITERIA MET")
    else:
        print("\n\u274c SOME PERFORMANCE CRITERIA NOT MET")

if __name__ == "__main__":
    asyncio.run(main())