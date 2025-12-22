# -*- coding: utf-8 -*-
"""Tests for the AcceptanceAgent module."""
import pytest
from unittest.mock import MagicMock, AsyncMock

from agentscope.ones.acceptance_agent import (
    AcceptanceAgent,
    AcceptanceResult,
    AcceptanceStatus,
    ValidationCheck,
    ValidationEnvironment,
    VALIDATION_STRATEGY_PROMPT,
    RESULT_ANALYSIS_PROMPT,
)


class TestAcceptanceStatus:
    """Tests for AcceptanceStatus enum."""

    def test_status_values(self):
        """Test that all expected status values exist."""
        assert AcceptanceStatus.PASSED.value == "passed"
        assert AcceptanceStatus.FAILED.value == "failed"
        assert AcceptanceStatus.PARTIAL.value == "partial"
        assert AcceptanceStatus.ERROR.value == "error"


class TestValidationEnvironment:
    """Tests for ValidationEnvironment enum."""

    def test_environment_values(self):
        """Test that all expected environment values exist."""
        assert ValidationEnvironment.CLI.value == "cli"
        assert ValidationEnvironment.BROWSER.value == "browser"
        assert ValidationEnvironment.API.value == "api"
        assert ValidationEnvironment.GUI.value == "gui"
        assert ValidationEnvironment.MOBILE.value == "mobile"
        assert ValidationEnvironment.VISUAL.value == "visual"


class TestValidationCheck:
    """Tests for ValidationCheck dataclass."""

    def test_validation_check_creation(self):
        """Test creating a validation check."""
        check = ValidationCheck(
            name="test_check",
            description="Test description",
            environment=ValidationEnvironment.CLI,
            action={"type": "shell", "command": "echo test"},
            passed=True,
            output="test output",
        )
        assert check.name == "test_check"
        assert check.passed is True
        assert check.environment == ValidationEnvironment.CLI
        assert check.action["type"] == "shell"
        assert check.error is None

    def test_validation_check_with_browser_env(self):
        """Test creating a browser validation check."""
        check = ValidationCheck(
            name="ui_check",
            description="Check UI element",
            environment=ValidationEnvironment.BROWSER,
            action={"type": "check_element", "selector": "#app"},
            passed=True,
            screenshot="/path/to/screenshot.png",
        )
        assert check.environment == ValidationEnvironment.BROWSER
        assert check.screenshot is not None

    def test_validation_check_with_error(self):
        """Test creating a failed validation check with error."""
        check = ValidationCheck(
            name="failed_check",
            description="Failed test",
            environment=ValidationEnvironment.API,
            action={"type": "request", "url": "http://example.com"},
            passed=False,
            error="Connection refused",
        )
        assert check.passed is False
        assert check.error == "Connection refused"


class TestAcceptanceResult:
    """Tests for AcceptanceResult dataclass."""

    def test_passed_result(self):
        """Test a passed acceptance result."""
        result = AcceptanceResult(
            status=AcceptanceStatus.PASSED,
            score=0.95,
            summary="All checks passed",
        )
        assert result.passed is True
        assert result.score == 0.95

    def test_failed_result(self):
        """Test a failed acceptance result."""
        result = AcceptanceResult(
            status=AcceptanceStatus.FAILED,
            score=0.3,
            summary="Multiple checks failed",
        )
        assert result.passed is False
        assert result.score == 0.3

    def test_result_with_deliverable_assessment(self):
        """Test result with deliverable assessment."""
        result = AcceptanceResult(
            status=AcceptanceStatus.PARTIAL,
            score=0.7,
            checks=[],
            deliverable_assessment={
                "criterion_1": {"met": True, "evidence": "API returns 200"},
                "criterion_2": {"met": False, "evidence": "UI missing"},
            },
        )
        assert "criterion_1" in result.deliverable_assessment
        assert result.deliverable_assessment["criterion_1"]["met"] is True

    def test_to_dict(self):
        """Test converting result to dictionary."""
        check = ValidationCheck(
            name="check1",
            description="desc1",
            environment=ValidationEnvironment.BROWSER,
            action={"type": "navigate"},
            passed=True,
            output="output",
            screenshot="/screenshot.png",
        )
        result = AcceptanceResult(
            status=AcceptanceStatus.PASSED,
            score=0.9,
            checks=[check],
            summary="Good",
            recommendations=["Consider adding more tests"],
            deliverable_assessment={"test": {"met": True}},
        )
        d = result.to_dict()
        assert d["status"] == "passed"
        assert d["score"] == 0.9
        assert len(d["checks"]) == 1
        assert d["checks"][0]["environment"] == "browser"
        assert d["deliverable_assessment"]["test"]["met"] is True


