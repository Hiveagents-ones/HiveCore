# -*- coding: utf-8 -*-
"""MCP (Model Context Protocol) client management utilities.

This module provides:
- MCP server configuration parsing
- Client initialization and discovery
- Smithery integration
- Resource summarization
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from agentscope.mcp import StdIOStatefulClient, HttpStatefulClient


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TRUSTED_MCP_DOMAINS: set[str] = {
    "github.com",
    "npmmirror.com",
    "npmjs.org",
    "anthropic.com",
}

MCP_SUMMARY_MAX_TOOLS: int = 6
MCP_DISCOVERY_TOPK: int = 3


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
@dataclass
class MCPServerConfig:
    """Configuration for an MCP server.

    Attributes:
        name: Server name identifier
        transport: Transport type ('sse' or 'stdio')
        url: Server URL for SSE transport
        command: Command for stdio transport
        args: Arguments for stdio transport
    """

    name: str
    transport: str = "sse"
    url: str = ""
    command: str = ""
    args: list[str] = field(default_factory=list)


def parse_mcp_server(raw: str) -> MCPServerConfig:
    """Parse MCP server configuration from command line string.

    Args:
        raw: Configuration string in format 'name,url' or 'name,transport,url'

    Returns:
        MCPServerConfig: Parsed configuration

    Raises:
        ValueError: If format is invalid
    """
    parts = [p.strip() for p in raw.split(",")]
    if len(parts) == 2:
        return MCPServerConfig(name=parts[0], transport="sse", url=parts[1])
    elif len(parts) == 3:
        return MCPServerConfig(name=parts[0], transport=parts[1], url=parts[2])
    else:
        raise ValueError(f"Invalid MCP server format: {raw}")


# ---------------------------------------------------------------------------
# Client Initialization
# ---------------------------------------------------------------------------
async def initialize_mcp_clients(
    configs: list[MCPServerConfig] | None,
    *,
    enable_playwright: bool = False,
    enable_advisor: bool = True,
) -> tuple[list[Any], list[Any]]:
    """Initialize MCP clients from configurations.

    Args:
        configs: List of MCP server configurations
        enable_playwright: Whether to enable Playwright MCP
        enable_advisor: Whether to enable MCP Advisor

    Returns:
        tuple: (regular_clients, aa_side_clients)
    """
    from agentscope.mcp import StdIOStatefulClient, HttpStatefulClient

    clients: list[StdIOStatefulClient | HttpStatefulClient] = []
    aa_clients: list[StdIOStatefulClient | HttpStatefulClient] = []

    if configs:
        for cfg in configs:
            try:
                if cfg.transport == "stdio":
                    client = StdIOStatefulClient(
                        name=cfg.name,
                        command=cfg.command,
                        args=cfg.args,
                    )
                else:
                    client = HttpStatefulClient(name=cfg.name, url=cfg.url)
                await client.connect()
                clients.append(client)
                from ._observability import get_logger
                get_logger().info(f"[MCP] 已连接: {cfg.name} ({cfg.transport})")
            except Exception as exc:
                from ._observability import get_logger
                get_logger().warn(f"[MCP] 连接失败 {cfg.name}: {exc}")

    # Playwright MCP (if enabled)
    if enable_playwright:
        try:
            pw_client = StdIOStatefulClient(
                name="playwright",
                command="npx",
                args=["-y", "@anthropic-ai/mcp-server-playwright"],
            )
            await pw_client.connect()
            clients.append(pw_client)
            from ._observability import get_logger
            get_logger().info("[MCP] Playwright MCP 已连接")
        except Exception as exc:
            from ._observability import get_logger
            get_logger().warn(f"[MCP] Playwright MCP 连接失败: {exc}")

    # MCP Advisor (AA side)
    # See: https://mcpservers.org/servers/olaservo/mcp-advisor
    if enable_advisor:
        try:
            advisor_client = StdIOStatefulClient(
                name="mcp-advisor",
                command="npx",
                args=["-y", "mcp-advisor@latest"],
            )
            await advisor_client.connect()
            aa_clients.append(advisor_client)
            from ._observability import get_logger
            get_logger().info("[MCP] MCP Advisor 已连接 (AA side)")
        except Exception as exc:
            from ._observability import get_logger
            get_logger().warn(f"[MCP] MCP Advisor 连接失败: {exc}")

    return clients, aa_clients


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------
async def discover_mcp_candidates(
    query: str,
    *,
    topk: int = MCP_DISCOVERY_TOPK,
) -> list[dict[str, Any]]:
    """Discover MCP server candidates based on query.

    Args:
        query: Search query for MCP servers
        topk: Maximum number of results

    Returns:
        list: List of candidate server configurations
    """
    # Placeholder for actual discovery logic
    # In production, this would query a registry or use Smithery
    return []


async def build_clients_from_candidates(
    candidates: list[dict[str, Any]],
) -> list[Any]:
    """Build MCP clients from discovered candidates.

    Args:
        candidates: List of candidate configurations

    Returns:
        list: List of connected MCP clients
    """
    from agentscope.mcp import StdIOStatefulClient, HttpStatefulClient

    clients: list[StdIOStatefulClient | HttpStatefulClient] = []

    for candidate in candidates:
        name = candidate.get("name", "unknown")
        transport = candidate.get("transport", "sse")
        url = candidate.get("url", "")

        try:
            if transport == "stdio":
                client = StdIOStatefulClient(
                    name=name,
                    command=candidate.get("command", ""),
                    args=candidate.get("args", []),
                )
            else:
                client = HttpStatefulClient(name=name, url=url)
            await client.connect()
            clients.append(client)
            from ._observability import get_logger
            get_logger().info(f"[MCP] 自动发现并连接: {name}")
        except Exception as exc:
            from ._observability import get_logger
            get_logger().warn(f"[MCP] 自动连接失败 {name}: {exc}")

    return clients


# ---------------------------------------------------------------------------
# Smithery Integration
# ---------------------------------------------------------------------------
async def discover_mcp_via_smithery(
    query: str,
    *,
    topk: int = MCP_DISCOVERY_TOPK,
) -> list[dict[str, Any]]:
    """Discover MCP servers via Smithery registry.

    Args:
        query: Search query
        topk: Maximum number of results

    Returns:
        list: List of Smithery server configurations
    """
    # Placeholder for Smithery API integration
    return []


async def build_clients_from_smithery_configs(
    configs: list[dict[str, Any]],
) -> list[Any]:
    """Build MCP clients from Smithery configurations.

    Args:
        configs: List of Smithery configuration dicts

    Returns:
        list: List of connected MCP clients
    """
    return await build_clients_from_candidates(configs)


# ---------------------------------------------------------------------------
# Summarization
# ---------------------------------------------------------------------------
async def summarize_mcp_clients(
    clients: list[Any],
) -> tuple[str, list[dict[str, Any]]]:
    """Summarize available tools from MCP clients.

    Args:
        clients: List of connected MCP clients

    Returns:
        tuple: (summary_text, resource_handles)
    """
    if not clients:
        return "", []

    summaries: list[str] = []
    resource_handles: list[dict[str, Any]] = []

    for client in clients:
        try:
            tools = await client.list_tools()
            tool_names = [t.get("name", "?") for t in tools[:MCP_SUMMARY_MAX_TOOLS]]
            extra = f" (+{len(tools) - MCP_SUMMARY_MAX_TOOLS} more)" if len(tools) > MCP_SUMMARY_MAX_TOOLS else ""
            summaries.append(f"- {client.name}: {', '.join(tool_names)}{extra}")

            # Collect resource handles
            for tool in tools:
                resource_handles.append({
                    "client": client.name,
                    "tool": tool.get("name", ""),
                    "description": tool.get("description", ""),
                })
        except Exception as exc:
            summaries.append(f"- {client.name}: (工具列表获取失败: {exc})")

    summary_text = "可用 MCP 工具:\n" + "\n".join(summaries) if summaries else ""
    return summary_text, resource_handles


async def advisor_hints(aa_clients: list[Any]) -> str:
    """Get hints from MCP Advisor clients.

    Args:
        aa_clients: List of AA-side MCP clients (typically MCP Advisor)

    Returns:
        str: Advisor hints text
    """
    if not aa_clients:
        return ""

    hints: list[str] = []
    for client in aa_clients:
        if client.name == "mcp-advisor":
            try:
                # Call advisor for hints
                result = await client.call_tool("get_hints", {})
                if result:
                    hints.append(f"MCP Advisor 建议:\n{json.dumps(result, ensure_ascii=False, indent=2)}")
            except Exception as exc:
                hints.append(f"MCP Advisor 获取建议失败: {exc}")

    return "\n".join(hints)


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
async def shutdown_mcp_clients(clients: list[Any]) -> None:
    """Shutdown and disconnect all MCP clients.

    Args:
        clients: List of MCP clients to shutdown
    """
    from ._observability import get_logger
    logger = get_logger()
    for client in clients:
        try:
            await client.close()
            logger.info(f"[MCP] 已断开: {client.name}")
        except Exception as exc:
            logger.warn(f"[MCP] 断开失败 {client.name}: {exc}")


__all__ = [
    "TRUSTED_MCP_DOMAINS",
    "MCP_SUMMARY_MAX_TOOLS",
    "MCP_DISCOVERY_TOPK",
    "MCPServerConfig",
    "parse_mcp_server",
    "initialize_mcp_clients",
    "discover_mcp_candidates",
    "build_clients_from_candidates",
    "discover_mcp_via_smithery",
    "build_clients_from_smithery_configs",
    "summarize_mcp_clients",
    "advisor_hints",
    "shutdown_mcp_clients",
]
