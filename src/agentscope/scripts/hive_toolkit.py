# -*- coding: utf-8 -*-
"""HiveCore-specific toolkit management."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Sequence, Any, Coroutine

from agentscope._logging import logger
from agentscope.mcp import MCPClientBase
from agentscope.message import TextBlock
from agentscope.tool import Toolkit, metaso_search, metaso_read, metaso_chat, ToolResponse
from agentscope.tool import view_text_file, write_text_file, insert_text_file
from agentscope.tool import execute_shell_command, execute_python_code


class HiveToolkitManager:
    """Factory/helper that builds toolkits with秘塔、MCP及交付长链工具。"""

    def __init__(self, *, mcp_clients: Sequence[MCPClientBase] | None = None, llm: Any | None = None) -> None:
        self._mcp_clients = list(mcp_clients or [])
        self._llm = llm

    def build_toolkit(self, tools_filter: set[str] | None = None) -> Toolkit:
        """Create a fresh toolkit instance containing Metaso + MCP + 文件操作工具.

        Args:
            tools_filter: Optional set of tool names to include. If provided,
                only tools whose names are in this set will be registered.
                If None, all tools are registered.

        Returns:
            A Toolkit instance with the requested tools.
        """
        toolkit = Toolkit()
        self._register_file_tools(toolkit, tools_filter)
        self._register_execution_tools(toolkit, tools_filter)
        self._register_metaso_tools(toolkit, tools_filter)
        self._register_mcp_clients(toolkit, tools_filter)
        if self._llm is not None:
            self._register_delivery_tools(toolkit, tools_filter)
        return toolkit

    def _register_file_tools(
        self,
        toolkit: Toolkit,
        tools_filter: set[str] | None = None,
    ) -> None:
        """注册文件操作工具到 toolkit（类似 Claude Code 的增删改查能力）.

        Args:
            toolkit: The toolkit to register tools to.
            tools_filter: Optional set of tool names to include.
        """
        file_tools = [
            ("view_text_file", view_text_file),
            ("write_text_file", write_text_file),
            ("insert_text_file", insert_text_file),
        ]
        # Filter tools if whitelist provided
        if tools_filter is not None:
            file_tools = [(n, f) for n, f in file_tools if n in tools_filter]
        if not file_tools:
            return

        if "file_ops" not in toolkit.groups:
            toolkit.create_tool_group(
                "file_ops",
                description="文件操作工具（读取、写入、插入、编辑）",
                active=True,
                notes="""【文件操作工具使用指南】
- view_text_file: 查看文件内容，支持指定行号范围 [start, end]
- write_text_file: 创建新文件或覆盖现有文件，支持部分替换（指定 ranges=[start, end] 只替换指定行）
- insert_text_file: 在指定行号处插入新内容

【编辑最佳实践】
1. 修改代码前，先用 view_text_file 查看相关代码段
2. 使用 write_text_file 的 ranges 参数进行精确替换，避免破坏其他代码
3. 确保替换内容包含完整的代码单元（完整的函数、类、语句等）
4. 编辑后再次使用 view_text_file 验证修改结果
""",
            )
        for _, func in file_tools:
            toolkit.register_tool_function(func, group_name="file_ops")

    def _register_execution_tools(
        self,
        toolkit: Toolkit,
        tools_filter: set[str] | None = None,
    ) -> None:
        """注册代码执行工具到 toolkit.

        Args:
            toolkit: The toolkit to register tools to.
            tools_filter: Optional set of tool names to include.
        """
        exec_tools = [
            ("execute_shell_command", execute_shell_command),
            ("execute_python_code", execute_python_code),
        ]
        # Filter tools if whitelist provided
        if tools_filter is not None:
            exec_tools = [(n, f) for n, f in exec_tools if n in tools_filter]
        if not exec_tools:
            return

        if "code_exec" not in toolkit.groups:
            toolkit.create_tool_group(
                "code_exec",
                description="代码执行工具（Shell 命令、Python 代码）",
                active=True,
                notes="""【代码执行工具使用指南】
- execute_shell_command: 执行 shell 命令（如 npm、pip、git 等）
- execute_python_code: 执行 Python 代码片段