class TestAcceptanceAgent:
    """Tests for AcceptanceAgent class."""

    @pytest.fixture
    def mock_model(self):
        """Create a mock LLM model."""
        model = MagicMock()
        model.reply = AsyncMock()
        return model

    @pytest.fixture
    def mock_orchestrator(self):
        """Create a mock sandbox orchestrator."""
        orchestrator = MagicMock()
        # Mock execute_command to return success
        result = MagicMock()
        result.success = True
        result.output = "Command output"
        result.error = None
        orchestrator.execute_command.return_value = result
        return orchestrator

    @pytest.fixture
    def agent(self, mock_model, mock_orchestrator):
        """Create an AcceptanceAgent instance."""
        return AcceptanceAgent(
            model=mock_model,
            sandbox_orchestrator=mock_orchestrator,
        )

    def test_agent_creation(self, agent):
        """Test creating an AcceptanceAgent."""
        assert agent._default_timeout == 120
        assert agent._model is not None
        assert agent._orchestrator is not None

    def test_get_available_environments(self, agent):
        """Test getting available environments description."""
        envs = agent._get_available_environments()
        assert "cli" in envs
        assert "browser" in envs
        assert "api" in envs

    def test_extract_json_from_code_block(self, agent):
        """Test extracting JSON from markdown code block."""
        text = '''Here is the strategy:
```json
{
  "artifact_analysis": {"detected_type": "web"},
  "validation_checks": []
}
```
'''
        result = agent._extract_json(text)
        assert result is not None
        assert result["artifact_analysis"]["detected_type"] == "web"

    def test_extract_json_bare(self, agent):
        """Test extracting bare JSON."""
        text = '{"status": "passed", "score": 85}'
        result = agent._extract_json(text)
        assert result is not None
        assert result["status"] == "passed"

    def test_extract_json_invalid(self, agent):
        """Test extracting from invalid JSON."""
        text = "This is not JSON at all"
        result = agent._extract_json(text)
        assert result is None

    @pytest.mark.asyncio
    async def test_list_workspace_files(self, agent, mock_orchestrator):
        """Test listing workspace files."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "/workspace/main.py\n/workspace/test.py\n"
        mock_orchestrator.execute_command.return_value = mock_result

        files = await agent._list_workspace_files("/workspace")
        assert "main.py" in files
        assert "test.py" in files

    @pytest.mark.asyncio
    async def test_validate_empty_workspace(self, agent, mock_orchestrator):
        """Test validation with empty workspace."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = ""
        mock_orchestrator.execute_command.return_value = mock_result

        result = await agent.validate(workspace_dir="/workspace")
        assert result.status == AcceptanceStatus.ERROR
        assert "为空" in result.summary

    @pytest.mark.asyncio
    async def test_execute_cli_check_shell(self, agent, mock_orchestrator):
        """Test executing a CLI shell check."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "OK"
        mock_result.error = None
        mock_orchestrator.execute_command.return_value = mock_result

        check = await agent._execute_cli_check(
            name="test",
            description="Test shell command",
            action={"type": "shell", "command": "echo OK"},
            workspace_dir="/workspace",
        )
        assert check.passed is True
        assert check.environment == ValidationEnvironment.CLI

    @pytest.mark.asyncio
    async def test_execute_cli_check_file_exists(self, agent, mock_orchestrator):
        """Test executing a file existence check."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "EXISTS"
        mock_orchestrator.execute_command.return_value = mock_result

        check = await agent._execute_cli_check(
            name="file_check",
            description="Check file exists",
            action={"type": "file_check", "paths": ["main.py"], "check": "exists"},
            workspace_dir="/workspace",
        )
        assert check.passed is True

    @pytest.mark.asyncio
    async def test_execute_api_check(self, agent, mock_orchestrator):
        """Test executing an API check."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "200"
        mock_result.error = None
        mock_orchestrator.execute_command.return_value = mock_result

        check = await agent._execute_api_check(
            name="api_test",
            description="Test API endpoint",
            action={
                "type": "request",
                "method": "GET",
                "url": "http://localhost:8000/api/health",
                "expected_status": 200,
            },
        )
        assert check.passed is True
        assert check.environment == ValidationEnvironment.API

    @pytest.mark.asyncio
    async def test_validate_with_strategy(self, agent, mock_model, mock_orchestrator):
        """Test full validation flow with LLM strategy."""
        # Mock file listing
        list_result = MagicMock()
        list_result.success = True
        list_result.output = "/workspace/main.py\n/workspace/package.json\n"

        # Mock command execution
        exec_result = MagicMock()
        exec_result.success = True
        exec_result.output = "OK"
        exec_result.error = None

        mock_orchestrator.execute_command.side_effect = [list_result, exec_result]

        # Mock LLM responses
        strategy_response = MagicMock()
        strategy_response.content = '''```json
{
  "artifact_analysis": {
    "detected_type": "web",
    "main_components": ["frontend"],
    "entry_points": ["http://localhost:3000"]
  },
  "validation_strategy": {
    "approach": "CLI and browser testing",
    "environments_needed": ["cli"]
  },
  "validation_checks": [
    {
      "name": "check_files",
      "description": "Verify files exist",
      "environment": "cli",
      "action": {"type": "shell", "command": "ls -la"},
      "required": true
    }
  ],
  "reasoning": "Web project detected"
}
```'''

        analysis_response = MagicMock()
        analysis_response.content = '''```json
{
  "deliverable_assessment": {
    "files_complete": {"met": true, "evidence": "All files present"}
  },
  "status": "passed",
  "score": 90,
  "summary": "All acceptance criteria met",
  "recommendations": []
}
```'''

        mock_model.reply.side_effect = [strategy_response, analysis_response]

        result = await agent.validate(
            workspace_dir="/workspace",
            user_requirement="Create a web app",
            acceptance_criteria=["Files must exist", "App must run"],
            artifact_type="web",
        )

        assert mock_model.reply.call_count == 2
        assert result.status == AcceptanceStatus.PASSED


class TestPromptTemplates:
    """Tests for prompt templates."""

    def test_strategy_prompt_has_placeholders(self):
        """Test that strategy prompt has required placeholders."""
        assert "{user_requirement}" in VALIDATION_STRATEGY_PROMPT
        assert "{acceptance_criteria}" in VALIDATION_STRATEGY_PROMPT
        assert "{artifact_type}" in VALIDATION_STRATEGY_PROMPT
        assert "{file_list}" in VALIDATION_STRATEGY_PROMPT
        assert "{available_environments}" in VALIDATION_STRATEGY_PROMPT

    def test_result_analysis_prompt_has_placeholders(self):
        """Test that result analysis prompt has required placeholders."""
        assert "{user_requirement}" in RESULT_ANALYSIS_PROMPT
        assert "{acceptance_criteria}" in RESULT_ANALYSIS_PROMPT
        assert "{results}" in RESULT_ANALYSIS_PROMPT

    def test_strategy_prompt_describes_environments(self):
        """Test that strategy prompt describes available environments."""
        assert "cli" in VALIDATION_STRATEGY_PROMPT.lower()
        assert "browser" in VALIDATION_STRATEGY_PROMPT.lower()
        assert "api" in VALIDATION_STRATEGY_PROMPT.lower()

    def test_strategy_prompt_has_action_examples(self):
        """Test that strategy prompt has action type examples."""
        assert '"type": "shell"' in VALIDATION_STRATEGY_PROMPT
        assert '"type": "navigate"' in VALIDATION_STRATEGY_PROMPT
        assert '"type": "request"' in VALIDATION_STRATEGY_PROMPT


class TestLLMDrivenValidation:
    """Tests demonstrating LLM-driven validation (no hardcoded methods)."""

    def test_no_hardcoded_framework_detection(self):
        """Verify no hardcoded framework detection exists."""
        import inspect
        from agentscope.ones.acceptance_agent import AcceptanceAgent

        source = inspect.getsource(AcceptanceAgent)

        # Should NOT contain hardcoded framework names in validation logic
        hardcoded_patterns = [
            "if 'django'",
            "if 'flask'",
            "if 'fastapi'",
            "if 'react'",
            "if 'vue'",
            "manage.py",
            "settings.py",
        ]

        for pattern in hardcoded_patterns:
            lines = [
                line for line in source.split("\n")
                if pattern in line.lower()
                and not line.strip().startswith("#")
                and not line.strip().startswith('"""')
                and not line.strip().startswith("'''")
            ]
            assert len(lines) == 0, f"Found hardcoded pattern: {pattern}"

    def test_validation_uses_multiple_environments(self):
        """Verify validation supports multiple environments."""
        envs = [e.value for e in ValidationEnvironment]
        assert "cli" in envs
        assert "browser" in envs
        assert "api" in envs
        assert "gui" in envs
        assert "mobile" in envs

    def test_validation_is_llm_driven(self):
        """Verify validation logic uses LLM prompts."""
        assert "根据" in VALIDATION_STRATEGY_PROMPT or "分析" in VALIDATION_STRATEGY_PROMPT
        assert "交付标准" in VALIDATION_STRATEGY_PROMPT
        assert "产物类型" in VALIDATION_STRATEGY_PROMPT


