# HiveCore Backend Adaptation Plan

> HiveCore/AgentScope 后端完整适配方案

---

## 总体进度概览

### 已完成模块 ✅

| 模块 | 状态 | 说明 |
|------|------|------|
| 多租户系统 | ✅ DONE | Tenant 模型、API Key 认证、行级隔离 |
| 可观测性 API | ✅ DONE | Ingest/Query API、SSE 流 |
| 核心 Models | ✅ DONE | Project, Agent, Conversation, Task 等 13 个模型 |
| 核心 ViewSets | ✅ DONE | 所有模型的 CRUD API |
| JWT 认证 | ✅ DONE | SimpleJWT + API Key 双认证 |
| AgentScope Webhook | ✅ DONE | WebhookExporter 推送数据 |
| **CLI → API 封装** | ✅ DONE | `run_execution_for_api()` 可被后端调用 |
| **执行状态管理** | ✅ DONE | ExecutionRound、ExecutionProgress、ExecutionLog 等 |
| **Celery 后台任务** | ✅ DONE | `execute_project_task` 异步执行 |
| **CLIObserver 改造** | ✅ DONE | Observer 类支持 webhook 推送 |
| **执行 API** | ✅ DONE | `/projects/{id}/execute/` 启动执行 |

### 待实现模块 ⏳

| 模块 | 优先级 | 说明 |
|------|--------|------|
| **实时推送 (Redis SSE)** | ✅ DONE | pubsub 模块、SSE 端点、前端订阅 |
| **工件 S3 存储** | ✅ DONE | S3 存储服务、工件 API、同步任务、前端加载 |
| **项目决策存储** | ✅ DONE | ProjectDecision 模型、决策 API、Ingest 端点、前端加载 |
| **Agent 选择决策存储** | ✅ DONE | AgentSelectionDecision 增强、API 端点、Ingest 端点、前端加载 |
| **AA 对话接口** | ✅ DONE | LLM 对话服务、需求提取、交付标准更新、前端 API |
| 配额检查 | P2 | Token 使用量限制 |
| 执行历史查询 | P2 | 重放/分析历史 |

### 已解决的关键阻塞问题 ✅

| 问题 | 影响 | 解决方案 | 状态 |
|------|------|---------|------|
| `full_user_flow_cli.py` 不能直接用 | 前端无法触发执行 | 创建 `runner.py` + `run_execution_for_api()` | ✅ 已解决 |
| CLI 是同步阻塞的 | 前端会超时 | 使用 Celery 后台任务 `execute_project_task` | ✅ 已解决 |
| 无进度回调 | 前端无法显示实时进度 | Observer 集成 ObservabilityHub webhook | ✅ 已解决 |
| workspace 路径硬编码 | 无法多租户 | 按 project_id 隔离 workspace | ✅ 已解决 |

**当前版本: v1.6.0 (AA 对话接口)**

---

## 一、项目架构概览 ✅

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Frontend                                    │
│                         React + TypeScript                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ HomePage │  │Monitoring│  │   Work   │  │ Delivery │  │  Team    │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
│       └─────────────┴─────────────┴─────────────┴─────────────┘        │
│                                   │                                     │
│                            REST API / SSE                               │
└───────────────────────────────────┼─────────────────────────────────────┘
                                    │
┌───────────────────────────────────┼─────────────────────────────────────┐
│                           Django Backend                                │
│  ┌─────────┐  ┌───────────┐  ┌──────────┐  ┌────────────┐  ┌────────┐ │
│  │ tenants │  │observabil.│  │   api    │  │authentication│  │ app   │ │
│  └────┬────┘  └─────┬─────┘  └────┬─────┘  └──────┬──────┘  └───┬────┘ │
│       │             │             │               │              │      │
│       └─────────────┴─────────────┴───────────────┴──────────────┘      │
│                                   │                                     │
│                          PostgreSQL (AWS RDS)                           │
└───────────────────────────────────┼─────────────────────────────────────┘
                                    │
                              Webhook Push
                                    │
┌───────────────────────────────────┼─────────────────────────────────────┐
│                            AgentScope                                   │
│  ┌─────────┐  ┌─────────┐  ┌───────────────┐  ┌─────────┐  ┌─────────┐ │
│  │  ones/  │  │   aa/   │  │ observability │  │  model/ │  │  agent/ │ │
│  └────┬────┘  └────┬────┘  └───────┬───────┘  └────┬────┘  └────┬────┘ │
│       │            │               │               │            │       │
│       └────────────┴───────────────┴───────────────┴────────────┘       │
│                                                                         │
│         ExecutionLoop → TaskGraph → AssistantOrchestrator              │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 数据流

```
用户需求 → Frontend → Backend API → AgentScope 执行
                ↑                          │
                │                          ↓
           SSE 推送 ←───── 观测数据 ←── WebhookExporter
```

---

## 二、多租户系统 ✅

### 2.1 Tenant 模型 ✅

**文件**: `backend/tenants/models.py`

```python
class Tenant(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    api_key = models.CharField(max_length=64, unique=True)  # hc_xxx

    # 配额
    max_tokens_per_month = models.BigIntegerField(default=500_000)
    max_projects = models.IntegerField(default=10)

    is_active = models.BooleanField(default=True)
```

### 2.2 中间件与 Mixin ✅

| 组件 | 文件 | 功能 |
|------|------|------|
| TenantMiddleware | `tenants/middleware.py` | 从请求解析 Tenant |
| TenantModelMixin | `tenants/mixins.py` | 模型自动关联 Tenant |
| TenantQuerySetMixin | `tenants/mixins.py` | ViewSet 自动过滤 |

### 2.3 测试数据 ✅

```
租户名称: Default Tenant
租户 Slug: default
API Key: hc_2nJ9NMyNbHnoZ82mZrRLI92plU511YtnxSnPNMcRtGE
```

---

## 三、核心 API 模型 ✅

### 3.1 已实现模型 ✅

**文件**: `backend/api/models.py` (436 LOC)