【安全注意事项】
1. 避免执行危险命令（rm -rf、sudo 等）
2. 优先使用文件操作工具，仅在必要时使用 shell
3. 执行前确认命令的安全性
""",
            )
        for _, func in exec_tools:
            toolkit.register_tool_function(func, group_name="code_exec")

    def _register_metaso_tools(
        self,
        toolkit: Toolkit,
        tools_filter: set[str] | None = None,
    ) -> None:
        """Expose秘塔常用工具到 toolkit.

        Args:
            toolkit: The toolkit to register tools to.
            tools_filter: Optional set of tool names to include.
        """
        metaso_tools = [
            ("metaso_search", metaso_search),
            ("metaso_read", metaso_read),
            ("metaso_chat", metaso_chat),
        ]
        # Filter tools if whitelist provided
        if tools_filter is not None:
            metaso_tools = [(n, f) for n, f in metaso_tools if n in tools_filter]
        if not metaso_tools:
            return

        if "metaso" not in toolkit.groups:
            toolkit.create_tool_group(
                "metaso",
                description="秘塔搜索/阅读/对话工具",
                active=True,
                notes="用于信息检索、拉取原文和秘塔对话生成。",
            )
        for _, func in metaso_tools:
            toolkit.register_tool_function(func, group_name="metaso")

    def _register_mcp_clients(
        self,
        toolkit: Toolkit,
        tools_filter: set[str] | None = None,
    ) -> None:
        """将 MCP 客户端内的工具批量注册到 toolkit.

        Args:
            toolkit: The toolkit to register tools to.
            tools_filter: Optional set of tool names to include.
        """
        if not self._mcp_clients:
            return
        if "mcp" not in toolkit.groups:
            toolkit.create_tool_group(
                "mcp",
                description="外接 MCP 工具集",
                active=True,
                notes="包含 Playwright 等外部工具，可按需调用。",
            )

        async def _do_register() -> None:
            for client in self._mcp_clients:
                try:
                    # Use enable_funcs to filter MCP tools
                    enable_funcs = list(tools_filter) if tools_filter else None
                    await toolkit.register_mcp_client(
                        client,
                        group_name="mcp",
                        enable_funcs=enable_funcs,
                    )
                except Exception as exc:  # pragma: no cover - best effort
                    name = getattr(client, "name", "unknown")
                    logger.warning("注册 MCP 客户端 %s 失败: %s", name, exc)

        self._run_coro(_do_register())

    def _register_delivery_tools(
        self,
        toolkit: Toolkit,
        tools_filter: set[str] | None = None,
    ) -> None:
        """Expose 设计/实现/QA 工具，便于 AA/Agent 自主调用。

        Args:
            toolkit: The toolkit to register tools to.
            tools_filter: Optional set of tool names to include.
        """
        async def design_tool(
            requirement: str | dict[str, Any],
            feedback: str = "",
            passed_ids: list[str] | None = None,
            failed_criteria: list[dict[str, Any]] | None = None,
            prev_blueprint: str | dict[str, Any] | None = None,
            contextual_notes: str | None = None,
        ) -> ToolResponse:
            try:
                from agentscope.scripts import full_user_flow_cli as flow  # 避免循环导入
                req_obj = self._ensure_obj(requirement)
                prev_bp_obj = self._ensure_obj(prev_blueprint) if prev_blueprint else None
                resp = await flow.design_requirement(
                    self._llm,
                    req_obj,
                    feedback,
                    set(passed_ids or []),
                    failed_criteria or [],
                    prev_bp_obj,
                    contextual_notes=contextual_notes,
                )
                return self._json_response(resp)
            except Exception as exc:
                return self._error_response(f"design_requirement 调用失败: {exc}")

        async def implement_tool(
            requirement: str | dict[str, Any],
            blueprint: str | dict[str, Any],
            feedback: str = "",
            passed_ids: list[str] | None = None,
            failed_criteria: list[dict[str, Any]] | None = None,
            previous_artifact: str = "",
            contextual_notes: str | None = None,
        ) -> ToolResponse:
            try:
                from agentscope.scripts import full_user_flow_cli as flow
                req_obj = self._ensure_obj(requirement)
                bp_obj = self._ensure_obj(blueprint)
                resp = await flow.implement_requirement(
                    self._llm,
                    req_obj,
                    bp_obj,
                    feedback,
                    set(passed_ids or []),
                    failed_criteria or [],
                    previous_artifact,
                    contextual_notes=contextual_notes,
                )
                return self._json_response(resp)
            except Exception as exc:
                return self._error_response(f"implement_requirement 调用失败: {exc}")

        async def qa_tool(
            requirement: str | dict[str, Any],
            blueprint: str | dict[str, Any],
            artifact_path: str,
            criteria: list[dict[str, Any]] | None = None,
            round_index: int = 1,
        ) -> ToolResponse:
            try:
                from agentscope.scripts import full_user_flow_cli as flow
                req_obj = self._ensure_obj(requirement)
                bp_obj = self._ensure_obj(blueprint)
                path = Path(artifact_path)
                resp = await flow.qa_requirement(
                    llm=self._llm,
                    requirement=req_obj,
                    blueprint=bp_obj,
                    artifact_path=path,
                    criteria=criteria or [],
                    round_index=round_index,
                )
                return self._json_response(resp)
            except Exception as exc:
                return self._error_response(f"qa_requirement 调用失败: {exc}")

        # Define all delivery tools with their names
        delivery_tools = [
            ("design_tool", design_tool),
            ("implement_tool", implement_tool),
            ("qa_tool", qa_tool),
        ]
        # Filter tools if whitelist provided
        if tools_filter is not None:
            delivery_tools = [(n, f) for n, f in delivery_tools if n in tools_filter]
        if not delivery_tools:
            return

        if "delivery" not in toolkit.groups:
            toolkit.create_tool_group(
                "delivery",
                description="HiveCore 交付流程工具（设计/实现/QA）",
                active=True,
                notes="需要提供需求/Blueprint/验收标准等上下文。",
            )

        for _, func in delivery_tools:
            toolkit.register_tool_function(func, group_name="delivery")

    @staticmethod
    def _json_response(obj: Any) -> ToolResponse:
        text = json.dumps(obj, ensure_ascii=False, indent=2)
        return ToolResponse(content=[TextBlock(type="text", text=text)])

    @staticmethod
    def _error_response(msg: str) -> ToolResponse:
        return ToolResponse(content=[TextBlock(type="text", text=f"[ERROR] {msg}")])

    @staticmethod
    def _ensure_obj(obj: Any) -> Any:
        if obj is None:
            return {}
        if isinstance(obj, (dict, list)):
            return obj
        if isinstance(obj, str):
            try:
                return json.loads(obj)
            except Exception:
                return {"value": obj}
        return obj

    @staticmethod
    def _run_coro(coro: Coroutine[Any, Any, Any]) -> Any:
        """Utility to run async code regardless of当前线程是否已有 loop."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            new_loop = asyncio.new_event_loop()
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()
        return asyncio.run(coro)

