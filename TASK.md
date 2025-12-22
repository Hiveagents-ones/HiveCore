# HiveCore / AgentScope 总任务板（Master TASK.md · v2 · merged）

> 目标：把「一句话需求 → 岗位 → 选人 → 执行 → 验收 → 复盘」的白板流程，和当前已有的 HiveCore 骨架测试任务**整合**成一份可执行、可回归的总任务板。  
> 范围：HiveCore + AgentScope 主库 / runtime / studio 集成。

---

## 0. 使用约定

- **里程碑（Milestone）**
  - M0：基础骨架 & 最小可运行 Demo（含骨架验证脚本）
  - M1：选人/评分/Top5/顺延/Override & 基础流水线
  - M2：Runtime 沙箱 / 治理 / 审计 / 失败矩阵 / 可观测性
  - M3：模板化 / 画像更新 / 文档 & Demo & 产品化

- **优先级**
  - P0：必须完成；阻塞后续
  - P1：重要；影响主要能力
  - P2：增强；可延后

- **状态**
  - TODO / DOING / DONE / BLOCKED

每个任务项格式：

- `[状态] [ID]（里程碑 / 优先级） 标题`
  - 目标：
  - 产出：
  - 依赖：
  - 验收标准：

---

## 1. 基础设施 & 里程碑（M0）

### 1.1 仓库骨架 & 目录结构

- [TODO] A1（M0 / P0）建立 HiveCore 目录结构
  - 目标：为 HiveCore 拆出清晰模块目录，便于后续按模块实现。
  - 产出：
    - `/hivecore/core`：AA、Selector、Orchestrator、TaskGraph、KPI
    - `/hivecore/memory`：AAMemoryStore、摘要、画像
    - `/hivecore/runtime`：Sandbox、Quota、审计、Trace Hook
    - `/hivecore/msg`：MsgHub Broadcaster、Registry、Schema
    - `/hivecore/governance`：StateSync、ConflictResolver、GovLog
    - `/hivecore/templates`：项目模板 & 复用
    - `/hivecore/docs`：README / 设计文档
    - `/hivecore/examples`：Demo & 回归数据
  - 依赖：无
  - 验收标准：目录创建完毕，有基础 `__init__.py` / README 占位。

- [DONE] A2（M0 / P0）配置基础 CI（测试 + Lint）
  - 目标：确保合并前自动跑单测 & Lint。
  - 产出：GitHub Actions / CI 配置，包含：
    - 安装依赖
    - 运行单测（pytest）
    - 代码风格检查（ruff/flake8 等）
  - 依赖：项目基础依赖列表
  - 验收标准：PR 提交后自动触发 CI；失败无法合并。

---

## 2. 需求接收 & 项目上下文（白板步骤 1）

### 2.1 需求模型 & 存储

- [TODO] B1（M0 / P0）定义 Requirement 模型
  - 目标：把“一句话需求”结构化存储。
  - 产出：
    - `Requirement` 数据结构：
      - `id`、`trace_id`
      - `goal`、`constraints[]`
      - `acceptance`（验收口径）
      - `priority`、`deadline`
      - `created_by`、`created_at`
  - 依赖：无
  - 验收标准：可创建/读取 Requirement；单元测试覆盖正常/异常输入。

- [TODO] B2（M0 / P0）实现 `/intake/requirement` 接口
  - 目标：提供统一入口接收用户需求。
  - 产出：
    - API：`POST /intake/requirement`
      - 请求：自然语言需求 + 可选结构字段
      - 响应：`requirement_id` + `trace_id`
    - 参数校验 & 错误码设计
  - 依赖：B1
  - 验收标准：E2E 流程中可通过此接口创建需求；错误输入返回合理错误。

### 2.2 项目上下文 & MsgHub 事件

- [TODO] B3（M0 / P1）定义 ProjectContext 结构
  - 目标：集中存储项目上下文（需求、画像、历史摘要等）。
  - 产出：
    - `ProjectContext` 结构：
      - `project_id`、`requirement_id`
      - `user_profile_ref`
      - `history_summary_ref`
      - `assets_refs[]`
  - 依赖：B1
  - 验收标准：可为新项目创建 ProjectContext 并通过 ID 查询。

