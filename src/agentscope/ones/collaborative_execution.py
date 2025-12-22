# -*- coding: utf-8 -*-
"""Collaborative execution framework with real Agent interactions via MsgHub."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, TYPE_CHECKING

from ..agent import AgentBase
from ..message import Msg, TextBlock
from ..pipeline import MsgHub
from .memory import MemoryEntry, MemoryPool
from .architect_agent import ArchitectAgent

if TYPE_CHECKING:
    from ..model import ChatModelBase


class CollaborationHistory:
    """Records and manages Agent interaction history."""

    def __init__(self, project_id: str, memory_pool: MemoryPool | None = None):
        self.project_id = project_id
        self.memory_pool = memory_pool or MemoryPool()
        self.messages: list[dict[str, Any]] = []
        self.round_count = 0

    def record(
        self,
        agent_name: str,
        message_type: str,
        content: str,
        metadata: dict | None = None,
    ) -> None:
        """Record an interaction message."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "round": self.round_count,
            "agent": agent_name,
            "type": message_type,
            "content": content[:2000],  # Truncate for storage
            "metadata": metadata or {},
        }
        self.messages.append(entry)

        # Save to MemoryPool
        key = f"collab_history:{self.project_id}:{len(self.messages)}"
        mem_entry = MemoryEntry(
            key=key,
            content=json.dumps(entry, ensure_ascii=False),
            tags={"collaboration", "history", self.project_id, agent_name},
        )
        self.memory_pool.save(mem_entry)

    def start_round(self) -> None:
        """Start a new collaboration round."""
        self.round_count += 1

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent interaction history."""
        return self.messages[-limit:]

    def get_summary(self) -> str:
        """Get a summary of the collaboration history."""
        if not self.messages:
            return "No interactions yet."

        summary_parts = [f"Collaboration History ({len(self.messages)} messages):"]
        for msg in self.messages[-10:]:
            summary_parts.append(
                f"  [{msg['agent']}] ({msg['type']}): {msg['content'][:100]}..."
            )
        return "\n".join(summary_parts)


class CollaborativeCodeAgent(AgentBase):
    """An agent specialized for collaborative code generation."""

    def __init__(
        self,
        *,
        name: str,
        role: str,
        model: "ChatModelBase",
        history: CollaborationHistory | None = None,
    ) -> None:
        super().__init__()
        self.name = name  # Set name after init
        self.role = role
        self.model = model
        self.history = history
        self._last_response: str = ""
        self.sys_prompt = self._build_sys_prompt(role)
        self._memory: list[dict[str, Any]] = []

    def _build_sys_prompt(self, role: str) -> str:
        """Build system prompt based on role."""
        prompts = {
            "backend": """你是后端工程专家 (BackendEngineer)。
职责：
- 设计和实现后端 API、数据模型、数据库逻辑
- 遵循架构契约中定义的路径和接口规范
- 与前端工程师协调 API 接口定义

输出要求：
- 生成完整的可运行代码
- 使用 JSON 格式输出文件列表
- 明确说明 API 端点和数据模型""",

            "frontend": """你是前端工程专家 (FrontendEngineer)。
职责：
- 实现前端页面、组件和状态管理
- 根据后端提供的 API 接口实现数据交互
- 遵循架构契约中定义的前端路径规范

输出要求：
- 生成完整的可运行代码
- 确保与后端 API 接口一致
- 使用 JSON 格式输出文件列表""",

            "qa": """你是质量保证专家 (QAEngineer)。
职责：
- 审查后端和前端代码的一致性
- 检查 API 接口是否匹配
- 验证代码是否符合架构契约

输出要求：
- 列出发现的问题和不一致
- 提出具体的修改建议
- 确认通过或要求修改""",

            "architect": """你是架构师 (Architect)。
职责：
- 定义整体架构和技术选型
- 制定前后端接口契约
- 协调各角色之间的依赖关系

