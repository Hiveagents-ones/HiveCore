# -*- coding: utf-8 -*-
"""Repair Engine for error analysis and fixing (language agnostic).

This module provides a generic repair engine that uses Agent manifest
configurations to analyze errors and generate fixes. All language-specific
logic is defined in the manifest, not in this module.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from .._logging import logger

if TYPE_CHECKING:
    from .manifest import AgentManifest, RepairConfig


@dataclass
class RepairAction:
    """A single repair action to be taken.

    Attributes:
        pattern (`str`):
            The error pattern that was matched.
        hint (`str`):
            The repair hint from manifest configuration.
        sync_files (`list[str]`):
            Files that need to be synchronized after repair.
        matched_groups (`dict[str, str]`):
            Named groups captured from the regex match.
    """

    pattern: str
    hint: str
    sync_files: list[str] = field(default_factory=list)
    matched_groups: dict[str, str] = field(default_factory=dict)


@dataclass
class FilePatch:
    """A file patch to apply.

    Attributes:
        file_path (`str`):
            Path to the file to patch.
        action (`str`):
            Action type: "modify", "append", "create", "delete".
        content (`str`):
            The content to apply (diff format for modify, raw for others).
        description (`str`):
            Human-readable description of what this patch does.
    """

    file_path: str
    action: str
    content: str
    description: str = ""


@dataclass
class RepairResult:
    """Result of a repair operation.

    Attributes:
        success (`bool`):
            Whether the repair was successful.
        patches_applied (`list[FilePatch]`):
            List of patches that were applied.
        errors (`list[str]`):
            Any errors encountered during repair.
        sync_files_updated (`list[str]`):
            List of sync files that were updated.
    """

    success: bool
    patches_applied: list[FilePatch] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    sync_files_updated: list[str] = field(default_factory=list)


class RepairEngine:
    """Generic repair engine using manifest configuration.

    This engine analyzes errors using patterns defined in the Agent manifest
    and generates repair actions. It does not contain any language-specific
    logic - all such logic is defined in the manifest.

    Example usage:
        ```python
        engine = RepairEngine(manifest)
        actions = engine.analyze_error(error_message)
        prompt = engine.build_repair_prompt(error_message, actions, file_content)
        # Send prompt to LLM and get patches
        result = await engine.apply_patches(patches, workspace)
        ```
    """

    def __init__(self, manifest: "AgentManifest"):
        """Initialize the repair engine.

        Args:
            manifest: The agent manifest containing repair configuration.
        """
        self.manifest = manifest
        self.repair_config = manifest.repair_config

    def analyze_error(self, error_message: str) -> list[RepairAction]:
        """Analyze an error message and return matching repair actions.

        Uses the error_patterns defined in the manifest's repair_config
        to match against the error message.

        Args:
            error_message: The error message to analyze.

        Returns:
            List of RepairAction objects for matched patterns.
        """
        if not self.repair_config:
            return []

        actions: list[RepairAction] = []
        sync_files = self.repair_config.sync_files

        for pattern, hint in self.repair_config.error_patterns.items():
            try:
                match = re.search(pattern, error_message, re.MULTILINE | re.IGNORECASE)
                if match:
                    # Extract named groups if any
                    matched_groups = match.groupdict() if match.lastindex else {}

                    # Substitute captured groups into hint
                    resolved_hint = hint
                    for i, group in enumerate(match.groups(), 1):
                        if group:
                            resolved_hint = resolved_hint.replace(f"${i}", group)

                    actions.append(RepairAction(
                        pattern=pattern,
                        hint=resolved_hint,
                        sync_files=sync_files,
                        matched_groups=matched_groups,
                    ))
            except re.error as e:
                logger.warning("Invalid regex pattern '%s': %s", pattern, e)

        return actions

    def get_common_fix(self, error_type: str) -> str | None:
        """Get a common fix template for a known error type.

        Args:
            error_type: The type of error (e.g., "circular_import").

        Returns:
            The fix template if found, None otherwise.
        """
        if not self.repair_config:
            return None
        return self.repair_config.common_fixes.get(error_type)

    def build_repair_prompt(
        self,
        error_message: str,
        actions: list[RepairAction],
        affected_files: dict[str, str] | None = None,
    ) -> str:
        """Build a repair prompt for the LLM.

        Args:
            error_message: The original error message.
            actions: List of repair actions from analyze_error().
            affected_files: Optional dict of file_path -> content.

        Returns:
            A prompt string to send to the LLM.
        """
        # Get repair guidelines from manifest
        guidelines: list[str] = []
        if self.repair_config:
            guidelines.extend(self.repair_config.repair_guidelines)
        if self.manifest.prompt_config:
            guidelines.extend(self.manifest.prompt_config.repair_guidelines)

        # Build hints section
        hints = []
        for action in actions:
            hints.append(f"- {action.hint}")
            if action.sync_files:
                hints.append(f"  需要同步更新: {', '.join(action.sync_files)}")

        # Build files section
        files_section = ""
        if affected_files:
            files_parts = []
            for path, content in affected_files.items():
                # Truncate large files
                if len(content) > 2000:
                    content = content[:2000] + "\n... (truncated)"
                files_parts.append(f"=== {path} ===\n{content}")
            files_section = "\n\n".join(files_parts)

        prompt = f"""请修复以下错误:

