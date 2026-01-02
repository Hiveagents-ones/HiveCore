# Task-Level Immediate Validation Design

## Problem Statement

Current validation flow:
```
REQ-001 → REQ-002 → ... → REQ-014 → Unified Validation → All fail → Round 2 redo all
```

Issues:
1. Errors accumulate (e.g., `ModuleNotFoundError: No module named 'app'` breaks all subsequent tasks)
2. Late discovery of issues
3. Wasteful re-execution of all tasks
4. Dynamic Agent creation in loop (should reuse)
5. Claude Code execution not transparent
6. Result summaries truncated

## Proposed Solution

### New Flow: Task-Level Immediate Validation

```
REQ-001 Execute → REQ-001 Validate → (if fail) REQ-001 Fix → REQ-001 Re-validate → Pass →
REQ-002 Execute → REQ-002 Validate → ...
```

### Key Components

#### 1. TaskLevelValidator

```python
class TaskLevelValidator:
    """Validates each task immediately after completion."""

    async def validate_task(
        self,
        node_id: str,
        requirement: Requirement,
        output: TaskOutput,
        workspace_dir: str,
    ) -> TaskValidationResult:
        """
        Quick validation checks for a single task:
        - File existence check
        - Syntax/import check (for code files)
        - Basic functionality check (if applicable)
        """

    async def generate_fix_prompt(
        self,
        validation_result: TaskValidationResult,
        original_requirement: Requirement,
    ) -> str:
        """Generate a targeted fix prompt for the agent."""
```

#### 2. Modified Execution Loop

```python
async def _execute_with_msghub(self, ...):
    for node_id in graph.topological_order():
        # Execute task
        output = await self._invoke_agent_async(...)

        # IMMEDIATE VALIDATION (NEW)
        validation = await self.task_validator.validate_task(
            node_id=node_id,
            requirement=node.requirement,
            output=output,
            workspace_dir=self.workspace_dir,
        )

        if not validation.passed:
            # IMMEDIATE FIX (NEW)
            for retry in range(self.max_task_retries):
                fix_prompt = await self.task_validator.generate_fix_prompt(
                    validation, node.requirement
                )
                logger.warning(
                    "[%s] 验收失败 (尝试 %d/%d): %s",
                    node_id, retry + 1, self.max_task_retries,
                    validation.error_summary
                )

                # Let SAME agent fix the issue
                output = await self._invoke_agent_async(
                    node.assigned_agent_id,
                    fix_prompt,  # Targeted fix prompt
                    context=context,
                    node_id=node_id,
                    is_fix=True,
                )

                # Re-validate
                validation = await self.task_validator.validate_task(...)
                if validation.passed:
                    break

            if not validation.passed:
                # Mark as failed, but continue with other tasks
                graph.mark_failed(node_id, reason=validation.error_summary)
                continue

        graph.mark_completed(node_id)
```

#### 3. Agent Caching

```python
class ExecutionLoop:
    def __init__(self, ...):
        self._agent_cache: dict[str, AgentBase] = {}

    def _get_or_create_agent(self, agent_id: str) -> AgentBase:
        """Reuse cached agents instead of creating new ones."""
        if agent_id in self._agent_cache:
            return self._agent_cache[agent_id]

        agent = self._create_agent(agent_id)
        self._agent_cache[agent_id] = agent
        return agent
```

#### 4. Claude Code Execution Transparency

```python
class AgentReActObserver:
    def on_claude_code_start(self, agent_id: str, task_id: str, prompt: str) -> None:
        self.ctx.logger.info(f"[{agent_id}]   🖥️ Claude Code 开始执行...")
        self.ctx.logger.info(f"[{agent_id}]     提示词: {prompt[:100]}...")

    def on_claude_code_action(self, agent_id: str, action: str, target: str) -> None:
        """Log Claude Code internal actions."""
        action_icons = {
            "read": "📖",
            "write": "✏️",
            "edit": "🔧",
            "bash": "💻",
            "search": "🔍",
        }
        icon = action_icons.get(action, "▸")
        self.ctx.logger.info(f"[{agent_id}]     {icon} {action}: {target}")

    def on_claude_code_complete(
        self, agent_id: str, success: bool, summary: str, files_changed: list[str]
    ) -> None:
        status = "✓" if success else "✗"
        self.ctx.logger.info(f"[{agent_id}]   🖥️ Claude Code 完成 {status}")
        if files_changed:
            self.ctx.logger.info(f"[{agent_id}]     修改文件: {', '.join(files_changed)}")
        # Show FULL summary, not truncated
        self.ctx.logger.info(f"[{agent_id}]     总结: {summary}")
```

### Validation Checks by Task Type

| Task Type | Quick Checks |
|-----------|--------------|
| database  | SQLAlchemy models import, table definitions exist |
| backend   | Python syntax, FastAPI app imports, endpoint exists |
| frontend  | HTML/JS syntax, required files exist |
| ui        | CSS/design files exist |
| test      | Test files exist, pytest can discover |

### Example Validation for Backend Task

```python
async def _validate_backend_task(
    self, node_id: str, requirement: Requirement, workspace_dir: str
) -> TaskValidationResult:
    """Validate backend API task."""
    errors = []

    # 1. Check if backend directory exists
    backend_dir = Path(workspace_dir) / "backend"
    if not backend_dir.exists():
        errors.append("backend/ directory not found")

    # 2. Check if app module can be imported
    try:
        result = subprocess.run(
            ["python", "-c", "from app.main import app"],
            cwd=str(backend_dir),
            capture_output=True,
            timeout=10,
        )
        if result.returncode != 0:
            errors.append(f"Import error: {result.stderr.decode()}")
    except Exception as e:
        errors.append(f"Validation error: {e}")

    # 3. Check if specific endpoint exists (based on requirement)
    # ...

    return TaskValidationResult(
        passed=len(errors) == 0,
        errors=errors,
        error_summary="; ".join(errors) if errors else "",
    )
```

## Benefits

1. **Early Detection**: Issues found immediately after task completion
2. **Targeted Fix**: Agent fixes only what's broken, with specific error context
3. **No Accumulation**: REQ-003's `app` import error fixed before REQ-004 starts
4. **Agent Reuse**: Same agent instance handles both task and fix
5. **Transparency**: Full visibility into Claude Code execution
6. **Efficiency**: No need to re-execute successful tasks

## Implementation Plan

1. Create `TaskLevelValidator` class
2. Add validation checks for each task type
3. Modify `_execute_with_msghub` to include immediate validation
4. Add Agent caching in `ExecutionLoop`
5. Enhance `AgentReActObserver` for Claude Code transparency
6. Test with gym membership system

## Configuration

```python
class ExecutionLoop:
    def __init__(
        self,
        ...,
        enable_task_validation: bool = True,  # NEW
        max_task_retries: int = 2,  # NEW: retries per task
        task_validation_timeout: float = 30.0,  # NEW
    ):
```
