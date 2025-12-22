# 监控配置文档

## 概述

本文档描述了项目监控系统的配置和使用方法。监控系统基于 Prometheus + Grafana 技术栈，用于收集、存储和可视化应用程序的性能指标。

## 架构

```
+-------------------+     +-------------------+     +-------------------+
|   应用程序        |     |   Prometheus      |     |   Grafana         |
| (FastAPI/Vue)     |---->| (指标收集与存储)  |---->| (可视化仪表盘)    |
+-------------------+     +-------------------+     +-------------------+
        |                         |                         |
        v                         v                         v
+-------------------+     +-------------------+     +-------------------+
|   自定义指标      |     |   告警规则        |     |   告警通知        |
+-------------------+     +-------------------+     +-------------------+
```

## 后端监控配置

### 1. Prometheus 指标暴露

后端通过 `backend/app/core/monitoring.py` 模块暴露指标：

```python
# 指标端点: /metrics
# 示例指标:
# - http_requests_total: HTTP 请求总数
# - http_request_duration_seconds: HTTP 请求持续时间
# - booking_operations_total: 预约操作总数
# - active_sessions_total: 活跃会话数
```

### 2. 关键指标

- **业务指标**:
  - `booking_operations_total`: 预约操作计数
  - `course_views_total`: 课程查看次数
  - `user_registrations_total`: 用户注册数

- **性能指标**:
  - `http_request_duration_seconds`: API 响应时间
  - `database_query_duration_seconds`: 数据库查询时间
  - `redis_operation_duration_seconds`: Redis 操作时间

- **系统指标**:
  - `cpu_usage_percent`: CPU 使用率
  - `memory_usage_bytes`: 内存使用量
  - `disk_usage_bytes`: 磁盘使用量

## 前端监控配置

### 1. 性能监控

前端通过 `frontend/src/services/api.js` 集成监控：

```javascript
// 自动收集的指标:
// - 页面加载时间
// - API 请求响应时间
// - 用户交互延迟
// - 错误率
```

### 2. 自定义事件追踪

```javascript
// 示例: 追踪课程查看事件
monitoring.trackEvent('course_view', {
  courseId: '123',
  userId: '456',
  timestamp: Date.now()
});
```

## Prometheus 配置

### prometheus.yml

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'backend-api'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'frontend'
    static_configs:
      - targets: ['frontend:3000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['redis-exporter:9121']
```

### 告警规则

```yaml
# alerts.yml
groups:
  - name: api_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "API 错误率过高"
          description: "5xx 错误率超过 10%"

      - alert: SlowResponse
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API 响应缓慢"
          description: "95% 的请求响应时间超过 1 秒"

      - alert: BookingFailures
        expr: rate(booking_operations_total{status="failed"}[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "预约失败率过高"
          description: "预约失败率超过 5%"
```

## Grafana 仪表盘

### 1. 系统概览仪表盘

- **面板配置**:
  - CPU 使用率 ( gauge )
  - 内存使用率 ( gauge )
  - 磁盘使用率 ( gauge )
  - 网络流量 ( graph )
  - 容器状态 ( stat )

### 2. API 性能仪表盘

- **面板配置**:
  - 请求速率 ( graph )
  - 响应时间分布 ( heatmap )
  - 错误率 ( singlestat )
  - 端点性能排行 ( table )

### 3. 业务指标仪表盘

- **面板配置**:
  - 预约趋势 ( graph )
  - 课程查看次数 ( stat )
  - 用户活跃度 ( graph )
  - 转化率 ( singlestat )

## 部署配置

### Kubernetes 部署

```yaml
# monitoring-namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: monitoring

---
# prometheus-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      containers:
      - name: prometheus
        image: prom/prometheus:latest
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: config
          mountPath: /etc/prometheus
      volumes:
      - name: config
        configMap:
          name: prometheus-config

---
# grafana-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
      - name: grafana
        image: grafana/grafana:latest
        ports:
        - containerPort: 3000
        env:
        - name: GF_SECURITY_ADMIN_PASSWORD
          value: "admin"
```

## 使用指南

### 1. 访问监控界面

- Prometheus: http://prometheus:9090
- Grafana: http://grafana:3000 (admin/admin)

### 2. 查询示例

```promql
# 查询过去5分钟的API请求速率
rate(http_requests_total[5m])

# 查询95分位响应时间
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# 查询预约成功率
sum(rate(booking_operations_total{status="success"}[5m])) / sum(rate(booking_operations_total[5m]))
```

### 3. 告警处理

1. 查看告警详情
2. 确认告警级别
3. 执行相应处理流程
4. 更新告警状态

## 最佳实践

1. **指标命名规范**:
   - 使用 snake_case
   - 包含单位后缀 (_seconds, _bytes, _percent)
   - 使用有意义的标签

2. **采样频率**:
   - 关键指标: 5-10秒
   - 普通指标: 15-30秒
   - 系统指标: 30-60秒

3. **保留策略**:
   - 原始数据: 15天
   - 聚合数据: 90天
   - 长期趋势: 1年

4. **告警优化**:
   - 设置合理的阈值
   - 使用告警抑制
   - 配置告警分级

## 故障排查

### 常见问题

1. **指标缺失**:
   - 检查 Prometheus 配置
   - 验证目标端点可达性
   - 查看抓取日志

2. **告警不触发**:
   - 检查规则语法
   - 验证表达式正确性
   - 确认评估间隔

3. **仪表盘异常**:
   - 检查数据源连接
   - 验证查询语法
   - 刷新缓存

### 日志位置

- Prometheus: /var/log/prometheus/
- Grafana: /var/log/grafana/
- AlertManager: /var/log/alertmanager/

## 维护计划

### 定期任务

1. **每日**:
   - 检查告警状态
   - 验证数据完整性

2. **每周**:
   - 审查仪表盘配置
   - 优化查询性能

3. **每月**:
   - 更新告警规则
   - 清理过期数据

4. **每季度**:
   - 评估监控覆盖度
   - 升级组件版本

## 联系方式

- 监控负责人: ops-team@example.com
- 紧急联系: +86-xxx-xxxx-xxxx
- 文档更新: 请提交 PR 到项目仓库