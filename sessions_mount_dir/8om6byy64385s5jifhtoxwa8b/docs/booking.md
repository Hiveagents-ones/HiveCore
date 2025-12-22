# 课程预约系统使用和配置文档

## 概述

课程预约系统允许会员浏览课程表，预约或取消团体课程（如瑜伽、动感单车）。系统会自动管理课程容量和预约状态，确保预约流程的顺畅和数据的准确性。

## 功能特性

- **课程浏览**：会员可以查看未来一周的课程安排，包括课程名称、时间、地点、教练和剩余名额。
- **课程预约**：会员可以预约有名额的课程，系统会实时更新课程容量。
- **预约取消**：会员可以取消已预约的课程，释放名额给其他会员。
- **状态管理**：系统自动管理预约状态（已预约、已取消、已完成等）。
- **筛选功能**：支持按日期和课程类别筛选课程。
- **私教课程**：支持预约一对一私教课程，包含特殊的时间安排和定价规则。

## 技术架构

- **前端**：Vue 3 + Vite + Pinia + Vue Router + Vue I18n
- **后端**：FastAPI + SQLAlchemy + Alembic + Pydantic
- **数据库**：PostgreSQL
- **部署**：Docker + Nginx + Let's Encrypt
- **监控**：Prometheus + Grafana

## API 接口

### 预约管理

#### 创建预约

- **端点**：`POST /api/v1/bookings/`
- **描述**：创建新的课程预约
- **请求体**：
  ```json
  {
    "user_id": 1,
    "class_schedule_id": 1
  }
  ```
- **响应**：
  ```json
  {
    "id": 1,
    "user_id": 1,
    "class_schedule_id": 1,
    "status": "booked",
    "created_at": "2023-10-01T10:00:00Z",
    "updated_at": "2023-10-01T10:00:00Z"
  }
  ```

#### 获取预约列表

- **端点**：`GET /api/v1/bookings/`
- **描述**：获取预约列表，支持按用户、课程和状态筛选
- **查询参数**：
  - `skip`：跳过记录数（默认0）
  - `limit`：返回记录数（默认100）
  - `user_id`：用户ID（可选）
  - `class_schedule_id`：课程ID（可选）
  - `status`：预约状态（可选）
- **响应**：预约对象数组

#### 获取单个预约

- **端点**：`GET /api/v1/bookings/{booking_id}`
- **描述**：获取指定预约的详细信息
- **响应**：预约对象

#### 更新预约

- **端点**：`PUT /api/v1/bookings/{booking_id}`
- **描述**：更新预约状态
- **请求体**：
  ```json
  {
    "status": "cancelled"
  }
  ```
- **响应**：更新后的预约对象

#### 取消预约

- **端点**：`DELETE /api/v1/bookings/{booking_id}`
- **描述**：取消指定预约
- **响应**：204 No Content

### 课程管理

#### 获取课程列表

- **端点**：`GET /api/v1/courses/`
- **描述**：获取课程列表，支持按日期和类别筛选
- **查询参数**：
  - `date`：日期（可选）
  - `category`：课程类别（可选）
  - `type`：课程类型（group/private，可选）
- **响应**：课程对象数组

#### 获取课程详情

- **端点**：`GET /api/v1/courses/{course_id}`
- **描述**：获取指定课程的详细信息
- **响应**：课程对象

#### 创建私教课程

- **端点**：`POST /api/v1/courses/private`
- **描述**：创建新的私教课程
- **请求体**：
  ```json
  {
    "name": "瑜伽私教",
    "instructor_id": 1,
    "start_time": "2023-10-01T10:00:00Z",
    "duration": 60,
    "price": 200
  }
  ```
- **响应**：创建的课程对象

## 前端组件

### CourseSchedule.vue

课程表视图组件，展示课程列表并提供预约/取消预约功能。

**主要功能**：
- 按日期和类别筛选课程
- 显示课程详细信息
- 预约/取消预约按钮
- 实时更新课程容量