- [TODO] B4（M1 / P1）实现 REQ.CREATED 事件广播
  - 目标：新需求创建时向 MsgHub 广播事件。
  - 产出：
    - 事件类型：`REQ.CREATED`
    - 事件结构：`trace_id`、`requirement_id`、`project_id`（如已有）、时间戳
  - 依赖：B2、MsgHub 基础（见 F1 / 12.5）
  - 验收标准：创建需求后，可在 MsgHub 订阅端收到事件。

---

## 3. 需求分解 → 岗位（Role）& TaskGraph（白板步骤 2）

### 3.1 Role 与 TaskGraph 基础模型

- [TODO] C1（M0 / P0）定义 Role 模型
  - 目标：描述“岗位/角色”的能力需求。
  - 产出：
    - `Role` 结构：
      - `id`、`project_id`
      - `name`、`description`
      - `skills[]`
      - `kpi`（预期指标：质量/时效/成本）
  - 依赖：B3
  - 验收标准：可为项目创建多个 Role；单元测试覆盖。

- [DONE] C2（M0 / P0）定义 Task & TaskGraph 模型
  - 目标：支持 Plan → Assign → Execute → Review → Accept 的 DAG。
  - 产出：
    - `Task` 结构：
      - `id`、`role_id`
      - `state`（plan/assign/execute/review/accept）
      - `inputs`、`outputs`
      - `logs_ref`、`acceptance_result`
    - `TaskGraph`：
      - 节点集合、依赖关系（有向无环）
  - 依赖：C1
  - 验收标准：能创建简单 DAG（串行 + 并行 + 条件分支），有单测。

### 3.2 需求分解接口

- [TODO] C3（M1 / P0）实现 `/aa/plan/decompose` 接口（Stub + 插桩）
  - 目标：将 Requirement 转为 Role + TaskGraph 初稿。
  - 产出：
    - API：`POST /aa/plan/decompose { requirement_id }`
    - 当前可返回模拟/简单规则结果（后续接 LLM）
  - 依赖：B1、C1、C2
  - 验收标准：对给定 Requirement，可得到包含 1–3 个 Role + TaskGraph 的结果。

---

## 4. 评分体系：ScoreCard & DemandFit & Top5（白板步骤 3–6）

### 4.1 CandidateAgent & 静态评分（ScoreCard）

- [DONE] D1（M1 / P0）定义 CandidateAgent 模型
  - 目标：描述候选 Agent 的静态信息。
  - 产出：
    - `CandidateAgent`：
      - `id`、`capabilities[]`
      - `cost_profile`
      - `brand_cert`
      - `reputation`
      - `fault_history[]`
  - 依赖：无
  - 验收标准：可插入/查询候选 Agent，并关联到 Role。

- [TODO] D2（M1 / P0）实现 ScoreCard 数据结构 & 冻结逻辑
  - 目标：为 Role×CandidateAgent 生成一次性的静态评分。
  - 产出：
    - `ScoreCard`：
      - `agent_id`、`role_id`
      - `static_perf`、`brand_cert`、`user_reputation`、`fault_penalty`
      - `frozen_at`、`evidence`
    - 服务：`freeze_scorecard(role_id)` 只在项目初始化执行一次。
  - 依赖：D1、C1
  - 验收标准：同一项目同一 role+agent 组合，ScoreCard 不会重复生成；`frozen_at` 不变。

### 4.2 ShortlistPolicy & Top5 首批候选

- [DOING] D3（M1 / P0）定义 ShortlistPolicy 配置
  - 目标：明确 TopK & 顺延策略。
  - 产出：
    - 配置结构：
      - `top_k`（默认 5）
      - `page_size`（默认 5）
      - `max_pages_per_role`
      - `min_demandfit`
      - `stop_conditions[]`
  - 依赖：D2
  - 验收标准：可加载/修改策略，单测覆盖极端配置。