| 模型 | 状态 | 用途 |
|------|------|------|
| Agent | ✅ | 系统级 Agent 资源 |
| Project | ✅ | 租户隔离项目 |
| Conversation | ✅ | 对话会话 |
| Message | ✅ | 聊天消息 |
| Requirement | ✅ | 需求定义 |
| DeliveryStandard | ✅ | 交付标准详情 |
| TeamMember | ✅ | 团队成员 (Agent 分配) |
| Task | ✅ | 项目任务 |
| AgentThinking | ✅ | Agent 思考过程 |
| AgentTaskItem | ✅ | Agent 任务板项目 |
| AgentCollaboration | ✅ | Agent 协作消息 |
| Folder | ✅ | 文件夹 |
| File | ✅ | 文件 |

### 3.2 已实现 ViewSets ✅

**文件**: `backend/api/views.py` (601 LOC)

| ViewSet | 端点 | 特殊 Actions |
|---------|------|-------------|
| AgentViewSet | `/agents/` | - |
| ProjectViewSet | `/projects/` | `stats`, `team`, `tasks`, `file-tree` |
| ConversationViewSet | `/conversations/` | `add_message`, `add_requirement` |
| MessageViewSet | `/messages/` | - |
| RequirementViewSet | `/requirements/` | - |
| DeliveryStandardViewSet | `/delivery-standards/` | - |
| TeamMemberViewSet | `/team-members/` | - |
| TaskViewSet | `/tasks/` | - |
| AgentThinkingViewSet | `/agent-thinkings/` | - |
| AgentTaskItemViewSet | `/agent-task-items/` | - |
| AgentCollaborationViewSet | `/agent-collaborations/` | - |
| FolderViewSet | `/folders/` | 路径递归 |
| FileViewSet | `/files/` | `search`, `previewable` |

---

## 四、可观测性系统 ✅

### 4.1 数据模型 ✅

**文件**: `backend/observability/models.py`

| 模型 | AgentScope 对应 | 用途 |
|------|----------------|------|
| UsageRecord | UsageRecord | LLM 调用 token/成本 |
| ExecutionRecord | AgentExecution | Agent 执行状态 |
| TimelineEvent | TimelineEvent | 时间线事件 |

### 4.2 Ingest APIs ✅

**文件**: `backend/observability/views.py`

| 端点 | 方法 | 状态 |
|------|------|------|
| `/api/v1/observability/ingest/usage/` | POST | ✅ |
| `/api/v1/observability/ingest/execution/` | POST | ✅ |
| `/api/v1/observability/ingest/timeline/` | POST | ✅ |

### 4.3 Query APIs ✅

| 端点 | 方法 | 状态 |
|------|------|------|
| `/api/v1/observability/usage/` | GET | ✅ |
| `/api/v1/observability/usage/summary/` | GET | ✅ |
| `/api/v1/observability/usage/trend/` | GET | ✅ |
| `/api/v1/observability/executions/` | GET | ✅ |
| `/api/v1/observability/executions/active/` | GET | ✅ |
| `/api/v1/observability/timeline/` | GET | ✅ |
| `/api/v1/observability/project/{id}/stats/` | GET | ✅ |
| `/api/v1/observability/stream/` | GET (SSE) | ✅ |

### 4.4 AgentScope 集成 ✅

**文件**: `agentscope/src/agentscope/observability/_webhook.py`

```python
from agentscope.observability import ObservabilityHub, WebhookExporter

hub = ObservabilityHub()
exporter = WebhookExporter(
    api_url="http://localhost:8000/api/v1/observability",
    api_key="hc_xxx"
)
hub.set_webhook(exporter)
```

---

## 五、认证系统 ✅

### 5.1 双认证模式 ✅

**文件**: `backend/authentication/backends.py`

| 认证方式 | 使用场景 | Header |
|----------|---------|--------|
| JWT | Frontend 用户 | `Authorization: Bearer xxx` |
| API Key | AgentScope 推送 | `X-API-Key: hc_xxx` |

### 5.2 Permission Classes ✅

```python
class IsAuthenticatedOrAPIKey(BasePermission):
    """允许 JWT 用户或 API Key 访问"""
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            return True
        if hasattr(request, 'tenant') and request.tenant:
            return True
        return False
```

---

## 六、执行状态管理 ✅

### 6.1 已实现模型 ✅

**文件**: `backend/execution/models.py`

| 模型 | 状态 | 用途 |
|------|------|------|
| ExecutionRound | ✅ | 执行轮次，关联 Celery 任务 |
| ExecutionProgress | ✅ | 实时进度追踪（SSE 用） |
| ExecutionLog | ✅ | 详细执行日志 |
| ExecutionArtifact | ✅ | 生成的代码/配置工件 |
| AgentSelectionDecision | ✅ | AA 系统选择决策 |

### 6.2 已实现 API ✅

| 端点 | 方法 | 说明 | 状态 |
|------|------|------|------|
| `/api/v1/projects/{id}/execute/` | POST | 启动执行 | ✅ |
| `/api/v1/execution/rounds/` | GET | 执行轮次列表 | ✅ |
| `/api/v1/execution/rounds/{id}/` | GET | 轮次详情 | ✅ |
| `/api/v1/execution/rounds/{id}/status/` | GET | 执行状态 + 统计 | ✅ |
| `/api/v1/execution/rounds/{id}/cancel/` | POST | 取消执行 | ✅ |
| `/api/v1/execution/rounds/{id}/agents/` | GET | Agent 选择决策 | ✅ |
| `/api/v1/execution/rounds/{id}/artifacts/` | GET | 生成的工件 | ✅ |
| `/api/v1/execution/rounds/{id}/logs/` | GET | 执行日志 | ✅ |
| `/api/v1/execution/active/` | GET | 当前活动执行 | ✅ |

---

## 七、Agent 选择决策存储 ✅

### 7.1 已实现模型 ✅

**文件**: `backend/execution/models.py`