## 错误信息
```
{error_message}
```

## 修复提示
{chr(10).join(hints) if hints else "无特定提示"}

## 修复指南
{chr(10).join(f'- {g}' for g in guidelines) if guidelines else "无特定指南"}

"""

        if files_section:
            prompt += f"""## 相关文件
{files_section}

"""

        prompt += """## 输出格式
请使用 unified diff 格式输出修复补丁:

```diff
--- a/path/to/file
+++ b/path/to/file
@@ -line,count +line,count @@
-old line
+new line
```

如果需要创建新文件或追加内容，请说明文件路径和内容。
如果需要修改依赖文件，请同时提供修改内容。
"""

        return prompt

    def parse_patches_from_response(self, response: str) -> list[FilePatch]:
        """Parse file patches from LLM response.

        Args:
            response: The LLM response containing patches.

        Returns:
            List of FilePatch objects.
        """
        patches: list[FilePatch] = []

        # Find all diff blocks
        diff_pattern = r"```diff\n(.*?)```"
        diff_matches = re.findall(diff_pattern, response, re.DOTALL)

        for diff_content in diff_matches:
            # Extract file path from diff header
            path_match = re.search(r"^[-+]{3}\s+[ab]/(.+)$", diff_content, re.MULTILINE)
            if path_match:
                file_path = path_match.group(1)
                patches.append(FilePatch(
                    file_path=file_path,
                    action="modify",
                    content=diff_content,
                    description=f"Patch for {file_path}",
                ))

        # Find create file blocks
        create_pattern = r"创建文件[：:]\s*`?([^\n`]+)`?\n```\w*\n(.*?)```"
        create_matches = re.findall(create_pattern, response, re.DOTALL)

        for file_path, content in create_matches:
            patches.append(FilePatch(
                file_path=file_path.strip(),
                action="create",
                content=content,
                description=f"Create {file_path}",
            ))

        # Find append blocks
        append_pattern = r"追加到[：:]\s*`?([^\n`]+)`?\n```\w*\n(.*?)```"
        append_matches = re.findall(append_pattern, response, re.DOTALL)

        for file_path, content in append_matches:
            patches.append(FilePatch(
                file_path=file_path.strip(),
                action="append",
                content=content,
                description=f"Append to {file_path}",
            ))

        return patches

    async def apply_patches(
        self,
        patches: list[FilePatch],
        workspace: Any,
    ) -> RepairResult:
        """Apply patches to files in the workspace.

        Args:
            patches: List of patches to apply.
            workspace: The RuntimeWorkspace to apply patches to.

        Returns:
            RepairResult with success status and details.
        """
        result = RepairResult(success=True)

        for patch in patches:
            try:
                if patch.action == "create":
                    await self._create_file(workspace, patch)
                elif patch.action == "append":
                    await self._append_to_file(workspace, patch)
                elif patch.action == "modify":
                    await self._apply_diff(workspace, patch)
                elif patch.action == "delete":
                    await self._delete_file(workspace, patch)
                else:
                    result.errors.append(f"Unknown action: {patch.action}")
                    continue

                result.patches_applied.append(patch)

                # Track sync files
                if self.repair_config:
                    for sync_file in self.repair_config.sync_files:
                        if sync_file in patch.file_path:
                            result.sync_files_updated.append(sync_file)

            except Exception as e:
                result.errors.append(f"Failed to apply patch to {patch.file_path}: {e}")
                result.success = False

        return result

    async def _create_file(self, workspace: Any, patch: FilePatch) -> None:
        """Create a new file."""
        # Use workspace API to create file
        if hasattr(workspace, "write_file"):
            workspace.write_file(patch.file_path, patch.content)
        else:
            # Fallback: execute command
            workspace.execute_command(
                f"cat > {patch.file_path} << 'EOF'\n{patch.content}\nEOF"
            )

    async def _append_to_file(self, workspace: Any, patch: FilePatch) -> None:
        """Append content to a file."""
        if hasattr(workspace, "write_file"):
            existing = workspace.read_file(patch.file_path)
            workspace.write_file(patch.file_path, existing + "\n" + patch.content)
        else:
            workspace.execute_command(
                f"cat >> {patch.file_path} << 'EOF'\n{patch.content}\nEOF"
            )

    async def _apply_diff(self, workspace: Any, patch: FilePatch) -> None:
        """Apply a diff patch."""
        # Write diff to temp file and apply with patch command
        workspace.execute_command(
            f"echo '{patch.content}' | patch -p1"
        )

    async def _delete_file(self, workspace: Any, patch: FilePatch) -> None:
        """Delete a file."""
        workspace.execute_command(f"rm -f {patch.file_path}")
