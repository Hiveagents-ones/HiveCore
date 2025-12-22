import asyncio
import aiohttp
import time
from typing import List, Dict
import random
import string

BASE_URL = "http://localhost:8000"
REGISTER_ENDPOINT = "/api/v1/members/register"
CONCURRENT_USERS = 100
TOTAL_REQUESTS = 1000

def generate_random_phone() -> str:
    """Generate a random phone number"""
    return f"1{random.randint(3000000000, 9999999999)}"

def generate_random_id_card() -> str:
    """Generate a random ID card number"""
    return ''.join(random.choices(string.digits, k=18))

def generate_random_name() -> str:
    """Generate a random name"""
    return f"TestUser{''.join(random.choices(string.ascii_letters, k=5))}"

def generate_member_data() -> Dict:
    """Generate random member data for registration"""
    return {
        "name": generate_random_name(),
        "phone": generate_random_phone(),
        "id_card": generate_random_id_card()
    }

async def register_member(session: aiohttp.ClientSession, member_data: Dict) -> Dict:
    """Register a single member"""
    start_time = time.time()
    try:
        async with session.post(
            f"{BASE_URL}{REGISTER_ENDPOINT}",
            json=member_data
        ) as response:
            response_time = time.time() - start_time
            if response.status == 201:
                return {
                    "success": True,
                    "response_time": response_time,
                    "status_code": response.status
                }
            else:
                return {
                    "success": False,
                    "response_time": response_time,
                    "status_code": response.status,
                    "error": await response.text()
                }
    except Exception as e:
        return {
            "success": False,
            "response_time": time.time() - start_time,
            "error": str(e)
        }

async def run_load_test() -> Dict:
    """Run the load test with concurrent users"""
    print(f"Starting load test with {CONCURRENT_USERS} concurrent users...")
    print(f"Total requests to be sent: {TOTAL_REQUESTS}")
    
    connector = aiohttp.TCPConnector(limit=CONCURRENT_USERS)
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = []
        for i in range(TOTAL_REQUESTS):
            member_data = generate_member_data()
            task = register_member(session, member_data)
            tasks.append(task)
        
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Calculate statistics
        successful_requests = sum(1 for r in results if r["success"])
        failed_requests = TOTAL_REQUESTS - successful_requests
        response_times = [r["response_time"] for r in results if r["success"]]
        
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]
        else:
            avg_response_time = min_response_time = max_response_time = p95_response_time = 0
        
        requests_per_second = TOTAL_REQUESTS / total_time if total_time > 0 else 0
        
        return {
            "total_requests": TOTAL_REQUESTS,
            "concurrent_users": CONCURRENT_USERS,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": (successful_requests / TOTAL_REQUESTS) * 100,
            "total_time": total_time,
            "requests_per_second": requests_per_second,
            "avg_response_time": avg_response_time,
            "min_response_time": min_response_time,
            "max_response_time": max_response_time,
            "p95_response_time": p95_response_time
        }

def print_results(results: Dict):
    """Print load test results in a formatted way"""
    print("\n" + "="*50)
    print("LOAD TEST RESULTS")
    print("="*50)
    print(f"Total Requests: {results['total_requests']}")
    print(f"Concurrent Users: {results['concurrent_users']}")
    print(f"Successful Requests: {results['successful_requests']}")
    print(f"Failed Requests: {results['failed_requests']}")
    print(f"Success Rate: {results['success_rate']:.2f}%")
    print(f"Total Time: {results['total_time']:.2f} seconds")
    print(f"Requests per Second: {results['requests_per_second']:.2f}")
    print("\nResponse Times (seconds):")
    print(f"  Average: {results['avg_response_time']:.3f}")
    print(f"  Minimum: {results['min_response_time']:.3f}")
    print(f"  Maximum: {results['max_response_time']:.3f}")
    print(f"  95th Percentile: {results['p95_response_time']:.3f}")
    print("="*50)

if __name__ == "__main__":
    # Run the load test
    results = asyncio.run(run_load_test())
    print_results(results)
    
    # Performance criteria check
    print("\nPERFORMANCE CRITERIA CHECK:")
    print("-"*30)
    
    if results['success_rate'] >= 99:
        print("✓ Success rate (>=99%): PASS")
    else:
        print(f"✗ Success rate (>=99%): FAIL ({results['success_rate']:.2f}%)")
    
    if results['p95_response_time'] <= 1.0:
        print("✓ 95th percentile response time (<=1s): PASS")
    else:
        print(f"✗ 95th percentile response time (<=1s): FAIL ({results['p95_response_time']:.3f}s)")
    
    if results['requests_per_second'] >= 100:
        print("✓ Throughput (>=100 RPS): PASS")
    else:
        print(f"✗ Throughput (>=100 RPS): FAIL ({results['requests_per_second']:.2f} RPS)")
