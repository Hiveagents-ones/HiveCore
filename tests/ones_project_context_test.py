# -*- coding: utf-8 -*-
"""Tests for ProjectContext integration with ExecutionLoop.

This module tests:
1. File registration and tracking
2. Agent output parsing for generated files
3. Dependency validation
4. Round feedback generation
5. Integration with ExecutionContext
"""
import pytest
import tempfile
from pathlib import Path

from agentscope.ones import (
    EnhancedProjectContext,
    create_project_context,
    RoundFeedback,
    FileRegistry,
    FileType,
    FileMetadata,
    ValidationResult,
    IssueSeverity,
    IssueCategory,
)
from agentscope.ones.execution import (
    ExecutionLoop,
    ExecutionContext,
    AgentOutput,
)


class TestProjectContext:
    """Test suite for EnhancedProjectContext."""

    def test_create_project_context(self) -> None:
        """Test project context creation."""
        context = create_project_context(
            project_id="test-project",
        )
        assert context.project_id == "test-project"
        assert context.file_registry is not None

    def test_register_file(self) -> None:
        """Test file registration."""
        context = create_project_context(project_id="test-project")

        content = """
import React from 'react';

export function Button({ label }) {
    return <button>{label}</button>;
}
"""
        metadata = context.register_file(
            path="src/components/Button.tsx",
            content=content,
            created_by="frontend_agent",
            description="Button component",
        )

        assert metadata.path == "src/components/Button.tsx"
        assert metadata.created_by == "frontend_agent"
        assert context.file_exists("src/components/Button.tsx")

    def test_file_content_caching(self) -> None:
        """Test that file content is cached."""
        context = create_project_context(project_id="test-project")
        content = "const x = 1;"
        context.register_file(
            path="src/index.js",
            content=content,
        )

        cached = context.get_file_content("src/index.js")
        assert cached == content

    def test_dependency_declaration_from_package_json(self) -> None:
        """Test dependency declaration from package.json."""
        context = create_project_context(project_id="test-project")

        package_json = """{
    "name": "test-app",
    "dependencies": {
        "react": "^18.0.0",
        "axios": "^1.0.0"
    },
    "devDependencies": {
        "typescript": "^5.0.0"
    }
}"""
        context.register_file(
            path="package.json",
            content=package_json,
        )
        context.declare_dependencies_from_file("package.json", package_json)

        assert "react" in context._declared_dependencies
        assert "axios" in context._declared_dependencies
        assert "typescript" in context._declared_dependencies

    def test_validation(self) -> None:
        """Test validation runs without errors."""
        context = create_project_context(project_id="test-project")

        # Register some files
        context.register_file(
            path="src/index.js",
            content="import { App } from './App';\nApp();",
        )
        context.register_file(
            path="src/App.js",
            content="export function App() { return 'Hello'; }",
        )

        result = context.validate()
        assert isinstance(result, ValidationResult)


class TestRoundFeedback:
    """Test suite for RoundFeedback."""

    def test_feedback_creation(self) -> None:
        """Test feedback object creation."""
        feedback = RoundFeedback(
            requirement_id="REQ-001",
            round_index=1,
        )
        assert feedback.requirement_id == "REQ-001"
        assert feedback.round_index == 1
        assert feedback.is_successful()

    def test_feedback_with_issues(self) -> None:
        """Test feedback with issues."""
        feedback = RoundFeedback(
            requirement_id="REQ-001",
            round_index=1,
            critical_issues=["Missing file: src/main.ts"],
            warnings=["Unused import in utils.ts"],
        )
        assert not feedback.is_successful()
        assert len(feedback.critical_issues) == 1
        assert len(feedback.warnings) == 1

    def test_build_feedback_prompt(self) -> None:
        """Test feedback prompt generation."""
        feedback = RoundFeedback(
            requirement_id="REQ-001",
            round_index=1,
            critical_issues=["Missing file: src/main.ts"],
            warnings=["Unused import"],
        )
        prompt = feedback.build_feedback_prompt()

        assert "Round 1 Feedback" in prompt
        assert "Critical Issues" in prompt
        assert "Missing file" in prompt

    def test_generate_round_feedback(self) -> None:
        """Test generating feedback from context."""
        context = create_project_context(project_id="test-project")

        # Register a file
        context.register_file(
            path="src/index.js",
            content="console.log('hello');",
        )

        feedback = context.generate_round_feedback(
            requirement_id="REQ-001",
            round_index=1,
        )

        assert feedback.requirement_id == "REQ-001"
        assert feedback.files_registered == 1


