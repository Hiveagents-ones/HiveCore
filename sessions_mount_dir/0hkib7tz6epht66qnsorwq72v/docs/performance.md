# 性能优化文档

## 概述

本文档描述了课程预约系统的性能优化策略和最佳实践。系统采用前后端分离架构，前端使用 Vue 3 + Vite，后端使用 FastAPI + SQLAlchemy，数据库使用 PostgreSQL。

## 性能目标

- 响应时间：95% 的 API 请求响应时间 < 200ms
- 并发处理：支持 100+ 并发用户
- 吞吐量：处理 1000+ 请求/分钟
- 资源利用率：CPU < 70%，内存 < 80%

## 性能测试

### 测试工具

使用 `tests/performance/load_test.py` 进行负载测试。该脚本模拟多用户并发访问，测试系统在高负载下的表现。

### 测试配置

```python
# 测试参数
CONCURRENT_USERS = 50
REQUESTS_PER_USER = 10
TEST_DURATION = 60  # seconds
```

### 测试指标

- 平均响应时间
- 最小/最大响应时间
- 错误率
- 成功请求数

## 优化策略

### 数据库优化

1. **索引优化**
   - 为课程表的时间字段添加索引
   - 为预约表的用户ID和课程ID添加复合索引

2. **查询优化**
   - 使用 SQLAlchemy 的 `selectinload` 预加载关联数据
   - 避免N+1查询问题

3. **连接池配置**
   ```python
   # backend/app/database.py
   engine = create_engine(
       DATABASE_URL,
       pool_size=20,
       max_overflow=30,
       pool_pre_ping=True
   )
   ```

### API 优化

1. **缓存策略**
   - 使用 Redis 缓存课程列表和课程表数据
   - 缓存过期时间设置为 5 分钟

2. **分页处理**
   - 所有列表接口实现分页
   - 默认每页 20 条记录

3. **异步处理**
   - 使用 FastAPI 的异步特性处理 I/O 密集型操作
   - 数据库查询使用异步 SQLAlchemy

### 前端优化

1. **组件懒加载**
   ```javascript
   // frontend/src/router/index.js
   const CourseSchedule = () => import('@/views/CourseSchedule.vue')
   ```

2. **状态管理优化**
   - 使用 Pinia 进行状态管理
   - 避免不必要的响应式数据

3. **资源优化**
   - 图片使用 WebP 格式
   - 启用 Gzip 压缩

## 监控指标

### Prometheus 指标

- `http_requests_total` - HTTP 请求总数
- `http_request_duration_seconds` - 请求持续时间
- `database_connections_active` - 活跃数据库连接数

### Grafana 仪表板

- API 响应时间趋势
- 错误率统计
- 系统资源使用情况

## 性能调优建议

1. **定期分析慢查询**
   - 使用 PostgreSQL 的 `pg_stat_statements` 扩展
   - 优化执行计划

2. **实施 CDN**
   - 静态资源使用 CDN 加速
   - 减少服务器负载

3. **水平扩展**
   - 使用 Docker Swarm 或 Kubernetes 进行容器编排
   - 根据负载自动扩缩容

## 性能测试报告

### 测试结果示例

```
Starting load test with 50 concurrent users...
Total requests: 1000
Successful requests: 995
Error rate: 0.5%
Average response time: 145ms
Min response time: 23ms
Max response time: 512ms
Median response time: 132ms
```

### 性能瓶颈分析

1. 数据库查询是主要瓶颈
2. 课程表接口在高峰期响应较慢
3. 预约操作存在锁竞争

## 优化实施计划

### 第一阶段（短期）
- [ ] 添加数据库索引
- [ ] 实施基本缓存
- [ ] 优化前端资源加载

### 第二阶段（中期）
- [ ] 实施 Redis 缓存
- [ ] 优化数据库连接池
- [ ] 添加性能监控

### 第三阶段（长期）
- [ ] 实施微服务架构
- [ ] 添加 CDN
- [ ] 实施自动扩缩容

## 相关文件

- `tests/performance/load_test.py` - 负载测试脚本
- `backend/app/database.py` - 数据库配置
- `backend/app/api/v1/endpoints/courses.py` - 课程相关 API
- `frontend/src/views/CourseSchedule.vue` - 课程表组件

## 更新日志

- 2023-12-01: 初始版本
- 2023-12-15: 添加缓存策略
- 2024-01-10: 更新性能测试结果