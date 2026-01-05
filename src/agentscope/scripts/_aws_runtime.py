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
                networkConfiguration={
                    "awsvpcConfiguration": {
                        "subnets": self._get_subnets(),
                        "securityGroups": self._get_security_groups(),
                        # DISABLED - using VPC Endpoints for ECR/S3/Logs access
                        "assignPublicIp": "DISABLED",
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
            await self._wait_for_task_running()

            self._started = True
            return True

        except Exception as e:
            logger.error(f"[AWSRuntime] Error starting task: {e}")
            return False

    async def _wait_for_task_running(self, max_wait: int = 120) -> bool:
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

    def list_files(self) -> list[str]:
        """List all files in the workspace.

        Returns:
            `list[str]`: List of file paths.
        """
        try:
            prefix = f"{self.s3_prefix}/files/"
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix=prefix,
            )

            files = []
            for obj in response.get("Contents", []):
                # Remove prefix to get relative path
                rel_path = obj["Key"][len(prefix):]
                if rel_path:
                    files.append(rel_path)

            return files

        except Exception as e:
            logger.error(f"[AWSRuntime] Error listing files: {e}")
            return list(self._local_cache.keys())

    def execute_command(
        self,
        command: str,
        timeout: int | None = None,
        cwd: str | None = None,
    ) -> dict[str, Any]:
        """Execute a command in the sandbox container.

        Uses ECS Exec to run commands in the running task.

        Args:
            command: Command to execute.
            timeout: Command timeout in seconds.
            cwd: Working directory.

        Returns:
            `dict`: Result with stdout, stderr, returncode.
        """
        if not self.task_arn:
            return {
                "stdout": "",
                "stderr": "Task not running",
                "returncode": 1,
            }

        try:
            import subprocess

            # Use AWS CLI for ECS Exec (boto3 doesn't support interactive exec well)
            exec_cmd = [
                "aws", "ecs", "execute-command",
                "--cluster", self.cluster_name,
                "--task", self.task_arn,
                "--container", "sandbox",
                "--command", command,
                "--interactive",
                "--region", self.region,
            ]

            result = subprocess.run(
                exec_cmd,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
                cwd=cwd,
            )

            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": "Command timed out",
                "returncode": 124,
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": 1,
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
        # These should be configured via environment or parameter store
        subnets = os.getenv("ECS_SUBNETS", "").split(",")
        if not subnets or subnets == [""]:
            # Fallback: describe subnets in default VPC
            import boto3
            ec2 = boto3.client("ec2", region_name=self.region)
            response = ec2.describe_subnets(
                Filters=[{"Name": "default-for-az", "Values": ["true"]}]
            )
            subnets = [s["SubnetId"] for s in response.get("Subnets", [])][:2]
        return subnets

    def _get_security_groups(self) -> list[str]:
        """Get security groups for the task.

        Returns:
            `list[str]`: List of security group IDs.
        """
        sgs = os.getenv("ECS_SECURITY_GROUPS", "").split(",")
        if not sgs or sgs == [""]:
            # Use default security group
            sgs = []
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
