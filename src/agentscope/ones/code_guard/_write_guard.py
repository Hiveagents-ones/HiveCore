# -*- coding: utf-8 -*-
"""WriteGuard: Validate write operations.

This module provides basic syntax validation for code being written,
including bracket matching and other structural checks.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ..dependency_validation import (
    ValidationResult,
    ValidationIssue,
    IssueSeverity,
    IssueCategory,
)

if TYPE_CHECKING:
    from ._config import CodeGuardConfig


class WriteGuard:
    """Guard for validating write operations.

    Performs basic syntax validation including:
    - Bracket/brace/parenthesis matching
    - Basic quote closure checking
    """

    def __init__(self, config: "CodeGuardConfig") -> None:
        """Initialize WriteGuard.

        Args:
            config (`CodeGuardConfig`):
                The CodeGuard configuration.
        """
        self.config = config

    def validate_write(
        self,
        file_path: str,
        content: str,
        original_content: str | None = None,
        ranges: list[int] | None = None,
    ) -> ValidationResult:
        """Validate a write operation.

        Args:
            file_path (`str`):
                Path of the file being written.
            content (`str`):
                The content being written.
            original_content (`str | None`, optional):
                The original file content (for range validation).
            ranges (`list[int] | None`, optional):
                [start, end] line range for partial write.

        Returns:
            `ValidationResult`:
                Validation result with any issues found.
        """
        result = ValidationResult(is_valid=True)

        if not self.config.write_guard_enabled:
            return result

        # Check if file should be validated
        if not self.config.should_validate_file(file_path):
            return result

        # Perform syntax checks
        if self.config.check_syntax:
            syntax_result = self.check_syntax(file_path, content)
            for issue in syntax_result.issues:
                result.add_issue(issue)

        # Validate range consistency if applicable
        if self.config.check_ranges_match and original_content and ranges:
            range_result = self._validate_range_write(
                file_path,
                content,
                original_content,
                ranges,
            )
            for issue in range_result.issues:
                result.add_issue(issue)

        return result

    def check_syntax(
        self,
        file_path: str,
        content: str,
    ) -> ValidationResult:
        """Perform basic syntax checks.

        Args:
            file_path (`str`):
                Path of the file.
            content (`str`):
                The content to check.

        Returns:
            `ValidationResult`:
                Validation result with syntax issues.
        """
        result = ValidationResult(is_valid=True)

        # Check bracket balance
        bracket_issues = self._check_brackets(content, file_path)
        for issue in bracket_issues:
            result.add_issue(issue)

        return result

    def _check_brackets(
        self,
        content: str,
        file_path: str,
    ) -> list[ValidationIssue]:
        """Check bracket/brace/parenthesis balance.

        Args:
            content (`str`):
                The content to check.
            file_path (`str`):
                Path of the file (for error reporting).

        Returns:
            `list[ValidationIssue]`:
                List of bracket-related issues.
        """
        issues: list[ValidationIssue] = []
        stack: list[tuple[str, int, int]] = []  # (char, line, col)
        pairs = {"(": ")", "[": "]", "{": "}"}
        reverse_pairs = {v: k for k, v in pairs.items()}

        in_string = False
        string_char: str | None = None
        prev_char: str | None = None
        in_line_comment = False
        in_block_comment = False

        lines = content.split("\n")
        ext = Path(file_path).suffix.lower()
        is_python = ext in (".py", ".pyw")

        for line_num, line in enumerate(lines, 1):
            in_line_comment = False
            col = 0

            for char in line:
                col += 1

                # Handle Python line comments
                if is_python and char == "#" and not in_string:
                    in_line_comment = True

                # Handle C-style comments
                if not is_python and not in_string:
                    if prev_char == "/" and char == "/":
                        in_line_comment = True
                    elif prev_char == "/" and char == "*":
                        in_block_comment = True
                    elif prev_char == "*" and char == "/" and in_block_comment:
                        in_block_comment = False
                        prev_char = char
                        continue

                if in_line_comment or in_block_comment:
                    prev_char = char
                    continue

                # Handle string boundaries
                if char in "\"'`" and prev_char != "\\":
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                        string_char = None

                if not in_string:
                    if char in pairs:
                        stack.append((char, line_num, col))
                    elif char in reverse_pairs:
                        if stack:
                            open_char, open_line, open_col = stack[-1]
                            if pairs.get(open_char) == char:
                                stack.pop()
                            else:
                                issues.append(
                                    ValidationIssue(
                                        severity=IssueSeverity.ERROR,
                                        category=IssueCategory.SYNTAX_ERROR,
                                        message=(
                                            f"Mismatched brackets: expected "
                                            f"'{pairs[open_char]}' but found '{char}'"
                                        ),
                                        source_file=file_path,
                                        line_number=line_num,
                                        suggestion=(
                                            f"Opening bracket '{open_char}' at "
                                            f"line {open_line}, column {open_col}"
                                        ),
                                    )
                                )
                        else:
                            issues.append(
                                ValidationIssue(
                                    severity=IssueSeverity.ERROR,
                                    category=IssueCategory.SYNTAX_ERROR,
                                    message=f"Unexpected closing bracket '{char}'",
                                    source_file=file_path,
                                    line_number=line_num,
                                    suggestion="Remove this bracket or add matching opening bracket",
                                )
                            )

                prev_char = char

        # Check for unclosed brackets
        for open_char, line_num, col in stack:
            issues.append(
                ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    category=IssueCategory.SYNTAX_ERROR,
                    message=f"Unclosed bracket '{open_char}'",
                    source_file=file_path,
                    line_number=line_num,
                    suggestion=f"Add closing bracket '{pairs[open_char]}'",
                )
            )

        return issues

    def _validate_range_write(
        self,
        file_path: str,
        content: str,
        original_content: str,
        ranges: list[int],
    ) -> ValidationResult:
        """Validate range-based write operation.

        Args:
            file_path (`str`):
                Path of the file.
            content (`str`):
                The new content for the range.
            original_content (`str`):
                The original file content.
            ranges (`list[int]`):
                [start, end] line range.

        Returns:
            `ValidationResult`:
                Validation result with any issues.
        """
        result = ValidationResult(is_valid=True)

        if len(ranges) != 2:
            result.add_issue(
                ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.INVALID_REFERENCE,
                    message="Invalid range format, expected [start, end]",
                    source_file=file_path,
                )
            )
            return result

        start, end = ranges
        original_lines = original_content.split("\n")
        total_lines = len(original_lines)

        # Validate range bounds
        if start < 1 or start > total_lines + 1:
            result.add_issue(
                ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.INVALID_REFERENCE,
                    message=(
                        f"Start line {start} is out of bounds "
                        f"(file has {total_lines} lines)"
                    ),
                    source_file=file_path,
                    line_number=start,
                )
            )

        if end < start or end > total_lines:
            result.add_issue(
                ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.INVALID_REFERENCE,
                    message=(
                        f"End line {end} is invalid "
                        f"(file has {total_lines} lines, start is {start})"
                    ),
                    source_file=file_path,
                    line_number=end,
                )
            )

        return result