```python
class AgentSelectionDecision(TenantModelMixin):
    """AA 系统的 Agent 选择决策

    对应 AgentScope 的 SelectionDecision 和 CandidateRanking。
    """
    DECISION_SOURCE_CHOICES = [('system', 'System'), ('user', 'User')]

    execution_round = models.ForeignKey(ExecutionRound, on_delete=models.CASCADE)
    agent = models.ForeignKey('api.Agent', on_delete=models.SET_NULL, null=True)
    agent_name = models.CharField(max_length=100, blank=True)  # 缓存名称

    # 评分详情
    s_base_score = models.FloatField(default=0)
    requirement_fit_score = models.FloatField(default=0)
    total_score = models.FloatField(default=0)
    scoring_breakdown = models.JSONField(default=dict)

    # 需求匹配详情 (RequirementFitBreakdown)
    requirement_fit_matched = models.JSONField(default=dict)   # 匹配的能力
    requirement_fit_missing = models.JSONField(default=dict)   # 缺失的能力
    requirement_fit_partial = models.JSONField(default=dict)   # 部分匹配分数
    requirement_fit_rationales = models.JSONField(default=list)  # 解释

    # 冷启动
    is_cold_start = models.BooleanField(default=False)
    cold_start_slot_reserved = models.BooleanField(default=False)

    # 风险和选择结果
    risk_notes = models.JSONField(default=list)
    is_selected = models.BooleanField(default=False)
    decision_source = models.CharField(max_length=10, choices=DECISION_SOURCE_CHOICES)

    # 排序
    selection_order = models.IntegerField(default=0)  # 排名顺序
    batch_index = models.IntegerField(default=0)
```

### 7.2 与 AgentScope AA 系统对应

| AgentScope 类 | Django 模型/字段 | 说明 | 状态 |
|--------------|-----------------|------|------|
| `SelectionDecision` | `AgentSelectionDecision` | 选择结果 | ✅ |
| `CandidateRanking` | `AgentSelectionDecision` | 候选人排名详情 | ✅ |
| `RequirementFitBreakdown` | `requirement_fit_*` 字段 | 匹配详情 | ✅ |
| `SelectionAuditLog` | 多条 `AgentSelectionDecision` | 审计日志 | ✅ |

### 7.3 API 端点 ✅

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/execution/selections/` | GET | 列出选择决策 |
| `/api/v1/execution/selections/{id}/` | GET | 决策详情 |
| `/api/v1/execution/selections/by_round/` | GET | 按执行轮次分组 |
| `/api/v1/execution/selections/agent_history/` | GET | Agent 选择历史统计 |
| `/api/v1/observability/ingest/agent-selection/` | POST | AgentScope 推送决策 |

### 7.4 前端 API ✅

**文件**: `frontend/src/api/selection.ts`

```typescript
// 类型
export interface AgentSelectionDecision {
  id: string;
  agentName: string;
  sBaseScore: number;
  requirementFitScore: number;
  totalScore: number;
  requirementFitMatched: Record<string, string[]>;
  requirementFitMissing: Record<string, string[]>;
  isSelected: boolean;
  // ...
}

// 函数
export async function listSelections(params?)
export async function getSelection(id)
export async function getSelectionsByRound(projectId)
export async function getAgentSelectionHistory(agentId)
export async function getRankedCandidates(roundId)
```

### 7.5 AgentScope 集成 ⏳

- [x] Ingest 端点已创建
- [ ] AgentScope `AssistantAgentSelector.select()` 后调用 webhook 推送
- [ ] 前端 TeamBuildingPage 展示选择理由和排名

---

## 八、执行工件存储 ✅

### 8.1 已实现模型 ✅

**文件**: `backend/execution/models.py`

```python
class ExecutionArtifact(TenantModelMixin):
    """生成的代码、配置等工件"""
    execution_round = models.ForeignKey(ExecutionRound, on_delete=models.CASCADE)
    artifact_type = models.CharField(max_length=20, choices=[
        ('code', 'Code'),
        ('config', 'Config'),
        ('document', 'Document'),
        ('test', 'Test'),
        ('deliverable', 'Deliverable'),
    ])
    file_path = models.CharField(max_length=500)
    file_name = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    content_hash = models.CharField(max_length=64, blank=True)
    size_bytes = models.IntegerField(default=0)
    language = models.CharField(max_length=50, blank=True)
    s3_key = models.CharField(max_length=500, blank=True)  # S3 存储大文件
    generated_by_agent = models.ForeignKey('api.Agent', null=True)