输出要求：
- 输出明确的架构契约
- 定义 API 端点、数据模型、文件结构
- 使用 JSON 格式""",
        }
        return prompts.get(role, "你是一个软件工程专家。")

    async def observe(self, msg: Msg | list[Msg] | None = None) -> None:
        """Observe messages from other agents."""
        if msg is None:
            return

        msgs = [msg] if isinstance(msg, Msg) else msg
        for m in msgs:
            content = m.get_text_content() or ""
            self._memory.append({
                "role": "user" if m.name != self.name else "assistant",
                "content": f"[{m.name}]: {content}",
            })

    async def reply(self, msg: Msg | list[Msg] | None = None, **kwargs: Any) -> Msg:
        """Generate a reply based on input and conversation history."""
        # Add input message to memory
        if msg:
            await self.observe(msg)

        # Build messages for LLM
        messages = [{"role": "system", "content": self.sys_prompt}]
        messages.extend(self._memory[-20:])  # Keep last 20 messages for context

        # Call LLM
        response = await self.model(messages)

        # Extract text from response
        if hasattr(response, "content") and isinstance(response.content, list):
            response_text = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in response.content
                if isinstance(block, dict) and block.get("type") == "text"
            ).strip()
        elif hasattr(response, "text"):
            response_text = response.text
        else:
            response_text = str(response)

        self._last_response = response_text

        # Record to history
        if self.history:
            input_text = ""
            if msg:
                if isinstance(msg, list):
                    input_text = " | ".join([m.get_text_content() or "" for m in msg])
                else:
                    input_text = msg.get_text_content() or ""

            self.history.record(
                agent_name=self.name,
                message_type="reply",
                content=self._last_response,
                metadata={"input_summary": input_text[:200]},
            )

        # Add response to memory
        self._memory.append({
            "role": "assistant",
            "content": response_text,
        })

        # Return as Msg
        return Msg(
            name=self.name,
            role="assistant",
            content=[TextBlock(type="text", text=response_text)],
        )


class CollaborativeExecution:
    """Framework for executing multi-agent tasks with real MsgHub communication.

    This class orchestrates multiple specialized agents using AgentScope's MsgHub
    for genuine inter-agent communication. Each agent can see and respond to
    messages from other agents.

    Example:
        .. code-block:: python

            execution = CollaborativeExecution(
                model=llm_model,
                project_id="gym_system",
            )

            result = await execution.execute(
                requirements=requirements,
                architecture_contract=contract,
            )

            # Get interaction history
            history = execution.get_interaction_history()
    """

    def __init__(
        self,
        *,
        model: "ChatModelBase",
        memory_pool: MemoryPool | None = None,
        project_id: str = "default",
    ) -> None:
        self.model = model
        self.memory_pool = memory_pool or MemoryPool()
        self.project_id = project_id

        # Initialize collaboration history
        self.history = CollaborationHistory(project_id, self.memory_pool)

        # Initialize specialized agents with shared history
        self.backend_agent = CollaborativeCodeAgent(
            name="BackendEngineer",
            role="backend",
            model=model,
            history=self.history,
        )

        self.frontend_agent = CollaborativeCodeAgent(
            name="FrontendEngineer",
            role="frontend",
            model=model,
            history=self.history,
        )

        self.qa_agent = CollaborativeCodeAgent(
            name="QAEngineer",
            role="qa",
            model=model,
            history=self.history,
        )

        self.architect_agent = CollaborativeCodeAgent(
            name="Architect",
            role="architect",
            model=model,
            history=self.history,
        )

    async def execute(
        self,
        requirement: dict[str, Any],
        architecture_contract: dict[str, Any],
        blueprint: dict[str, Any] | None = None,
        *,
        max_rounds: int = 3,
        verbose: bool = False,
    ) -> dict[str, Any]:
        """Execute a requirement using collaborative agents with MsgHub.

        The collaboration flow:
        1. Architect announces the contract to all agents
        2. BackendEngineer generates backend code
        3. FrontendEngineer sees backend code and generates matching frontend
        4. QAEngineer reviews and either approves or requests changes
        5. If changes requested, loop back to step 2

        Args:
            requirement: The requirement to implement.
            architecture_contract: The architecture contract to follow.
            blueprint: Optional blueprint with file plans.
            max_rounds: Maximum collaboration rounds.
            verbose: Whether to print verbose output.

        Returns:
            dict containing generated code and collaboration history.
        """
        results = {
            "requirement_id": requirement.get("id", ""),
            "files": [],
            "summary": "",
            "collaboration_history": [],
            "success": False,
        }

        # Prepare contract text
        contract_text = ArchitectAgent.format_contract(architecture_contract)

        # Prepare file plan from blueprint
        files_plan = ""
        if blueprint and blueprint.get("files_plan"):
            files_plan = "\n".join([
                f"- {f.get('path', '')}: {f.get('description', '')}"
                for f in blueprint.get("files_plan", [])[:10]
            ])

        # Create announcement message with contract
        announcement = Msg(
            name="System",
            role="system",
            content=[TextBlock(
                type="text",
                text=f"""【项目协作启动】

需求: {requirement.get('title', '')}
描述: {requirement.get('details', requirement.get('description', ''))}