- [DOING] D4（M1 / P0）实现 `/aa/shortlist/first_batch`
  - 目标：按静态分生成首批 Top5 候选。
  - 产出：
    - API：`POST /aa/shortlist/first_batch { role_id }`
    - 返回：5 个候选 + 静态分 + 解释
  - 依赖：D2、D3
  - 验收标准：排序正确；无候选时返回空列表并有合理错误/提示。

### 4.3 DemandFit 动态评分与综合得分

- [DONE] D5（M1 / P0）实现 DemandFit 打分服务
  - 目标：基于本次需求特征计算动态符合度。
  - 产出：
    - `DemandFitResult`：
      - `agent_id`、`role_id`
      - `req_features`
      - `score`
      - `factors[]`、`explanation`、`weighting_used`
    - 服务：`compute_demandfit(req_features, candidate_ids[])`
  - 依赖：B1、D1
  - 验收标准：对同一输入得到稳定输出；包含可读 explanation。

- [DONE] D6（M1 / P0）实现综合得分合并逻辑
  - 目标：静态分 + 动态分 → total_score。
  - 产出：
    - 公式：`total_score = w_static * static + w_dynamic * demandfit`
    - 权重可配置（配置文件/数据库）
  - 依赖：D2、D5
  - 验收标准：更改权重后，排序发生预期变化；有单测验证。

### 4.4 自动选择 + 人工 Override + 顺延

- [TODO] D7（M1 / P0）实现 `/aa/select/auto`
  - 目标：默认选综合得分最高者。
  - 产出：API：`POST /aa/select/auto { role_id }`
  - 依赖：D4、D6
  - 验收标准：返回候选中得分最高者；有 GovLog 记录（见 G2）。

- [TODO] D8（M1 / P0）实现 `/aa/select/override`
  - 目标：支持人工改选候选。
  - 产出：
    - API：`POST /aa/select/override { role_id, agent_id, reason }`
    - 写入 ChangeRequest + GovLog
  - 依赖：D4、G2
  - 验收标准：可查询到 override 记录；回放时可复现改动。

- [DOING] D9（M1 / P1）实现 `/aa/shortlist/next_batch` 顺延逻辑
  - 目标：不满意时，从下一批 Top5 继续选。
  - 产出：
    - API：`POST /aa/shortlist/next_batch { role_id, last_page_no }`
    - 返回：下一页候选 + stop_reason
  - 依赖：D3、D4
  - 验收标准：
    - 页码递增正确；
    - 触达 `max_pages_per_role` 或 `min_demandfit` 时，返回终止原因。

---

## 5. Agent 生命周期 & Registry（白板步骤 7）

- [TODO] E1（M1 / P0）实现 AgentRegistry 模型
  - 目标：统一管理 Agent 状态（运行/停用/归档/成本）。
  - 产出：
    - 字段：
      - `status`（active/inactive/archived）
      - `runtime_flags`
      - `cost_limit`、`runtime_stats`
  - 依赖：D1
  - 验收标准：可对 Agent 做状态切换；数据持久化无误。

- [TODO] E2（M1 / P1）实现 `/agent/archive` & `/agent/clone_from`
  - 目标：支持只归档不删除；按模板克隆。
  - 产出：
    - API：
      - `POST /agent/archive { agent_id, reason }`
      - `POST /agent/clone_from { archived_agent_id, overrides? }`
  - 依赖：E1
  - 验收标准：归档后不再参与新选型；克隆 Agent 不带旧运行态。

- [TODO] E3（M1 / P1）实现 `/agent/activate` & `/agent/deactivate`
  - 目标：控制运行/停用 flag。
  - 产出：两条 API + 简单权限校验。
  - 依赖：E1
  - 验收标准：停用状态下 Agent 不再被选入新任务；有 GovLog 记录。

---

## 6. 执行流水线 & 看板 & 中途变更（白板步骤 8–9）

### 6.1 Plan → Assign → Execute → Review → Accept 状态机