class TestExecutionContextWithFeedback:
    """Test ExecutionContext with feedback integration."""

    def test_context_with_feedback(self) -> None:
        """Test ExecutionContext includes feedback in prompt."""
        feedback = RoundFeedback(
            requirement_id="REQ-001",
            round_index=1,
            critical_issues=["Missing file: src/main.ts"],
        )

        context = ExecutionContext(
            intent_utterance="Build a todo app",
            round_feedback=feedback,
        )

        prompt = context.build_prompt(
            current_node_id="frontend_task",
            requirement_desc="Create frontend components",
        )

        assert "Missing file" in prompt
        assert "Critical Issues" in prompt

    def test_context_without_feedback(self) -> None:
        """Test ExecutionContext works without feedback."""
        context = ExecutionContext(
            intent_utterance="Build a todo app",
        )

        prompt = context.build_prompt(
            current_node_id="frontend_task",
            requirement_desc="Create frontend components",
        )

        assert "Build a todo app" in prompt
        assert "frontend_task" in prompt


class TestAgentOutputParsing:
    """Test parsing agent output for file extraction."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        # Create a minimal ExecutionLoop for testing
        from unittest.mock import MagicMock

        self.mock_project_pool = MagicMock()
        self.mock_memory_pool = MagicMock()
        self.mock_resource_library = MagicMock()
        self.mock_orchestrator = MagicMock()
        self.mock_task_graph_builder = MagicMock()
        self.mock_kpi_tracker = MagicMock()

    def test_parse_file_block_pattern(self) -> None:
        """Test parsing **File: path** pattern."""
        context = create_project_context(project_id="test-project")

        output = AgentOutput(
            agent_id="frontend_agent",
            node_id="task-1",
            content="""
Here is the component:

**File: src/components/Button.tsx**
```typescript
import React from 'react';

export function Button() {
    return <button>Click me</button>;
}
```

Done!
""",
            success=True,
        )

        loop = ExecutionLoop(
            project_pool=self.mock_project_pool,
            memory_pool=self.mock_memory_pool,
            resource_library=self.mock_resource_library,
            orchestrator=self.mock_orchestrator,
            task_graph_builder=self.mock_task_graph_builder,
            kpi_tracker=self.mock_kpi_tracker,
        )

        files = loop._parse_agent_output_files(output, context)

        assert len(files) == 1
        assert "src/components/Button.tsx" in files
        assert context.file_exists("src/components/Button.tsx")

    def test_parse_xml_file_pattern(self) -> None:
        """Test parsing <file path="..."> pattern."""
        context = create_project_context(project_id="test-project")

        output = AgentOutput(
            agent_id="backend_agent",
            node_id="task-2",
            content="""
<file path="src/api/users.py">
from flask import Blueprint

users_bp = Blueprint('users', __name__)

@users_bp.route('/users')
def get_users():
    return []
</file>
""",
            success=True,
        )

        loop = ExecutionLoop(
            project_pool=self.mock_project_pool,
            memory_pool=self.mock_memory_pool,
            resource_library=self.mock_resource_library,
            orchestrator=self.mock_orchestrator,
            task_graph_builder=self.mock_task_graph_builder,
            kpi_tracker=self.mock_kpi_tracker,
        )

        files = loop._parse_agent_output_files(output, context)

        assert len(files) == 1
        assert "src/api/users.py" in files

    def test_parse_json_files_pattern(self) -> None:
        """Test parsing JSON format with files array."""
        context = create_project_context(project_id="test-project")

        output = AgentOutput(
            agent_id="code_agent",
            node_id="task-3",
            content="""
