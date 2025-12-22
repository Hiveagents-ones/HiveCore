# 数据统计 API 文档

## 概述

数据统计 API 为商家提供其店铺的经营数据分析功能，包括课程预约量、会员增长趋势、热门课程排行、收入统计等。

## 基础信息

- **基础路径**: `/api/analytics`
- **认证方式**: Bearer Token (商家登录后获取)
- **数据格式**: JSON
- **字符编码**: UTF-8

## 接口列表

### 1. 获取综合统计数据

**接口地址**: `POST /api/analytics/`

**请求方式**: POST

**请求头**:
```http
Content-Type: application/json
Authorization: Bearer <token>
```

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| start_date | string | 是 | 开始日期 (YYYY-MM-DD) |
| end_date | string | 是 | 结束日期 (YYYY-MM-DD) |
| course_ids | array | 否 | 指定课程ID列表 |
| include_growth | boolean | 否 | 是否包含会员增长数据 (默认: false) |
| include_revenue | boolean | 否 | 是否包含收入统计 (默认: false) |

**请求示例**:
```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "course_ids": [1, 2, 3],
  "include_growth": true,
  "include_revenue": true
}
```

**响应参数**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| success | boolean | 请求是否成功 |
| data | object | 统计数据 |
| data.overview | object | 总览数据 |
| data.booking_stats | array | 预约统计数据 |
| data.member_growth | array | 会员增长数据 |
| data.popular_courses | array | 热门课程排行 |
| data.revenue_stats | array | 收入统计数据 |

**响应示例**:
```json
{
  "success": true,
  "data": {
    "overview": {
      "total_bookings": 1250,
      "total_members": 856,
      "total_revenue": 125000.00,
      "avg_rating": 4.8
    },
    "booking_stats": [
      {
        "date": "2024-01-01",
        "count": 45,
        "course_id": 1,
        "course_name": "瑜伽基础课"
      }
    ],
    "member_growth": [
      {
        "date": "2024-01-01",
        "new_members": 12,
        "total_members": 856
      }
    ],
    "popular_courses": [
      {
        "course_id": 1,
        "course_name": "瑜伽基础课",
        "booking_count": 320,
        "revenue": 32000.00
      }
    ],
    "revenue_stats": [
      {
        "date": "2024-01-01",
        "amount": 4500.00,
        "type": "course_booking"
      }
    ]
  }
}
```

## 数据模型

### AnalyticsRequest

```typescript
interface AnalyticsRequest {
  start_date: string;      // YYYY-MM-DD
  end_date: string;        // YYYY-MM-DD
  course_ids?: number[];   // 可选，指定课程ID列表
  include_growth?: boolean;
  include_revenue?: boolean;
}
```

### AnalyticsResponse

```typescript
interface AnalyticsResponse {
  success: boolean;
  data: DetailedAnalytics;
}

interface DetailedAnalytics {
  overview: AnalyticsOverview;
  booking_stats: CourseBookingStats[];
  member_growth: MemberGrowthStats[];
  popular_courses: PopularCourseRanking[];
  revenue_stats: RevenueStats[];
}

interface AnalyticsOverview {
  total_bookings: number;
  total_members: number;
  total_revenue: number;
  avg_rating: number;
}

interface CourseBookingStats {
  date: string;
  count: number;
  course_id: number;
  course_name: string;
}

interface MemberGrowthStats {
  date: string;
  new_members: number;
  total_members: number;
}

interface PopularCourseRanking {
  course_id: number;
  course_name: string;
  booking_count: number;
  revenue: number;
}

interface RevenueStats {
  date: string;
  amount: number;
  type: string;
}
```

## 错误码说明

| 错误码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未授权访问 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 使用限制

1. 日期范围不能超过365天
2. 结束日期必须晚于开始日期
3. 需要商家登录认证
4. 只能查看自己店铺的数据

## 示例代码

### JavaScript (Axios)

```javascript
const axios = require('axios');

const getAnalytics = async (startDate, endDate) => {
  try {
    const response = await axios.post('/api/analytics/', {
      start_date: startDate,
      end_date: endDate,
      include_growth: true,
      include_revenue: true
    }, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    
    return response.data;
  } catch (error) {
    console.error('获取统计数据失败:', error.response.data);
    throw error;
  }
};

// 使用示例
getAnalytics('2024-01-01', '2024-01-31')
  .then(data => {
    console.log('统计数据:', data);
  })
  .catch(error => {
    console.error('错误:', error);
  });
```

### Python (Requests)

```python
import requests

def get_analytics(start_date, end_date, token):
    url = '/api/analytics/'
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    data = {
        'start_date': start_date,
        'end_date': end_date,
        'include_growth': True,
        'include_revenue': True
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f'获取统计数据失败: {e}')
        raise

# 使用示例
try:
    data = get_analytics('2024-01-01', '2024-01-31', 'your_token_here')
    print('统计数据:', data)
except Exception as e:
    print('错误:', e)
```

## 更新日志

- **v1.0.0** (2024-01-15): 初始版本发布
  - 支持基础统计数据查询
  - 支持课程预约量统计
  - 支持会员增长趋势
  - 支持热门课程排行
  - 支持收入统计

## 相关文档

- [商家端API文档](./merchant_api.md)
- [认证授权文档](./auth.md)
- [错误处理指南](./error_handling.md)