- [DONE] F1（M0 / P0）实现 Task 状态机
  - 目标：定义合法状态流转。
  - 产出：
    - 状态转换规则表
    - 状态机实现（方法或类）
  - 依赖：C2
  - 验收标准：非法状态转换抛出明确异常；单测覆盖所有合法/非法路径。

- [TODO] F2（M1 / P0）实现 `/pipeline/*` API
  - 目标：对外暴露流水线操作。
  - 产出：
    - `POST /pipeline/plan { project_id }`
    - `POST /pipeline/assign { task_id, agent_id }`
    - `POST /pipeline/execute { task_id }`
    - `POST /pipeline/review { task_id }`
    - `POST /pipeline/accept { task_id, acceptance_result }`
  - 依赖：F1、D7–D8
  - 验收标准：通过 3 个 Demo 场景（文本/RAG/工具）的 E2E 流程。

### 6.2 AA 看板操作：set_next / enqueue_front

- [TODO] F3（M1 / P1）实现待执行队列结构
  - 目标：为每个项目维护一个可操作的待执行队列。
  - 产出：队列数据结构与基本操作（push/pop/enqueue_front）。
  - 依赖：C2
  - 验收标准：队列操作符合 FIFO + enqueue_front 语义，有单测。

- [TODO] F4（M1 / P1）实现 `/aa/kanban/set_next` & `/aa/kanban/enqueue_front`
  - 目标：允许 AA 调整下一条任务。
  - 产出：
    - API：
      - `POST /aa/kanban/set_next { project_id, task_id }`
      - `POST /aa/kanban/enqueue_front { project_id, task_spec }`
    - 快照机制：记录变更前后队列 & DAG 版本。
  - 依赖：F3、G1、G2
  - 验收标准：仅影响待执行队列，不破坏已执行节点；可通过快照回滚。

---

## 7. 治理 & 审计 & 失败矩阵（白板步骤 10–11）

### 7.1 GovLog & ChangeRequest

- [TODO] G1（M2 / P0）定义 ChangeRequest 模型
  - 目标：记录所有人工/系统变更请求。
  - 产出：
    - `ChangeRequest`：
      - `id`、`type`（override/reassign/set_next/...）
      - `request_by`、`reason`
      - `impact`、`status`
      - `rollback_ref`
  - 依赖：E1、F1
  - 验收标准：所有 override / reassign / set_next 都产生一条 ChangeRequest。

- [TODO] G2（M2 / P0）实现 GovLog 日志体系
  - 目标：为治理与审计记录统一日志。
  - 产出：
    - `GovLog`：
      - `change_id`、`trace_id`
      - `actor`、`action`
      - `object_ref`
      - `before/after`
      - `reason`、`timestamp`
      - `links`
    - 查询接口：`GET /govlog/query`
  - 依赖：G1
  - 验收标准：可按项目/时间/actor 查询；重要操作全部可追溯。

### 7.2 StateSync & ConflictResolver

- [TODO] G3（M2 / P1）实现 StateSync 订阅机制
  - 目标：周期性/事件驱动地同步各 Agent & Task 状态。
  - 产出：StateSync 服务 + 心跳/状态订阅接口。
  - 依赖：runtime / msg 基础
  - 验收标准：状态视图与真实运行状态偏差在可控范围内。

- [TODO] G4（M2 / P1）实现 ConflictResolver
  - 目标：处理资源争用 / 调度冲突。
  - 产出：冲突检测规则 + 冲突处理策略（排队/改派/降级）。
  - 依赖：G3、E1
  - 验收标准：能在测试场景下自动缓解冲突；记录处理过程到 GovLog。

### 7.3 失败处置矩阵

- [TODO] G5（M2 / P0）定义失败策略矩阵
  - 目标：统一错误类型 → 行为的映射。
  - 产出：
    - 错误分类：可恢复/不可恢复/外部依赖/超时/配额等
    - 行为：`retry`（带退避）/`degrade`/`reassign`/`abort`
  - 依赖：F2
  - 验收标准：文档化 + 配置化，可被执行引擎调用。

