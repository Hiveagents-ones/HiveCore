# -*- coding: utf-8 -*-
"""Container Agent Service.

This service runs inside the container and provides:
- Coding Agent execution
- QA/Acceptance Agent execution
- Claude Code integration (local mode)

The service receives tasks via HTTP API and executes them using
the installed agentscope package.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import base64
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI(title="Agent Service", version="1.0.0")

# Configuration
WORKSPACE_DIR = os.environ.get("WORKSPACE_DIR", "/workspace")
ZHIPU_API_KEY = os.environ.get("ZHIPU_API_KEY", "")
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/anthropic"


class TaskRequest(BaseModel):
    """Task execution request."""
    task_type: str  # "coding" or "qa"
    requirement: dict[str, Any]
    blueprint: dict[str, Any] = {}
    feedback: str = ""
    workspace_files: dict[str, str] = {}
    criteria: list[dict[str, Any]] = []
    verbose: bool = False


class TaskResponse(BaseModel):
    """Task execution response."""
    success: bool
    result: dict[str, Any] = {}
    error: str = ""


class ClaudeCodeRequest(BaseModel):
    """Claude Code execution request."""
    prompt: str
    timeout: int = 480


class ClaudeCodeResponse(BaseModel):
    """Claude Code execution response."""
    success: bool
    output: Any = None
    error: str = ""


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "workspace": WORKSPACE_DIR}


@app.post("/claude_code", response_model=ClaudeCodeResponse)
async def call_claude_code(request: ClaudeCodeRequest):
    """Call Claude Code CLI directly (local mode).

    Since we're inside the container, Claude Code runs locally
    without docker exec.
    """
    if not ZHIPU_API_KEY:
        return ClaudeCodeResponse(
            success=False,
            error="ZHIPU_API_KEY not set"
        )

    try:
        # Encode prompt to avoid shell escaping issues
        prompt_b64 = base64.b64encode(request.prompt.encode("utf-8")).decode("ascii")

        # Build environment for Claude Code
        env = os.environ.copy()
        env["ANTHROPIC_BASE_URL"] = ZHIPU_BASE_URL
        env["ANTHROPIC_API_KEY"] = ZHIPU_API_KEY
        env["ANTHROPIC_AUTH_TOKEN"] = ZHIPU_API_KEY
        env["HOME"] = "/home/node"

        # Call Claude Code as 'node' user
        cmd = f"echo '{prompt_b64}' | base64 -d | claude -p - --output-format json --dangerously-skip-permissions"

        process = await asyncio.create_subprocess_shell(
            f"su - node -c 'cd {WORKSPACE_DIR} && {cmd}'",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=request.timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return ClaudeCodeResponse(
                success=False,
                error=f"Timeout ({request.timeout}s)"
            )

        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")

        if process.returncode == 0:
            try:
                output = json.loads(stdout_text)
                return ClaudeCodeResponse(success=True, output=output)
            except json.JSONDecodeError:
                return ClaudeCodeResponse(success=True, output=stdout_text)
        else:
            return ClaudeCodeResponse(
                success=False,
                error=stderr_text or stdout_text
            )

    except Exception as exc:
        return ClaudeCodeResponse(success=False, error=str(exc))


@app.post("/execute_task", response_model=TaskResponse)
async def execute_task(request: TaskRequest):
    """Execute a coding or QA task.

    This runs the Agent logic inside the container.
    """
    try:
        if request.task_type == "coding":
            result = await _execute_coding_task(request)
        elif request.task_type == "qa":
            result = await _execute_qa_task(request)
        else:
            return TaskResponse(
                success=False,
                error=f"Unknown task type: {request.task_type}"
            )

        return TaskResponse(success=True, result=result)

    except Exception as exc:
        return TaskResponse(success=False, error=str(exc))


async def _execute_coding_task(request: TaskRequest) -> dict[str, Any]:
    """Execute coding task using Claude Code.

    The Agent analyzes the requirement and calls Claude Code
    to implement the solution.
    """
    requirement = request.requirement
    blueprint = request.blueprint
    feedback = request.feedback

    # Build the coding prompt
    prompt_parts = [
        "# Task: Implement the following requirement",
        "",
        "## Requirement",
        json.dumps(requirement, ensure_ascii=False, indent=2),
        "",
        "## Technical Blueprint",
        f"Recommended Stack: {blueprint.get('recommended_stack', '')}",
        f"Deliverable: {blueprint.get('deliverable_pitch', '')}",
        "",
        f"## Working Directory: {WORKSPACE_DIR}",
        "",
    ]

    if feedback:
        prompt_parts.extend([
            "## Previous QA Feedback (must fix)",
            feedback,
            "",
        ])

    prompt_parts.extend([
        "## Instructions",
        "1. Analyze the requirement and technical blueprint",
        "2. Create/modify the necessary files in the workspace",
        "3. Ensure the code is complete and functional",
        "4. Follow best practices for the chosen tech stack",
    ])

    prompt = "\n".join(prompt_parts)

    # Call Claude Code
    response = await call_claude_code(ClaudeCodeRequest(prompt=prompt))

    if not response.success:
        return {"error": response.error, "files_changed": []}

    # List files in workspace
    files_changed = []
    workspace = Path(WORKSPACE_DIR)
    if workspace.exists():
        for f in workspace.rglob("*"):
            if f.is_file() and not str(f).startswith(".git"):
                files_changed.append(str(f.relative_to(workspace)))

    return {
        "summary": "Coding task completed",
        "output": response.output,
        "files_changed": files_changed,
    }


async def _execute_qa_task(request: TaskRequest) -> dict[str, Any]:
    """Execute QA/acceptance task.

    The QA Agent reviews the implementation and checks
    if it meets the acceptance criteria.
    """
    requirement = request.requirement
    criteria = request.criteria
    workspace_files = request.workspace_files

    # If no workspace_files provided, read from disk
    if not workspace_files:
        workspace = Path(WORKSPACE_DIR)
        if workspace.exists():
            for f in workspace.rglob("*"):
                if f.is_file() and not str(f.relative_to(workspace)).startswith("."):
                    try:
                        rel_path = str(f.relative_to(workspace))
                        workspace_files[rel_path] = f.read_text(encoding="utf-8")
                    except (UnicodeDecodeError, Exception):
                        pass

    # Build QA prompt
    prompt_parts = [
        "# Task: QA Review",
        "",
        "## Requirement",
        json.dumps(requirement, ensure_ascii=False, indent=2),
        "",
        "## Acceptance Criteria",
        json.dumps(criteria, ensure_ascii=False, indent=2),
        "",
        "## Files to Review",
    ]

    for path, content in list(workspace_files.items())[:10]:  # Limit files
        prompt_parts.extend([
            f"### {path}",
            "```",
            content[:3000],  # Truncate large files
            "```",
            "",
        ])

    prompt_parts.extend([
        "",
        "## Instructions",
        "Review the implementation and provide a QA report in JSON format:",
        "```json",
        "{",
        '  "criteria": [',
        '    {"name": "criterion name", "pass": true/false, "comment": "..."}',
        "  ],",
        '  "overall_pass": true/false,',
        '  "summary": "overall assessment"',
        "}",
        "```",
    ])

    prompt = "\n".join(prompt_parts)

    # Call Claude Code for QA
    response = await call_claude_code(ClaudeCodeRequest(prompt=prompt, timeout=120))

    if not response.success:
        return {"error": response.error, "criteria": [], "overall_pass": False}

    # Try to parse QA result
    output = response.output
    if isinstance(output, str):
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', output)
            if json_match:
                output = json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    if isinstance(output, dict):
        return output

    return {
        "criteria": [],
        "overall_pass": False,
        "summary": str(output),
    }


@app.get("/list_files")
async def list_files():
    """List files in workspace."""
    files = []
    workspace = Path(WORKSPACE_DIR)
    if workspace.exists():
        for f in workspace.rglob("*"):
            if f.is_file() and not str(f.relative_to(workspace)).startswith(".git"):
                files.append(str(f.relative_to(workspace)))
    return {"files": files}


@app.get("/read_file")
async def read_file(path: str):
    """Read a file from workspace."""
    full_path = Path(WORKSPACE_DIR) / path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    try:
        content = full_path.read_text(encoding="utf-8")
        return {"path": path, "content": content}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
