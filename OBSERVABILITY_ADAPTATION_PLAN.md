# Observability Backend Adaptation Plan

> HiveCore/AgentScope 可观测性后端适配方案

---

## 总体进度

| 阶段 | 状态 | 说明 |
|------|------|------|
| 架构设计 | ✅ DONE | 多租户 + Webhook 架构 |
| 数据模型 | ✅ DONE | Django 模型已创建并迁移 |
| Ingest API | ✅ DONE | 3 个端点已实现并测试 |
| Query API | ✅ DONE | 8 个端点已实现并测试 |
| 认证系统 | ✅ DONE | API Key + JWT 双认证 |
| AgentScope 集成 | ✅ DONE | WebhookExporter 已实现 |
| 数据库迁移 | ✅ DONE | 已应用到 RDS |
| 集成测试 | ✅ DONE | Ingest + Query 验证通过 |
| Redis SSE | ⏳ TODO | 可选增强 |
| 配额检查 | ⏳ TODO | 可选增强 |

**当前版本: v1.0.0 (MVP)**

---

## 1. 概述 ✅

### 1.1 目标

将 agentscope 的可观测性数据（token 使用量、agent 执行记录、时间线事件）推送到 Django 后端，支持：
- 多租户数据隔离
- 前端实时查询与展示
- 用量统计与成本分析

### 1.2 架构图

```
┌─────────────────┐     Webhook (HTTP POST)     ┌──────────────────┐
│   AgentScope    │ ──────────────────────────> │  Django Backend  │
│                 │      X-API-Key Auth         │                  │
│ ObservabilityHub│                             │  /ingest/usage/  │
│ WebhookExporter │                             │  /ingest/exec/   │
└─────────────────┘                             │  /ingest/timeline│
                                                └────────┬─────────┘
                                                         │
                                                         ▼
┌─────────────────┐      REST API (JWT)         ┌──────────────────┐
│    Frontend     │ <────────────────────────── │   PostgreSQL     │
│   React + TS    │                             │   (AWS RDS)      │
│                 │  /usage/summary/            │                  │
│                 │  /usage/trend/              │  UsageRecord     │
│                 │  /executions/               │  ExecutionRecord │
└─────────────────┘                             │  TimelineEvent   │
                                                └──────────────────┘
```

### 1.3 设计原则

| 原则 | 说明 |
|------|------|
| MVP 优先 | 支持 ~100 用户规模，避免过度设计 |
| 行级隔离 | 使用 `tenant_id` 字段实现多租户 |
| 双认证 | API Key (agentscope) + JWT (frontend) |
| 现有基础设施 | 复用 AWS RDS PostgreSQL、S3、CloudFront |

---

## 2. 数据模型映射 ✅

### 2.1 AgentScope → Django 模型对应 ✅

| AgentScope 类型 | Django 模型 | 用途 |
|----------------|-------------|------|
| `UsageRecord` | `observability.UsageRecord` | LLM 调用的 token/成本记录 |
| `AgentExecution` | `observability.ExecutionRecord` | Agent 执行状态与结果 |
| `TimelineEvent` | `observability.TimelineEvent` | 执行时间线事件 |

### 2.2 字段映射详情 ✅

**UsageRecord:**
```
agentscope                    Django
─────────────────────────────────────────────────
project_id          →         agentscope_project_id
agent_id            →         agentscope_agent_id
agent_name          →         agent_name
model_name          →         model_name
input_tokens        →         input_tokens
output_tokens       →         output_tokens
total_tokens        →         total_tokens
cost_usd            →         cost_usd (Decimal)
duration_ms         →         duration_ms
timestamp           →         timestamp
span_id             →         span_id (可选)
                    +         tenant_id (多租户)
```

**AgentExecution:**
```
agentscope                    Django
─────────────────────────────────────────────────
execution_id        →         execution_id (唯一)
project_id          →         agentscope_project_id
agent_id            →         agentscope_agent_id
agent_name          →         agent_name
node_id             →         node_id
round_index         →         round_index
start_time          →         start_time
end_time            →         end_time
duration_ms         →         duration_ms
success             →         status (running/completed/failed)
content             →         content (TextField)
error_message       →         error_message
                    +         tenant_id (多租户)
```

---

## 3. API 设计 ✅

### 3.1 Ingest APIs (AgentScope → Backend) ✅

| 端点 | 方法 | 认证 | 描述 |
|------|------|------|------|
| `/api/v1/observability/ingest/usage/` | POST | API Key | 推送 token 使用记录 |
| `/api/v1/observability/ingest/execution/` | POST | API Key | 推送/更新执行记录 |
| `/api/v1/observability/ingest/timeline/` | POST | API Key | 推送时间线事件 |

