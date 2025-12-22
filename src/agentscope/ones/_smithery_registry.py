# -*- coding: utf-8 -*-
"""Smithery Registry client for MCP server discovery.

Provides structured MCP server search and configuration extraction,
replacing the text-based mcpadvisor approach.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

from .._logging import logger


SMITHERY_REGISTRY_URL = "https://registry.smithery.ai"


@dataclass
class SmitheryServerInfo:
    """Information about an MCP server from Smithery Registry."""

    qualified_name: str
    display_name: str
    description: str
    remote: bool = False
    verified: bool = False
    use_count: int = 0
    icon_url: str = ""
    homepage: str = ""
    connections: list[dict[str, Any]] = field(default_factory=list)

    def get_stdio_config(self) -> dict[str, Any] | None:
        """Extract stdio connection config if available.

        Returns:
            Dict with 'command' and 'args' keys, or None if not available.
        """
        for conn in self.connections:
            if conn.get("type") == "stdio":
                stdio_func = conn.get("stdioFunction", "")
                if stdio_func:
                    return self._parse_stdio_function(stdio_func)
        return None

    def get_websocket_url(self, config: dict[str, Any] | None = None) -> str | None:
        """Get WebSocket connection URL for remote servers.

        Args:
            config: Optional configuration to encode in URL.

        Returns:
            WebSocket URL string, or None if not a remote server.
        """
        if not self.remote:
            return None
        import base64
        import json

        config_b64 = base64.b64encode(
            json.dumps(config or {}).encode()
        ).decode()
        return f"wss://server.smithery.ai/{self.qualified_name}/ws?config={config_b64}"

    @staticmethod
    def _parse_stdio_function(func_str: str) -> dict[str, Any] | None:
        """Parse stdioFunction string to extract command and args.

        Example input: "() => ({ command: 'npx', args: ['-y', '@pkg/name'] })"
        """
        # Extract command
        cmd_match = re.search(r"command:\s*['\"]([^'\"]+)['\"]", func_str)
        if not cmd_match:
            return None

        command = cmd_match.group(1)

        # Extract args array
        args: list[str] = []
        args_match = re.search(r"args:\s*\[([^\]]*)\]", func_str)
        if args_match:
            args_str = args_match.group(1)
            # Extract quoted strings
            args = re.findall(r"['\"]([^'\"]+)['\"]", args_str)

        return {"command": command, "args": args}


class SmitheryRegistryClient:
    """Client for Smithery Registry API.

    Provides MCP server discovery with structured configuration output.
    """

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize Smithery Registry client.

        Args:
            api_key: Smithery API key. If not provided, reads from
                     SMITHERY_API_KEY environment variable.
        """
        self._api_key = api_key or os.environ.get("SMITHERY_API_KEY", "")
        if not self._api_key:
            logger.warning(
                "SMITHERY_API_KEY not set. Smithery Registry features disabled."
            )

    @property
    def is_available(self) -> bool:
        """Check if the client is properly configured."""
        return bool(self._api_key)

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authentication."""
        return {"Authorization": f"Bearer {self._api_key}"}

    def search_servers(
        self,
        query: str,
        *,
        page: int = 1,
        page_size: int = 10,
        verified_only: bool = False,
        remote_only: bool = False,
    ) -> list[SmitheryServerInfo]:
        """Search for MCP servers in the registry.

        Args:
            query: Search query. Supports filters like:
                   - "owner:username" - Filter by owner
                   - "repo:name" - Filter by repository
                   - "is:verified" - Only verified servers
                   - "is:deployed" - Only deployed servers
            page: Page number (1-indexed).
            page_size: Results per page.
            verified_only: If True, add "is:verified" filter.
            remote_only: If True, only return remote-capable servers.

        Returns:
            List of SmitheryServerInfo objects.
        """
        if not self.is_available:
            logger.warning("Smithery API key not configured")
            return []

        try:
            import requests
        except ImportError:
            logger.error("requests library required for Smithery Registry")
            return []

        # Build query with filters
        search_query = query
        if verified_only and "is:verified" not in query:
            search_query = f"{query} is:verified"

        params = {
            "q": search_query,
            "page": str(page),
            "pageSize": str(page_size),
        }

        try:
            resp = requests.get(
                f"{SMITHERY_REGISTRY_URL}/servers",
                params=params,
                headers=self._get_headers(),
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.error("Smithery Registry search failed: %s", exc)
            return []

        servers = []
        for item in data.get("servers", []):
            if remote_only and not item.get("remote", False):
                continue
            servers.append(
                SmitheryServerInfo(
                    qualified_name=item.get("qualifiedName", ""),
                    display_name=item.get("displayName", ""),
                    description=item.get("description", ""),
                    remote=item.get("remote", False),
                    verified=item.get("verified", False),
                    use_count=item.get("useCount", 0),
                    icon_url=item.get("iconUrl", ""),
                    homepage=item.get("homepage", ""),
                )
            )

        return servers

    def get_server_details(
        self,
        qualified_name: str,
    ) -> SmitheryServerInfo | None:
        """Get detailed information about a specific MCP server.

        Args:
            qualified_name: Server qualified name (e.g., "@owner/server-name").

        Returns:
            SmitheryServerInfo with full details including connections,
            or None if not found.
        """
        if not self.is_available:
            logger.warning("Smithery API key not configured")
            return None

        try:
            import requests
        except ImportError:
            logger.error("requests library required for Smithery Registry")
            return None

        try:
            resp = requests.get(
                f"{SMITHERY_REGISTRY_URL}/servers/{qualified_name}",
                headers=self._get_headers(),
                timeout=30,
            )
            resp.raise_for_status()
            item = resp.json()
        except Exception as exc:
            logger.error("Failed to get server details for %s: %s", qualified_name, exc)
            return None

        return SmitheryServerInfo(
            qualified_name=item.get("qualifiedName", ""),
            display_name=item.get("displayName", ""),
            description=item.get("description", ""),
            remote=item.get("remote", False),
            verified=item.get("verified", False),
            use_count=item.get("useCount", 0),
            icon_url=item.get("iconUrl", ""),
            homepage=item.get("homepage", ""),
            connections=item.get("connections", []),
        )

    def get_mcp_server_config(
        self,
        qualified_name: str,
    ) -> dict[str, Any] | None:
        """Get MCP server configuration ready for use.

        Args:
            qualified_name: Server qualified name.

        Returns:
            Dict with 'name', 'command', 'args', 'env' keys suitable
            for MCPServerConfig, or None if not available.
        """
        server = self.get_server_details(qualified_name)
        if not server:
            return None

        stdio_config = server.get_stdio_config()
        if stdio_config:
            return {
                "name": server.display_name or qualified_name.split("/")[-1],
                "command": stdio_config["command"],
                "args": stdio_config["args"],
                "env": {},
                "optional": False,
                "source": "smithery",
                "qualified_name": qualified_name,
            }

        # For remote servers, return WebSocket info
        if server.remote:
            ws_url = server.get_websocket_url()
            return {
                "name": server.display_name or qualified_name.split("/")[-1],
                "transport": "websocket",
                "url": ws_url,
                "source": "smithery",
                "qualified_name": qualified_name,
            }

        return None


def search_and_get_mcp_configs(
    query: str,
    *,
    max_results: int = 5,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    """Search Smithery and return ready-to-use MCP configurations.

    Convenience function that combines search and config extraction.

    Args:
        query: Search query for MCP servers.
        max_results: Maximum number of results to return.
        api_key: Optional API key (defaults to env var).

    Returns:
        List of MCP configuration dicts ready for MCPServerConfig.
    """
    client = SmitheryRegistryClient(api_key)
    if not client.is_available:
        return []

    servers = client.search_servers(query, page_size=max_results * 2)
    configs = []

    for server in servers[:max_results * 2]:
        config = client.get_mcp_server_config(server.qualified_name)
        if config:
            configs.append(config)
            if len(configs) >= max_results:
                break

    return configs
