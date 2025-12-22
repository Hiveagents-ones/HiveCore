import asyncio
import aiohttp
import time
import json
import statistics
from typing import List, Dict, Any

# 配置参数
BASE_URL = "http://localhost:8000"
CONCURRENT_USERS = 50
TOTAL_REQUESTS = 1000
TEST_DURATION = 60  # seconds

# 测试数据
TEST_USER = {
    "username": "testuser",
    "password": "testpass123"
}

RENEWAL_DATA = {
    "plan_type": "monthly",
    "payment_method": "credit_card"
}

class PerformanceTest:
    def __init__(self):
        self.session = None
        self.auth_token = None
        self.results = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "response_times": [],
            "errors": []
        }

    async def setup(self):
        """初始化测试环境"""
        self.session = aiohttp.ClientSession()
        await self.authenticate()

    async def authenticate(self):
        """获取认证token"""
        auth_url = f"{BASE_URL}/auth/token"
        async with self.session.post(auth_url, json=TEST_USER) as response:
            if response.status == 200:
                data = await response.json()
                self.auth_token = data.get("access_token")
            else:
                raise Exception("Authentication failed")

    async def make_request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict[str, Any]:
        """发送HTTP请求"""
        url = f"{BASE_URL}{endpoint}"
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        start_time = time.time()
        try:
            if method == "GET":
                async with self.session.get(url, headers=headers) as response:
                    await response.text()
                    status = response.status
            elif method == "POST":
                async with self.session.post(url, headers=headers, json=data) as response:
                    await response.text()
                    status = response.status
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            self.results["total_requests"] += 1
            self.results["response_times"].append(response_time)
            
            if status == 200:
                self.results["successful_requests"] += 1
            else:
                self.results["failed_requests"] += 1
                self.results["errors"].append(f"Status: {status}, Endpoint: {endpoint}")
            
            return {"status": status, "response_time": response_time}
        
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.results["total_requests"] += 1
            self.results["failed_requests"] += 1
            self.results["errors"].append(str(e))
            return {"status": 500, "response_time": response_time, "error": str(e)}

    async def run_concurrent_test(self):
        """运行并发测试"""
        tasks = []
        
        # 创建并发任务
        for i in range(CONCURRENT_USERS):
            task = asyncio.create_task(self.user_simulation(i))
            tasks.append(task)
        
        # 等待所有任务完成
        await asyncio.gather(*tasks)

    async def user_simulation(self, user_id: int):
        """模拟单个用户的行为"""
        requests_per_user = TOTAL_REQUESTS // CONCURRENT_USERS
        
        for i in range(requests_per_user):
            # 测试会员续费接口
            await self.make_request("/api/payment/renew", "POST", RENEWAL_DATA)
            
            # 测试获取会员信息接口
            await self.make_request("/api/membership/info")
            
            # 模拟用户思考时间
            await asyncio.sleep(0.1)

    async def cleanup(self):
        """清理资源"""
        if self.session:
            await self.session.close()

    def generate_report(self):
        """生成测试报告"""
        if not self.results["response_times"]:
            return "No data collected"
        
        avg_response_time = statistics.mean(self.results["response_times"])
        median_response_time = statistics.median(self.results["response_times"])
        p95_response_time = statistics.quantiles(self.results["response_times"], n=20)[18]
        p99_response_time = statistics.quantiles(self.results["response_times"], n=100)[98]
        
        success_rate = (self.results["successful_requests"] / self.results["total_requests"]) * 100
        
        report = f"""
Performance Test Report
========================
Test Configuration:
- Base URL: {BASE_URL}
- Concurrent Users: {CONCURRENT_USERS}
- Total Requests: {TOTAL_REQUESTS}

Results:
- Total Requests: {self.results['total_requests']}
- Successful Requests: {self.results['successful_requests']}
- Failed Requests: {self.results['failed_requests']}
- Success Rate: {success_rate:.2f}%

Response Times (ms):
- Average: {avg_response_time:.2f}
- Median: {median_response_time:.2f}
- 95th Percentile: {p95_response_time:.2f}
- 99th Percentile: {p99_response_time:.2f}

Errors:
{chr(10).join(self.results['errors'][:10])}  # Show first 10 errors
"""
        return report

async def main():
    """主测试函数"""
    test = PerformanceTest()
    
    try:
        print("Starting performance test...")
        await test.setup()
        
        start_time = time.time()
        await test.run_concurrent_test()
        end_time = time.time()
        
        print(f"Test completed in {end_time - start_time:.2f} seconds")
        print(test.generate_report())
        
        # 性能基准检查
        avg_time = statistics.mean(test.results["response_times"]) if test.results["response_times"] else 0
        success_rate = (test.results["successful_requests"] / test.results["total_requests"]) * 100 if test.results["total_requests"] > 0 else 0
        
        if avg_time > 500:  # 平均响应时间超过500ms
            print("WARNING: Average response time exceeds 500ms")
        
        if success_rate < 99:  # 成功率低于99%
            print("WARNING: Success rate is below 99%")
        
        if avg_time <= 500 and success_rate >= 99:
            print("Performance test PASSED")
        else:
            print("Performance test FAILED")
    
    except Exception as e:
        print(f"Test failed with error: {str(e)}")
    
    finally:
        await test.cleanup()

if __name__ == "__main__":
    asyncio.run(main())