class TestMultiEnvironmentValidation:
    """Tests for multi-environment validation capabilities."""

    def test_cli_action_types(self):
        """Test CLI action types are documented."""
        assert "shell" in VALIDATION_STRATEGY_PROMPT
        assert "file_check" in VALIDATION_STRATEGY_PROMPT

    def test_browser_action_types(self):
        """Test browser action types are documented."""
        assert "navigate" in VALIDATION_STRATEGY_PROMPT
        assert "screenshot" in VALIDATION_STRATEGY_PROMPT
        assert "check_element" in VALIDATION_STRATEGY_PROMPT
        assert "click" in VALIDATION_STRATEGY_PROMPT

    def test_api_action_types(self):
        """Test API action types are documented."""
        assert "request" in VALIDATION_STRATEGY_PROMPT
        assert "GET" in VALIDATION_STRATEGY_PROMPT or "method" in VALIDATION_STRATEGY_PROMPT


class TestDeliverableAssessment:
    """Tests for deliverable assessment against acceptance criteria."""

    def test_result_includes_deliverable_assessment(self):
        """Test that result includes deliverable assessment."""
        result = AcceptanceResult(
            status=AcceptanceStatus.PASSED,
            score=0.9,
            deliverable_assessment={
                "api_accessible": {"met": True, "evidence": "Returns 200"},
                "ui_renders": {"met": True, "evidence": "Page loads"},
            },
        )
        assert "api_accessible" in result.deliverable_assessment
        assert result.deliverable_assessment["api_accessible"]["met"] is True

    def test_analysis_prompt_asks_for_criterion_check(self):
        """Test that analysis prompt asks LLM to check each criterion."""
        assert "交付标准" in RESULT_ANALYSIS_PROMPT
        assert "criterion" in RESULT_ANALYSIS_PROMPT.lower() or "标准" in RESULT_ANALYSIS_PROMPT


class TestIntegrationWithExecutionLoop:
    """Tests for integration with ExecutionLoop."""

    def test_execution_report_has_acceptance_result(self):
        """Test that ExecutionReport includes acceptance_result field."""
        from agentscope.ones.execution import ExecutionReport
        import dataclasses

        fields = {f.name for f in dataclasses.fields(ExecutionReport)}
        assert "acceptance_result" in fields

    def test_execution_loop_accepts_acceptance_agent(self):
        """Test that ExecutionLoop constructor accepts acceptance_agent."""
        from agentscope.ones.execution import ExecutionLoop
        import inspect

        sig = inspect.signature(ExecutionLoop.__init__)
        params = sig.parameters
        assert "acceptance_agent" in params
        assert "workspace_dir" in params
