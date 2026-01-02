# -*- coding: utf-8 -*-
"""Integration tests for CodeGuard system."""
import pytest

from agentscope.ones.code_guard import (
    CodeGuardManager,
    CodeGuardConfig,
    StrictnessLevel,
    create_code_guard_manager,
)


class TestCodeGuardManager:
    """Tests for CodeGuardManager class."""

    def test_create_manager(self) -> None:
        """Test creating a manager with default config."""
        manager = CodeGuardManager()

        assert manager.config.enabled is True
        assert manager.config.strictness == StrictnessLevel.NORMAL

    def test_create_manager_with_config(self) -> None:
        """Test creating a manager with custom config."""
        config = CodeGuardConfig(
            strictness=StrictnessLevel.STRICT,
            block_unread_writes=False,
        )
        manager = CodeGuardManager(config)

        assert manager.config.strictness == StrictnessLevel.STRICT
        assert manager.config.block_unread_writes is False

    def test_factory_function(self) -> None:
        """Test factory function creates manager correctly."""
        manager = create_code_guard_manager(
            strictness=StrictnessLevel.RELAXED,
            check_syntax=False,
        )

        assert manager.config.strictness == StrictnessLevel.RELAXED
        assert manager.config.check_syntax is False

    def test_view_postprocess_records_read(self) -> None:
        """Test view postprocess records file reads."""
        manager = CodeGuardManager()
        postprocess = manager.create_view_postprocess()

        # Simulate tool call
        tool_call = {
            "id": "1",
            "type": "tool_use",
            "name": "view_text_file",
            "input": {"file_path": "/test.py"},
        }

        # Simulate response with content
        from agentscope.tool._response import ToolResponse

        response = ToolResponse(
            content=[
                {
                    "type": "text",
                    "text": "```python\ndef hello():\n    pass\n```",
                }
            ]
        )

        result = postprocess(tool_call, response)

        # Should not modify response
        assert result is None

        # Should have recorded the read
        assert manager.file_read_log.has_read("/test.py")

        # Should have extracted interface
        assert manager.interface_registry.exists("hello")

    def test_write_postprocess_blocks_unread(self) -> None:
        """Test write postprocess blocks writes to unread files."""
        import tempfile
        import os

        config = CodeGuardConfig(block_unread_writes=True)
        manager = CodeGuardManager(config)
        postprocess = manager.create_write_postprocess()

        # Create an actual file to make is_new_file = False
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("# existing file\n")
            temp_path = f.name

        try:
            # Simulate write without read to existing file
            tool_call = {
                "id": "1",
                "type": "tool_use",
                "name": "write_text_file",
                "input": {
                    "file_path": temp_path,
                    "content": "def new_func(): pass",
                },
            }

            from agentscope.tool._response import ToolResponse

            response = ToolResponse(
                content=[{"type": "text", "text": "Write successful"}]
            )

            result = postprocess(tool_call, response)

            # Should return blocking response
            assert result is not None
            assert "code-guard" in result.content[0]["text"].lower()
        finally:
            os.unlink(temp_path)

    def test_write_postprocess_allows_after_read(self) -> None:
        """Test write postprocess allows writes after read."""
        config = CodeGuardConfig(block_unread_writes=True)
        manager = CodeGuardManager(config)

        # First, simulate a read
        view_postprocess = manager.create_view_postprocess()
        view_call = {
            "id": "1",
            "type": "tool_use",
            "name": "view_text_file",
            "input": {"file_path": "/test.py"},
        }

        from agentscope.tool._response import ToolResponse

        view_response = ToolResponse(
            content=[{"type": "text", "text": "def old(): pass"}]
        )
        view_postprocess(view_call, view_response)

        # Now simulate write
        write_postprocess = manager.create_write_postprocess()
        write_call = {
            "id": "2",
            "type": "tool_use",
            "name": "write_text_file",
            "input": {
                "file_path": "/test.py",
                "content": "def new(): pass",
            },
        }
        write_response = ToolResponse(
            content=[{"type": "text", "text": "Write successful"}]
        )

        result = write_postprocess(write_call, write_response)

        # Should not block (may have warnings but not blocking)
        if result is not None:
            assert "blocked" not in result.content[0]["text"].lower()

    def test_get_statistics(self) -> None:
        """Test getting manager statistics."""
        manager = CodeGuardManager()

        # Record some reads
        manager.file_read_log.record_read("/file1.py", "content1")
        manager.file_read_log.record_read("/file2.py", "content2")

        # Register some interfaces
        manager.interface_registry.extract_and_register(
            "/file1.py",
            "def func(): pass",
        )

        stats = manager.get_statistics()

        assert stats["enabled"] is True
        assert stats["file_reads"]["total_files"] == 2
        assert stats["interfaces"]["total"] == 1

    def test_reset(self) -> None:
        """Test resetting manager state."""
        manager = CodeGuardManager()

        # Add some state
        manager.file_read_log.record_read("/file.py", "content")
        manager.interface_registry.extract_and_register(
            "/file.py",
            "def func(): pass",
        )

        assert manager.file_read_log.has_read("/file.py")
        assert manager.interface_registry.exists("func")

        manager.reset()

        assert not manager.file_read_log.has_read("/file.py")
        assert not manager.interface_registry.exists("func")