**请求示例:**
```bash
curl -X POST http://localhost:8000/api/v1/observability/ingest/usage/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: hc_xxxxx" \
  -d '{
    "timestamp": "2024-01-01T00:00:00Z",
    "agentscope_project_id": "proj-123",
    "agentscope_agent_id": "agent-456",
    "agent_name": "Strategy Agent",
    "model_name": "gpt-4",
    "input_tokens": 100,
    "output_tokens": 50,
    "total_tokens": 150,
    "cost_usd": 0.01,
    "duration_ms": 1500
  }'
```

### 3.2 Query APIs (Frontend → Backend) ✅

| 端点 | 方法 | 认证 | 描述 |
|------|------|------|------|
| `/api/v1/observability/usage/` | GET | JWT/API Key | 列出使用记录 |
| `/api/v1/observability/usage/summary/` | GET | JWT/API Key | 使用量汇总统计 |
| `/api/v1/observability/usage/trend/` | GET | JWT/API Key | 使用量趋势 |
| `/api/v1/observability/executions/` | GET | JWT/API Key | 列出执行记录 |
| `/api/v1/observability/executions/active/` | GET | JWT/API Key | 当前运行中的执行 |
| `/api/v1/observability/timeline/` | GET | JWT/API Key | 时间线事件 |
| `/api/v1/observability/project/{id}/stats/` | GET | JWT/API Key | 项目统计 |
| `/api/v1/observability/stream/` | GET | JWT/API Key | SSE 实时流 |

**响应示例 (summary):**
```json
{
  "summary": {
    "total_tokens": 150000,
    "total_cost_usd": 15.50,
    "total_calls": 500,
    "avg_duration_ms": 1200.5
  },
  "by_agent": [
    {"agent_name": "Strategy Agent", "tokens": 80000, "cost": 8.00, "calls": 200}
  ],
  "by_model": [
    {"model_name": "gpt-4", "tokens": 100000, "cost": 12.00, "calls": 300}
  ]
}
```

### 3.3 认证流程 ✅

```
AgentScope 推送:
┌──────────┐    X-API-Key: hc_xxx    ┌──────────┐
│AgentScope│ ──────────────────────> │ Backend  │
└──────────┘                         └──────────┘
                                           │
                                           ▼
                                     TenantMiddleware
                                     解析 API Key → Tenant

Frontend 查询:
┌──────────┐    Authorization: Bearer xxx    ┌──────────┐
│ Frontend │ ──────────────────────────────> │ Backend  │
└──────────┘                                 └──────────┘
                                                   │
                                                   ▼
                                             JWTAuthentication
                                             解析 Token → User → Tenant
```

---

## 4. 多租户设计 ✅

### 4.1 租户模型 ✅

```python
class Tenant(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    api_key = models.CharField(max_length=64, unique=True)  # hc_xxx 格式

    # 配额限制
    max_tokens_per_month = models.BigIntegerField(default=500_000)
    max_projects = models.IntegerField(default=10)

    is_active = models.BooleanField(default=True)
```

### 4.2 数据隔离 ✅

所有可观测性模型继承 `TenantModelMixin`:

```python
class TenantModelMixin(models.Model):
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        db_index=True
    )

    class Meta:
        abstract = True
```

ViewSet 使用 `TenantQuerySetMixin` 自动过滤:

```python
class TenantQuerySetMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        tenant = getattr(self.request, 'tenant', None)
        if tenant:
            return qs.filter(tenant=tenant)
        return qs.none()  # 无租户则返回空
```

### 4.3 API Key 格式 ✅

- 前缀: `hc_` (HiveCore)
- 长度: 64 字符 (含前缀)
- 生成: `secrets.token_urlsafe(45)` + 前缀

---

## 5. 实现状态

### 5.1 已完成 ✅

| 组件 | 文件 | 状态 |
|------|------|------|
| 租户模型 | `backend/tenants/models.py` | ✅ 完成 |
| 租户中间件 | `backend/tenants/middleware.py` | ✅ 完成 |
| 租户 Mixin | `backend/tenants/mixins.py` | ✅ 完成 |
| 租户 API | `backend/tenants/views.py` | ✅ 完成 |
| 可观测性模型 | `backend/observability/models.py` | ✅ 完成 |
| 可观测性序列化器 | `backend/observability/serializers.py` | ✅ 完成 |
| Ingest APIs | `backend/observability/views.py` | ✅ 完成 |
| Query APIs | `backend/observability/views.py` | ✅ 完成 |
| SSE 流 | `backend/observability/views.py` | ✅ 完成 |
| 认证后端 | `backend/authentication/backends.py` | ✅ 完成 |
| WebhookExporter | `agentscope/observability/_webhook.py` | ✅ 完成 |
| Hub 集成 | `agentscope/observability/_hub.py` | ✅ 完成 |
| 数据库迁移 | `migrate` | ✅ 完成 |
| API 测试 | Ingest + Query | ✅ 通过 |

