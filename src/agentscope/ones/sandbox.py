# -*- coding: utf-8 -*-
"""Sandbox executor for isolated agent execution using agentscope-runtime."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from .._logging import logger

if TYPE_CHECKING:
    from .manifest import AgentManifest


@dataclass
class SandboxExecutionResult:
    """Result of a sandbox execution."""

    success: bool
    output: Any = None
    error: str | None = None
    logs: list[str] = field(default_factory=list)


class SandboxExecutor:
    """Executor that runs agent code in an isolated Docker sandbox.

    Uses agentscope-runtime's BaseSandbox for isolation.
    Each agent gets its own sandbox with its declared MCP servers.
    """

    def __init__(
        self,
        manifest: "AgentManifest",
        *,
        timeout: int = 300,
        base_url: str | None = None,
    ) -> None:
        """Initialize sandbox executor.

        Args:
            manifest: Agent manifest containing MCP dependencies.
            timeout: Sandbox timeout in seconds.
            base_url: Optional remote sandbox server URL.
        """
        self._manifest = manifest
        self._timeout = timeout
        self._base_url = base_url
        self._sandbox: Any = None
        self._initialized = False

    @property
    def manifest(self) -> "AgentManifest":
        """Get the agent manifest."""
        return self._manifest

    @property
    def is_initialized(self) -> bool:
        """Check if sandbox is initialized."""
        return self._initialized

    def _get_sandbox_class(self) -> type:
        """Lazily import BaseSandbox to avoid hard dependency."""
        try:
            from agentscope_runtime.sandbox import BaseSandbox
            return BaseSandbox
        except ImportError as exc:
            raise ImportError(
                "agentscope-runtime is required for sandbox execution. "
                "Install with: pip install agentscope-runtime"
            ) from exc

    def __enter__(self) -> "SandboxExecutor":
        """Enter sandbox context."""
        self.initialize()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit sandbox context."""
        self.cleanup()

    def initialize(self) -> None:
        """Initialize the sandbox and add MCP servers."""
        if self._initialized:
            return

        BaseSandbox = self._get_sandbox_class()

        # Create sandbox
        kwargs: dict[str, Any] = {"timeout": self._timeout}
        if self._base_url:
            kwargs["base_url"] = self._base_url

        self._sandbox = BaseSandbox(**kwargs)
        self._sandbox.__enter__()

        # Add MCP servers from manifest
        mcp_configs = self._manifest.get_mcp_runtime_configs()
        mcp_server_names = list(mcp_configs.get("mcpServers", {}).keys())
        if mcp_server_names:
            logger.info(
                "Adding MCP servers to sandbox for agent %s: %s",
                self._manifest.id,
                mcp_server_names,
            )
            try:
                self._sandbox.add_mcp_servers(mcp_configs)
            except Exception as exc:
                logger.warning("Failed to add MCP servers: %s", exc)
                # Continue without MCP if optional
                if any(
                    not cfg.optional
                    for cfg in self._manifest.mcp_servers.values()
                ):
                    raise

        self._initialized = True
        logger.info(
            "Sandbox initialized for agent %s (id=%s)",
            self._manifest.name,
            self._sandbox.sandbox_id,
        )

    def cleanup(self) -> None:
        """Cleanup sandbox resources."""
        if self._sandbox is not None:
            try:
                self._sandbox.__exit__(None, None, None)
            except Exception as exc:
                logger.warning("Error cleaning up sandbox: %s", exc)
            finally:
                self._sandbox = None
                self._initialized = False

    def list_tools(self) -> list[dict[str, Any]]:
        """List available tools in the sandbox."""
        if not self._initialized:
            raise RuntimeError("Sandbox not initialized")
        return self._sandbox.list_tools()

    def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> SandboxExecutionResult:
        """Call a tool in the sandbox.

        Args:
            tool_name: Name of the tool to call.
            arguments: Tool arguments.

        Returns:
            SandboxExecutionResult with the tool output.
        """
        if not self._initialized:
            raise RuntimeError("Sandbox not initialized")

        try:
            result = self._sandbox.call_tool(tool_name, arguments or {})
            return SandboxExecutionResult(
                success=True,
                output=result,
            )
        except Exception as exc:
            logger.error("Tool call failed: %s", exc)
            return SandboxExecutionResult(
                success=False,
                error=str(exc),
            )

    def run_python(self, code: str) -> SandboxExecutionResult:
        """Execute Python code in the sandbox.

        Args:
            code: Python code to execute.

        Returns:
            SandboxExecutionResult with execution output.
        """
        if not self._initialized:
            raise RuntimeError("Sandbox not initialized")

        try:
            result = self._sandbox.run_ipython_cell(code=code)
            return SandboxExecutionResult(
                success=True,
                output=result,
            )
        except Exception as exc:
            logger.error("Python execution failed: %s", exc)
            return SandboxExecutionResult(
                success=False,
                error=str(exc),
            )

    def run_shell(self, command: str) -> SandboxExecutionResult:
        """Execute shell command in the sandbox.

        Args:
            command: Shell command to execute.

        Returns:
            SandboxExecutionResult with command output.
        """
        if not self._initialized:
            raise RuntimeError("Sandbox not initialized")

        try:
            result = self._sandbox.run_shell_command(command=command)
            return SandboxExecutionResult(
                success=True,
                output=result,
            )
        except Exception as exc:
            logger.error("Shell command failed: %s", exc)
            return SandboxExecutionResult(
                success=False,
                error=str(exc),
            )

    def get_info(self) -> dict[str, Any]:
        """Get sandbox information."""
        if not self._initialized:
            return {"initialized": False}
        return {
            "initialized": True,
            "sandbox_id": self._sandbox.sandbox_id,
            "agent_id": self._manifest.id,
            "agent_name": self._manifest.name,
            "mcp_servers": list(self._manifest.mcp_servers.keys()),
        }


class SandboxManager:
    """Manager for multiple sandbox executors.

    Provides pooling and lifecycle management for sandboxes.
    """

    def __init__(
        self,
        *,
        default_timeout: int = 300,
        base_url: str | None = None,
    ) -> None:
        """Initialize sandbox manager.

        Args:
            default_timeout: Default timeout for sandboxes.
            base_url: Optional remote sandbox server URL.
        """
        self._default_timeout = default_timeout
        self._base_url = base_url
        self._sandboxes: dict[str, SandboxExecutor] = {}

    def get_or_create(self, manifest: "AgentManifest") -> SandboxExecutor:
        """Get or create a sandbox for an agent.

        Args:
            manifest: Agent manifest.

        Returns:
            SandboxExecutor for the agent.
        """
        if manifest.id in self._sandboxes:
            executor = self._sandboxes[manifest.id]
            if executor.is_initialized:
                return executor

        executor = SandboxExecutor(
            manifest,
            timeout=self._default_timeout,
            base_url=self._base_url,
        )
        executor.initialize()
        self._sandboxes[manifest.id] = executor
        return executor

    def cleanup(self, agent_id: str | None = None) -> None:
        """Cleanup sandboxes.

        Args:
            agent_id: If provided, only cleanup this agent's sandbox.
                     Otherwise cleanup all sandboxes.
        """
        if agent_id:
            if agent_id in self._sandboxes:
                self._sandboxes[agent_id].cleanup()
                del self._sandboxes[agent_id]
        else:
            for executor in self._sandboxes.values():
                executor.cleanup()
            self._sandboxes.clear()

    def __enter__(self) -> "SandboxManager":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.cleanup()