**使用方法**：
```vue
<template>
  <CourseSchedule />
</template>

<script setup>
import CourseSchedule from '@/views/CourseSchedule.vue'
</script>
```

### BookingModal.vue

预约模态框组件，用于确认预约操作。

**主要功能**：
- 显示预约详情
- 确认/取消预约操作

**使用方法**：
```vue
<template>
  <BookingModal 
    v-if="showModal" 
    :course="selectedCourse" 
    @confirm="handleConfirm" 
    @cancel="handleCancel" 
  />
</template>

<script setup>
import { ref } from 'vue'
import BookingModal from '@/components/BookingModal.vue'

const showModal = ref(false)
const selectedCourse = ref(null)

const handleConfirm = () => {
  // 处理预约确认
}

const handleCancel = () => {
  showModal.value = false
}
</script>
```

## 数据库模型

### Booking

预约表，存储预约信息。

**字段**：
- `id`：主键
- `user_id`：用户ID
- `class_schedule_id`：课程ID
- `status`：预约状态（booked/cancelled/completed）
- `created_at`：创建时间
- `updated_at`：更新时间

### ClassSchedule

课程表，存储课程信息。

**字段**：
- `id`：主键
- `name`：课程名称
- `category`：课程类别
- `type`：课程类型（group/private）
- `start_time`：开始时间
- `end_time`：结束时间
- `instructor_id`：教练ID
- `location`：地点
- `capacity`：容量
- `booked_count`：已预约人数
- `price`：课程价格（私教课程）
- `description`：课程描述

## 配置说明

### 环境变量

后端配置通过环境变量设置：

```bash
# 数据库配置
DATABASE_URL=postgresql://user:password@localhost/dbname

# JWT配置
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 应用配置
DEBUG=False
```

### 数据库迁移

使用Alembic管理数据库迁移：

```bash
# 创建迁移
alembic revision --autogenerate -m "Create booking table"

# 应用迁移
alembic upgrade head
```

## 部署指南

### Docker部署

1. 构建镜像：
```bash
docker build -t booking-system .
```

2. 运行容器：
```bash
docker run -d -p 8000:8000 booking-system
```

### Nginx配置

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 监控和日志

### Prometheus指标

系统暴露以下指标：
- `booking_requests_total`：预约请求总数
- `booking_duration_seconds`：预约处理时间
- `active_bookings`：当前活跃预约数

### 日志格式

日志采用JSON格式：
```json
{
  "timestamp": "2023-10-01T10:00:00Z",
  "level": "INFO",
  "message": "Booking created",
  "user_id": 1,
  "class_schedule_id": 1
}
```

## 测试

### API测试

运行API测试：
```bash
pytest tests/test_booking_api.py
```

### 性能测试

运行负载测试：
```bash
python tests/performance/booking_load_test.py
```

## 常见问题

### Q: 如何预约私教课程？
A: 私教课程需要先与教练协商时间，然后通过系统创建预约。私教课程不受团体课程容量限制。

### Q: 私教课程如何收费？
A: 私教课程价格单独设置，预约时需要确认价格信息。支持按次收费或套餐购买。

### Q: 如何处理课程满员情况？
A: 系统会自动检查课程容量，当`booked_count`达到`capacity`时，预约按钮会变为禁用状态并显示"已满员"提示。

### Q: 预约可以提前多久取消？
A: 目前系统支持随时取消预约，未来版本可以添加取消时间限制。

### Q: 如何查看历史预约记录？
A: 通过`GET /api/v1/bookings/`接口，传入`user_id`参数可以获取指定用户的所有预约记录。

## 更新日志

### v1.1.0 (2023-10-15)
- 新增私教课程支持
- 优化预约流程
- 添加课程详情页面

### v1.0.0 (2023-10-01)
- 初始版本发布
- 实现基本预约功能
- 添加课程浏览和筛选

## 联系方式

如有问题或建议，请联系开发团队：
- 邮箱：dev@example.com
- 项目地址：https://github.com/example/booking-system