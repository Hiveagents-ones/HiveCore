# -*- coding: utf-8 -*-
"""AWS ECS-based RuntimeWorkspace for multi-tenant code execution.

This module provides isolated code execution environment using AWS ECS Fargate tasks.
Each execution gets its own container with isolated filesystem and network.

Architecture:
- Worker triggers ECS task for code execution
- ECS task runs the runtime-sandbox container
- Files are transferred via S3 or EFS
- Results are returned via S3

Usage::

    from agentscope.scripts._aws_runtime import AWSRuntimeWorkspace

    # Initialize workspace
    workspace = AWSRuntimeWorkspace(
        execution_id="exec-123",
        tenant_id="tenant-abc",
    )

    # Start the execution container
    await workspace.start()

    # Write files
    workspace.write_file("src/main.py", "print('hello')")

    # Execute commands
    result = workspace.execute_command("python src/main.py")

    # Read files back
    content = workspace.read_file("output.txt")

    # Stop and cleanup
    await workspace.stop()
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _filter_ecs_exec_output(output: str) -> str:
    """Filter out ECS Exec session manager messages from command output.

    Args:
        output: Raw output from ecs execute-command

    Returns:
        Filtered output with only the actual command result
    """
    lines = []
    for line in output.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        # Skip session manager messages - check if line starts with or contains these patterns
        if (stripped.startswith("The Session Manager plugin") or
            stripped.startswith("Starting session with") or
            stripped.startswith("Exiting session with") or
            stripped.startswith("Cannot perform start session") or
            "SessionId:" in stripped or
            "session with SessionId:" in stripped.lower()):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


class AWSRuntimeWorkspace:
    """AWS ECS-based workspace for isolated code execution.

    Provides multi-tenant isolation using:
    - Separate ECS Fargate task per execution
    - S3 bucket for file transfer (isolated by execution_id)
    - VPC security groups for network isolation

    Args:
        execution_id (`str`):
            Unique identifier for this execution.
        tenant_id (`str`):
            Tenant identifier for isolation.
        cluster_name (`str`):
            ECS cluster name. Defaults to 'hivecore-cluster'.
        task_definition (`str`):
            ECS task definition for sandbox. Defaults to 'hivecore-sandbox'.
        s3_bucket (`str | None`):
            S3 bucket for file transfer. Defaults to env var HIVECORE_S3_BUCKET.
        region (`str`):
            AWS region. Defaults to 'ap-northeast-1'.
        timeout (`int`):
            Task timeout in seconds. Defaults to 600.
    """

    def __init__(
        self,
        execution_id: str,
        tenant_id: str,
        project_id: str | None = None,
        cluster_name: str = "hivecore-cluster",
        task_definition: str = "hivecore-sandbox",
        s3_bucket: str | None = None,
        region: str = "ap-northeast-1",
        timeout: int = 600,
    ) -> None:
        """Initialize the AWS runtime workspace.

        S3 path structure for multi-tenant multi-project isolation:
            s3://bucket/tenants/{tenant_id}/projects/{project_id}/executions/{execution_id}/files/
        """
        self.execution_id = execution_id
        self.tenant_id = tenant_id
        self.project_id = project_id
        self.cluster_name = cluster_name
        self.task_definition = task_definition
        self.s3_bucket = s3_bucket or os.getenv("HIVECORE_S3_BUCKET", "hivecore-workspaces")
        self.region = region
        self.timeout = timeout

        self.workspace_dir = "/workspace"
        self.task_arn: str | None = None
        self.container_ip: str | None = None
        self._started = False
        self._local_cache: dict[str, str] = {}  # Cache files locally

        # S3 prefix for this execution (hierarchical: tenant -> project -> execution)
        if project_id:
            self.s3_prefix = f"tenants/{tenant_id}/projects/{project_id}/executions/{execution_id}"
        else:
            self.s3_prefix = f"tenants/{tenant_id}/executions/{execution_id}"

        # Lazy-loaded AWS clients
        self._ecs_client: Any = None
        self._s3_client: Any = None

    @property
    def base_workspace_dir(self) -> str:
        """Base workspace directory for compatibility with AcceptanceAgent.

        AcceptanceAgent expects this attribute name.
        """
        return self.workspace_dir

    @property
    def ecs_client(self) -> Any:
        """Lazy-initialized ECS client."""
        if self._ecs_client is None:
            import boto3
            self._ecs_client = boto3.client("ecs", region_name=self.region)
        return self._ecs_client

    @property
    def s3_client(self) -> Any:
        """Lazy-initialized S3 client."""
        if self._s3_client is None:
            import boto3
            self._s3_client = boto3.client("s3", region_name=self.region)
        return self._s3_client

    @property
    def is_initialized(self) -> bool:
        """Check if the workspace is initialized."""
        return self._started and self.task_arn is not None

    async def attach(self, task_arn: str) -> bool:
        """Attach to an existing ECS task.

        Use this to reuse a container across multiple requirements within
        the same project/execution round.

        Args:
            task_arn: ARN of the running ECS task.

        Returns:
            `bool`: True if successfully attached.
        """
        try:
            # Verify task is running
            response = self.ecs_client.describe_tasks(
                cluster=self.cluster_name,
                tasks=[task_arn],
            )

            if not response.get("tasks"):
                logger.error(f"[AWSRuntime] Task not found: {task_arn}")
                return False

            task = response["tasks"][0]
            status = task.get("lastStatus")

            if status != "RUNNING":
                logger.error(f"[AWSRuntime] Task not running: {status}")
                return False

            self.task_arn = task_arn
            self._started = True

            # Get container IP
            attachments = task.get("attachments", [])
            for att in attachments:
                if att.get("type") == "ElasticNetworkInterface":
                    for detail in att.get("details", []):
                        if detail.get("name") == "privateIPv4Address":
                            self.container_ip = detail.get("value")
                            break

            logger.info(f"[AWSRuntime] Attached to task: {task_arn}, IP: {self.container_ip}")
            return True

        except Exception as e:
            logger.error(f"[AWSRuntime] Error attaching to task: {e}")
            return False

    async def start(self) -> bool:
        """Start the ECS task for code execution.

        Returns:
            `bool`: True if started successfully.
        """
        try:
            # Run ECS task
            response = self.ecs_client.run_task(
                cluster=self.cluster_name,
                taskDefinition=self.task_definition,
                launchType="FARGATE",
                enableExecuteCommand=True,  # Required for ecs execute-command
                networkConfiguration={
                    "awsvpcConfiguration": {
                        "subnets": self._get_subnets(),
                        "securityGroups": self._get_security_groups(),
                        # ENABLED - required for accessing Secrets Manager and ECR
                        "assignPublicIp": "ENABLED",
                    }
                },
                overrides={
                    "containerOverrides": [
                        {
                            "name": "sandbox",
                            "environment": [
                                {"name": "EXECUTION_ID", "value": self.execution_id},
                                {"name": "TENANT_ID", "value": self.tenant_id},
                                {"name": "S3_BUCKET", "value": self.s3_bucket},
                                {"name": "S3_PREFIX", "value": self.s3_prefix},
                            ],
                        }
                    ]
                },
                tags=[
                    {"key": "execution_id", "value": self.execution_id},
                    {"key": "tenant_id", "value": self.tenant_id},
                ],
            )

            if not response.get("tasks"):
                failures = response.get("failures", [])
                logger.error(f"[AWSRuntime] Failed to start task: {failures}")
                return False

            self.task_arn = response["tasks"][0]["taskArn"]
            logger.info(f"[AWSRuntime] Started task: {self.task_arn}")

            # Wait for task to be running
            if not await self._wait_for_task_running():
                logger.error("[AWSRuntime] Task failed to reach RUNNING state within timeout")
                return False

            self._started = True
            return True

        except Exception as e:
            logger.error(f"[AWSRuntime] Error starting task: {e}")
            return False

    async def _wait_for_task_running(self, max_wait: int = 300) -> bool:
        """Wait for task to reach RUNNING state.

        Args:
            max_wait: Maximum wait time in seconds.

        Returns:
            `bool`: True if task is running.
        """
        import asyncio

        start_time = time.time()
        while time.time() - start_time < max_wait:
            response = self.ecs_client.describe_tasks(
                cluster=self.cluster_name,
                tasks=[self.task_arn],
            )

            if response.get("tasks"):
                task = response["tasks"][0]
                status = task.get("lastStatus")

                if status == "RUNNING":
                    # Get container IP for direct communication
                    attachments = task.get("attachments", [])
                    for att in attachments:
                        if att.get("type") == "ElasticNetworkInterface":
                            for detail in att.get("details", []):
                                if detail.get("name") == "privateIPv4Address":
                                    self.container_ip = detail.get("value")
                                    break
                    logger.info(f"[AWSRuntime] Task running, IP: {self.container_ip}")
                    # Wait additional time for execute command agent to be ready
                    # The execute command agent needs extra time after task is RUNNING
                    logger.info("[AWSRuntime] Waiting for execute command agent to be ready...")
                    await asyncio.sleep(10)
                    return True

                elif status in ("STOPPED", "DEPROVISIONING"):
                    logger.error(f"[AWSRuntime] Task stopped unexpectedly")
                    return False

            await asyncio.sleep(2)

        logger.error(f"[AWSRuntime] Timeout waiting for task to start")
        return False

    async def stop(self) -> None:
        """Stop the ECS task and cleanup resources."""
        if self.task_arn:
            try:
                self.ecs_client.stop_task(
                    cluster=self.cluster_name,
                    task=self.task_arn,
                    reason="Execution completed",
                )
                logger.info(f"[AWSRuntime] Stopped task: {self.task_arn}")
            except Exception as e:
                logger.warning(f"[AWSRuntime] Error stopping task: {e}")
            finally:
                self.task_arn = None
                self._started = False

        # Cleanup S3 files (optional, could keep for debugging)
        # self._cleanup_s3_files()

    def write_file(self, path: str, content: str) -> bool:
        """Write a file to the workspace via S3.

        Args:
            path: Relative path within workspace.
            content: File content.

        Returns:
            `bool`: True if successful.
        """
        if path.startswith(".git/"):
            return True

        try:
            s3_key = f"{self.s3_prefix}/files/{path}"
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=content.encode("utf-8"),
            )

            # Cache locally
            self._local_cache[path] = content

            logger.debug(f"[AWSRuntime] Wrote file: {path}")
            return True

        except Exception as e:
            logger.error(f"[AWSRuntime] Error writing file {path}: {e}")
            return False

    def write_files(self, files: list[dict[str, str]]) -> list[dict[str, Any]]:
        """Write multiple files to the workspace.

        Args:
            files: List of dicts with 'path' and 'content' keys.

        Returns:
            `list`: Results for each file.
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
            path: Relative path within workspace.

        Returns:
            `str`: File content.
        """
        # Check local cache first
        if path in self._local_cache:
            return self._local_cache[path]

        try:
            s3_key = f"{self.s3_prefix}/files/{path}"
            response = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
            )
            content = response["Body"].read().decode("utf-8")
            self._local_cache[path] = content
            return content

        except self.s3_client.exceptions.NoSuchKey:
            return ""
        except Exception as e:
            logger.error(f"[AWSRuntime] Error reading file {path}: {e}")
            return ""

    async def read_files_async(
        self,
        files: list[str],
        max_files: int = 20,
    ) -> dict[str, str]:
        """Async version: Read multiple files from the workspace.

        Uses ECS exec to read files directly from the container.

        Args:
            files: List of relative file paths to read.
            max_files: Maximum number of files to read.

        Returns:
            `dict[str, str]`: Mapping of file path to content.
        """
        if not self.task_arn:
            logger.warning("[AWSRuntime] Cannot read files: task not running")
            return {}

        result = {}
        files_to_read = files[:max_files]

        for file_path in files_to_read:
            try:
                import subprocess

                # Read file using cat
                full_path = f"{self.workspace_dir}/{file_path}"
                cat_command = f"cat '{full_path}' 2>/dev/null"
                escaped_command = cat_command.replace("'", "'\\''")
                exec_cmd = [
                    "aws", "ecs", "execute-command",
                    "--cluster", self.cluster_name,
                    "--task", self.task_arn,
                    "--container", "sandbox",
                    "--command", f"/bin/bash -c '{escaped_command}'",
                    "--interactive",
                    "--region", self.region,
                ]

                process = subprocess.Popen(
                    exec_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                try:
                    stdout, stderr = process.communicate(timeout=30)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    logger.warning(f"[AWSRuntime] Timeout reading file: {file_path}")
                    continue

                if process.returncode == 0:
                    # Filter out ECS session messages
                    content = _filter_ecs_exec_output(stdout)
                    result[file_path] = content
                    logger.debug(f"[AWSRuntime] Read file: {file_path} ({len(content)} bytes)")
                else:
                    logger.warning(f"[AWSRuntime] Failed to read file: {file_path}")

            except Exception as e:
                logger.warning(f"[AWSRuntime] Error reading file {file_path}: {e}")

        logger.info(f"[AWSRuntime] read_files_async: read {len(result)}/{len(files_to_read)} files")
        return result

    def list_files(self) -> list[str]:
        """List all files in the workspace.

        Returns:
            `list[str]`: List of file paths.
        """
        return self.list_directory("")

    async def list_files_async(self, max_files: int = 50) -> list[str]:
        """Async version: List all files in the workspace recursively.

        This method uses ECS exec to run find command to get all files
        (not directories) in the workspace.

        Args:
            max_files: Maximum number of files to return.

        Returns:
            `list[str]`: List of relative file paths.
        """
        if not self.task_arn:
            logger.warning("[AWSRuntime] Cannot list files: task not running")
            return []

        try:
            import subprocess

            # Use find to list all files recursively (exclude .git)
            find_command = f"find {self.workspace_dir} -type f ! -path '*/.git/*' 2>/dev/null | head -n {max_files}"
            escaped_command = find_command.replace("'", "'\\''")
            exec_cmd = [
                "aws", "ecs", "execute-command",
                "--cluster", self.cluster_name,
                "--task", self.task_arn,
                "--container", "sandbox",
                "--command", f"/bin/bash -c '{escaped_command}'",
                "--interactive",
                "--region", self.region,
            ]

            logger.debug(f"[AWSRuntime] Running: {' '.join(exec_cmd)}")

            process = subprocess.Popen(
                exec_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            try:
                stdout, stderr = process.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                logger.error("[AWSRuntime] Timeout listing files")
                return []

            if process.returncode != 0:
                logger.warning(f"[AWSRuntime] find command failed: {stderr[:500]}")
                return []

            # Filter and convert to relative paths
            filtered_output = _filter_ecs_exec_output(stdout)
            files = []
            workspace_prefix = f"{self.workspace_dir}/"
            for line in filtered_output.split("\n"):
                path = line.strip()
                if not path or not path.startswith(workspace_prefix):
                    continue
                # Convert to relative path
                rel_path = path[len(workspace_prefix):]
                if rel_path:
                    files.append(rel_path)

            logger.info(f"[AWSRuntime] list_files_async: found {len(files)} files")
            return files[:max_files]

        except Exception as e:
            logger.error(f"[AWSRuntime] Error listing files: {e}")
            return []

    def list_directory(self, path: str = "") -> list[str]:
        """List files in a directory within the workspace.

        This method matches the RuntimeWorkspace interface expected by
        AcceptanceAgent. It lists files directly from the ECS container
        (not S3) since claude_code_edit creates files in the container.

        Args:
            path: Relative path within workspace (empty string for root).

        Returns:
            `list[str]`: List of file/directory names in the specified path.
        """
        logger.info(
            f"[AWSRuntime] list_directory called: path={path}, "
            f"task_arn={self.task_arn[:40] if self.task_arn else None}..., "
            f"is_initialized={self.is_initialized}"
        )

        if not self.task_arn:
            logger.warning("[AWSRuntime] Cannot list directory: task not running")
            return []

        try:
            import subprocess

            # Build the full path in the container
            container_path = f"{self.workspace_dir}/{path.rstrip('/')}" if path else self.workspace_dir

            # Use ECS execute-command to run ls in the container
            # Note: Wrap command in bash -c for proper execution
            ls_command = f"ls -1 {container_path}"
            # Escape single quotes in command for bash -c
            escaped_command = ls_command.replace("'", "'\\''")
            exec_cmd = [
                "aws", "ecs", "execute-command",
                "--cluster", self.cluster_name,
                "--task", self.task_arn,
                "--container", "sandbox",
                "--command", f"/bin/bash -c '{escaped_command}'",
                "--interactive",
                "--region", self.region,
            ]

            logger.debug(f"[AWSRuntime] Running command: {' '.join(exec_cmd)}")

            # Use Popen with stdout=PIPE (same approach as claude_code_edit)
            process = subprocess.Popen(
                exec_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Wait for process to complete with timeout
            try:
                stdout, stderr = process.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                logger.error("[AWSRuntime] Timeout listing directory")
                return []

            if process.returncode != 0:
                # Log full error for debugging
                logger.warning(
                    f"[AWSRuntime] ls command failed (rc={process.returncode}): "
                    f"stderr={stderr[:1000]}, stdout={stdout[:200]}"
                )
                return []

            # Filter out ECS Exec session messages
            filtered_output = _filter_ecs_exec_output(stdout)

            # Parse ls output - each line is a file/directory name
            entries = []
            for line in filtered_output.split("\n"):
                name = line.strip()
                # Skip empty names, ., .., and any Session Manager related messages
                if not name or name in (".", ".."):
                    continue
                # Extra filtering for any remaining Session Manager messages
                if name.startswith("The Session Manager plugin") or name.startswith("Starting session"):
                    continue
                # Filter out ls error messages that might appear in output
                if name.startswith("ls: cannot access") or "Not a directory" in name or "No such file" in name:
                    continue
                # Filter out lines that look like error messages
                if "/" in name and ("cannot access" in name or "Not a directory" in name):
                    continue
                entries.append(name)

            logger.info(f"[AWSRuntime] list_directory({path}): found {len(entries)} entries")
            return entries

        except Exception as e:
            logger.error(f"[AWSRuntime] Error listing directory {path}: {e}")
            return []

    def execute_command(
        self,
        command: str,
        timeout: int | None = None,
        working_dir: str | None = None,
    ) -> dict[str, Any]:
        """Execute a command in the sandbox container.

        Uses ECS Exec to run commands in the running task.

        Args:
            command: Command to execute.
            timeout: Command timeout in seconds.
            working_dir: Working directory (relative to workspace or absolute).

        Returns:
            `dict`: Result with success, output, error keys.
        """
        if not self.task_arn:
            return {
                "success": False,
                "output": "",
                "error": "Task not running",
            }

        try:
            import subprocess

            # Build command with working directory if specified
            if working_dir:
                # Handle relative or absolute paths
                if working_dir.startswith("/"):
                    work_path = working_dir
                else:
                    work_path = f"{self.workspace_dir}/{working_dir}"
                full_command = f"cd {work_path} && {command}"
            else:
                full_command = f"cd {self.workspace_dir} && {command}"

            # Use AWS CLI for ECS Exec (boto3 doesn't support interactive exec well)
            # Note: Wrap command in bash -c for proper execution
            # Escape single quotes in command for bash -c
            escaped_command = full_command.replace("'", "'\\''")
            exec_cmd = [
                "aws", "ecs", "execute-command",
                "--cluster", self.cluster_name,
                "--task", self.task_arn,
                "--container", "sandbox",
                "--command", f"/bin/bash -c '{escaped_command}'",
                "--interactive",
                "--region", self.region,
            ]

            result = subprocess.run(
                exec_cmd,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
            )

            # Filter out ECS Exec session messages from output
            filtered_stdout = _filter_ecs_exec_output(result.stdout)
            filtered_stderr = _filter_ecs_exec_output(result.stderr)

            return {
                "success": result.returncode == 0,
                "output": filtered_stdout,
                "error": filtered_stderr if result.returncode != 0 else "",
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "Command timed out",
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
            }

    def execute_setup_commands(self, commands: list[str]) -> list[dict[str, Any]]:
        """Execute multiple setup commands.

        Args:
            commands: List of commands to execute.

        Returns:
            `list[dict]`: Results for each command.
        """
        results = []
        for cmd in commands:
            result = self.execute_command(cmd)
            results.append(result)
            if result["returncode"] != 0:
                logger.warning(f"[AWSRuntime] Setup command failed: {cmd}")
                break
        return results

    def _get_subnets(self) -> list[str]:
        """Get VPC subnets for the task.

        Returns:
            `list[str]`: List of subnet IDs.
        """
        # Read from environment or use hardcoded defaults for HiveCore VPC
        subnets = os.getenv("ECS_SUBNETS", "").split(",")
        if not subnets or subnets == [""]:
            # Default: HiveCore VPC subnets in ap-northeast-1
            subnets = [
                "subnet-02500862d92432bb2",  # ap-northeast-1a
                "subnet-0078bf20f1aa30f5d",  # ap-northeast-1c
            ]
        return subnets

    def _get_security_groups(self) -> list[str]:
        """Get security groups for the task.

        Returns:
            `list[str]`: List of security group IDs.
        """
        sgs = os.getenv("ECS_SECURITY_GROUPS", "").split(",")
        if not sgs or sgs == [""]:
            # Default: HiveCore ECS security group
            sgs = ["sg-0bff52c5274aa9893"]  # hivecore-ecs-sg
        return sgs

    def _cleanup_s3_files(self) -> None:
        """Cleanup S3 files for this execution."""
        try:
            # List and delete all objects with this prefix
            prefix = f"{self.s3_prefix}/"
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix=prefix,
            )

            if response.get("Contents"):
                objects = [{"Key": obj["Key"]} for obj in response["Contents"]]
                self.s3_client.delete_objects(
                    Bucket=self.s3_bucket,
                    Delete={"Objects": objects},
                )
                logger.info(f"[AWSRuntime] Cleaned up {len(objects)} S3 objects")

        except Exception as e:
            logger.warning(f"[AWSRuntime] Error cleaning up S3: {e}")

    def __enter__(self) -> "AWSRuntimeWorkspace":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        import asyncio
        asyncio.get_event_loop().run_until_complete(self.stop())


__all__ = ["AWSRuntimeWorkspace"]