- [TODO] G6（M2 / P1）在执行流程中接入失败矩阵
  - 目标：执行任务失败时自动执行策略。
  - 产出：在 `/pipeline/execute` 路径中接入 G5。
  - 依赖：G5
  - 验收标准：在 Demo C（工具链调用）中可验证「超时→退避重试→改派→成功」路径。

---

## 8. Runtime 沙箱 & 可观测性（白板步骤 10 的 Runtime 部分）

- [TODO] H1（M2 / P0）定义 Runtime 配额策略结构
  - 目标：定义 CPU/内存/Token/外呼额度配额。
  - 产出：Quota 配置结构与加载方式。
  - 依赖：E1
  - 验收标准：可为不同项目/Agent 设置不同配额。

- [TODO] H2（M2 / P1）实现 Runtime 拦截器
  - 目标：在调用链入/出点执行配额检查 & 元数据采集。
  - 产出：拦截器接口 & 若干实现（配额检查 / Trace 采集）。
  - 依赖：H1
  - 验收标准：配额命中时能阻止执行并记录日志。

- [TODO] H3（M2 / P1）接入 OpenTelemetry / 自定义 TraceSpan
  - 目标：实现端到端调用链追踪。
  - 产出：
    - `TraceSpan` 数据结构
    - 与主程序调用链集成
  - 依赖：H2
  - 验收标准：可在本地/测试环境中查看整条执行链路。

---

## 9. Memory / 模板 / 画像更新 & 复盘（白板步骤 12）

- [TODO] I1（M3 / P1）实现项目摘要写入 Memory
  - 目标：生成项目级别的压缩摘要。
  - 产出：`POST /project/summarize { project_id }` + 存储逻辑。
  - 依赖：F2
  - 验收标准：项目结束后可生成摘要，并被后续项目读取。

- [TODO] I2（M3 / P1）实现从项目生成模板
  - 目标：将成功项目沉淀为模板。
  - 产出：`POST /templates/create_from_project { project_id }`
  - 依赖：I1、C1、C2、D3
  - 验收标准：新项目从模板创建耗时 < 10s；结构完整。

- [TODO] I3（M3 / P1）实现画像更新事件 PROFILE.UPDATE
  - 目标：基于项目结果更新用户画像，支持撤回。
  - 产出：事件定义 + 更新服务 + 撤回机制。
  - 依赖：B3
  - 验收标准：更新有审计记录；可撤回到某一版本。

---

## 10. 可观测性 & SLO & 测试矩阵

- [DOING] J1（M2 / P0）定义核心 KPI & SLO
  - 目标：明确成功率/时延/错误率等指标目标。
  - 产出：文档 & 指标配置：
    - 成功率≥98%
    - E2E p95 < 4s（不含外部 API）
    - 错误率≤1%
  - 依赖：F2、H3
  - 验收标准：监控系统中可看到这些指标。

- [TODO] J2（M2 / P0）建立测试矩阵
  - 目标：覆盖关键路径（Top5→顺延→Override→改派）。
  - 产出：测试用例表 & 自动化测试。
  - 依赖：D7–D9、F2、G6
  - 验收标准：回归测试通过率 100%，任一改动需跑完矩阵。

---

## 11. 文档 / Demo / 版本与发布（M3）

- [TODO] K1（M3 / P1）撰写架构与扩展点文档
  - 目标：让外部用户看文档就能理解 HiveCore 结构 & 如何扩展。
  - 产出：`/docs/architecture.md`、`/docs/extensibility.md`
  - 依赖：整体架构相对稳定
  - 验收标准：新开发者在 1 小时内可理解主要模块与扩展点。

- [TODO] K2（M3 / P1）准备三套 Demo（文本 / RAG / 工具链）
  - 目标：用于演示和回归。
  - 产出：`/examples/demo_text.py`、`demo_rag.py`、`demo_tools.py`
  - 依赖：F2、G6
  - 验收标准：三套 Demo 在 README 步骤下可跑通。