### 5.2 测试数据

```
租户名称: Default Tenant
租户 Slug: default
API Key: hc_2nJ9NMyNbHnoZ82mZrRLI92plU511YtnxSnPNMcRtGE
```

### 5.3 待实现 (可选增强)

| 功能 | 优先级 | 说明 |
|------|--------|------|
| Redis SSE | P2 | 当前 fallback 到心跳模式，配置 Redis 可启用实时推送 |
| 配额检查 | P2 | 在 Ingest 时检查 `max_tokens_per_month` |
| 批量 Ingest | P3 | 支持单次请求推送多条记录 |
| 数据归档 | P3 | 超过 90 天的数据归档到 S3 |
| Grafana 集成 | P3 | 导出 Prometheus 格式指标 |

---

## 6. 使用指南 ✅

### 6.1 AgentScope 配置 ✅

```python
from agentscope.observability import ObservabilityHub, WebhookExporter

# 初始化 Hub 和 Exporter
hub = ObservabilityHub()
exporter = WebhookExporter(
    api_url="https://api.yoursite.com/api/v1/observability",
    api_key="hc_your_tenant_api_key",
    async_mode=True,  # 异步推送，不阻塞主流程
    timeout=5.0,
)
hub.set_webhook(exporter)

# 之后所有 hub.record_usage() / record_execution() / record_timeline_event()
# 会自动推送到后端
```

### 6.2 前端集成 (示例代码)

```typescript
// 获取使用量汇总
const response = await fetch('/api/v1/observability/usage/summary/?days=30', {
  headers: {
    'Authorization': `Bearer ${jwtToken}`,
  },
});
const data = await response.json();
// data.summary.total_tokens, data.summary.total_cost_usd, etc.

// SSE 实时订阅
const eventSource = new EventSource(
  '/api/v1/observability/stream/?project=proj-123',
  { headers: { 'Authorization': `Bearer ${jwtToken}` } }
);
eventSource.addEventListener('usage', (event) => {
  const usage = JSON.parse(event.data);
  console.log('New usage:', usage);
});
```

### 6.3 创建新租户 ✅

```python
# Django Shell
from tenants.models import Tenant

tenant = Tenant.objects.create(
    name="Customer A",
    slug="customer-a",
)
print(f"API Key: {tenant.api_key}")
```

---

## 7. 部署注意事项 ✅

### 7.1 环境变量 ✅

```bash
# .env
DATABASE_URL=postgres://user:pass@rds-host:5432/dbname
REDIS_URL=redis://elasticache-host:6379/0  # 可选，用于 SSE
SECRET_KEY=your-django-secret-key
```

### 7.2 数据库迁移 ✅

```bash
cd backend
python manage.py migrate tenants
python manage.py migrate observability
```

### 7.3 性能优化

- 索引已添加: `tenant_id`, `timestamp`, `agentscope_project_id`
- 大量写入时考虑使用 `bulk_create`
- SSE 建议配置 Redis 而非数据库轮询

---

## 8. 文件清单 ✅

```
backend/
├── tenants/                              ✅ 新增
│   ├── __init__.py                       ✅
│   ├── admin.py                          ✅
│   ├── apps.py                           ✅
│   ├── middleware.py                     ✅ TenantMiddleware
│   ├── mixins.py                         ✅ TenantModelMixin, TenantQuerySetMixin
│   ├── models.py                         ✅ Tenant, TenantUser
│   ├── urls.py                           ✅
│   └── views.py                          ✅ TenantViewSet
├── observability/                        ✅ 新增
│   ├── __init__.py                       ✅
│   ├── admin.py                          ✅
│   ├── apps.py                           ✅
│   ├── models.py                         ✅ UsageRecord, ExecutionRecord, TimelineEvent
│   ├── serializers.py                    ✅
│   ├── urls.py                           ✅
│   └── views.py                          ✅ Ingest + Query APIs
├── authentication/                       ✅ 新增
│   ├── __init__.py                       ✅
│   └── backends.py                       ✅ APIKeyAuthentication, JWTAuthenticationWithTenant
└── backend/
    ├── settings.py                       ✅ 已更新
    └── urls.py                           ✅ 已更新

agentscope/src/agentscope/observability/
├── __init__.py                           ✅ 已更新，导出 WebhookExporter
├── _hub.py                               ✅ 已更新，支持 webhook
└── _webhook.py                           ✅ 新增
```

---

## 9. 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2025-12-30 | 初始 MVP 实现，完成 Ingest/Query API |

---

## 10. 联系与支持

如有问题，请参考：
- AgentScope 文档: `agentscope/src/agentscope/observability/`
- Django 后端: `backend/observability/views.py`
- 前端类型定义: `frontend/src/types/api.ts`