Here are the generated files:

```json
{
    "files": [
        {
            "path": "src/utils/helper.ts",
            "content": "export function helper() { return 42; }",
            "description": "Utility helper"
        }
    ]
}
```
""",
            success=True,
        )

        loop = ExecutionLoop(
            project_pool=self.mock_project_pool,
            memory_pool=self.mock_memory_pool,
            resource_library=self.mock_resource_library,
            orchestrator=self.mock_orchestrator,
            task_graph_builder=self.mock_task_graph_builder,
            kpi_tracker=self.mock_kpi_tracker,
        )

        files = loop._parse_agent_output_files(output, context)

        assert len(files) == 1
        assert "src/utils/helper.ts" in files

    def test_parse_filename_comment_pattern(self) -> None:
        """Test parsing # filename: path pattern."""
        context = create_project_context(project_id="test-project")

        output = AgentOutput(
            agent_id="python_agent",
            node_id="task-4",
            content="""
Here is the model:

```python
# filename: src/models/user.py
from dataclasses import dataclass

@dataclass
class User:
    id: int
    name: str
```
""",
            success=True,
        )

        loop = ExecutionLoop(
            project_pool=self.mock_project_pool,
            memory_pool=self.mock_memory_pool,
            resource_library=self.mock_resource_library,
            orchestrator=self.mock_orchestrator,
            task_graph_builder=self.mock_task_graph_builder,
            kpi_tracker=self.mock_kpi_tracker,
        )

        files = loop._parse_agent_output_files(output, context)

        assert len(files) == 1
        assert "src/models/user.py" in files


class TestProjectContextPersistence:
    """Test ProjectContext persistence."""

    def test_save_and_load(self) -> None:
        """Test context saves and loads from disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create and populate context
            context1 = create_project_context(
                project_id="test-project",
                workspace_dir=tmpdir,
            )
            context1.register_file(
                path="src/index.js",
                content="console.log('hello');",
                created_by="test_agent",
            )
            context1.declare_dependency("react", "^18.0.0")

            # Create new context from same directory
            context2 = create_project_context(
                project_id="test-project",
                workspace_dir=tmpdir,
            )

            # Should load saved state
            assert context2.file_exists("src/index.js")
            assert "react" in context2._declared_dependencies


class TestFileRegistry:
    """Test FileRegistry functionality."""

    def test_basic_operations(self) -> None:
        """Test basic registry operations."""
        registry = FileRegistry()

        metadata = registry.register(
            path="src/index.ts",
            content="export const x = 1;",
        )

        assert registry.exists("src/index.ts")
        assert registry.get("src/index.ts") == metadata

    def test_query_by_file_type(self) -> None:
        """Test querying files by file type."""
        registry = FileRegistry()

        registry.register(
            path="src/app.py",
            content="print('hello')",
        )
        registry.register(
            path="src/utils.py",
            content="def helper(): pass",
        )
        registry.register(
            path="README.md",
            content="# Readme",
        )

        source_files = registry.query(file_type=FileType.SOURCE_CODE)
        assert len(source_files) == 2

        doc_files = registry.query(file_type=FileType.DOCUMENTATION)
        assert len(doc_files) == 1

    def test_statistics(self) -> None:
        """Test file statistics."""
        registry = FileRegistry()

        registry.register(
            path="src/app.py",
            content="print('hello')",
        )
        registry.register(
            path="src/index.js",
            content="console.log('hi');",
        )

        stats = registry.get_statistics()
        assert stats["total_files"] == 2
        assert "source_code" in stats["by_type"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
