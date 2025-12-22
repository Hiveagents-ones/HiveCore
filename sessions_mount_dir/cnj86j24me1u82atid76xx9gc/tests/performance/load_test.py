import asyncio
import aiohttp
import time
from typing import List, Dict
import statistics
import json

# Configuration
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"
ENDPOINTS = {
    "courses": f"{API_PREFIX}/courses",
    "course_schedule": f"{API_PREFIX}/courses/schedule"
}

# Test parameters
CONCURRENT_USERS = 50
REQUESTS_PER_USER = 10
TEST_DURATION = 60  # seconds

class LoadTester:
    def __init__(self):
        self.results: List[float] = []
        self.errors: List[Dict] = []
        self.total_requests = 0
        self.successful_requests = 0

    async def make_request(self, session: aiohttp.ClientSession, endpoint: str) -> float:
        """Make a single request and return response time"""
        start_time = time.time()
        try:
            async with session.get(f"{BASE_URL}{endpoint}") as response:
                await response.text()
                if response.status == 200:
                    self.successful_requests += 1
                else:
                    self.errors.append({
                        "status": response.status,
                        "endpoint": endpoint,
                        "timestamp": time.time()
                    })
        except Exception as e:
            self.errors.append({
                "error": str(e),
                "endpoint": endpoint,
                "timestamp": time.time()
            })
        finally:
            return time.time() - start_time

    async def user_session(self, user_id: int) -> None:
        """Simulate a single user's session"""
        async with aiohttp.ClientSession() as session:
            for _ in range(REQUESTS_PER_USER):
                # Test course listing endpoint
                response_time = await self.make_request(session, ENDPOINTS["courses"])
                self.results.append(response_time)
                self.total_requests += 1
                
                # Test course schedule endpoint
                response_time = await self.make_request(session, ENDPOINTS["course_schedule"])
                self.results.append(response_time)
                self.total_requests += 1
                
                # Small delay between requests
                await asyncio.sleep(0.1)

    async def run_load_test(self) -> Dict:
        """Run the load test with concurrent users"""
        print(f"Starting load test with {CONCURRENT_USERS} concurrent users...")
        start_time = time.time()
        
        # Create tasks for all users
        tasks = [self.user_session(i) for i in range(CONCURRENT_USERS)]
        
        # Run all tasks concurrently
        await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Calculate statistics
        if self.results:
            avg_response_time = statistics.mean(self.results)
            min_response_time = min(self.results)
            max_response_time = max(self.results)
            median_response_time = statistics.median(self.results)
            p95_response_time = statistics.quantiles(self.results, n=20)[18]  # 95th percentile
        else:
            avg_response_time = min_response_time = max_response_time = median_response_time = p95_response_time = 0
        
        # Calculate requests per second
        rps = self.total_requests / total_time if total_time > 0 else 0
        
        # Calculate success rate
        success_rate = (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0
        
        return {
            "test_duration": total_time,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": len(self.errors),
            "success_rate": success_rate,
            "requests_per_second": rps,
            "response_times": {
                "average": avg_response_time,
                "minimum": min_response_time,
                "maximum": max_response_time,
                "median": median_response_time,
                "p95": p95_response_time
            },
            "errors": self.errors[:10]  # Limit error output
        }

async def main():
    """Main function to run the load test"""
    tester = LoadTester()
    results = await tester.run_load_test()
    
    # Print results
    print("\n=== Load Test Results ===")
    print(f"Test Duration: {results['test_duration']:.2f} seconds")
    print(f"Total Requests: {results['total_requests']}")
    print(f"Successful Requests: {results['successful_requests']}")
    print(f"Failed Requests: {results['failed_requests']}")
    print(f"Success Rate: {results['success_rate']:.2f}%")
    print(f"Requests Per Second: {results['requests_per_second']:.2f}")
    print("\nResponse Times:")
    print(f"  Average: {results['response_times']['average']:.3f}s")
    print(f"  Minimum: {results['response_times']['minimum']:.3f}s")
    print(f"  Maximum: {results['response_times']['maximum']:.3f}s")
    print(f"  Median: {results['response_times']['median']:.3f}s")
    print(f"  95th Percentile: {results['response_times']['p95']:.3f}s")
    
    if results['errors']:
        print("\nSample Errors:")
        for error in results['errors']:
            print(f"  {error}")
    
    # Save results to file
    with open("load_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to load_test_results.json")

if __name__ == "__main__":
    asyncio.run(main())
