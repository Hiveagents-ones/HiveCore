# -*- coding: utf-8 -*-
"""AA 专用 toolkit 管理，严格管控敏感能力。"""
from __future__ import annotations

import asyncio
from typing import Any, Coroutine

from agentscope.tool import Toolkit, ToolResponse
from agentscope.message import TextBlock
from agentscope._logging import logger
from agentscope.ones import SmitheryRegistryClient


class AAToolkitManager:
    """Only registers AA-control tools; no business/MCP tools here."""

    def __init__(
        self,
        *,
        enable_agent_admin: bool = False,
        enable_mcp_discovery: bool = True,
    ) -> None:
        self.enable_agent_admin = enable_agent_admin
        self.enable_mcp_discovery = enable_mcp_discovery
        self._smithery_client: SmitheryRegistryClient | None = None

    def build_toolkit(self) -> Toolkit:
        tk = Toolkit()
        tk.create_tool_group(
            "aa_control",
            description="AA 自身控制工具，受限使用",
            active=True,
            notes="仅 AA 可用，用于查询/记录/安全输出，不包含业务工具。",
        )
        tk.register_tool_function(self._emit_log, group_name="aa_control")
        if self.enable_agent_admin:
            tk.register_tool_function(self._deny_create_agent, group_name="aa_control")

        # MCP 发现工具组
        if self.enable_mcp_discovery:
            tk.create_tool_group(
                "mcp_discovery",
                description="MCP 服务器发现工具",
                active=True,
                notes="用于搜索和获取 MCP 服务器配置。",
            )
            tk.register_tool_function(
                self._search_mcp_servers, group_name="mcp_discovery"
            )
            tk.register_tool_function(
                self._get_mcp_config, group_name="mcp_discovery"
            )
        return tk

    @staticmethod
    async def _emit_log(message: str) -> ToolResponse:
        logger.info("[AA toolkit log] %s", message)
        return ToolResponse(content=[TextBlock(type="text", text=f"[aa_log] {message}")])

    @staticmethod
    async def _deny_create_agent(*args, **kwargs) -> ToolResponse:
        return ToolResponse(
            content=[
                TextBlock(
                    type="text",
                    text="[DENY] 出于安全管控，AA 不允许在此路径动态创建 agent。",
                ),
            ],
        )

    @staticmethod
    def _run_coro(coro: Coroutine[Any, Any, Any]) -> Any:
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

    def _get_smithery_client(self) -> SmitheryRegistryClient:
        """Lazily initialize Smithery client."""
        if self._smithery_client is None:
            self._smithery_client = SmitheryRegistryClient()
        return self._smithery_client

    async def _search_mcp_servers(
        self,
        query: str,
        max_results: int = 5,
    ) -> ToolResponse:
        """Search Smithery Registry for MCP servers.

        Args:
            query (`str`):
                Search query. Supports filters like:
                - "owner:username" - Filter by owner
                - "repo:name" - Filter by repository
                - "is:verified" - Only verified servers
                - Or free text search like "browser automation"
            max_results (`int`, optional):
                Maximum number of results to return. Defaults to 5.

        Returns:
            `ToolResponse`:
                List of matching MCP servers with their details.
        """
        client = self._get_smithery_client()
        if not client.is_available:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text="[ERROR] Smithery API key not configured. "
                        "Set SMITHERY_API_KEY environment variable.",
                    )
                ]
            )

        servers = client.search_servers(query, page_size=max_results)
        if not servers:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=f"[INFO] No MCP servers found for query: {query}",
                    )
                ]
            )

        lines = [f"[Smithery MCP Search Results] Found {len(servers)} servers:\n"]
        for idx, server in enumerate(servers, 1):
            lines.append(f"{idx}. {server.display_name}")
            lines.append(f"   qualified_name: {server.qualified_name}")
            lines.append(f"   description: {server.description[:100]}...")
            lines.append(f"   verified: {server.verified}, use_count: {server.use_count}")
            lines.append(f"   remote: {server.remote}")
            lines.append("")

        return ToolResponse(
            content=[TextBlock(type="text", text="\n".join(lines))]
        )

    async def _get_mcp_config(
        self,
        qualified_name: str,
    ) -> ToolResponse:
        """Get MCP server configuration from Smithery.

        Args:
            qualified_name (`str`):
                The qualified name of the MCP server (e.g., "@owner/server-name").
                Use search_mcp_servers to find available servers.

        Returns:
            `ToolResponse`:
                MCP server configuration including command, args, etc.
                This config can be used to create an MCP client.
        """
        client = self._get_smithery_client()
        if not client.is_available:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text="[ERROR] Smithery API key not configured.",
                    )
                ]
            )

        config = client.get_mcp_server_config(qualified_name)
        if not config:
            return ToolResponse(
                content=[
                    TextBlock(
                        type="text",
                        text=f"[ERROR] Could not get config for: {qualified_name}",
                    )
                ]
            )

        import json
        lines = [
            f"[MCP Config] {config.get('name', qualified_name)}",
            f"qualified_name: {qualified_name}",
            "",
            "Configuration:",
            json.dumps(config, indent=2, ensure_ascii=False),
            "",
            "To use this MCP server, add to agent manifest or create client with:",
            f"  command: {config.get('command', 'N/A')}",
            f"  args: {config.get('args', [])}",
        ]

        return ToolResponse(
            content=[TextBlock(type="text", text="\n".join(lines))]
        )
