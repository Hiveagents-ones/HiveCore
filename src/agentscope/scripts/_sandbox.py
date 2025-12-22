# -*- coding: utf-8 -*-
"""Sandbox and workspace management utilities.

This module provides:
- SimpleHTTPServer for serving static files
- BrowserSandboxManager for Playwright testing in Docker
- RuntimeWorkspace for Docker-based code execution
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

        Returns:
            bool: True if started successfully
        """
        from ._observability import get_logger
        logger = get_logger()

        if not self.is_available:
            logger.warn(f"[BrowserSandbox] Docker image not available: {self.image}")
            return False

        try:
            # Start container with playwright
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--rm",
                    "--network=host",
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
            logger.info(f"[BrowserSandbox] Started container: {self.container_id[:12]}")
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
    """

    def __init__(
        self,
        workspace_dir: str = "/workspace",
        image: str = "agentscope/runtime-sandbox-filesystem:latest",
        timeout: int = 600,
        local_mirror_dir: Path | None = None,
    ):
        """Initialize the runtime workspace.

        Args:
            workspace_dir: Directory path inside container
            image: Docker image name
            timeout: Default command timeout
            local_mirror_dir: Local directory to mirror workspace files
        """
        self.workspace_dir = workspace_dir
        self.image = image
        self.timeout = timeout
        self.local_mirror_dir = local_mirror_dir

        self.container_id: str | None = None
        self.sandbox_id: str | None = None
        self._mount_dir: Path | None = None
        self._started = False

    @property
    def is_initialized(self) -> bool:
        """Check if the workspace is initialized."""
        return self._started and self.container_id is not None

    @property
    def mount_dir(self) -> Path | None:
        """Get the local mount directory."""
        return self._mount_dir

    def start(self) -> bool:
        """Start the runtime workspace container.

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

        try:
            # Create mount directory
            if self.local_mirror_dir:
                self._mount_dir = self.local_mirror_dir.resolve()  # Use absolute path
                self._mount_dir.mkdir(parents=True, exist_ok=True)
            else:
                import tempfile

                self._mount_dir = Path(tempfile.mkdtemp(prefix="runtime_")).resolve()

            # Start container with volume mount (must use absolute path)
            mount_path = str(self._mount_dir.resolve())
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--rm",
                    "-v",
                    f"{mount_path}:{self.workspace_dir}",
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
            logger.info(f"[RuntimeWorkspace] Started: {self.sandbox_id}")
            return True
        except Exception as exc:
            logger.warn(f"[RuntimeWorkspace] Error starting: {exc}")
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
        """Write a file to the workspace.

        Args:
            path: Relative path within workspace
            content: File content

        Returns:
            bool: True if successful
        """
        if not self._mount_dir:
            return False

        try:
            full_path = self._mount_dir / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            return True
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
        """Read a file from the workspace.

        Args:
            path: Relative path within workspace

        Returns:
            str: File content or empty string if not found
        """
        if not self._mount_dir:
            return ""

        try:
            full_path = self._mount_dir / path
            if full_path.exists():
                return full_path.read_text(encoding="utf-8")
            return ""
        except Exception:
            return ""

    def list_files(self, pattern: str = "**/*") -> list[str]:
        """List files in the workspace.

        Args:
            pattern: Glob pattern

        Returns:
            list: List of relative file paths
        """
        if not self._mount_dir:
            return []

        try:
            files = []
            for p in self._mount_dir.glob(pattern):
                if p.is_file():
                    files.append(str(p.relative_to(self._mount_dir)))
            return files
        except Exception:
            return []

    def execute_command(
        self,
        command: str,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Execute a command in the container.

        Args:
            command: Shell command to execute
            timeout: Command timeout (uses default if None)

        Returns:
            dict: Result with 'success', 'output', 'error' keys
        """
        if not self.container_id:
            return {"success": False, "output": "", "error": "Container not started"}

        timeout = timeout or self.timeout
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

    def sync_to_local(self, local_dir: Path) -> list[str]:
        """Sync workspace files to a local directory.

        Args:
            local_dir: Target local directory

        Returns:
            list: List of synced file paths
        """
        if not self._mount_dir:
            return []

        synced = []
        try:
            # Resolve both paths to absolute paths for comparison
            mount_resolved = self._mount_dir.resolve()
            local_resolved = Path(local_dir).resolve()

            # If source and destination are the same, just list the files
            if mount_resolved == local_resolved:
                for src in self._mount_dir.rglob("*"):
                    if src.is_file():
                        rel = src.relative_to(self._mount_dir)
                        synced.append(str(rel))
                return synced

            # Copy files from mount dir to local dir
            for src in self._mount_dir.rglob("*"):
                if src.is_file():
                    rel = src.relative_to(self._mount_dir)
                    dst = local_resolved / rel
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    synced.append(str(rel))
        except Exception as exc:
            from ._observability import get_logger
            get_logger().warn(f"[RuntimeWorkspace] Sync error: {exc}")

        return synced


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
]
