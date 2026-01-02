# -*- coding: utf-8 -*-
"""ReadGuard: Enforce read-before-write pattern.

This is the core anti-hallucination mechanism that ensures agents read files
before modifying them.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from ..dependency_validation import (
    ValidationResult,
    ValidationIssue,
    IssueSeverity,
    IssueCategory,
)

if TYPE_CHECKING:
    from ._config import CodeGuardConfig


@dataclass
class FileReadRecord:
    """Record of a single file read operation.

    Attributes:
        file_path (`str`):
            The path of the file that was read.
        read_at (`datetime`):
            Timestamp when the file was read.
        content_hash (`str`):
            SHA256 hash of the content (first 16 chars).
        line_count (`int`):
            Number of lines in the file.
        ranges_read (`list[tuple[int, int]] | None`):
            List of (start, end) line ranges that were read.
            None means the entire file was read.
    """

    file_path: str
    read_at: datetime
    content_hash: str
    line_count: int
    ranges_read: list[tuple[int, int]] | None = None

    def covers_range(self, start: int, end: int) -> bool:
        """Check if the read ranges cover the specified range.

        Args:
            start (`int`):
                Start line number (1-indexed).
            end (`int`):
                End line number (1-indexed, inclusive).

        Returns:
            `bool`:
                True if the specified range is covered by read ranges.
        """
        if self.ranges_read is None:
            return True  # Entire file was read

        for r_start, r_end in self.ranges_read:
            if r_start <= start and r_end >= end:
                return True
        return False

    def merge_range(self, start: int, end: int) -> None:
        """Merge a new range into existing ranges.

        Args:
            start (`int`):
                Start line number.
            end (`int`):
                End line number.
        """
        if self.ranges_read is None:
            return  # Already have full file

        new_range = (start, end)
        merged = []
        inserted = False

        for r_start, r_end in sorted(self.ranges_read + [new_range]):
            if merged and r_start <= merged[-1][1] + 1:
                # Merge overlapping or adjacent ranges
                merged[-1] = (merged[-1][0], max(merged[-1][1], r_end))
            else:
                merged.append((r_start, r_end))

        self.ranges_read = merged


class FileReadLog:
    """Track files that have been read by the agent.

    This log maintains records of all file read operations, including
    partial reads with specific line ranges.
    """

    def __init__(self) -> None:
        """Initialize the file read log."""
        self._records: dict[str, FileReadRecord] = {}
        self._read_order: list[str] = []

    def record_read(
        self,
        file_path: str,
        content: str,
        ranges: list[int] | None = None,
    ) -> FileReadRecord:
        """Record a file read operation.

        Args:
            file_path (`str`):
                Path of the file that was read.
            content (`str`):
                Content that was read from the file.
            ranges (`list[int] | None`, optional):
                [start, end] line range if partial read.

        Returns:
            `FileReadRecord`:
                The created or updated read record.
        """
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        line_count = content.count("\n") + 1

        # Convert ranges list to tuple
        ranges_tuple: list[tuple[int, int]] | None = None
        if ranges and len(ranges) == 2:
            ranges_tuple = [(ranges[0], ranges[1])]

        # Update existing record or create new one
        if file_path in self._records:
            existing = self._records[file_path]
            if ranges_tuple is None:
                # Reading entire file overrides partial reads
                existing.ranges_read = None
            elif existing.ranges_read is not None:
                # Merge new range with existing ranges
                existing.merge_range(ranges_tuple[0][0], ranges_tuple[0][1])
            existing.read_at = datetime.now(timezone.utc)
            existing.content_hash = content_hash
            return existing

        record = FileReadRecord(
            file_path=file_path,
            read_at=datetime.now(timezone.utc),
            content_hash=content_hash,
            line_count=line_count,
            ranges_read=ranges_tuple,
        )
        self._records[file_path] = record
        self._read_order.append(file_path)
        return record

    def has_read(self, file_path: str) -> bool:
        """Check if a file has been read.

        Args:
            file_path (`str`):
                Path of the file to check.

        Returns:
            `bool`:
                True if the file has been read.
        """
        return file_path in self._records

    def has_read_range(self, file_path: str, start: int, end: int) -> bool:
        """Check if a specific range has been read.

        Args:
            file_path (`str`):
                Path of the file to check.
            start (`int`):
                Start line number.
            end (`int`):
                End line number.

        Returns:
            `bool`:
                True if the specified range has been read.
        """
        record = self._records.get(file_path)
        if not record:
            return False
        return record.covers_range(start, end)

    def get_record(self, file_path: str) -> FileReadRecord | None:
        """Get the read record for a file.

        Args:
            file_path (`str`):
                Path of the file.

        Returns:
            `FileReadRecord | None`:
                The read record, or None if file hasn't been read.
        """
        return self._records.get(file_path)

    def get_all_read_files(self) -> list[str]:
        """Get all files that have been read, in read order.

        Returns:
            `list[str]`:
                List of file paths in the order they were first read.
        """
        return list(self._read_order)

    def get_statistics(self) -> dict[str, int]:
        """Get statistics about read operations.

        Returns:
            `dict[str, int]`:
                Statistics including total files, total lines, etc.
        """
        total_lines = sum(r.line_count for r in self._records.values())
        partial_reads = sum(
            1 for r in self._records.values() if r.ranges_read is not None
        )
        return {
            "total_files": len(self._records),
            "total_lines": total_lines,
            "partial_reads": partial_reads,
            "full_reads": len(self._records) - partial_reads,
        }

    def clear(self) -> None:
        """Clear all read records."""
        self._records.clear()
        self._read_order.clear()


class ReadGuard:
    """Guard that enforces read-before-write pattern.

    This is the core anti-hallucination mechanism. It ensures that agents
    cannot modify files they haven't read, preventing them from making
    assumptions about file contents based on training data.
    """

    def __init__(
        self,
        config: "CodeGuardConfig",
        file_read_log: FileReadLog,
    ) -> None:
        """Initialize ReadGuard.

        Args:
            config (`CodeGuardConfig`):
                The CodeGuard configuration.
            file_read_log (`FileReadLog`):
                The file read log to check against.
        """
        self.config = config
        self.file_read_log = file_read_log

    def check_before_write(
        self,
        file_path: str,
        ranges: list[int] | None = None,
        is_new_file: bool = False,
    ) -> ValidationResult:
        """Check if a write operation should be allowed.

        Args:
            file_path (`str`):
                Path of the file to write.
            ranges (`list[int] | None`, optional):
                [start, end] line range for partial write.
            is_new_file (`bool`, optional):
                Whether this is a new file creation.

        Returns:
            `ValidationResult`:
                Validation result with any issues found.
        """
        result = ValidationResult(is_valid=True)

        if not self.config.read_guard_enabled:
            return result

        # New files don't need to be read first
        if is_new_file:
            return result

        # Check if file has been read
        if not self.file_read_log.has_read(file_path):
            severity = (
                IssueSeverity.ERROR
                if self.config.block_unread_writes
                else IssueSeverity.WARNING
            )

            result.add_issue(
                ValidationIssue(
                    severity=severity,
                    category=IssueCategory.INVALID_REFERENCE,
                    message=(
                        f"Attempting to modify unread file '{file_path}'. "
                        "Please use view_text_file to read the file first."
                    ),
                    source_file=file_path,
                    suggestion=(
                        "Call view_text_file to read the file content and "
                        "understand the existing code structure before modifying."
                    ),
                )
            )
            return result

        # Check if the specific range has been read
        if ranges and len(ranges) == 2:
            start, end = ranges
            if not self.file_read_log.has_read_range(file_path, start, end):
                result.add_issue(
                    ValidationIssue(
                        severity=IssueSeverity.WARNING,
                        category=IssueCategory.INVALID_REFERENCE,
                        message=(
                            f"Attempting to modify unread range [{start}, {end}] "
                            f"in '{file_path}'."
                        ),
                        source_file=file_path,
                        line_number=start,
                        suggestion=(
                            f"Use view_text_file with ranges=[{start}, {end}] "
                            "to read this section first."
                        ),
                    )
                )

        return result

    def should_block(self, result: ValidationResult) -> bool:
        """Determine if an operation should be blocked based on validation result.

        Args:
            result (`ValidationResult`):
                The validation result to check.

        Returns:
            `bool`:
                True if the operation should be blocked.
        """
        from ._config import StrictnessLevel

        if self.config.strictness == StrictnessLevel.RELAXED:
            return False

        if self.config.strictness == StrictnessLevel.STRICT:
            return len(result.errors) > 0 or len(result.warnings) > 0

        # NORMAL: only block on errors
        return len(result.errors) > 0
