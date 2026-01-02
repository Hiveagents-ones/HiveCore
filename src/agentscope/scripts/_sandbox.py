# -*- coding: utf-8 -*-
"""Sandbox and workspace management utilities.

This module provides:
- SimpleHTTPServer for serving static files
- BrowserSandboxManager for Playwright testing in Docker
- RuntimeWorkspace for Docker-based code execution
- Shared Docker network for container communication
- Playwright test utilities
"""
from __future__ import annotations

import http.server
import json
import os
import shutil
import socketserver
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from agentscope.mcp import StatefulClientBase


# ---------------------------------------------------------------------------
# Shared Docker Network
# ---------------------------------------------------------------------------
SANDBOX_NETWORK_NAME = "agentscope-sandbox-net"


# ---------------------------------------------------------------------------
# Container Dependency Installation
# ---------------------------------------------------------------------------
def ensure_rsync_installed(container_id: str, timeout: int = 120) -> bool:
    """Ensure rsync is installed in the container.

    This function checks if rsync is available and installs it if missing.
    Uses apt-get for Debian-based containers (e.g., node:20-slim).
    The installation is idempotent - skips if rsync is already installed.

    Args:
        container_id (`str`):
            The Docker container ID to install rsync in.
        timeout (`int`):
            Timeout in seconds for the installation command.

    Returns:
        `bool`: True if rsync is available (already installed or newly installed).
    """
    from ._observability import get_logger

    logger = get_logger()

    try:
        # Check if rsync is already installed
        check_result = subprocess.run(
            ["docker", "exec", container_id, "which", "rsync"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if check_result.returncode == 0:
            logger.debug("[Container] rsync already installed")
            return True

        # Install rsync using apt-get
        logger.info("[Container] Installing rsync...")
        install_result = subprocess.run(
            [
                "docker", "exec", container_id,
                "sh", "-c",
                "apt-get update -qq && apt-get install -y -qq rsync",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if install_result.returncode != 0:
            logger.warn(
                f"[Container] Failed to install rsync: {install_result.stderr}"
            )
            return False

        logger.info("[Container] rsync installed successfully")
        return True

    except subprocess.TimeoutExpired:
        logger.warn("[Container] rsync installation timed out")
        return False
    except Exception as exc:
        logger.warn(f"[Container] Error installing rsync: {exc}")
        return False


async def ensure_rsync_installed_async(container_id: str, timeout: int = 120) -> bool:
    """Ensure rsync is installed in the container (async version).

    This function checks if rsync is available and installs it if missing.
    Uses apt-get for Debian-based containers (e.g., node:20-slim).
    The installation is idempotent - skips if rsync is already installed.

    Args:
        container_id (`str`):
            The Docker container ID to install rsync in.
        timeout (`int`):
            Timeout in seconds for the installation command.

    Returns:
        `bool`: True if rsync is available (already installed or newly installed).
    """
    import asyncio
    from ._observability import get_logger

    logger = get_logger()

    try:
        # Check if rsync is already installed
        check_proc = await asyncio.create_subprocess_exec(
            "docker", "exec", container_id, "which", "rsync",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            await asyncio.wait_for(check_proc.communicate(), timeout=10)
            if check_proc.returncode == 0:
                logger.debug("[Container] rsync already installed")
                return True
        except asyncio.TimeoutError:
            pass

        # Install rsync using apt-get
        logger.info("[Container] Installing rsync...")
        install_proc = await asyncio.create_subprocess_exec(
            "docker", "exec", container_id,
            "sh", "-c",
            "apt-get update -qq && apt-get install -y -qq rsync",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                install_proc.communicate(),
                timeout=timeout,
            )
            if install_proc.returncode != 0:
                logger.warn(
                    f"[Container] Failed to install rsync: {stderr.decode()}"
                )
                return False

            logger.info("[Container] rsync installed successfully")
            return True

        except asyncio.TimeoutError:
            install_proc.terminate()
            logger.warn("[Container] rsync installation timed out")
            return False

    except Exception as exc:
        logger.warn(f"[Container] Error installing rsync: {exc}")
        return False


def ensure_sandbox_network() -> bool:
    """Ensure the shared Docker network exists.

    Returns:
        bool: True if network exists or was created successfully
    """
    try:
        # Check if network exists
        result = subprocess.run(
            ["docker", "network", "inspect", SANDBOX_NETWORK_NAME],
            capture_output=True,
            timeout=10,
        )
        if result.returncode == 0:
            return True

        # Create network
        result = subprocess.run(
            ["docker", "network", "create", SANDBOX_NETWORK_NAME],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# SimpleHTTPServer
# ---------------------------------------------------------------------------
class SimpleHTTPServer:
    """Simple HTTP server for serving static files.

    Used for Playwright testing to access generated HTML files.
    """

    def __init__(self, directory: Path, port: int = 0):
        """Initialize the HTTP server.

        Args:
            directory: Directory to serve files from
            port: Port to listen on (0 for auto-assign)
        """
        self.directory = directory
        self.port = port
        self.server: socketserver.TCPServer | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> int:
        """Start the HTTP server in a background thread.

        Returns:
            int: The port the server is listening on
        """
        handler = http.server.SimpleHTTPRequestHandler

        class QuietHandler(handler):
            def __init__(self, *args, directory: str = "", **kwargs):
                super().__init__(*args, directory=directory, **kwargs)

            def log_message(self, format: str, *args: Any) -> None:
                pass  # Suppress logging

        # Create handler with directory
        def handler_factory(*args: Any, **kwargs: Any) -> QuietHandler:
            return QuietHandler(*args, directory=str(self.directory), **kwargs)

        self.server = socketserver.TCPServer(("127.0.0.1", self.port), handler_factory)
        self.port = self.server.server_address[1]

        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

        return self.port

    def stop(self) -> None:
        """Stop the HTTP server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        if self.thread:
            self.thread.join(timeout=2)
            self.thread = None


# ---------------------------------------------------------------------------
# BrowserSandboxManager
# ---------------------------------------------------------------------------
class BrowserSandboxManager:
    """Manager for browser-based testing in Docker sandbox.

    Uses agentscope-runtime Docker image with Playwright installed.
    Joins shared network to access RuntimeWorkspace HTTP server.
    """

    def __init__(
        self,
        image: str = "agentscope/runtime-sandbox-browser:latest",
        timeout: int = 300,
    ):
        """Initialize the browser sandbox manager.

        Args:
            image: Docker image name
            timeout: Command timeout in seconds
        """
        self.image = image
        self.timeout = timeout
        self.container_id: str | None = None
        self.container_name: str | None = None
        self._started = False

    @property
    def is_available(self) -> bool:
        """Check if Docker and the runtime image are available."""
        try:
            result = subprocess.run(
                ["docker", "images", "-q", self.image],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return bool(result.stdout.strip())
        except Exception:
            return False

    def start(self) -> bool:
        """Start the browser sandbox container.

        Container joins the shared network for accessing RuntimeWorkspace.

        Returns:
            bool: True if started successfully
        """
        from ._observability import get_logger
        logger = get_logger()

        if not self.is_available:
            logger.warn(f"[BrowserSandbox] Docker image not available: {self.image}")
            return False

        # Ensure shared network exists
        ensure_sandbox_network()

        try:
            # Generate unique container name
            import uuid
            self.container_name = f"browser-{uuid.uuid4().hex[:8]}"

            # Start container on shared network
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--rm",
                    "--name", self.container_name,
                    "--network", SANDBOX_NETWORK_NAME,
                    self.image,
                    "tail",
                    "-f",
                    "/dev/null",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                logger.warn(f"[BrowserSandbox] Failed to start: {result.stderr}")
                return False

            self.container_id = result.stdout.strip()
            self._started = True
            logger.info(f"[BrowserSandbox] Started container: {self.container_id[:12]} on network {SANDBOX_NETWORK_NAME}")
            return True
        except Exception as exc:
            logger.warn(f"[BrowserSandbox] Error starting: {exc}")
            return False

    def stop(self) -> None:
        """Stop and remove the container."""
        from ._observability import get_logger
        logger = get_logger()

        if self.container_id:
            try:
                subprocess.run(
                    ["docker", "stop", self.container_id],
                    capture_output=True,
                    timeout=30,
                )
                logger.info(f"[BrowserSandbox] Stopped container: {self.container_id[:12]}")
            except Exception as exc:
                logger.warn(f"[BrowserSandbox] Error stopping: {exc}")
            finally:
                self.container_id = None
                self._started = False

    def execute(self, script: str) -> dict[str, Any]:
        """Execute a Playwright script in the sandbox.

        Args:
            script: Python script to execute

        Returns:
            dict: Execution result with 'success', 'output', 'error' keys
        """
        if not self.container_id:
            return {"success": False, "output": "", "error": "Container not started"}

        try:
            # Write script to temp file and execute
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    self.container_id,
                    "python",
                    "-c",
                    script,
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": "", "error": "Timeout"}
        except Exception as exc:
            return {"success": False, "output": "", "error": str(exc)}


# ---------------------------------------------------------------------------
# RuntimeWorkspace
# ---------------------------------------------------------------------------
class RuntimeWorkspace:
    """Docker-based workspace for code execution.

    Provides isolated environment for:
    - File operations
    - Command execution
    - Code compilation/testing

    Architecture:
    - Container has its own isolated /workspace directory (no volume mount)
    - Claude Code works directly inside the container
    - Files are only exported when validation passes
    - This prevents accidental modification of host files
    """


    def __init__(
        self,
        workspace_dir: str = "/workspace",
        image: str = "agentscope/runtime-sandbox-filesystem:latest",
        timeout: int = 600,
        local_mirror_dir: Path | None = None,  # Deprecated, kept for compatibility
    ):
        """Initialize the runtime workspace.

        Args:
            workspace_dir: Directory path inside container
            image: Docker image name
            timeout: Default command timeout
            local_mirror_dir: Deprecated, no longer used
        """
        self.workspace_dir = workspace_dir
        self.image = image
        self.timeout = timeout

        self.container_id: str | None = None
        self.sandbox_id: str | None = None
        self.container_name: str | None = None
        self.http_port: int = 8080  # HTTP server port inside container
        self._started = False
        self._http_server_started = False

    @property
    def is_initialized(self) -> bool:
        """Check if the workspace is initialized."""
        return self._started and self.container_id is not None

    @property
    def http_url(self) -> str | None:
        """Get the HTTP URL for accessing files from other containers.

        Returns:
            str: URL like http://runtime-xxxx:8080 or None if not available
        """
        if self._http_server_started and self.container_name:
            return f"http://{self.container_name}:{self.http_port}"
        return None

    def start(self) -> bool:
        """Start the runtime workspace container.

        The container runs with an isolated /workspace directory.
        All files stay inside the container.
        Container joins the shared network for inter-container communication.

        Returns:
            bool: True if started successfully
        """
        from ._observability import get_logger
        logger = get_logger()

        # Check if Docker image exists
        try:
            result = subprocess.run(
                ["docker", "images", "-q", self.image],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if not result.stdout.strip():
                logger.warn(f"[RuntimeWorkspace] Docker image not found: {self.image}")
                return False
        except Exception as exc:
            logger.warn(f"[RuntimeWorkspace] Docker check failed: {exc}")
            return False

        # Ensure shared network exists
        ensure_sandbox_network()

        try:
            # Generate unique container name
            import uuid
            self.container_name = f"runtime-{uuid.uuid4().hex[:8]}"

            # Start container with network and name
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--rm",
                    "--name", self.container_name,
                    "--network", SANDBOX_NETWORK_NAME,
                    "-w",
                    self.workspace_dir,
                    self.image,
                    "tail",
                    "-f",
                    "/dev/null",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                logger.warn(f"[RuntimeWorkspace] Failed to start: {result.stderr}")
                return False

            self.container_id = result.stdout.strip()
            self.sandbox_id = self.container_id[:12]
            self._started = True

            # Create workspace directory in container
            subprocess.run(
                ["docker", "exec", self.container_id, "mkdir", "-p", self.workspace_dir],
                capture_output=True,
                timeout=10,
            )

            # Install rsync for directory synchronization
            if not ensure_rsync_installed(self.container_id):
                logger.warn("[RuntimeWorkspace] rsync installation failed, sync operations may not work")

            logger.info(f"[RuntimeWorkspace] Started (isolated): {self.sandbox_id} on network {SANDBOX_NETWORK_NAME}")
            return True
        except Exception as exc:
            logger.warn(f"[RuntimeWorkspace] Error starting: {exc}")
            return False

    def start_http_server(self) -> bool:
        """Start HTTP server inside container to serve workspace files.

        The server runs on port 8080 and serves files from /workspace.
        Other containers on the same network can access via http://{container_name}:8080

        Returns:
            bool: True if server started successfully
        """
        if not self.container_id:
            return False

        from ._observability import get_logger
        logger = get_logger()

        try:
            # Start Python HTTP server in background
            cmd = f"cd {self.workspace_dir} && python3 -m http.server {self.http_port} > /dev/null 2>&1 &"
            result = subprocess.run(
                ["docker", "exec", "-d", self.container_id, "sh", "-c", cmd],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                self._http_server_started = True
                logger.info(f"[RuntimeWorkspace] HTTP server started at {self.http_url}")
                return True
            return False
        except Exception as exc:
            logger.warn(f"[RuntimeWorkspace] Failed to start HTTP server: {exc}")
            return False

    def stop(self) -> None:
        """Stop the runtime workspace container."""
        from ._observability import get_logger
        logger = get_logger()

        if self.container_id:
            try:
                subprocess.run(
                    ["docker", "stop", self.container_id],
                    capture_output=True,
                    timeout=30,
                )
                logger.info(f"[RuntimeWorkspace] Stopped: {self.sandbox_id}")
            except Exception as exc:
                logger.warn(f"[RuntimeWorkspace] Error stopping: {exc}")
            finally:
                self.container_id = None
                self.sandbox_id = None
                self._started = False

    def write_file(self, path: str, content: str) -> bool:
        """Write a file to the workspace inside container.

        Uses docker cp for reliable file transfer instead of base64 encoding.

        Args:
            path: Relative path within workspace
            content: File content

        Returns:
            bool: True if successful
        """
        if not self.container_id:
            return False

        # Skip .git directory files
        if path.startswith(".git/") or path.startswith(".git\\"):
            return True

        try:
            import tempfile
            import os

            full_path = f"{self.workspace_dir}/{path}"

            # Create parent directory in container first
            parent_dir = os.path.dirname(full_path)
            mkdir_result = subprocess.run(
                ["docker", "exec", self.container_id, "mkdir", "-p", parent_dir],
                capture_output=True,
                timeout=30,
            )
            if mkdir_result.returncode != 0:
                return False

            # Write content to temporary file on host
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                suffix=os.path.basename(path),
                delete=False,
            ) as tmp_file:
                tmp_file.write(content)
                tmp_path = tmp_file.name

            try:
                # Use docker cp to copy file to container
                cp_result = subprocess.run(
                    ["docker", "cp", tmp_path, f"{self.container_id}:{full_path}"],
                    capture_output=True,
                    timeout=30,
                )
                if cp_result.returncode != 0:
                    from ._observability import get_logger
                    get_logger().warn(
                        f"[RuntimeWorkspace] docker cp failed {path}: {cp_result.stderr.decode()}"
                    )
                    return False

                # Fix ownership to node user
                chown_result = subprocess.run(
                    ["docker", "exec", self.container_id, "chown", "node:node", full_path],
                    capture_output=True,
                    timeout=30,
                )
                # Ownership fix is optional, don't fail if it doesn't work
                if chown_result.returncode != 0:
                    from ._observability import get_logger
                    get_logger().debug(
                        f"[RuntimeWorkspace] chown skipped {path}: {chown_result.stderr.decode()}"
                    )

                return True
            finally:
                # Clean up temporary file
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
        except Exception as exc:
            from ._observability import get_logger
            get_logger().warn(f"[RuntimeWorkspace] Write failed {path}: {exc}")
            return False

    def write_files(self, files: list[dict[str, str]]) -> list[dict[str, Any]]:
        """Write multiple files to the workspace.

        Args:
            files: List of dicts with 'path' and 'content' keys

        Returns:
            list: Results for each file
        """
        results = []
        for f in files:
            path = f.get("path", "")
            content = f.get("content", "")
            success = self.write_file(path, content)
            results.append({
                "path": path,
                "success": success,
                "error": "" if success else "Write failed",
            })
        return results

    def read_file(self, path: str) -> str:
        """Read a file from the workspace inside container.

        Args:
            path: Relative path within workspace

        Returns:
            str: File content or empty string if not found
        """
        if not self.container_id:
            return ""

        try:
            full_path = f"{self.workspace_dir}/{path}"
            result = subprocess.run(
                ["docker", "exec", self.container_id, "cat", full_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return result.stdout
            return ""
        except Exception:
            return ""

    def list_files(self, pattern: str = "**/*") -> list[str]:
        """List files in the workspace inside container.

        Args:
            pattern: Glob pattern (simplified: only supports * and **)

        Returns:
            list: List of relative file paths
        """
        if not self.container_id:
            return []

        try:
            # Use find command in container, excluding common third-party directories
            # This is critical for performance - node_modules can have 10000+ files
            result = subprocess.run(
                [
                    "docker", "exec", self.container_id, "find", self.workspace_dir,
                    "-type", "f",
                    "-not", "-path", "*/.git/*",
                    "-not", "-path", "*/node_modules/*",
                    "-not", "-path", "*/__pycache__/*",
                    "-not", "-path", "*/.venv/*",
                    "-not", "-path", "*/venv/*",
                    "-not", "-path", "*/.mypy_cache/*",
                    "-not", "-path", "*/.pytest_cache/*",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return []

            files = []
            prefix = self.workspace_dir + "/"
            for line in result.stdout.strip().split("\n"):
                if line and line.startswith(prefix):
                    files.append(line[len(prefix):])
            return files
        except Exception:
            return []

    def list_directory(self, path: str = "") -> list[str]:
        """List entries in a directory inside container.

        Args:
            path: Relative path within workspace (empty for root)

        Returns:
            list: List of entry names (files and directories)
        """
        if not self.container_id:
            return []

        try:
            target_dir = f"{self.workspace_dir}/{path}" if path else self.workspace_dir
            result = subprocess.run(
                ["docker", "exec", self.container_id, "ls", "-1", target_dir],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                return []
            return [name for name in result.stdout.strip().split("\n") if name]
        except Exception:
            return []

    def sync_to_host(self, host_dir: str) -> int:
        """Sync files from container workspace to host directory.

        This is needed for Git operations which run on the host filesystem.
        Only syncs source files, excluding node_modules, __pycache__, .git, etc.

        Args:
            host_dir: Host directory path to sync files to

        Returns:
            int: Number of files synced
        """
        if not self.container_id:
            return 0

        from pathlib import Path
        host_path = Path(host_dir)
        host_path.mkdir(parents=True, exist_ok=True)

        # Get list of source files in container
        files = self.list_files()
        if not files:
            return 0

        synced = 0
        skipped_empty = 0
        skipped_error = 0
        from ._observability import get_logger
        logger = get_logger()

        for rel_path in files:
            # Skip hidden files and common build artifacts
            if rel_path.startswith(".") or "node_modules" in rel_path or "__pycache__" in rel_path:
                continue

            try:
                # Read file content from container
                content = self.read_file(rel_path)
                # Skip if content is empty or None (read_file returns "" on failure)
                if not content:
                    skipped_empty += 1
                    # Log skipped .vue/.js/.ts files for debugging
                    if any(rel_path.endswith(ext) for ext in [".vue", ".js", ".ts", ".py"]):
                        logger.debug(f"[Sync] 跳过空文件: {rel_path}")
                    continue

                # Write to host
                target_path = host_path / rel_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding="utf-8")
                synced += 1
            except Exception as e:
                skipped_error += 1
                logger.debug(f"[Sync] 同步失败: {rel_path} - {e}")
                continue

        if skipped_empty > 0 or skipped_error > 0:
            logger.debug(f"[Sync] 同步统计: {synced} 成功, {skipped_empty} 空文件跳过, {skipped_error} 错误跳过")

        return synced

    def execute_command(
        self,
        command: str,
        timeout: int | None = None,
        working_dir: str | None = None,
    ) -> dict[str, Any]:
        """Execute a command in the container.

        Args:
            command: Shell command to execute
            timeout: Command timeout (uses default if None)
            working_dir: Working directory for command (relative to mount dir)

        Returns:
            dict: Result with 'success', 'output', 'error' keys
        """
        if not self.container_id:
            return {"success": False, "output": "", "error": "Container not started"}

        timeout = timeout or self.timeout

        # Prepend cd if working_dir is specified
        if working_dir:
            command = f"cd {working_dir} && {command}"

        try:
            result = subprocess.run(
                ["docker", "exec", self.container_id, "sh", "-c", command],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": "", "error": f"Timeout ({timeout}s)"}
        except Exception as exc:
            return {"success": False, "output": "", "error": str(exc)}

    def execute_setup_commands(
        self,
        commands: list[str],
    ) -> list[dict[str, Any]]:
        """Execute a list of setup commands.

        Args:
            commands: List of shell commands

        Returns:
            list: Results for each command
        """
        from ._observability import get_logger
        logger = get_logger()
        results = []
        for cmd in commands:
            result = self.execute_command(cmd)
            result["command"] = cmd
            results.append(result)
            if not result["success"]:
                logger.warn(f"[RuntimeWorkspace] Command failed: {cmd}")
        return results



# ---------------------------------------------------------------------------
# PlaywrightDockerManager (Deprecated)
# ---------------------------------------------------------------------------
class PlaywrightDockerManager:
    """Deprecated: Use BrowserSandboxManager instead."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize (deprecated)."""
        import warnings

        warnings.warn(
            "PlaywrightDockerManager is deprecated, use BrowserSandboxManager",
            DeprecationWarning,
        )
        self._sandbox = BrowserSandboxManager()

    def start(self) -> bool:
        """Start (delegates to BrowserSandboxManager)."""
        return self._sandbox.start()

    def stop(self) -> None:
        """Stop (delegates to BrowserSandboxManager)."""
        self._sandbox.stop()


# ---------------------------------------------------------------------------
# Playwright Test Utilities
# ---------------------------------------------------------------------------
async def run_playwright_test(
    client: "StatefulClientBase",
    url: str,
    test_steps: list[dict[str, Any]],
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """Run Playwright tests via MCP client.

    Args:
        client: MCP client with Playwright tools
        url: URL to test
        test_steps: List of test step configurations
        verbose: Whether to print debug info

    Returns:
        dict: Test results with 'passed', 'results', 'errors' keys
    """
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    all_passed = True

    try:
        # Navigate to URL
        nav_result = await client.call_tool("navigate", {"url": url})
        if verbose:
            from ._observability import get_logger
            get_logger().debug(f"[Playwright] Navigated to {url}")

        for step in test_steps:
            step_name = step.get("name", "unnamed")
            action = step.get("action", "")

            try:
                if action == "screenshot":
                    result = await client.call_tool("screenshot", {})
                    results.append({
                        "step": step_name,
                        "passed": True,
                        "result": "Screenshot taken",
                    })
                elif action == "check_text":
                    expected = step.get("expected", "")
                    page_text = await client.call_tool("get_text", {})
                    passed = expected in str(page_text) if expected else True
                    results.append({
                        "step": step_name,
                        "passed": passed,
                        "result": f"Text check: {passed}",
                    })
                    if not passed:
                        all_passed = False
                elif action == "check_element":
                    selector = step.get("selector", "")
                    result = await client.call_tool(
                        "query_selector",
                        {"selector": selector},
                    )
                    passed = result is not None
                    results.append({
                        "step": step_name,
                        "passed": passed,
                        "result": f"Element '{selector}': {'found' if passed else 'not found'}",
                    })
                    if not passed:
                        all_passed = False
                else:
                    results.append({
                        "step": step_name,
                        "passed": True,
                        "result": f"Unknown action: {action}",
                    })
            except Exception as exc:
                results.append({
                    "step": step_name,
                    "passed": False,
                    "result": str(exc),
                })
                all_passed = False
                errors.append(f"{step_name}: {exc}")

    except Exception as exc:
        errors.append(f"Navigation failed: {exc}")
        all_passed = False

    return {
        "passed": all_passed,
        "results": results,
        "errors": errors,
    }


def run_browser_sandbox_test(
    sandbox: BrowserSandboxManager,
    url: str,
    test_steps: list[dict[str, Any]],
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    """Run Playwright tests in browser sandbox.

    Args:
        sandbox: BrowserSandboxManager instance
        url: URL to test
        test_steps: List of test step configurations
        verbose: Whether to print debug info

    Returns:
        dict: Test results with 'passed', 'results', 'errors' keys
    """
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    all_passed = True

    # Build test script
    script_lines = [
        "from playwright.sync_api import sync_playwright",
        "import json",
        "",
        "results = []",
        "with sync_playwright() as p:",
        "    browser = p.chromium.launch(headless=True)",
        "    page = browser.new_page()",
        f'    page.goto("{url}")',
        "",
    ]

    for i, step in enumerate(test_steps):
        step_name = step.get("name", f"step_{i}")
        action = step.get("action", "")

        if action == "screenshot":
            script_lines.append(f'    results.append({{"step": "{step_name}", "passed": True, "result": "Screenshot"}})')
        elif action == "check_text":
            expected = step.get("expected", "")
            if expected:
                script_lines.append(f'    text = page.content()')
                script_lines.append(f'    passed = "{expected}" in text')
                script_lines.append(f'    results.append({{"step": "{step_name}", "passed": passed, "result": "Text check"}})')
            else:
                script_lines.append(f'    results.append({{"step": "{step_name}", "passed": True, "result": "Text check (no expected)"}})')
        elif action == "check_element":
            selector = step.get("selector", "body")
            script_lines.append(f'    try:')
            script_lines.append(f'        el = page.query_selector("{selector}")')
            script_lines.append(f'        passed = el is not None')
            script_lines.append(f'    except:')
            script_lines.append(f'        passed = False')
            script_lines.append(f'    results.append({{"step": "{step_name}", "passed": passed, "result": "Element check"}})')

    script_lines.extend([
        "",
        "    browser.close()",
        "print(json.dumps(results))",
    ])

    script = "\n".join(script_lines)

    if verbose:
        from ._observability import get_logger
        get_logger().debug(f"[BrowserSandbox] Executing test script for {url}")

    # Execute in sandbox
    exec_result = sandbox.execute(script)

    if exec_result["success"]:
        try:
            results = json.loads(exec_result["output"])
            all_passed = all(r.get("passed", False) for r in results)
        except json.JSONDecodeError:
            errors.append(f"Failed to parse results: {exec_result['output']}")
            all_passed = False
    else:
        errors.append(exec_result.get("error", "Unknown error"))
        all_passed = False

    return {
        "passed": all_passed,
        "results": results,
        "errors": errors,
    }


__all__ = [
    "SimpleHTTPServer",
    "BrowserSandboxManager",
    "RuntimeWorkspace",
    "PlaywrightDockerManager",
    "run_playwright_test",
    "run_browser_sandbox_test",
    "ensure_rsync_installed",
    "ensure_rsync_installed_async",
]
