# 日志监控配置文档

## 概述

本文档描述了课程预约系统的日志监控配置方案，包括日志收集、指标监控和告警设置。

## 技术栈

- **Prometheus**: 用于收集和存储系统指标
- **Grafana**: 用于可视化监控数据和创建仪表板
- **PostgreSQL**: 存储审计日志和系统日志
- **Docker**: 容器化部署监控组件

## 监控架构

```
应用服务 → Prometheus → Grafana
    ↓           ↓
PostgreSQL ← 告警管理器
```

## 配置步骤

### 1. Prometheus 配置

创建 `prometheus.yml` 配置文件：

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'course-booking-api'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### 2. 告警规则配置

创建 `alert_rules.yml` 文件：

```yaml
groups:
- name: course_booking_alerts
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value }} errors per second"

  - alert: HighMemoryUsage
    expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.9
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage"
      description: "Memory usage is above 90%"

  - alert: DatabaseConnectionFailure
    expr: up{job="postgres"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Database connection failure"
      description: "Cannot connect to PostgreSQL database"
```

### 3. Grafana 仪表板

#### 3.1 API 性能仪表板

- **请求速率**: `rate(http_requests_total[5m])`
- **错误率**: `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])`
- **响应时间**: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`

#### 3.2 系统资源仪表板

- **CPU 使用率**: `100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)`
- **内存使用率**: `(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100`
- **磁盘使用率**: `(1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100`

#### 3.3 业务指标仪表板

- **课程预约数**: `sum(course_bookings_total)`
- **活跃用户数**: `count(distinct(user_id))`
- **课程容量使用率**: `course_bookings_total / course_capacity`

### 4. 日志配置

#### 4.1 应用日志

在 `backend/app/main.py` 中配置结构化日志：

```python
import logging
import sys
from pythonjsonlogger import jsonlogger

# 配置 JSON 格式日志
logHandler = logging.StreamHandler(sys.stdout)
formatter = jsonlogger.JsonFormatter(
    '%(asctime)s %(name)s %(levelname)s %(message)s'
)
logHandler.setFormatter(formatter)
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(logHandler)
```

#### 4.2 审计日志

审计日志已通过 `backend/app/core/audit.py` 中的 `AuditMiddleware` 自动记录到数据库。

关键审计事件：
- 用户登录/登出
- 课程预约/取消
- 权限变更
- 系统配置修改

### 5. Docker 部署配置

创建 `docker-compose.monitoring.yml`:

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - ./alert_rules.yml:/etc/prometheus/alert_rules.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-storage:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources

  alertmanager:
    image: prom/alertmanager:latest
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml

  postgres-exporter:
    image: prometheuscommunity/postgres-exporter
    environment:
      - DATA_SOURCE_NAME=postgresql://user:password@postgres:5432/course_booking
    ports:
      - "9187:9187"

volumes:
  grafana-storage:
```

### 6. 告警通知配置

创建 `alertmanager.yml`:

```yaml
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@coursebooking.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
- name: 'web.hook'
  email_configs:
  - to: 'admin@coursebooking.com'
    subject: '[CourseBooking] {{ .GroupLabels.alertname }}'
    body: |
      {{ range .Alerts }}
      Alert: {{ .Annotations.summary }}
      Description: {{ .Annotations.description }}
      {{ end }}
```

## 监控指标

### 1. 应用指标

- `http_requests_total`: HTTP 请求总数
- `http_request_duration_seconds`: HTTP 请求持续时间
- `course_bookings_total`: 课程预约总数
- `active_users_total`: 活跃用户总数

### 2. 系统指标

- `node_cpu_seconds_total`: CPU 使用时间
- `node_memory_MemTotal_bytes`: 总内存
- `node_memory_MemAvailable_bytes`: 可用内存
- `node_filesystem_size_bytes`: 文件系统大小
- `node_filesystem_avail_bytes`: 可用文件系统空间

### 3. 数据库指标

- `pg_stat_database_numbackends`: 数据库连接数
- `pg_stat_database_xact_commit`: 事务提交数
- `pg_stat_database_xact_rollback`: 事务回滚数
- `pg_stat_database_tup_returned`: 返回的元组数

## 维护指南

### 1. 日志轮转

配置 logrotate 处理应用日志：

```bash
/var/log/coursebooking/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 app app
    postrotate
        systemctl reload coursebooking
    endscript
}
```

### 2. 数据保留策略

- Prometheus 指标保留 200 小时
- 审计日志保留 1 年
- 应用日志保留 30 天

### 3. 性能优化

- 调整 Prometheus 抓取间隔
- 配置适当的采样率
- 使用聚合规则减少存储

## 故障排查

### 1. 常见问题

**问题**: Prometheus 无法抓取指标
**解决**: 检查目标服务是否在 `/metrics` 端点暴露指标

**问题**: Grafana 无法连接 Prometheus
**解决**: 验证数据源配置和网络连通性

**问题**: 告警未触发
**解决**: 检查告警规则语法和评估间隔

### 2. 调试命令

```bash
# 检查 Prometheus 目标状态
curl http://localhost:9090/api/v1/targets

# 查询当前告警
curl http://localhost:9090/api/v1/alerts

# 验证规则语法
promtool check rules alert_rules.yml
```

## 安全考虑

1. 限制监控端点的访问权限
2. 使用 HTTPS 传输监控数据
3. 定期更新监控组件
4. 实施访问控制和审计

## 扩展建议

1. 集成 ELK Stack 进行日志分析
2. 添加分布式追踪（Jaeger/Zipkin）
3. 实施混沌工程测试
4. 使用机器学习进行异常检测