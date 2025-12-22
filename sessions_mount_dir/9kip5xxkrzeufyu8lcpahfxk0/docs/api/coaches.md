# 教练排班 API 文档

## 基础信息
- 基础路径: `/api/v1/coaches`
- 认证方式: Bearer Token (JWT)

## 教练管理

### 获取所有教练信息
```
GET /
```

**响应示例**
```json
[
  {
    "id": 1,
    "name": "张三",
    "phone": "13800138000",
    "email": "zhangsan@example.com",
    "specialty": "瑜伽",
    "status": "active"
  }
]
```

### 创建新教练
```
POST /
```

**请求体**
```json
{
  "name": "李四",
  "phone": "13900139000",
  "email": "lisi@example.com",
  "specialty": "普拉提",
  "status": "active"
}
```

### 更新教练信息
```
PUT /{coach_id}
```

**请求体**
```json
{
  "name": "李四",
  "phone": "13900139001",
  "status": "on_leave"
}
```

### 删除教练
```
DELETE /{coach_id}
```

## 排班管理

### 获取所有教练排班
```
GET /schedules
```

**响应示例**
```json
[
  {
    "id": 1,
    "coach_id": 1,
    "date": "2023-10-15",
    "start_time": "09:00",
    "end_time": "12:00",
    "status": "scheduled",
    "coach": {
      "id": 1,
      "name": "张三"
    }
  }
]
```

### 获取指定教练的排班
```
GET /schedules/{coach_id}
```

### 按日期查询排班
```
GET /schedules/date/{date}
```

**日期格式**: YYYY-MM-DD

## 错误码
| 状态码 | 说明 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 404 | 教练不存在 |
| 500 | 服务器内部错误 |