【架构契约 - 所有人必须遵循】
{contract_text}

【需要生成的文件】
{files_plan}

请按以下顺序协作：
1. BackendEngineer 先生成后端代码
2. FrontendEngineer 看到后端 API 后生成前端代码
3. QAEngineer 审查代码一致性

每个人输出时使用 JSON 格式：
```json
{{
  "summary": "实现摘要",
  "files": [{{"path": "路径", "content": "完整代码"}}],
  "message_to_others": "给其他 Agent 的说明"
}}
```
""",
            )],
        )

        all_agents = [
            self.architect_agent,
            self.backend_agent,
            self.frontend_agent,
            self.qa_agent,
        ]

        all_files = []
        approved = False
        qa_feedback: str | None = None  # Store QA feedback for next round

        # Collaboration loop
        for round_idx in range(max_rounds):
            self.history.start_round()

            if verbose:
                from ..scripts._observability import get_logger
                get_logger().info(f"\n[COLLAB] ===== 协作轮次 {round_idx + 1}/{max_rounds} =====")

            # Build round announcement - include QA feedback if available
            round_announcement = announcement
            if round_idx > 0 and qa_feedback:
                # Create a new announcement that includes both contract and QA feedback
                round_announcement = Msg(
                    name="System",
                    role="system",
                    content=[TextBlock(
                        type="text",
                        text=f"""【第 {round_idx + 1} 轮协作 - 请修复 QA 发现的问题】

【QA 上一轮审查反馈 - 必须修复以下问题】
{qa_feedback}

【架构契约 - 必须严格遵循】
{contract_text}

请根据 QA 反馈修改代码，确保：
1. API 端点路径与架构契约完全一致
2. 前后端数据模型匹配
3. 所有导入和依赖正确
""",
                    )],
                )

            async with MsgHub(
                participants=all_agents,
                announcement=round_announcement,
                enable_auto_broadcast=True,
            ) as hub:
                # Record announcement
                if round_idx == 0:
                    self.history.record(
                        agent_name="System",
                        message_type="announcement",
                        content=contract_text,
                        metadata={"requirement": requirement.get("title", "")},
                    )

                # Step 1: Backend Engineer generates backend code
                if verbose:
                    from ..scripts._observability import get_logger
                    get_logger().info("[COLLAB] BackendEngineer 开始生成后端代码...")

                backend_task = Msg(
                    name="Orchestrator",
                    role="user",
                    content=[TextBlock(
                        type="text",
                        text=f"""请生成后端代码，严格遵循架构契约。

需要生成的后端文件：
{chr(10).join([f"- {f.get('path', '')}" for f in blueprint.get("files_plan", []) if f.get('path', '').startswith('backend')][:5]) if blueprint else '- backend/app/main.py\n- backend/app/routers/\n- backend/app/models.py'}

输出 JSON 格式，包含完整代码。""",
                    )],
                )

                backend_response = await self.backend_agent.reply(backend_task)
                backend_text = backend_response.get_text_content() or ""
                backend_files = self._extract_files(backend_text)
                all_files.extend(backend_files)

                if verbose:
                    from ..scripts._observability import get_logger
                    get_logger().info(f"[COLLAB] BackendEngineer 生成了 {len(backend_files)} 个文件")

                # Step 2: Frontend Engineer generates frontend code
                if verbose:
                    from ..scripts._observability import get_logger
                    get_logger().info("[COLLAB] FrontendEngineer 开始生成前端代码...")

                frontend_task = Msg(
                    name="Orchestrator",
                    role="user",
                    content=[TextBlock(
                        type="text",
                        text=f"""请根据 BackendEngineer 提供的 API 接口，生成前端代码。

后端 API 摘要：
{self._summarize_backend_apis(backend_text)}

需要生成的前端文件：
{chr(10).join([f"- {f.get('path', '')}" for f in blueprint.get("files_plan", []) if f.get('path', '').startswith('frontend')][:5]) if blueprint else '- frontend/src/api/\n- frontend/src/views/\n- frontend/src/router/'}

确保前端调用的 API 路径与后端一致。输出 JSON 格式。""",
                    )],
                )

                frontend_response = await self.frontend_agent.reply(frontend_task)
                frontend_text = frontend_response.get_text_content() or ""
                frontend_files = self._extract_files(frontend_text)
                all_files.extend(frontend_files)

                if verbose:
                    from ..scripts._observability import get_logger
                    get_logger().info(f"[COLLAB] FrontendEngineer 生成了 {len(frontend_files)} 个文件")

                # Step 3: QA Engineer reviews
                if verbose:
                    from ..scripts._observability import get_logger
                    get_logger().info("[COLLAB] QAEngineer 开始审查代码...")

                qa_task = Msg(
                    name="Orchestrator",
                    role="user",
                    content=[TextBlock(
                        type="text",
                        text=f"""请审查 BackendEngineer 和 FrontendEngineer 的代码：