class ExecutionLog(TenantModelMixin):
    """详细执行日志"""
    execution_round = models.ForeignKey(ExecutionRound, on_delete=models.CASCADE)
    agent = models.ForeignKey('api.Agent', null=True)
    level = models.CharField(max_length=10)  # debug, info, warning, error
    message = models.TextField()
    metadata = models.JSONField(default=dict)
    source = models.CharField(max_length=100, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
```

### 8.2 已实现 API ✅

| 端点 | 方法 | 说明 | 状态 |
|------|------|------|------|
| `/api/v1/execution/rounds/{id}/artifacts/` | GET | 工件列表 | ✅ |
| `/api/v1/execution/rounds/{id}/logs/` | GET | 执行日志 | ✅ |
| `/api/v1/execution/artifacts/` | GET | 全部工件列表 | ✅ |
| `/api/v1/execution/artifacts/{id}/` | GET | 工件详情（含内容） | ✅ |

### 8.3 S3 存储服务 ✅

**文件**: `backend/execution/storage.py`

| 函数 | 功能 |
|------|------|
| `store_artifact_content()` | 自动判断存储位置（DB <100KB, S3 ≥100KB） |
| `get_artifact_content()` | 从 DB 或 S3 获取工件内容 |
| `get_cloudfront_url()` | 获取 CloudFront CDN URL |
| `get_presigned_url()` | 生成 S3 预签名 URL |
| `migrate_artifact_to_s3()` | 迁移工件到 S3 |

### 8.4 工件 API 扩展 ✅

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/execution/artifacts/{id}/content/` | GET | 获取工件内容（DB 或 S3） |
| `/api/v1/execution/artifacts/{id}/download_url/` | GET | 获取下载 URL（S3 预签名） |

### 8.5 工件同步任务 ✅

**文件**: `backend/execution/tasks.py`

| 任务 | 功能 |
|------|------|
| `sync_artifact_from_workspace()` | 从工作空间同步单个工件到存储 |
| `migrate_artifacts_to_s3()` | 批量迁移大工件到 S3 |
| `cleanup_orphan_s3_artifacts()` | 清理 S3 孤儿文件 |

### 8.6 前端工件 API ✅

**文件**: `frontend/src/api/execution.ts`

| 函数 | 功能 |
|------|------|
| `getArtifact()` | 获取工件详情 |
| `getArtifactContent()` | 获取工件内容 |
| `getArtifactDownloadUrl()` | 获取下载 URL |
| `downloadArtifact()` | 下载工件（自动处理 DB/S3） |

---

## 九、项目决策存储 ✅

### 9.1 已实现模型 ✅

**文件**: `backend/api/models.py`

| 模型 | 说明 |
|------|------|
| `ProjectDecision` | 项目技术决策记录（8 种类型） |
| `ProjectFileRegistry` | 项目文件注册表 |

**决策类型**: tech_stack, architecture, file_structure, api_design, component, constraint, dependency, tooling

### 9.2 已实现 API ✅

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/decisions/` | GET | 决策列表（支持 project/category 过滤） |
| `/api/v1/decisions/{id}/` | GET | 决策详情 |
| `/api/v1/decisions/` | POST | 创建决策（自动 supersede 旧决策） |
| `/api/v1/file-registry/` | GET/POST | 文件注册表 |
| `/api/v1/projects/{id}/context/` | GET | 完整项目上下文（含 prompt） |

### 9.3 Ingest 端点 ✅

**文件**: `backend/observability/views.py`

| 端点 | 说明 |
|------|------|
| `POST /api/v1/observability/ingest/decision/` | AgentScope 推送决策 |
| `POST /api/v1/observability/ingest/file-registry/` | AgentScope 推送文件注册 |

### 9.4 前端 API ✅

**文件**: `frontend/src/api/decision.ts`

| 函数 | 说明 |
|------|------|
| `listDecisions()` | 列出决策 |
| `getProjectDecisions()` | 获取项目决策 |
| `getDecisionsByCategory()` | 按类别分组 |
| `getProjectContext()` | 获取完整上下文 |
| `getCategoryLabel()` | 类别中文标签 |

### 9.5 与 AgentScope Memory 对应 ✅

| AgentScope | Django | 状态 |
|------------|--------|------|
| `ProjectMemory.record_decision()` | `ProjectDecision` | ✅ |
| `ProjectMemory.register_file()` | `ProjectFileRegistry` | ✅ |
| `ProjectMemory.get_context_for_prompt()` | `/projects/{id}/context/` | ✅ |

---

## 9.5 AA 对话接口 ✅

### 9.5.1 功能概述

实现了 AA (Assistant Agent) 对话接口，支持：
1. 用户与 AA 的实时对话
2. 从对话中自动提取需求和交付标准
3. 每轮对话自动更新需求列表

### 9.5.2 后端实现

**文件**: `backend/api/chat_service.py`

```python
class AAChatService:
    """LLM 对话服务"""
    async def chat(conversation_history, user_message) -> ChatResponse
    # 返回 AA 回复 + 提取的需求

class RequirementExtractor:
    """需求提取服务"""
    async def extract(messages) -> list[ExtractedRequirement]
    # 从对话历史中提取所有需求
```

### 9.5.3 API 端点 ✅

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/conversations/{id}/chat/` | POST | 与 AA 对话，自动提取需求 |
| `/api/v1/conversations/{id}/extract_requirements/` | POST | 重新分析对话，提取所有需求 |

### 9.5.4 请求/响应格式

```typescript
// 请求
POST /conversations/{id}/chat/
{ "content": "用户消息" }

// 响应
{
  "user_message": { id, type: "user", content, createdAt },
  "assistant_message": { id, type: "assistant", content, createdAt },
  "requirements_created": [...],   // 新创建的需求
  "requirements_updated": [...]    // 更新的需求
}
```

### 9.5.5 前端 API ✅

**文件**: `frontend/src/api/conversation.ts`

```typescript
export interface ChatResponse {
  userMessage: Message;
  assistantMessage: Message;
  requirementsCreated: Requirement[];
  requirementsUpdated: Requirement[];
}

export async function chat(conversationId: number, content: string): Promise<ChatResponse>
export async function extractRequirements(conversationId: number): Promise<Requirement[]>
```

### 9.5.6 使用示例

```typescript
import { chat, extractRequirements } from '@/api';

// 发送消息并自动提取需求
const response = await chat(conversationId, "我需要一个登录页面");
console.log(response.assistantMessage.content);  // AA 回复
console.log(response.requirementsCreated);        // 新提取的需求

// 手动触发需求重新提取
const requirements = await extractRequirements(conversationId);
```

---

## 十、待实现：实时推送 (Redis SSE) ⏳

### 10.1 当前状态

- SSE 端点已实现: `/api/v1/observability/stream/`
- 当前 fallback 到心跳模式
- 需要配置 Redis 启用实时推送

### 10.2 需要的配置

```python
# settings.py
REDIS_URL = "redis://elasticache-host:6379/0"

# 或使用 Django Channels
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("elasticache-host", 6379)],
        },
    },
}
```

### 10.3 事件类型

| 事件 | 触发时机 | 数据 |
|------|---------|------|
| `execution_started` | 执行开始 | round_id, project_id |
| `agent_started` | Agent 开始工作 | agent_name, task |
| `agent_completed` | Agent 完成 | agent_name, output |
| `usage_recorded` | Token 使用 | tokens, cost |
| `artifact_created` | 工件生成 | file_path, type |
| `round_completed` | 轮次完成 | summary, stats |

---

## 十一、Frontend API 需求对照 ✅

### 11.1 已满足的 API

| Frontend 模块 | API 端点 | 状态 |
|--------------|---------|------|
| agent.ts | `/agents/`, `/agent-thinkings/`, `/agent-task-items/`, `/agent-collaborations/` | ✅ |
| project.ts | `/projects/`, `/projects/{id}/stats/`, `/projects/{id}/team/`, `/projects/{id}/tasks/`, `/projects/{id}/file-tree/` | ✅ |
| conversation.ts | `/conversations/`, `/messages/`, `/conversations/{id}/add_message/`, `/conversations/{id}/add_requirement/` | ✅ |
| requirement.ts | `/requirements/`, `/delivery-standards/` | ✅ |
| task.ts | `/tasks/` | ✅ |
| file.ts | `/folders/`, `/files/`, `/files/search/`, `/files/previewable/` | ✅ |

### 11.2 新增的 API ✅

| Frontend 需求 | API 端点 | 状态 |
|--------------|---------|------|
| 执行启动 | `/projects/{id}/execute/` | ✅ |
| 执行轮次 | `/execution/rounds/` | ✅ |
| 执行状态 | `/execution/rounds/{id}/status/` | ✅ |
| 取消执行 | `/execution/rounds/{id}/cancel/` | ✅ |
| 工件查看 | `/execution/artifacts/` | ✅ |
| 执行日志 | `/execution/rounds/{id}/logs/` | ✅ |
| Agent 决策 | `/execution/rounds/{id}/agents/` | ✅ |
| 活动执行 | `/execution/active/` | ✅ |
| 实时更新 | WebSocket / SSE | ⏳ (SSE 框架已有) |

---

## 十二、AgentScope 模块对应 ✅

### 12.1 ones/ 模块

| AgentScope 模块 | Backend 支持 | 状态 |
|----------------|-------------|------|
| ExecutionLoop | ExecutionRound | ✅ |
| TaskGraphBuilder | Task | ✅ |
| AssistantOrchestrator | AgentSelectionDecision | ✅ |
| MemoryPool | ProjectDecision | ⏳ |
| KPITracker | UsageRecord | ✅ |
| AcceptanceAgent | DeliveryStandard | ✅ |

### 12.2 aa/ 模块

| AgentScope 模块 | Backend 支持 | 状态 |
|----------------|-------------|------|
| AssistantAgentSelector | AgentSelectionDecision | ✅ 模型已创建 |
| RequirementFitScorer | AgentSelectionDecision.scoring_breakdown | ✅ 模型已创建 |
| SelectionAuditLog | AgentSelectionDecision | ✅ 模型已创建 |

### 12.3 observability/ 模块

| AgentScope 模块 | Backend 支持 | 状态 |
|----------------|-------------|------|
| UsageRecord | observability.UsageRecord | ✅ |
| AgentExecution | observability.ExecutionRecord | ✅ |
| TimelineEvent | observability.TimelineEvent | ✅ |
| WebhookExporter | Ingest APIs | ✅ |

### 12.4 scripts/_observability.py 模块

| Observer 类 | Webhook 支持 | 状态 |
|------------|--------------|------|
| LLMObserver | `_record_usage()` | ✅ |
| ExecutionObserver | `_record_timeline_event()` | ✅ |
| CLIObserver | `_record_timeline_event()` | ✅ |

---

## 十三、实现文件清单

### 13.1 已完成文件 ✅

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
├── api/                                  ✅ 已有
│   ├── models.py                         ✅ 13 个核心模型
│   ├── views.py                          ✅ 13 个 ViewSets
│   ├── serializers.py                    ✅ 所有序列化器
│   └── urls.py                           ✅
└── backend/
    ├── settings.py                       ✅ 已更新
    └── urls.py                           ✅ 已更新

agentscope/src/agentscope/observability/
├── __init__.py                           ✅ 已更新
├── _hub.py                               ✅ 已更新
└── _webhook.py                           ✅ 新增
```

### 13.2 新增的执行模块文件 ✅

```
backend/execution/                        ✅ 新增
├── __init__.py                           ✅
├── admin.py                              ✅
├── apps.py                               ✅
├── models.py                             ✅ ExecutionRound, ExecutionProgress, ExecutionLog,
│                                            ExecutionArtifact, AgentSelectionDecision
├── serializers.py                        ✅ 所有序列化器
├── views.py                              ✅ ExecutionRoundViewSet, ProjectExecuteView,
│                                            ExecutionArtifactViewSet, ActiveExecutionsView
├── urls.py                               ✅
├── tasks.py                              ✅ Celery 任务 execute_project_task
├── runner.py                             ✅ run_execution_for_api()
└── migrations/
    └── 0001_initial.py                   ✅

backend/backend/
├── celery.py                             ✅ 新增 Celery 配置
├── __init__.py                           ✅ 更新：加载 celery_app
├── settings.py                           ✅ 更新：CELERY_*, EXECUTION_* 配置
└── urls.py                               ✅ 更新：execution routes

backend/requirements.txt                  ✅ 更新：添加 celery>=5.3

agentscope/src/agentscope/scripts/
└── _observability.py                     ✅ 更新：Observer webhook 集成
```

### 13.3 实时通信模块文件 ✅

```
backend/observability/
└── pubsub.py                             ✅ 新增 Redis pub/sub 工具模块
    - publish_event()
    - publish_execution_progress()
    - publish_agent_event()
    - publish_artifact_event()
    - subscribe_events()
    - subscribe_execution()

backend/execution/
├── sse.py                                ✅ 新增 SSE 视图
│   - ExecutionSSEView
│   - ActiveExecutionsSSEView
└── urls.py                               ✅ 更新：添加 SSE 路由

frontend/src/api/
├── execution.ts                          ✅ 新增 执行 API 和 SSE 订阅
│   - startExecution()
│   - getExecutionStatus()
│   - subscribeToExecution()
│   - subscribeToActiveExecutions()
└── index.ts                              ✅ 更新：导出 execution API

frontend/src/hooks/
└── useExecutionStream.ts                 ✅ 新增 React Hook
```

### 13.4 待实现文件 ⏳

```
backend/
├── channels/                             ⏳ WebSocket 支持 (可选)
│   ├── __init__.py
│   ├── consumers.py
│   └── routing.py
└── requirements.txt                      ⏳ 添加 channels, channels-redis (如需 WebSocket)
```

---

## 十四、实现优先级

### Phase 1 - 核心执行追踪 (P0) ✅ 已完成

- [x] 添加 `ExecutionRound` 模型
- [x] 添加 `ExecutionProgress` 模型
- [x] 添加 `AgentSelectionDecision` 模型
- [x] 添加 `ExecutionArtifact` 模型
- [x] 添加 `ExecutionLog` 模型
- [x] 实现 `/projects/{id}/execute/` API
- [x] 实现 `/execution/rounds/` ViewSet
- [x] 实现 Celery 后台任务 `execute_project_task`
- [x] 创建 `run_execution_for_api()` 封装函数
- [x] 改造 Observer 类支持 webhook 推送

### Phase 2 - 工件和日志 (P1) ⏳ 模型已就绪

- [x] 添加 `ExecutionArtifact` 模型
- [x] 添加 `ExecutionLog` 模型
- [x] 实现 `/artifacts/` ViewSet
- [ ] 集成 S3 存储大文件
- [ ] AgentScope 执行完成后同步工件

### Phase 3 - 实时通信 (P1) ✅

- [x] 配置 Redis pub/sub 模块 (`observability/pubsub.py`)
- [x] 实现 SSE 端点 (`execution/sse.py`)
- [x] 前端 SSE 订阅 (`frontend/src/api/execution.ts`)
- [x] React hook (`frontend/src/hooks/useExecutionStream.ts`)

### Phase 4 - 工件存储 (P1) ✅

- [x] S3 存储服务 (`execution/storage.py`)
- [x] 工件 API 扩展 (`content/`, `download_url/`)
- [x] 工件同步任务 (`sync_artifact_from_workspace`)
- [x] 前端工件加载

### Phase 5 - 决策和历史 (P2) ⏳

- [ ] 添加 `ProjectDecision` 模型
- [ ] 实现配额检查
- [ ] 实现执行历史查询和重放

---

## 十五、部署配置 ✅

### 15.1 环境变量

```bash
# .env
DATABASE_URL=postgres://user:pass@rds-host:5432/dbname
REDIS_URL=redis://elasticache-host:6379/0  # 可选
SECRET_KEY=your-django-secret-key
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_S3_BUCKET=xxx
```

### 15.2 数据库迁移

```bash
cd backend
python manage.py migrate tenants
python manage.py migrate observability
python manage.py migrate api
```

---

## 十六、版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2025-12-30 | MVP: 多租户、可观测性、核心 API |
| 1.1.0 | 2025-12-30 | 执行集成: ExecutionRound、Celery、Observer webhook |
| 1.2.0 | 2025-12-30 | 实时通信: Redis pub/sub、SSE 端点、前端订阅 |
| 1.3.0 | 2025-12-30 | 工件存储: S3 服务、工件 API、同步任务、前端加载 |
| 1.4.0 | - | 计划: 项目决策存储 |
| 1.5.0 | - | 计划: 配额检查、执行历史查询 |

---

## 十七、前端流程与 AgentScope CLI 对照分析 ⚠️

### 17.1 前端用户流程

```
┌─────────────┐    ┌──────────────────┐    ┌────────────────┐    ┌──────────────┐
│  HomePage   │ →  │ TeamBuildingPage │ →  │ MonitoringPage │ →  │    Work      │
│  输入需求   │    │   确认需求/团队   │    │   项目监控     │    │  查看文件    │
└─────────────┘    └──────────────────┘    └────────────────┘    └──────────────┘
      │                    │                       │                    │
      ↓                    ↓                       ↓                    ↓
  conversationApi      projectApi            projectApi.stats       fileApi
  requirementApi       agentApi              teamMemberApi          folderApi
                       teamMemberApi         taskApi
```

**页面功能详情：**

| 页面 | 文件 | 功能 | 调用的 API |
|------|------|------|-----------|
| HomePage | `HomePage.tsx` | 输入需求，对话澄清 | `conversationApi`, `requirementApi` |
| TeamBuildingPage | `TeamBuildingPage.tsx` | Agent 推荐，团队配置 | `projectApi`, `agentApi`, `teamMemberApi` |
| MonitoringPage | `MonitoringPage.tsx` | 实时进度，成员状态 | `projectApi.getProjects()` |
| Work | `Work.tsx` | 文件树，交付物预览 | `fileApi.getFileTree()`, `fileApi.getPreviewFiles()` |

### 17.2 AgentScope CLI 流程 (full_user_flow_cli.py)

```
run_cli()
    │
    ├── 1. init_observability()        # 初始化日志/追踪
    ├── 2. initialize_llm()            # 初始化 LLM
    ├── 3. collect_spec()              # 需求收集和澄清
    ├── 4. enrich_acceptance_map()     # 丰富验收标准
    ├── 5. initialize_mcp_clients()    # 初始化 MCP 工具
    ├── 6. RuntimeWorkspace.start()    # 启动 Docker 容器
    ├── 7. build_runtime_harness()     # 构建执行环境
    ├── 8. aa_agent.reply()            # AA Agent 规划团队
    ├── 9. run_execution()             # 多轮执行
    │       ├── design_requirement()
    │       ├── implement_requirement()
    │       └── qa_requirement()
    └── 10. cleanup                    # 清理资源
```

### 17.3 关键差异对照 ⚠️

| 对比项 | 前端期望 | CLI 现状 | 差距 |
|--------|---------|---------|------|
| **执行模式** | 异步 + 实时更新 | 同步阻塞 | ❌ 严重 |
| **状态持久化** | 数据库存储 | 内存中，无持久化 | ❌ 严重 |
| **进度反馈** | SSE/WebSocket 推送 | stdout 打印 | ❌ 严重 |
| **中间结果** | 可随时查询 | 执行完才有结果 | ❌ 严重 |
| **错误恢复** | 可从断点继续 | 失败需重新开始 | ⚠️ 中等 |
| **多用户** | 租户隔离 | 单用户 CLI | ⚠️ 中等 |
| **资源隔离** | 按项目隔离 | 全局共享 | ⚠️ 中等 |

### 17.4 CLI 不能直接使用的原因

**1. 阻塞式长时间执行**
```python
# full_user_flow_cli.py:118-144
async def run_cli(
    initial_requirement: str,
    ...
) -> None:
    # 这个函数会执行数分钟到数小时
    # 期间无法返回中间状态给前端
```

**2. 无结构化返回值**
```python
# run_cli() 返回 None，只打印到 stdout
# 前端无法获取执行结果
```

**3. 硬编码的本地路径**
```python
# full_user_flow_cli.py:226
workspace_dir = DELIVERABLE_DIR / "workspace"
# 所有用户共享同一个 workspace，无法多租户
```

**4. 无进度回调机制**
```python
# 进度信息直接打印
cli_obs.on_deliverables_header()
cli_obs.on_deliverable(rid, str(path.resolve()))
# 前端无法订阅这些事件
```

---

## 十八、AgentScope 集成方案 ⏳

### 18.1 方案选择

| 方案 | 复杂度 | 实时性 | 推荐 |
|------|--------|--------|------|
| **A. 封装为后台任务** | 低 | 中 | ✅ MVP 推荐 |
| B. 拆分为微服务 | 高 | 高 | 后期优化 |
| C. 重构为事件驱动 | 极高 | 极高 | 理想但工作量大 |

### 18.2 方案 A：封装为后台任务（推荐）

**架构：**
```
Frontend                Backend                    AgentScope
   │                       │                           │
   │ POST /execute/        │                           │
   │──────────────────────>│                           │
   │                       │ 创建 ExecutionRound       │
   │                       │ 启动 Celery Task          │
   │ 202 Accepted          │──────────────────────────>│
   │<──────────────────────│                           │
   │                       │                           │
   │ GET /stream/ (SSE)    │      Webhook 回调         │
   │──────────────────────>│<──────────────────────────│
   │     实时进度          │                           │
   │<──────────────────────│                           │
```

**需要创建的组件：**

```python
# backend/execution/tasks.py (新增)

from celery import shared_task
from agentscope.scripts.full_user_flow_cli import run_cli

@shared_task(bind=True)
def execute_project_task(self, project_id, requirement, options):
    """后台执行项目任务"""
    from execution.models import ExecutionRound
    from observability.views import IngestUsageView

    # 1. 创建执行轮次
    round = ExecutionRound.objects.create(
        project_id=project_id,
        status='running',
    )

    # 2. 配置 WebhookExporter
    from agentscope.observability import ObservabilityHub, WebhookExporter
    hub = ObservabilityHub()
    exporter = WebhookExporter(
        api_url=f"{settings.INTERNAL_API_URL}/api/v1/observability",
        api_key=get_project_api_key(project_id),
        # 添加 execution_round_id 用于关联
        extra_headers={'X-Execution-Round': str(round.id)},
    )
    hub.set_webhook(exporter)

    # 3. 执行（需要修改 run_cli 使其可被调用）
    try:
        import asyncio
        result = asyncio.run(run_cli_for_api(
            initial_requirement=requirement,
            project_id=str(project_id),
            **options,
        ))

        # 4. 更新执行状态
        round.status = 'completed'
        round.summary = result.get('summary', '')
        round.save()

    except Exception as e:
        round.status = 'failed'
        round.error_message = str(e)
        round.save()
        raise

    return {'round_id': str(round.id)}
```

### 18.3 需要修改的 AgentScope 代码 ⏳

**1. 创建 API 版本的执行函数**

```python
# agentscope/scripts/_api_execution.py (新增)

async def run_cli_for_api(
    initial_requirement: str,
    project_id: str,
    tenant_api_key: str,
    backend_url: str,
    **options,
) -> dict:
    """API 可调用的执行函数

    与 run_cli 的区别：
    1. 返回结构化结果而非 None
    2. 不直接打印，通过 WebhookExporter 推送
    3. 支持自定义 workspace 路径（按项目隔离）
    4. 支持中断和恢复
    """
    # 设置项目级 workspace
    workspace_dir = Path(f"/workspaces/{project_id}")
    workspace_dir.mkdir(parents=True, exist_ok=True)

    # 配置 WebhookExporter
    from agentscope.observability import ObservabilityHub, WebhookExporter
    hub = ObservabilityHub()
    exporter = WebhookExporter(
        api_url=f"{backend_url}/api/v1/observability",
        api_key=tenant_api_key,
    )
    hub.set_webhook(exporter)

    # ... 执行逻辑（复用 run_cli 的核心代码）

    # 返回结构化结果
    return {
        'status': 'completed',
        'deliverables': deliverables_dict,
        'summary': summary_text,
        'rounds': rounds_data,
        'total_cost': total_cost,
        'total_tokens': total_tokens,
    }
```

**2. 添加进度回调机制**

```python
# agentscope/scripts/_observability.py (修改)

class CLIObserver:
    """CLI 观察者 - 需要添加 webhook 支持"""

    def __init__(self):
        self._webhook: WebhookExporter | None = None

    def set_webhook(self, webhook: WebhookExporter):
        self._webhook = webhook

    def on_round_start(self, round_index: int, total_rounds: int):
        """轮次开始"""
        if self._webhook:
            self._webhook.push_progress({
                'event': 'round_start',
                'round_index': round_index,
                'total_rounds': total_rounds,
            })

    def on_agent_start(self, agent_name: str, task: str):
        """Agent 开始执行"""
        if self._webhook:
            self._webhook.push_progress({
                'event': 'agent_start',
                'agent_name': agent_name,
                'task': task,
            })

    def on_artifact_created(self, file_path: str, artifact_type: str):
        """工件创建"""
        if self._webhook:
            self._webhook.push_progress({
                'event': 'artifact_created',
                'file_path': file_path,
                'artifact_type': artifact_type,
            })
```

### 18.4 Backend 需要新增的 API ⏳

```python
# backend/api/views.py (新增)

class ProjectExecuteView(APIView):
    """启动项目执行

    POST /api/v1/projects/{id}/execute/
    """
    permission_classes = [IsAuthenticatedOrAPIKey]

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        tenant = request.tenant

        # 验证权限
        if project.tenant != tenant:
            return Response({'error': 'Forbidden'}, status=403)

        # 获取执行参数
        requirement = request.data.get('requirement', '')
        options = {
            'max_rounds': request.data.get('max_rounds', 3),
            'use_parallel_execution': request.data.get('parallel', True),
            'use_pr_mode': request.data.get('pr_mode', True),
        }

        # 启动后台任务
        from execution.tasks import execute_project_task
        task = execute_project_task.delay(
            project_id=str(project.id),
            requirement=requirement,
            options=options,
        )

        # 创建执行轮次记录
        round = ExecutionRound.objects.create(
            project=project,
            celery_task_id=task.id,
            status='pending',
        )

        return Response({
            'execution_round_id': str(round.id),
            'task_id': task.id,
            'status': 'started',
        }, status=202)


class ExecutionStatusView(APIView):
    """获取执行状态

    GET /api/v1/execution-rounds/{id}/status/
    """
    permission_classes = [IsAuthenticatedOrAPIKey]

    def get(self, request, pk):
        round = get_object_or_404(ExecutionRound, pk=pk)

        # 获取关联的观测数据
        usage_stats = UsageRecord.objects.filter(
            execution_round=round
        ).aggregate(
            total_tokens=Sum('total_tokens'),
            total_cost=Sum('cost_usd'),
        )

        return Response({
            'id': str(round.id),
            'status': round.status,
            'round_number': round.round_number,
            'started_at': round.started_at.isoformat(),
            'completed_at': round.completed_at.isoformat() if round.completed_at else None,
            'summary': round.summary,
            'error_message': round.error_message,
            'usage': {
                'total_tokens': usage_stats['total_tokens'] or 0,
                'total_cost_usd': float(usage_stats['total_cost'] or 0),
            },
        })
```

### 18.5 前端需要的修改

**1. 添加执行 API 调用**
```typescript
// frontend/src/api/execution.ts (新增)

export interface ExecutionOptions {
  requirement: string;
  maxRounds?: number;
  parallel?: boolean;
  prMode?: boolean;
}

export interface ExecutionResponse {
  executionRoundId: string;
  taskId: string;
  status: 'started';
}

export async function startExecution(
  projectId: number,
  options: ExecutionOptions
): Promise<ExecutionResponse> {
  const response = await apiClient.post(
    `/projects/${projectId}/execute/`,
    options
  );
  return response.data;
}

export async function getExecutionStatus(roundId: string) {
  const response = await apiClient.get(
    `/execution-rounds/${roundId}/status/`
  );
  return response.data;
}
```

**2. 修改 TeamBuildingPage 启动执行**
```typescript
// TeamBuildingPage.tsx 中
const handleStartProject = useCallback(async () => {
  try {
    // 创建项目（如果还没有）
    const project = await projectApi.createProject({
      name: '新项目',
      requirements: requirements.map(r => r.content),
    });

    // 启动执行
    const execution = await startExecution(project.id, {
      requirement: messages.map(m => m.content).join('\n'),
      maxRounds: 3,
    });

    // 跳转到监控页，传递执行 ID
    navigate('/monitoring', {
      state: {
        projectId: project.id,
        executionRoundId: execution.executionRoundId,
      },
    });
  } catch (error) {
    console.error('启动项目失败:', error);
  }
}, [messages, requirements, navigate]);
```

**3. MonitoringPage 订阅实时更新**
```typescript
// MonitoringPage.tsx 中
useEffect(() => {
  if (!executionRoundId) return;

  // 订阅 SSE
  const eventSource = new EventSource(
    `/api/v1/observability/stream/?round=${executionRoundId}`
  );

  eventSource.addEventListener('agent_start', (event) => {
    const data = JSON.parse(event.data);
    // 更新 Agent 状态
    updateAgentStatus(data.agent_name, 'Working');
  });

  eventSource.addEventListener('artifact_created', (event) => {
    const data = JSON.parse(event.data);
    // 添加到文件列表
    addArtifact(data.file_path, data.artifact_type);
  });

  eventSource.addEventListener('round_complete', (event) => {
    const data = JSON.parse(event.data);
    // 更新进度
    setProgress(data.progress);
  });

  return () => eventSource.close();
}, [executionRoundId]);
```

---

## 十九、实现路线图

### Phase 0 - 基础设施 ✅

- [x] 多租户系统 (tenants app)
- [x] 可观测性 API (observability app)
- [x] 核心模型 (api app)
- [x] WebhookExporter (agentscope)

### Phase 1 - 执行集成 (P0) ✅ 已完成

- [x] 创建 `ExecutionRound` 模型
- [x] 创建 `ExecutionProgress` 模型
- [x] 创建 `AgentSelectionDecision` 模型
- [x] 创建 `ExecutionArtifact` 模型
- [x] 创建 `ExecutionLog` 模型
- [x] 创建 `run_execution_for_api()` 封装函数
- [x] 添加 Celery 后台任务 `execute_project_task`
- [x] 实现 `/projects/{id}/execute/` API
- [x] 实现 `/execution/rounds/` ViewSet
- [x] 修改 Observer 类支持 webhook 推送
    - [x] `_record_timeline_event()` 辅助函数
    - [x] `_record_usage()` 辅助函数
    - [x] `LLMObserver.on_call_success()` 集成
    - [x] `ExecutionObserver.on_round_start()` 集成
    - [x] `ExecutionObserver.on_requirement_start/complete()` 集成
    - [x] `CLIObserver.on_deliverable()` 集成

### Phase 2 - 实时通信 (P1) ✅ 已完成

- [x] 配置 Redis（已有 REDIS_URL 配置）
- [x] 创建 `observability/pubsub.py` 统一 pub/sub 模块
- [x] 实现 `publish_event()`, `publish_execution_progress()` 等函数
- [x] 创建 `execution/sse.py` SSE 端点
    - [x] `ExecutionSSEView` - 单个执行轮次的实时流
    - [x] `ActiveExecutionsSSEView` - 所有活动执行的实时流
- [x] 更新 Celery task 推送进度事件
- [x] 创建前端订阅代码
    - [x] `frontend/src/api/execution.ts` - 执行 API 和 SSE 订阅
    - [x] `frontend/src/hooks/useExecutionStream.ts` - React Hook

### Phase 3 - 工件存储 (P1) ✅ 已完成

- [x] 创建 `ExecutionArtifact` 模型
- [x] S3 存储服务 (`execution/storage.py`)
    - [x] `store_artifact_content()` 自动判断存储位置
    - [x] `get_artifact_content()` 获取内容
    - [x] `get_cloudfront_url()` CDN URL
    - [x] `get_presigned_url()` 预签名 URL
- [x] 工件 API 扩展
    - [x] `/artifacts/{id}/content/` 获取内容
    - [x] `/artifacts/{id}/download_url/` 获取下载 URL
- [x] 工件同步任务
    - [x] `sync_artifact_from_workspace()` 同步工件
    - [x] `migrate_artifacts_to_s3()` 批量迁移
    - [x] `cleanup_orphan_s3_artifacts()` 清理孤儿
- [x] 前端工件加载
    - [x] `getArtifact()`, `getArtifactContent()`
    - [x] `getArtifactDownloadUrl()`, `downloadArtifact()`

### Phase 4 - 完善集成 (P2) ⏳

- [x] Agent 选择决策存储（模型已创建）
- [ ] 项目决策存储
- [ ] 执行历史查询
- [ ] 错误恢复机制

---

## 二十、参考文档

| 文档 | 位置 |
|------|------|
| AgentScope ones/ | `agentscope/src/agentscope/ones/` |
| AgentScope aa/ | `agentscope/src/agentscope/aa/` |
| AgentScope CLI | `agentscope/src/agentscope/scripts/full_user_flow_cli.py` |
| Frontend API 类型 | `frontend/src/api/types.ts` |
| Frontend 页面 | `frontend/src/pages/` |
| Django Models | `backend/api/models.py` |
| 可观测性详细方案 | `backend/OBSERVABILITY_ADAPTATION_PLAN.md` |