- [DOING] K3（M3 / P1）确定版本策略 & CHANGELOG
  - 目标：采用语义化版本 + 灰度发布。
  - 产出：`CHANGELOG.md`、版本标记流程。
  - 依赖：M1–M2 基本稳定
  - 验收标准：每次发布有版本号 & 对应 changelog 条目。

---

## 12. 骨架验证 & 实战演练任务（整合旧文档）

> 本节将原有的《HiveCore 骨架测试任务》转为可跟踪的任务项，用于验证当前 AgentScope + HiveCore 骨架是否稳定工作。

### 12.1 环境准备与可编辑安装

- [TODO] L1（M0 / P0）建立本地虚拟环境 & 可编辑安装流程
  - 目标：提供一套标准的本地开发环境步骤，确保所有人按同一方式起步。
  - 产出：
    - 文档段落（可写在 `README.md` 或 `docs/dev_setup.md`）：
      - 使用 `python3 -m venv .venv && source .venv/bin/activate`
      - `pip install -e .`
    - 可选：`.env.example` 说明模型/工具配置方式
  - 依赖：A1
  - 验收标准：
    - 在一台新机器上，按文档操作即可跑通后续测试；
    - 常见错误（缺依赖、Python 版本不对）在文档中有说明。

### 12.2 单元测试：AA 选型 & One·s 子模块

- [DONE] L2（M0 / P0）整理并跑通 AA 选型相关单测
  - 目标：验证 `AssistantAgentSelector` 和选型逻辑的当前实现是否可用。
  - 产出：
    - 测试脚本：`tests/aa_selection_test.py`（如已存在则梳理）
    - 运行指令：`pytest tests/aa_selection_test.py`
  - 依赖：D7 相关代码存在
  - 验收标准：
    - 测试全部通过；
    - 输出日志中 Requirement / Ranking 的内容符合预期排序逻辑。

- [DONE] L3（M0 / P1）补充并运行 One·s 子模块测试（如适用）
  - 目标：确保 One·s 相关子模块（若保留）行为可控。
  - 产出：
    - `tests/ones/` 目录及测试用例
    - 运行指令：`pytest tests/ones`
  - 依赖：现有 One·s 模块
  - 验收标准：
    - 测试全部通过；
    - 若有不再维护的模块，标明废弃并清理测试。

### 12.3 手工流程演练：最小 orchestrator / execution loop

- [TODO] L4（M0 / P0）编写最小 `manual_loop.py` 演练脚本
  - 目标：通过脚本串起 orchestrator、ExecutionLoop 与 AA，验证骨架可跑通一轮真实交互。
  - 产出：
    - 文件：`examples/manual_loop.py`，包含：
      - 创建 `SystemRegistry / AssistantOrchestrator / ExecutionLoop / KPITracker / TaskGraphBuilder / ProjectPool / MemoryPool / ResourceLibrary`
      - 注册一个简单的 `AgentProfile`（如 `agent-coder`）
      - 构造 `AASystemAgent` 与简单的 `requirement_resolver` / `acceptance_resolver`
      - 构建 `Msg`，触发 `aa.reply(...)` 并打印输出文本 & metadata
  - 依赖：核心骨架类已存在（可基于目前 codex 生成的骨架调整）
  - 验收标准：
    - 运行 `python examples/manual_loop.py` 不报错；
    - 控制台输出中包含任务状态列表、KPI 信息；
    - `response.metadata` 至少包含 `accepted`、`project_id`、`task_status` 等关键键。

### 12.4 MemoryPool & Registry 状态检查

- [TODO] L5（M0 / P1）在演练脚本中验证 MemoryPool 记录
  - 目标：确认用户意图/轮次摘要已经写入 MemoryPool。
  - 产出：
    - 在 `manual_loop.py` 中新增检查代码，例如：
      - `print(memory_pool.load("intent:user-1:None"))`
    - 文档说明：预期读到的 `MemoryEntry` 结构（至少包含 content = 用户输入）
  - 依赖：L4
  - 验收标准：
    - 实际运行输出中可看到期望的 MemoryEntry；
    - 若未写入，补齐 Memory 保存逻辑或记录 TODO。

