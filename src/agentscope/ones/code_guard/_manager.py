# -*- coding: utf-8 -*-
"""CodeGuardManager: Central manager for the CodeGuard system.

This module provides the main entry point for integrating CodeGuard
with the tool system via postprocess functions.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from ._config import CodeGuardConfig, StrictnessLevel
from ._read_guard import FileReadLog, ReadGuard
from ._write_guard import WriteGuard
from ._import_guard import ImportGuard
from ._interface_registry import InterfaceRegistry
from ._hallucination_detector import HallucinationDetector
from ..dependency_validation import ValidationIssue, IssueSeverity

if TYPE_CHECKING:
    from ...tool._response import ToolResponse
    from ...message import ToolUseBlock, TextBlock
    from ..file_tracking import FileRegistry
    from ..dependency_validation import ValidationResult


class CodeGuardManager:
    """Central manager for the CodeGuard system.

    This manager coordinates all Guard components and provides
    postprocess functions for tool integration.

    Usage:
        ```python
        from agentscope.ones.code_guard import (
            CodeGuardManager,
            CodeGuardConfig,
            StrictnessLevel,
        )

        # Create manager
        config = CodeGuardConfig(strictness=StrictnessLevel.NORMAL)
        code_guard = CodeGuardManager(config)

        # Register with toolkit
        toolkit.register_tool_function(
            view_text_file,
            postprocess_func=code_guard.create_view_postprocess(),
        )
        toolkit.register_tool_function(
            write_text_file,
            postprocess_func=code_guard.create_write_postprocess(),
        )
        ```
    """

    def __init__(
        self,
        config: CodeGuardConfig | None = None,
        file_registry: "FileRegistry | None" = None,
    ) -> None:
        """Initialize CodeGuardManager.

        Args:
            config (`CodeGuardConfig | None`, optional):
                The configuration. Defaults to CodeGuardConfig().
            file_registry (`FileRegistry | None`, optional):
                The file registry for import validation.
        """
        self.config = config or CodeGuardConfig()

        # Initialize shared components
        self.file_read_log = FileReadLog()
        self.interface_registry = InterfaceRegistry()

        # Initialize guards
        self.read_guard = ReadGuard(self.config, self.file_read_log)
        self.write_guard = WriteGuard(self.config)
        self.import_guard = ImportGuard(self.config, file_registry)
        self.hallucination_detector = HallucinationDetector(
            self.config,
            self.interface_registry,
        )

        # Store file registry reference
        self._file_registry = file_registry

    def create_view_postprocess(
        self,
    ) -> Callable[["ToolUseBlock", "ToolResponse"], "ToolResponse | None"]:
        """Create postprocess function for view_text_file.

        Returns:
            A postprocess function that records file reads and extracts interfaces.
        """

        def postprocess(
            tool_call: "ToolUseBlock",
            response: "ToolResponse",
        ) -> "ToolResponse | None":
            if not self.config.enabled:
                return None

            # Extract parameters from tool call
            inputs = tool_call.get("input", {}) or {}
            file_path = inputs.get("file_path", "")
            ranges = inputs.get("ranges")

            if not file_path:
                return None

            # Extract content from response
            content = self._extract_content_from_response(response)

            if content:
                # Record the read
                self.file_read_log.record_read(file_path, content, ranges)

                # Extract and register interfaces
                self.interface_registry.extract_and_register(file_path, content)

                # Register with file registry if available
                if self._file_registry:
                    try:
                        self._file_registry.register(file_path, content)
                    except Exception:
                        pass  # Ignore registration errors

            return None  # Don't modify response

        return postprocess

    def create_write_postprocess(
        self,
    ) -> Callable[["ToolUseBlock", "ToolResponse"], "ToolResponse | None"]:
        """Create postprocess function for write_text_file.

        Returns:
            A postprocess function that validates writes.
        """

        def postprocess(
            tool_call: "ToolUseBlock",
            response: "ToolResponse",
        ) -> "ToolResponse | None":
            if not self.config.enabled:
                return None

            # Extract parameters
            inputs = tool_call.get("input", {}) or {}
            file_path = inputs.get("file_path", "")
            content = inputs.get("content", "")
            ranges = inputs.get("ranges")

            if not file_path:
                return None

            # Check if file should be validated
            if not self.config.should_validate_file(file_path):
                return None

            # Determine if this is a new file
            is_new_file = not os.path.exists(file_path)

            all_issues: list[ValidationIssue] = []

            # 1. ReadGuard check (pre-write validation)
            if not is_new_file:
                read_result = self.read_guard.check_before_write(
                    file_path,
                    ranges,
                    is_new_file,
                )

                if self.read_guard.should_block(read_result):
                    # Block the operation
                    return self._create_block_response(read_result.issues)

                all_issues.extend(read_result.issues)

            # Only perform post-write checks if write was successful
            if content and self._is_write_successful(response):
                # 2. WriteGuard syntax check
                syntax_result = self.write_guard.check_syntax(file_path, content)
                all_issues.extend(syntax_result.issues)

                # 3. ImportGuard validation
                import_result = self.import_guard.validate_imports(file_path, content)
                all_issues.extend(import_result.issues)

                # 4. HallucinationDetector check
                halluc_result = self.hallucination_detector.check_function_calls(
                    file_path,
                    content,
                )
                all_issues.extend(halluc_result.issues)

                # Update registries
                self.interface_registry.extract_and_register(file_path, content)
                if self._file_registry:
                    try:
                        self._file_registry.register(file_path, content)
                    except Exception:
                        pass

                # Also record as "read" since we now know the content
                self.file_read_log.record_read(file_path, content)

            # Append warnings if any
            if all_issues:
                return self._append_warnings(response, all_issues)

            return None

        return postprocess

    def create_insert_postprocess(
        self,
    ) -> Callable[["ToolUseBlock", "ToolResponse"], "ToolResponse | None"]:
        """Create postprocess function for insert_text_file.

        Returns:
            A postprocess function that validates inserts.
        """
        # Use same logic as write
        return self.create_write_postprocess()

    def _extract_content_from_response(self, response: "ToolResponse") -> str:
        """Extract file content from a tool response.

        Args:
            response (`ToolResponse`):
                The tool response.

        Returns:
            `str`:
                The extracted content, or empty string.
        """
        for block in response.content:
            if block.get("type") == "text":
                text = block.get("text", "")

                # Try to extract content from code block
                if "```" in text:
                    start = text.find("```")
                    end = text.rfind("```")
                    if start != end:
                        content = text[start + 3 : end]
                        # Remove language identifier
                        if "\n" in content:
                            content = content[content.find("\n") + 1 :]
                        return content

                # Try to extract from line-numbered format
                lines = []
                for line in text.split("\n"):
                    # Match format: "   123: content" or "123	content"
                    stripped = line.lstrip()
                    if stripped and (": " in stripped or "\t" in stripped):
                        parts = stripped.split(": ", 1) if ": " in stripped else stripped.split("\t", 1)
                        if len(parts) == 2 and parts[0].strip().isdigit():
                            lines.append(parts[1])

                if lines:
                    return "\n".join(lines)

                # Return raw text if no special format detected
                return text

        return ""

    def _is_write_successful(self, response: "ToolResponse") -> bool:
        """Check if a write operation was successful.

        Args:
            response (`ToolResponse`):
                The tool response.

        Returns:
            `bool`:
                True if the write was successful.
        """
        for block in response.content:
            if block.get("type") == "text":
                text = block.get("text", "").lower()
                if "error" in text or "failed" in text or "failure" in text:
                    return False
                if "successfully" in text or "success" in text or "wrote" in text:
                    return True
        return True  # Assume success if no clear indicator

    def _create_block_response(
        self,
        issues: list[ValidationIssue],
    ) -> "ToolResponse":
        """Create a blocking response for validation errors.

        Args:
            issues (`list[ValidationIssue]`):
                The validation issues.

        Returns:
            `ToolResponse`:
                A response indicating the operation was blocked.
        """
        from ...tool._response import ToolResponse

        messages = [issue.format_message() for issue in issues if issue.severity == IssueSeverity.ERROR]

        text = "<code-guard>\nOperation blocked:\n"
        for msg in messages:
            text += f"- {msg}\n"
        text += "</code-guard>"

        return ToolResponse(
            content=[{"type": "text", "text": text}],
        )

    def _append_warnings(
        self,
        response: "ToolResponse",
        issues: list[ValidationIssue],
    ) -> "ToolResponse":
        """Append warnings to a response.

        Args:
            response (`ToolResponse`):
                The original response.
            issues (`list[ValidationIssue]`):
                The validation issues to append.

        Returns:
            `ToolResponse`:
                The response with warnings appended.
        """
        from ...tool._response import ToolResponse

        # Filter to warnings and info
        warnings = [
            i
            for i in issues
            if i.severity in (IssueSeverity.WARNING, IssueSeverity.INFO)
        ]

        if not warnings:
            return response

        text = "\n<code-guard-warnings>\n"
        for issue in warnings:
            text += f"- [{issue.severity.value.upper()}] {issue.message}\n"
            if issue.suggestion:
                text += f"  Suggestion: {issue.suggestion}\n"
        text += "</code-guard-warnings>"

        # Copy response and add warning block
        new_content = list(response.content)
        new_content.append({"type": "text", "text": text})

        return ToolResponse(
            content=new_content,
            metadata=response.metadata,
            stream=response.stream,
            is_last=response.is_last,
        )

    def record_file_read(
        self,
        file_path: str,
        content: str,
        ranges: list[int] | None = None,
    ) -> None:
        """Record a file read (for direct integration without postprocess).

        Args:
            file_path (`str`):
                The path to the file that was read.
            content (`str`):
                The content that was read.
            ranges (`list[int] | None`, optional):
                Line ranges if partial read.
        """
        if not self.config.enabled:
            return

        # Record the read
        self.file_read_log.record_read(file_path, content, ranges)

        # Extract and register interfaces
        self.interface_registry.extract_and_register(file_path, content)

        # Register with file registry if available
        if self._file_registry:
            try:
                self._file_registry.register(file_path, content)
            except Exception:
                pass

    def validate_content(
        self,
        file_path: str,
        content: str,
        is_new_file: bool = False,
    ) -> "ValidationResult":
        """Validate content before writing (for direct integration).

        This method performs all CodeGuard checks and returns a ValidationResult.
        Use this when integrating with FileEditor or other systems that don't
        use the postprocess mechanism.

        Args:
            file_path (`str`):
                The path to the file being written.
            content (`str`):
                The content to validate.
            is_new_file (`bool`, optional):
                Whether this is a new file. Defaults to False.

        Returns:
            `ValidationResult`:
                The validation result containing all issues.
        """
        from ..dependency_validation import ValidationResult

        if not self.config.enabled:
            return ValidationResult(is_valid=True, issues=[])

        # Check if file should be validated
        if not self.config.should_validate_file(file_path):
            return ValidationResult(is_valid=True, issues=[])

        all_issues: list[ValidationIssue] = []

        # 1. ReadGuard check (only for existing files)
        if not is_new_file:
            read_result = self.read_guard.check_before_write(
                file_path,
                ranges=None,
                is_new_file=is_new_file,
            )
            all_issues.extend(read_result.issues)

        # 2. WriteGuard syntax check
        if content:
            syntax_result = self.write_guard.check_syntax(file_path, content)
            all_issues.extend(syntax_result.issues)

            # 3. ImportGuard validation
            import_result = self.import_guard.validate_imports(file_path, content)
            all_issues.extend(import_result.issues)

            # 4. HallucinationDetector check
            halluc_result = self.hallucination_detector.check_function_calls(
                file_path,
                content,
            )
            all_issues.extend(halluc_result.issues)

        # Determine if valid (no errors)
        has_errors = any(i.severity == IssueSeverity.ERROR for i in all_issues)
        return ValidationResult(is_valid=not has_errors, issues=all_issues)

    def should_block_write(self, validation_result: "ValidationResult") -> bool:
        """Check if a write should be blocked based on validation result.

        Args:
            validation_result (`ValidationResult`):
                The validation result to check.

        Returns:
            `bool`:
                True if the write should be blocked.
        """
        return self.read_guard.should_block(validation_result)

    def format_warnings(
        self,
        validation_result: "ValidationResult",
    ) -> str:
        """Format validation warnings as a human-readable string.

        Args:
            validation_result (`ValidationResult`):
                The validation result to format.

        Returns:
            `str`:
                Formatted warnings string, or empty string if no warnings.
        """
        if not validation_result.issues:
            return ""

        lines = ["<code-guard-warnings>"]
        for issue in validation_result.issues:
            lines.append(f"- [{issue.severity.value.upper()}] {issue.message}")
            if issue.suggestion:
                lines.append(f"  Suggestion: {issue.suggestion}")
        lines.append("</code-guard-warnings>")

        return "\n".join(lines)

    def update_after_write(
        self,
        file_path: str,
        content: str,
    ) -> None:
        """Update registries after a successful write.

        Args:
            file_path (`str`):
                The path to the written file.
            content (`str`):
                The written content.
        """
        if not self.config.enabled:
            return

        # Update interface registry
        self.interface_registry.extract_and_register(file_path, content)

        # Update file registry
        if self._file_registry:
            try:
                self._file_registry.register(file_path, content)
            except Exception:
                pass

        # Record as read (since we now know the content)
        self.file_read_log.record_read(file_path, content)

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about CodeGuard operations.

        Returns:
            `dict[str, Any]`:
                Statistics including read counts, interface counts, etc.
        """
        return {
            "enabled": self.config.enabled,
            "strictness": self.config.strictness.value,
            "file_reads": self.file_read_log.get_statistics(),
            "interfaces": self.interface_registry.get_statistics(),
        }

    def reset(self) -> None:
        """Reset all state (useful for testing or new sessions)."""
        self.file_read_log.clear()
        self.interface_registry.clear()


def create_code_guard_manager(
    strictness: StrictnessLevel = StrictnessLevel.NORMAL,
    **config_kwargs: Any,
) -> CodeGuardManager:
    """Factory function to create a CodeGuardManager.

    Args:
        strictness (`StrictnessLevel`, optional):
            The strictness level. Defaults to NORMAL.
        **config_kwargs:
            Additional configuration options.

    Returns:
        `CodeGuardManager`:
            A configured CodeGuardManager instance.
    """
    config = CodeGuardConfig(strictness=strictness, **config_kwargs)
    return CodeGuardManager(config)