1. 检查前后端 API 路径是否一致
2. 检查数据模型是否匹配
3. 检查是否符合架构契约

如果通过，输出：
```json
{{"approved": true, "summary": "审查通过"}}
```

如果有问题，输出：
```json
{{"approved": false, "issues": ["问题1", "问题2"], "suggestions": ["建议1", "建议2"]}}
```""",
                    )],
                )

                qa_response = await self.qa_agent.reply(qa_task)
                qa_text = qa_response.get_text_content() or ""

                if verbose:
                    from ..scripts._observability import get_logger
                    get_logger().info(f"[COLLAB] QAEngineer 审查结果: {qa_text[:200]}...")

                # Check if approved
                approved = self._check_qa_approval(qa_text)

                if approved:
                    if verbose:
                        from ..scripts._observability import get_logger
                        get_logger().info("[COLLAB] ✓ QA 审查通过")
                    break
                else:
                    if verbose:
                        from ..scripts._observability import get_logger
                        get_logger().info("[COLLAB] ✗ QA 发现问题，需要修改")
                    # Store QA feedback for next round
                    qa_feedback = qa_text

        # Deduplicate files by path
        files_dict = {}
        for f in all_files:
            path = f.get("path", "")
            if path:
                files_dict[path] = f
        results["files"] = list(files_dict.values())

        results["summary"] = f"协作完成，共生成 {len(results['files'])} 个文件"
        results["collaboration_history"] = self.history.get_history()
        results["success"] = approved or len(results["files"]) > 0

        return results

    def _extract_files(self, text: str) -> list[dict[str, str]]:
        """Extract files from agent response."""
        files = []
        try:
            # Try to parse JSON
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                json_text = text[start:end].strip()
            elif "```" in text:
                start = text.find("```") + 3
                end = text.find("```", start)
                json_text = text[start:end].strip()
            else:
                json_text = text

            data = json.loads(json_text)
            if isinstance(data, dict) and "files" in data:
                files = data.get("files", [])
        except (json.JSONDecodeError, ValueError):
            pass
        return files

    def _summarize_backend_apis(self, backend_text: str) -> str:
        """Summarize backend APIs from response."""
        # Extract key API information
        lines = []
        if "/api/" in backend_text:
            for line in backend_text.split("\n"):
                if "/api/" in line or "def " in line or "async def" in line:
                    lines.append(line.strip()[:100])
        return "\n".join(lines[:10]) if lines else "参考上文 BackendEngineer 的输出"

    def _check_qa_approval(self, qa_text: str) -> bool:
        """Check if QA approved the code."""
        text_lower = qa_text.lower()
        if '"approved": true' in text_lower or '"approved":true' in text_lower:
            return True
        if "通过" in qa_text and "不通过" not in qa_text:
            return True
        return False

    def get_interaction_history(self) -> list[dict[str, Any]]:
        """Get the full interaction history."""
        return self.history.get_history()

    def get_history_summary(self) -> str:
        """Get a summary of interactions."""
        return self.history.get_summary()


async def execute_with_real_collaboration(
    llm: "ChatModelBase",
    requirement: dict[str, Any],
    architecture_contract: dict[str, Any],
    blueprint: dict[str, Any] | None = None,
    project_id: str = "default",
    *,
    memory_pool: MemoryPool | None = None,
    max_rounds: int = 3,
    verbose: bool = False,
) -> dict[str, Any]:
    """Execute a requirement using real multi-agent collaboration.

    This is the main entry point for using collaborative execution
    with genuine MsgHub-based agent communication.

    Args:
        llm: The LLM model.
        requirement: The requirement to implement.
        architecture_contract: The architecture contract.
        blueprint: Optional blueprint with file plans.
        project_id: Project identifier.
        memory_pool: Optional shared memory pool.
        max_rounds: Maximum collaboration rounds.
        verbose: Whether to print verbose output.

    Returns:
        Execution results with generated files and history.
    """
    execution = CollaborativeExecution(
        model=llm,
        memory_pool=memory_pool or MemoryPool(),
        project_id=project_id,
    )

    return await execution.execute(
        requirement=requirement,
        architecture_contract=architecture_contract,
        blueprint=blueprint,
        max_rounds=max_rounds,
        verbose=verbose,
    )