- [TODO] L6（M0 / P1）在演练脚本中验证 SystemRegistry 绑定关系
  - 目标：确认 `SystemRegistry` 中记录了用户与 AA 的绑定。
  - 产出：
    - 在 `manual_loop.py` 中新增：
      - `print(registry.aa_binding("user-1"))`
    - 文档说明预期输出（AA 的 id 或对象）
  - 依赖：L4
  - 验收标准：
    - 输出中能看到正确的 AA 绑定；
    - 若未绑定，则修复 registry 初始化/注册逻辑。

### 12.5 后续增强：持久化上下文 & KPI 返工逻辑

- [TODO] L7（M1 / P2）扩展 ProjectPool / MemoryPool 的持久化实现
  - 目标：支持在多次运行间共享项目上下文，用于真实多轮项目。
  - 产出：
    - 将当前内存实现替换或封装为可插拔持久化后端（文件/DB 均可）
    - 简单的配置参数选择后端
  - 依赖：B3、L4–L6
  - 验收标准：
    - 连续两次运行 `manual_loop.py` 时，第二次可以读取前一次的项目或记忆；
    - 有用例或简单测试脚本验证。

- [TODO] L8（M1 / P2）为 KPITracker 添加返工触发逻辑
  - 目标：当质量指标低于阈值时，自动触发返工/重试。
  - 产出：
    - 在 KPITracker 或流水线中添加断言：
      - 若质量 < 0.9，则返回「需返工」状态或重入任务队列
  - 依赖：F2、L4
  - 验收标准：
    - 人为降低 KPI 后，可看到返工逻辑生效；
    - 相关决策写入 GovLog（若 G2 已完成）。

### 12.6 MsgHub 实时广播集成（和白板 MsgHub 设计打通）

- [DONE] L9（M1 / P1）实现 MsgHubBroadcaster 桥接
  - 目标：将 ExecutionLoop 产生的轮次更新通过 AgentScope 的 `MsgHub` 广播给订阅者。
  - 产出：
    - 模块：`agentscope/ones/msghub.py` 或类似位置
    - 类：`MsgHubBroadcaster`，内部复用 `agentscope.pipeline.MsgHub`
    - 能将 RoundUpdate 格式化为 `Msg`（含结构化 metadata）
  - 依赖：F2、B4
  - 验收标准：
    - 写一个最小订阅 Agent（覆写 `observe` 记录消息）；
    - 运行 Demo / 测试时，订阅 Agent 能收到带 `project_id` / 轮次信息的消息。

- [DONE] L10（M1 / P2）注册项目级 MsgHub & 工厂方法
  - 目标：按 `project_id` 绑定不同的 MsgHub 或订阅者列表。
  - 产出：
    - `ProjectMsgHubRegistry` 或工厂函数：
      - `msg_hub_factory(project_id) -> MsgHubBroadcaster`
    - ExecutionLoop 中调用该工厂以获取广播器
  - 依赖：L9、B3
  - 验收标准：
    - 不同 project_id 可以走到不同的 Hub；
    - 未绑定项目时回退到内存实现，不影响功能。

- [TODO] L11（M1 / P2）CLI 集成实时广播（可选）
  - 目标：从命令行体验完整「用户输入 → AA 调用 → 实时广播」流程。
  - 产出：
    - 在 `scripts/full_user_flow_cli.py` 或新脚本中加入参数：
      - 例如 `--enable-broadcast`，打开 MsgHub 调试输出
    - README 中增加「如何开启实时广播」说明
  - 依赖：L9、L10
  - 验收标准：
    - 本地运行 CLI 时，可以看到实时轮次输出；
    - 对关闭广播时行为无破坏。

---

> 本 v2 版 `TASK.md` 在 v1 白板流程任务的基础上，完整吸收了当前骨架验证文档中的手工测试、脚本、MsgHub 演练等内容，用 L1–L11 任务确保现有骨架真的跑得通、看得见、可复现。