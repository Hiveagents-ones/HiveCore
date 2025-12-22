# -*- coding: utf-8 -*-
"""ArchitectAgent: Generates and maintains architecture contracts for multi-agent coordination."""
from __future__ import annotations

import json
import textwrap
from typing import Any, TYPE_CHECKING

from ..agent import AgentBase
from ..message import Msg, TextBlock
from .memory import MemoryEntry, MemoryPool, ProjectMemory

if TYPE_CHECKING:
    from ..model import ModelWrapperBase


# Contract memory key pattern
CONTRACT_KEY_PREFIX = "architecture_contract:"


class ArchitectAgent(AgentBase):
    """Agent responsible for generating and broadcasting architecture contracts.

    The ArchitectAgent analyzes project requirements and generates a unified
    architecture contract that all other agents (Frontend, Backend, QA) should
    follow. The contract is stored in project-level memory (MemoryPool) and
    can be broadcast to other agents via MsgHub.

    Example:
        .. code-block:: python

            from agentscope.ones.architect_agent import ArchitectAgent
            from agentscope.ones.memory import MemoryPool
            from agentscope.pipeline import MsgHub

            memory_pool = MemoryPool()
            architect = ArchitectAgent(
                name="Architect",
                model=llm_model,
                memory_pool=memory_pool,
                project_id="gym_system",
            )

            # Generate contract
            contract_msg = await architect.generate_contract(requirements)

            # Other agents can read contract from memory
            contract = memory_pool.load(f"architecture_contract:gym_system")
    """

    def __init__(
        self,
        *,
        name: str = "ArchitectAgent",
        model: "ModelWrapperBase | None" = None,
        memory_pool: MemoryPool | None = None,
        project_memory: ProjectMemory | None = None,
        project_id: str = "default",
    ) -> None:
        """Initialize the ArchitectAgent.

        Args:
            name (`str`):
                The name of this agent.
            model (`ModelWrapperBase | None`):
                The LLM model to use for generating contracts.
            memory_pool (`MemoryPool | None`):
                The memory pool to store contracts in.
            project_memory (`ProjectMemory | None`):
                The project memory for cross-agent context sharing.
            project_id (`str`):
                The project identifier for this contract.
        """
        super().__init__()
        self.name = name
        self.model = model
        self.memory_pool = memory_pool or MemoryPool()
        self.project_memory = project_memory
        self.project_id = project_id
        self._contract: dict[str, Any] = {}

    @property
    def contract_key(self) -> str:
        """Return the memory key for this project's contract."""
        return f"{CONTRACT_KEY_PREFIX}{self.project_id}"

    async def generate_contract(
        self,
        requirements: list[dict[str, Any]],
        *,
        verbose: bool = False,
    ) -> Msg:
        """Generate an architecture contract based on requirements.

        Args:
            requirements (`list[dict[str, Any]]`):
                List of requirement objects to analyze.
            verbose (`bool`):
                Whether to print verbose output.

        Returns:
            `Msg`:
                A message containing the generated contract.
        """
        prompt = self._build_contract_prompt(requirements)

        if self.model is None:
            # Return empty contract if no model
            self._contract = {}
            return self._create_contract_message({})

        try:
            response = self.model(prompt)
            contract_text = response.text if hasattr(response, "text") else str(response)

            # Parse JSON from response
            self._contract = self._parse_contract(contract_text)

            if verbose:
                from ..scripts._observability import get_logger
                get_logger().debug(f"[ARCH] Generated contract with {len(self._contract.get('api_endpoints', []))} endpoints")

        except Exception as e:
            if verbose:
                from ..scripts._observability import get_logger
                get_logger().warn(f"[ARCH] Contract generation failed: {e}")
            self._contract = {}

        # Store in memory pool
        self._save_to_memory()

        return self._create_contract_message(self._contract)

    def _build_contract_prompt(self, requirements: list[dict[str, Any]]) -> str:
        """Build the prompt for contract generation."""
        return textwrap.dedent(f"""
            你是一位资深架构师。请根据以下需求列表，生成一份统一的架构契约。
            这份契约将作为所有开发 Agent（前端、后端）的共同参考，确保接口一致性。

            【需求列表】
            {json.dumps(requirements, ensure_ascii=False, indent=2)}

            【输出格式】
            请输出 JSON 格式的架构契约：
            {{
                "project_name": "项目名称",
                "file_structure": {{
                    "backend": {{
                        "root": "backend",
                        "app_entry": "backend/app/main.py",
                        "routers_dir": "backend/app/routers",
                        "models_dir": "backend/app/models",
                        "schemas_dir": "backend/app/schemas",
                        "database": "backend/app/database.py"
                    }},
                    "frontend": {{
                        "root": "frontend",
                        "src_dir": "frontend/src",
                        "views_dir": "frontend/src/views",
                        "components_dir": "frontend/src/components",
                        "api_dir": "frontend/src/api"
                    }}
                }},
                "api_endpoints": [
                    {{
                        "path": "/api/v1/members",
                        "methods": ["GET", "POST"],
                        "description": "会员管理接口",
                        "request_schema": "MemberCreate",
                        "response_schema": "Member"
                    }}
                ],
                "data_models": [
                    {{
                        "name": "Member",
                        "fields": [
                            {{"name": "id", "type": "int", "description": "主键"}},
                            {{"name": "name", "type": "str", "description": "姓名"}}
                        ]
                    }}
                ],
                "import_conventions": {{
                    "backend_router_import": "from .routers import members, courses",
                    "backend_db_import": "from .database import engine, Base, get_db"
                }}
            }}

            【重要约束】
            1. 文件结构必须一致：所有需求生成的代码都必须遵循 file_structure 中定义的路径
            2. API 路径必须统一：前端调用的路径必须与后端定义的路径完全一致
            3. 数据模型必须共享：前后端使用相同的字段名和类型

            只输出 JSON，不要其他内容。
        """)

    def _parse_contract(self, text: str) -> dict[str, Any]:
        """Parse contract JSON from LLM response."""
        # Try to extract JSON from response
        text = text.strip()

        # Handle markdown code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    def _save_to_memory(self) -> None:
        """Save the contract to the memory pool and project memory."""
        if self._contract:
            # Save to MemoryPool (legacy)
            entry = MemoryEntry(
                key=self.contract_key,
                content=json.dumps(self._contract, ensure_ascii=False),
                tags={"architecture", "contract", self.project_id},
            )
            self.memory_pool.save(entry)

            # Save to ProjectMemory for cross-agent context sharing
            if self.project_memory:
                self.project_memory.import_from_contract(self._contract)

    def _create_contract_message(self, contract: dict[str, Any]) -> Msg:
        """Create a message containing the contract."""
        if not contract:
            content = "架构契约生成失败，将不使用契约约束。"
        else:
            content = self.format_contract(contract)

        return Msg(
            name=self.name,
            role="assistant",
            content=[TextBlock(type="text", text=content)],
            metadata={
                "contract": contract,
                "project_id": self.project_id,
            },
        )

    def load_contract(self) -> dict[str, Any]:
        """Load the contract from memory pool.

        Returns:
            `dict[str, Any]`:
                The stored contract, or empty dict if not found.
        """
        entry = self.memory_pool.load(self.contract_key)
        if entry:
            try:
                return json.loads(entry.content)
            except json.JSONDecodeError:
                pass
        return {}

    @staticmethod
    def format_contract(contract: dict[str, Any]) -> str:
        """Format contract as human-readable text for Agent context.

        Args:
            contract (`dict[str, Any]`):
                The contract dictionary.

        Returns:
            `str`:
                Formatted contract text.
        """
        if not contract:
            return ""

        parts = ["【架构契约 - 请严格遵循】"]

        # File structure
        file_struct = contract.get("file_structure", {})
        if file_struct:
            parts.append("\n文件结构约定:")
            if "backend" in file_struct:
                be = file_struct["backend"]
                parts.append(f"  后端入口: {be.get('app_entry', 'backend/app/main.py')}")
                parts.append(f"  路由目录: {be.get('routers_dir', 'backend/app/routers')}")
                parts.append(f"  数据库模块: {be.get('database', 'backend/app/database.py')}")
            if "frontend" in file_struct:
                fe = file_struct["frontend"]
                parts.append(f"  前端视图: {fe.get('views_dir', 'frontend/src/views')}")
                parts.append(f"  前端API: {fe.get('api_dir', 'frontend/src/api')}")

        # API endpoints
        endpoints = contract.get("api_endpoints", [])
        if endpoints:
            parts.append("\nAPI 端点定义:")
            for ep in endpoints[:10]:
                methods = ", ".join(ep.get("methods", ["GET"]))
                parts.append(f"  {methods} {ep.get('path', '')} - {ep.get('description', '')}")

        # Import conventions
        imports = contract.get("import_conventions", {})
        if imports:
            parts.append("\n导入约定:")
            for key, value in imports.items():
                parts.append(f"  {key}: {value}")

        # Data models
        models = contract.get("data_models", [])
        if models:
            parts.append("\n数据模型:")
            for model in models[:5]:
                fields = ", ".join([f.get("name", "") for f in model.get("fields", [])[:5]])
                parts.append(f"  {model.get('name', '')}: {fields}")

        return "\n".join(parts)

    async def observe(self, msg: Msg | list[Msg] | None) -> None:
        """Observe messages from other agents."""
        pass  # ArchitectAgent doesn't need to observe for now

    async def reply(self, msg: Msg | list[Msg] | None = None, **kwargs) -> Msg:
        """Reply with the current contract."""
        contract = self.load_contract() or self._contract
        return self._create_contract_message(contract)
