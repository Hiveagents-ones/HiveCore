# -*- coding: utf-8 -*-
"""Tests for ReadGuard module."""
import pytest

from agentscope.ones.code_guard import (
    FileReadLog,
    FileReadRecord,
    ReadGuard,
    CodeGuardConfig,
    StrictnessLevel,
)


class TestFileReadLog:
    """Tests for FileReadLog class."""

    def test_record_read_basic(self) -> None:
        """Test basic file read recording."""
        log = FileReadLog()
        record = log.record_read("/path/to/file.py", "line1\nline2\nline3")

        assert log.has_read("/path/to/file.py")
        assert not log.has_read("/other/file.py")
        assert record.line_count == 3
        assert record.content_hash is not None

    def test_record_read_with_ranges(self) -> None:
        """Test recording partial reads with ranges."""
        log = FileReadLog()
        log.record_read("/file.py", "content", ranges=[1, 10])

        assert log.has_read_range("/file.py", 1, 10)
        assert log.has_read_range("/file.py", 5, 8)
        assert not log.has_read_range("/file.py", 11, 20)

    def test_merge_ranges(self) -> None:
        """Test merging multiple read ranges."""
        log = FileReadLog()
        log.record_read("/file.py", "content1", ranges=[1, 10])
        log.record_read("/file.py", "content2", ranges=[15, 20])

        assert log.has_read_range("/file.py", 1, 10)
        assert log.has_read_range("/file.py", 15, 20)
        assert not log.has_read_range("/file.py", 11, 14)

    def test_full_read_overrides_partial(self) -> None:
        """Test that full read overrides partial reads."""
        log = FileReadLog()
        log.record_read("/file.py", "partial", ranges=[1, 10])
        log.record_read("/file.py", "full content")  # Full read

        assert log.has_read_range("/file.py", 1, 100)  # Should cover everything

    def test_get_all_read_files(self) -> None:
        """Test getting all read files in order."""
        log = FileReadLog()
        log.record_read("/file1.py", "content1")
        log.record_read("/file2.py", "content2")
        log.record_read("/file3.py", "content3")

        files = log.get_all_read_files()
        assert files == ["/file1.py", "/file2.py", "/file3.py"]

    def test_get_statistics(self) -> None:
        """Test getting read statistics."""
        log = FileReadLog()
        log.record_read("/file1.py", "line1\nline2")
        log.record_read("/file2.py", "line1", ranges=[1, 5])

        stats = log.get_statistics()
        assert stats["total_files"] == 2
        assert stats["full_reads"] == 1
        assert stats["partial_reads"] == 1

    def test_clear(self) -> None:
        """Test clearing the log."""
        log = FileReadLog()
        log.record_read("/file.py", "content")

        assert log.has_read("/file.py")
        log.clear()
        assert not log.has_read("/file.py")


class TestReadGuard:
    """Tests for ReadGuard class."""

    def test_block_unread_write(self) -> None:
        """Test blocking write to unread file."""
        config = CodeGuardConfig(block_unread_writes=True)
        log = FileReadLog()
        guard = ReadGuard(config, log)

        result = guard.check_before_write("/unread.py")

        assert len(result.errors) > 0
        assert guard.should_block(result)

    def test_allow_after_read(self) -> None:
        """Test allowing write after read."""
        config = CodeGuardConfig(block_unread_writes=True)
        log = FileReadLog()
        log.record_read("/file.py", "content")
        guard = ReadGuard(config, log)

        result = guard.check_before_write("/file.py")

        assert len(result.errors) == 0
        assert not guard.should_block(result)

    def test_allow_new_file(self) -> None:
        """Test allowing new file creation without read."""
        config = CodeGuardConfig(block_unread_writes=True)
        log = FileReadLog()
        guard = ReadGuard(config, log)

        result = guard.check_before_write("/new_file.py", is_new_file=True)

        assert len(result.errors) == 0

    def test_warn_unread_range(self) -> None:
        """Test warning when writing to unread range."""
        config = CodeGuardConfig(block_unread_writes=True)
        log = FileReadLog()
        log.record_read("/file.py", "content", ranges=[1, 10])
        guard = ReadGuard(config, log)

        result = guard.check_before_write("/file.py", ranges=[20, 30])

        assert len(result.warnings) > 0
        assert len(result.errors) == 0

    def test_strictness_relaxed(self) -> None:
        """Test RELAXED strictness never blocks."""
        config = CodeGuardConfig(
            strictness=StrictnessLevel.RELAXED,
            block_unread_writes=True,
        )
        log = FileReadLog()
        guard = ReadGuard(config, log)

        result = guard.check_before_write("/unread.py")

        assert not guard.should_block(result)

    def test_strictness_strict(self) -> None:
        """Test STRICT strictness blocks on warnings."""
        config = CodeGuardConfig(
            strictness=StrictnessLevel.STRICT,
            block_unread_writes=True,
        )
        log = FileReadLog()
        log.record_read("/file.py", "content", ranges=[1, 10])
        guard = ReadGuard(config, log)

        result = guard.check_before_write("/file.py", ranges=[20, 30])

        assert guard.should_block(result)

    def test_disabled_guard(self) -> None:
        """Test disabled guard allows everything."""
        config = CodeGuardConfig(read_guard_enabled=False)
        log = FileReadLog()
        guard = ReadGuard(config, log)

        result = guard.check_before_write("/unread.py")

        assert len(result.issues) == 0