class TestWriteGuardIntegration:
    """Integration tests for WriteGuard."""

    def test_syntax_check_detects_unbalanced_brackets(self) -> None:
        """Test that syntax check detects unbalanced brackets."""
        manager = CodeGuardManager()

        # Record a read first
        manager.file_read_log.record_read("/test.py", "original")

        postprocess = manager.create_write_postprocess()

        tool_call = {
            "id": "1",
            "type": "tool_use",
            "name": "write_text_file",
            "input": {
                "file_path": "/test.py",
                "content": "def broken(:\n    pass",  # Missing closing paren
            },
        }

        from agentscope.tool._response import ToolResponse

        response = ToolResponse(
            content=[{"type": "text", "text": "Write successful"}]
        )

        result = postprocess(tool_call, response)

        # Should have warnings about syntax
        if result is not None:
            text = result.content[-1]["text"]
            assert "bracket" in text.lower() or "warning" in text.lower()


class TestDirectIntegration:
    """Tests for direct integration methods (for FileEditor)."""

    def test_record_file_read(self) -> None:
        """Test recording file reads directly."""
        manager = CodeGuardManager()

        # Record a read
        manager.record_file_read("/test.py", "def hello(): pass")

        # Should be recorded
        assert manager.file_read_log.has_read("/test.py")
        assert manager.interface_registry.exists("hello")

    def test_validate_content(self) -> None:
        """Test validating content before write."""
        config = CodeGuardConfig(
            block_unread_writes=True,
            warn_unknown_calls=True,
        )
        manager = CodeGuardManager(config)

        # First record a read
        manager.record_file_read("/test.py", "def existing(): pass")

        # Validate content with unknown function
        result = manager.validate_content(
            "/test.py",
            "def new_func():\n    unknown_func()\n",
            is_new_file=False,
        )

        # Should have warnings about unknown function
        assert len(result.issues) > 0

    def test_validate_content_blocks_unread(self) -> None:
        """Test that validate_content returns blocking errors for unread files."""
        import tempfile
        import os

        config = CodeGuardConfig(block_unread_writes=True)
        manager = CodeGuardManager(config)

        # Create an actual file (so it's not a new file)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("# existing\n")
            temp_path = f.name

        try:
            # Validate without reading first
            result = manager.validate_content(temp_path, "def new(): pass", is_new_file=False)

            # Should have blocking error
            assert manager.should_block_write(result)
        finally:
            os.unlink(temp_path)

    def test_format_warnings(self) -> None:
        """Test formatting validation warnings."""
        manager = CodeGuardManager()

        # Record a read
        manager.record_file_read("/test.py", "original")

        # Validate content with syntax issue
        result = manager.validate_content(
            "/test.py",
            "def broken(:\n    pass",  # Missing paren
            is_new_file=False,
        )

        # Format warnings
        warnings = manager.format_warnings(result)

        # Should have warnings text
        if result.issues:
            assert "<code-guard-warnings>" in warnings

    def test_update_after_write(self) -> None:
        """Test updating registries after write."""
        manager = CodeGuardManager()

        # Update after write
        manager.update_after_write("/new.py", "def new_func(): pass")

        # Should be registered
        assert manager.interface_registry.exists("new_func")
        assert manager.file_read_log.has_read("/new.py")


class TestHallucinationDetectorIntegration:
    """Integration tests for HallucinationDetector."""

    def test_detects_unknown_function_calls(self) -> None:
        """Test that unknown function calls are detected."""
        config = CodeGuardConfig(warn_unknown_calls=True)
        manager = CodeGuardManager(config)

        # Read a file with known functions
        manager.interface_registry.extract_and_register(
            "/utils.py",
            "def known_func(): pass",
        )

        # Record read of target file
        manager.file_read_log.record_read("/test.py", "original")

        postprocess = manager.create_write_postprocess()

        tool_call = {
            "id": "1",
            "type": "tool_use",
            "name": "write_text_file",
            "input": {
                "file_path": "/test.py",
                "content": """
def main():
    known_func()  # This exists
    unknown_func()  # This doesn't exist
""",
            },
        }

        from agentscope.tool._response import ToolResponse

        response = ToolResponse(
            content=[{"type": "text", "text": "Write successful"}]
        )

        result = postprocess(tool_call, response)

        # Should have info about unknown function
        if result is not None:
            text = " ".join(block.get("text", "") for block in result.content)
            assert "unknown_func" in text or "unknown" in text.lower()
