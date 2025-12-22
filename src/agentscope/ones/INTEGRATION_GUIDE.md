# HiveCore Validation Integration Guide

## Overview

This guide explains how to integrate the new file tracking and validation modules into the HiveCore execution flow.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  EnhancedProjectContext                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │FileRegistry │ │ValidationEng│ │ContractReg  │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│         │               │               │                    │
│         └───────────────┼───────────────┘                   │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────┐            │
│  │           RoundFeedback Generator           │            │
│  └─────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Initialize Project Context

```python
from agentscope.ones import (
    create_project_context,
    ProjectMemory,
)

# Create with existing ProjectMemory (recommended)
project_memory = ProjectMemory(
    project_id="my-project",
    workspace_dir="/path/to/workspace"
)

context = create_project_context(
    project_id="my-project",
    workspace_dir="/path/to/workspace",
    project_memory=project_memory,
)
```

### 2. Register Architecture Contract

```python
# From ArchitectAgent output
architecture_contract = {
    "api_endpoints": [
        {
            "path": "/api/v1/users",
            "methods": ["GET", "POST"],
            "description": "User management",
            "request_schema": "CreateUserRequest",
            "response_schema": "UserResponse",
        }
    ],
    "data_models": [
        {
            "name": "User",
            "fields": [
                {"name": "id", "type": "int"},
                {"name": "email", "type": "string"},
            ]
        }
    ],
    "file_structure": {
        "backend": {"app_entry": "backend/app/main.py"},
        "frontend": {"views_dir": "frontend/src/views"},
    }
}

context.register_contract(architecture_contract)
```

### 3. Register Files After Generation

```python
# After generating files
files = [
    {"path": "backend/app/main.py", "content": "...", "description": "FastAPI app"},
    {"path": "frontend/src/App.vue", "content": "...", "description": "Main Vue component"},
]

context.register_files_batch(files, created_by="backend_agent")
```

### 4. Validate and Get Feedback

```python
# Run validation
feedback = context.generate_round_feedback(
    requirement_id="REQ-001",
    round_index=1,
    blueprint=blueprint_dict,
)

# Check results
if feedback.is_successful():
    print("Round passed validation!")
else:
    print("Issues found:")
    print(feedback.build_feedback_prompt())

# Use feedback for next round
next_round_prompt = feedback.build_feedback_prompt()
```

## Integration with Execution Loop

### In `_execution.py`

```python
# At the start of run_execution
from agentscope.ones import create_project_context

context = create_project_context(
    project_id=project_id,
    workspace_dir=workspace_dir,
    project_memory=project_memory,
)

# After architecture contract generation
if architecture_contract:
    context.register_contract(architecture_contract)

# After file generation (in stepwise_generate_files or similar)
for file_info in generated_files:
    context.register_file(
        path=file_info["path"],
        content=file_info["content"],
        created_by=f"round_{round_index}",
        description=file_info.get("description", ""),
    )

# After validation
feedback = context.generate_round_feedback(
    requirement_id=rid,
    round_index=round_index,
    blueprint=blueprint,
)

# Use feedback for next round
if not feedback.is_successful():
    feedback_prompt = feedback.build_feedback_prompt()
    # Include in next generation prompt
```

## Custom Validators

### Creating a Language-Specific Analyzer

```python
from agentscope.ones.file_tracking import BaseFileAnalyzer

class TypeScriptAnalyzer(BaseFileAnalyzer):
    def get_supported_extensions(self) -> list[str]:
        return [".ts", ".tsx"]

    def get_language_name(self) -> str:
        return "typescript"

    def _extract_imports(self, content: str) -> list[str]:
        import re
        # TypeScript-specific import patterns
        patterns = [
            r'import\s+.*?\s+from\s+["\']([^"\']+)["\']',
            r'import\s*\(["\']([^"\']+)["\']\)',
        ]
        imports = []
        for pattern in patterns:
            imports.extend(re.findall(pattern, content))
        return imports

    def _extract_exports(self, content: str) -> list[str]:
        import re
        patterns = [
            r'export\s+(?:default\s+)?(?:class|function|const|interface|type|enum)\s+(\w+)',
        ]
        exports = []
        for pattern in patterns:
            exports.extend(re.findall(pattern, content))
        return exports

# Register with context
context.analyzer_registry.register(TypeScriptAnalyzer())
```

### Creating a Custom Validator

```python
from agentscope.ones.dependency_validation import BaseValidator, ValidationResult, ValidationIssue

class SecurityValidator(BaseValidator):
    def get_name(self) -> str:
        return "security_validator"

    def validate(self, context: ValidationContext) -> ValidationResult:
        result = ValidationResult(is_valid=True)

        for path, metadata in context.get_all_files().items():
            # Check for hardcoded secrets
            content = context.file_registry._file_contents.get(path, "")
            if "password=" in content.lower() or "secret=" in content.lower():
                result.add_issue(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    category=IssueCategory.INVALID_REFERENCE,
                    message="Potential hardcoded secret detected",
                    source_file=path,
                ))

        return result

# Register with context
context.validation_engine.register(SecurityValidator())
```

## Feedback Structure

The `RoundFeedback` class provides structured feedback:

```python
feedback = RoundFeedback(
    requirement_id="REQ-001",
    round_index=2,
)

# Properties available:
feedback.is_successful()        # True if no critical issues
feedback.critical_issues        # List of error messages
feedback.warnings               # List of warning messages
feedback.suggestions            # List of info messages
feedback.contract_compliance    # 0-1 score
feedback.unimplemented_items    # List of missing implementations

# Generate prompt for next round
prompt = feedback.build_feedback_prompt(max_issues=10)
```

## Best Practices

1. **Register files immediately after generation**
   - Don't wait until the end of the round
   - This allows validation to catch issues early

2. **Use structured feedback in prompts**
   - Include `feedback.build_feedback_prompt()` in Agent prompts
   - This gives targeted guidance for fixes

3. **Register contracts before generation**
   - Allows blueprint validation against contract
   - Catches design issues before implementation

4. **Use language-specific analyzers when available**
   - More accurate import/export extraction
   - Better validation results

5. **Monitor contract compliance**
   - Track `feedback.contract_compliance` over rounds
   - Should approach 1.0 as implementation progresses
