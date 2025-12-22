import asyncio
import aiohttp
import time
from typing import List, Dict
import json
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.models.booking import Booking
from backend.app.core.audit import audit_log

class BookingLoadTest:
    def __init__(self, base_url: str = "http://localhost:8000", concurrent_users: int = 100, total_requests: int = 1000):
        self.base_url = base_url
        self.concurrent_users = concurrent_users
        self.total_requests = total_requests
        self.results = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "response_times": [],
            "errors": []
        }
        self.test_data = self._generate_test_data()

    def _generate_test_data(self) -> List[Dict]:
        """Generate test booking data"""
        bookings = []
        for i in range(self.total_requests):
            bookings.append({
                "course_id": f"course_{i % 10}",  # 10 different courses
                "member_id": f"member_{i}",
                "booking_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "confirmed"
            })
        return bookings

    async def _make_booking_request(self, session: aiohttp.ClientSession, booking_data: Dict) -> Dict:
        """Make a single booking request"""
        start_time = time.time()
        try:
            async with session.post(
                f"{self.base_url}/api/v1/bookings",
                json=booking_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                response_time = time.time() - start_time
                
                if response.status == 201:
                    result = {
                        "success": True,
                        "response_time": response_time,
                        "status_code": response.status
                    }
                else:
                    error_text = await response.text()
                    result = {
                        "success": False,
                        "response_time": response_time,
                        "status_code": response.status,
                        "error": error_text
                    }
                return result
        except Exception as e:
            response_time = time.time() - start_time
            return {
                "success": False,
                "response_time": response_time,
                "error": str(e)
            }

    async def _run_concurrent_requests(self, session: aiohttp.ClientSession, start_idx: int, end_idx: int):
        """Run a batch of concurrent requests"""
        tasks = []
        for i in range(start_idx, end_idx):
            task = self._make_booking_request(session, self.test_data[i])
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results

    async def run_load_test(self):
        """Execute the load test"""
        print(f"Starting load test with {self.concurrent_users} concurrent users and {self.total_requests} total requests")
        
        connector = aiohttp.TCPConnector(limit=self.concurrent_users)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            start_time = time.time()
            
            # Calculate batch size
            batch_size = self.total_requests // self.concurrent_users
            remaining = self.total_requests % self.concurrent_users
            
            # Run batches of concurrent requests
            for i in range(self.concurrent_users):
                start_idx = i * batch_size
                end_idx = start_idx + batch_size
                if i == self.concurrent_users - 1:
                    end_idx += remaining
                
                batch_results = await self._run_concurrent_requests(session, start_idx, end_idx)
                
                # Process results
                for result in batch_results:
                    self.results["total_requests"] += 1
                    self.results["response_times"].append(result["response_time"])
                    
                    if result["success"]:
                        self.results["successful_requests"] += 1
                    else:
                        self.results["failed_requests"] += 1
                        self.results["errors"].append({
                            "error": result.get("error", "Unknown error"),
                            "status_code": result.get("status_code")
                        })
            
            total_time = time.time() - start_time
            
            # Calculate statistics
            avg_response_time = sum(self.results["response_times"]) / len(self.results["response_times"]) if self.results["response_times"] else 0
            max_response_time = max(self.results["response_times"]) if self.results["response_times"] else 0
            min_response_time = min(self.results["response_times"]) if self.results["response_times"] else 0
            requests_per_second = self.results["total_requests"] / total_time if total_time > 0 else 0
            success_rate = (self.results["successful_requests"] / self.results["total_requests"]) * 100 if self.results["total_requests"] > 0 else 0
            
            # Print results
            print("\n=== Load Test Results ===")
            print(f"Total Requests: {self.results['total_requests']}")
            print(f"Successful Requests: {self.results['successful_requests']}")
            print(f"Failed Requests: {self.results['failed_requests']}")
            print(f"Success Rate: {success_rate:.2f}%")
            print(f"Requests Per Second: {requests_per_second:.2f}")
            print(f"Average Response Time: {avg_response_time:.3f}s")
            print(f"Min Response Time: {min_response_time:.3f}s")
            print(f"Max Response Time: {max_response_time:.3f}s")
            print(f"Total Test Duration: {total_time:.2f}s")
            
            if self.results["errors"]:
                print("\n=== Errors ===")
                error_counts = {}
                for error in self.results["errors"]:
                    error_key = f"{error['status_code']}: {error['error'][:50]}"
                    error_counts[error_key] = error_counts.get(error_key, 0) + 1
                
                for error, count in error_counts.items():
                    print(f"{error}: {count} occurrences")
            
            # Audit log
            await audit_log(
                action="load_test_completed",
                details={
                    "total_requests": self.results["total_requests"],
                    "success_rate": success_rate,
                    "avg_response_time": avg_response_time,
                    "requests_per_second": requests_per_second
                }
            )
            
            return self.results

async def main():
    """Main function to run the load test"""
    # Configuration
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    concurrent_users = int(os.getenv("CONCURRENT_USERS", "100"))
    total_requests = int(os.getenv("TOTAL_REQUESTS", "1000"))
    
    # Initialize and run test
    load_test = BookingLoadTest(
        base_url=base_url,
        concurrent_users=concurrent_users,
        total_requests=total_requests
    )
    
    results = await load_test.run_load_test()
    
    # Exit with appropriate code
    success_rate = (results["successful_requests"] / results["total_requests"]) * 100 if results["total_requests"] > 0 else 0
    if success_rate < 95:  # Consider test failed if success rate is below 95%
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
