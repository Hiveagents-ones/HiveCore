# -*- coding: utf-8 -*-
"""Unified project context that integrates all tracking and validation.

This module provides a single entry point for:
1. File registration and tracking
2. Dependency validation
3. Contract validation
4. Structured feedback generation

It bridges the gap between the existing ProjectMemory and the new
validation systems while maintaining backward compatibility.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .file_tracking import (
    FileRegistry,
    FileAnalyzerRegistry,
    FileMetadata,
    FileType,
)
from .dependency_validation import (
    ValidationContext,
    ValidationEngine,
    ValidationResult,
    ValidationIssue,
    IssueSeverity,
    IssueCategory,
    create_default_validation_engine,
)
from .contract_validation import (
    ArchitectureContract,
    ContractValidator,
    ContractRegistry,
)
from .memory import ProjectMemory, DecisionCategory


@dataclass
class RoundFeedback:
    """Structured feedback for a generation round.

    This provides clear, actionable feedback for the next round
    based on validation results and other checks.
    """

    requirement_id: str
    round_index: int

    # Validation results
    validation_result: ValidationResult | None = None

    # File statistics
    files_generated: int = 0
    files_registered: int = 0

    # Contract compliance
    contract_compliance: float = 1.0  # 0-1 score
    unimplemented_items: list[str] = field(default_factory=list)

    # Categorized issues for targeted feedback
    critical_issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def add_validation_result(self, result: ValidationResult) -> None:
        """Add validation result and categorize issues."""
        self.validation_result = result

        for issue in result.issues:
            msg = issue.format_message()

            if issue.severity == IssueSeverity.ERROR:
                self.critical_issues.append(msg)
            elif issue.severity == IssueSeverity.WARNING:
                self.warnings.append(msg)
            else:
                self.suggestions.append(msg)

    def add_acceptance_result(self, acceptance_result: "Any") -> None:
        """Add acceptance validation result to feedback.

        This integrates AcceptanceAgent's validation results (including
        dependency, compile, startup, and function checks) into the
        feedback that will be passed to agents in the next round.

        Args:
            acceptance_result: AcceptanceResult from AcceptanceAgent.
        """
        if acceptance_result is None:
            return

        # Add failed checks to critical issues
        for check in getattr(acceptance_result, "checks", []):
            if not check.passed:
                phase = getattr(check, "phase", "unknown")
                is_critical = getattr(check, "critical", False)
                error_msg = check.error or "检查失败"

                issue_msg = f"[{phase}] {check.name}: {error_msg}"

                if is_critical:
                    self.critical_issues.append(f"【关键】{issue_msg}")
                else:
                    self.warnings.append(issue_msg)

        # Add recommendations as suggestions
        for rec in getattr(acceptance_result, "recommendations", []):
            self.suggestions.append(f"建议: {rec}")

        # Add summary if failed
        if not getattr(acceptance_result, "passed", True):
            summary = getattr(acceptance_result, "summary", "验收未通过")
            if summary and summary not in self.critical_issues:
                self.critical_issues.insert(0, f"【验收失败】{summary}")

    def build_feedback_prompt(self, max_issues: int = 10) -> str:
        """Build a feedback prompt for the next generation round.

        Args:
            max_issues: Maximum number of issues to include per category.

        Returns:
            Formatted feedback string for use in agent prompts.
        """
        lines = []

        if self.critical_issues:
            lines.append("## Critical Issues (Must Fix)")
            lines.append("")
            for issue in self.critical_issues[:max_issues]:
                lines.append(f"- {issue}")
            if len(self.critical_issues) > max_issues:
                lines.append(f"- ... and {len(self.critical_issues) - max_issues} more")
            lines.append("")

        if self.warnings:
            lines.append("## Warnings (Should Fix)")
            lines.append("")
            for issue in self.warnings[:max_issues]:
                lines.append(f"- {issue}")
            if len(self.warnings) > max_issues:
                lines.append(f"- ... and {len(self.warnings) - max_issues} more")
            lines.append("")

        if self.unimplemented_items:
            lines.append("## Missing Implementations")
            lines.append("")
            for item in self.unimplemented_items[:max_issues]:
                lines.append(f"- {item}")
            lines.append("")

        if self.suggestions and not self.critical_issues:
            lines.append("## Suggestions")
            lines.append("")
            for sugg in self.suggestions[:5]:
                lines.append(f"- {sugg}")
            lines.append("")

        # Summary
        if not lines:
            lines.append("No issues detected in this round.")
        else:
            lines.insert(0, f"## Round {self.round_index} Feedback\n")

        return "\n".join(lines)

    def is_successful(self) -> bool:
        """Check if the round was successful (no critical issues)."""
        return len(self.critical_issues) == 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "requirement_id": self.requirement_id,
            "round_index": self.round_index,
            "files_generated": self.files_generated,
            "files_registered": self.files_registered,
            "contract_compliance": self.contract_compliance,
            "unimplemented_items": self.unimplemented_items,
            "critical_issues": self.critical_issues,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "is_successful": self.is_successful(),
        }


class ProjectContext:
    """Unified project context integrating all tracking and validation.

    This class provides a single interface for:
    - File registration and tracking
    - Dependency validation
    - Contract validation
    - Feedback generation

    It can be used alongside or instead of ProjectMemory.
    """

    CONTEXT_FILE_NAME = ".project_context.json"

    def __init__(
        self,
        project_id: str,
        workspace_dir: str | Path | None = None,
        project_memory: ProjectMemory | None = None,
    ) -> None:
        """Initialize project context.

        Args:
            project_id: Unique project identifier.
            workspace_dir: Optional workspace directory for persistence.
            project_memory: Optional existing ProjectMemory to integrate with.
        """
        self.project_id = project_id
        self.workspace_dir = Path(workspace_dir) if workspace_dir else None

        # Core components
        self.file_registry = FileRegistry()
        self.analyzer_registry = FileAnalyzerRegistry()
        self.validation_engine = create_default_validation_engine()
        self.contract_registry = ContractRegistry()
        self.contract_validator = ContractValidator()

        # Integration with existing ProjectMemory
        self._project_memory = project_memory

        # Declared dependencies (from package.json, requirements.txt, etc.)
        self._declared_dependencies: dict[str, str] = {}

        # Round history
        self._round_feedbacks: list[RoundFeedback] = []

        # File content cache for validation
        self._file_contents: dict[str, str] = {}

        # Change listeners
        self._on_file_registered: list[Callable[[str, FileMetadata], None]] = []

        # Load from disk if available
        self._load()

    def _get_context_path(self) -> Path | None:
        """Get path to context file."""
        if self.workspace_dir:
            return self.workspace_dir / self.CONTEXT_FILE_NAME
        return None

    def _load(self) -> None:
        """Load context from disk if available."""
        path = self._get_context_path()
        if path and path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                self.file_registry.from_dict(data.get("file_registry", {}))
                self._declared_dependencies = data.get("declared_dependencies", {})
            except (json.JSONDecodeError, KeyError, ValueError):
                pass  # Start fresh if corrupted

    def _save(self) -> None:
        """Persist context to disk."""
        path = self._get_context_path()
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "project_id": self.project_id,
                "file_registry": self.file_registry.to_dict(),
                "declared_dependencies": self._declared_dependencies,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    # ========== File Registration ==========

    def register_file(
        self,
        path: str,
        content: str,
        created_by: str = "",
        description: str = "",
        **extra: Any,
    ) -> FileMetadata:
        """Register a file with automatic metadata extraction.

        This also updates the ProjectMemory if available.

        Args:
            path: Relative file path.
            content: File content.
            created_by: Agent or process that created this file.
            description: Human-readable description.
            **extra: Additional metadata.

        Returns:
            FileMetadata for the registered file.
        """
        metadata = self.file_registry.register(
            path=path,
            content=content,
            created_by=created_by,
            description=description,
            **extra,
        )

        # Cache content for validation
        self._file_contents[path] = content

        # Update ProjectMemory if available
        if self._project_memory:
            self._project_memory.register_file(path, description or path)

        # Notify listeners
        for listener in self._on_file_registered:
            listener(path, metadata)

        self._save()
        return metadata

    def register_files_batch(
        self,
        files: list[dict[str, Any]],
        created_by: str = "",
    ) -> list[FileMetadata]:
        """Register multiple files at once.

        Args:
            files: List of dicts with 'path', 'content', 'description'.
            created_by: Agent or process that created these files.

        Returns:
            List of FileMetadata for registered files.
        """
        results = []
        for file_info in files:
            path = file_info.get("path", "")
            content = file_info.get("content", "")
            description = file_info.get("description", "")

            if path and content:
                metadata = self.register_file(
                    path=path,
                    content=content,
                    created_by=created_by,
                    description=description,
                )
                results.append(metadata)

        return results

    def get_file(self, path: str) -> FileMetadata | None:
        """Get metadata for a file."""
        return self.file_registry.get(path)

    def file_exists(self, path: str) -> bool:
        """Check if a file is registered."""
        return self.file_registry.exists(path)

    def get_file_content(self, path: str) -> str | None:
        """Get cached content for a file."""
        return self._file_contents.get(path)

    # ========== Dependency Management ==========

    def declare_dependency(
        self,
        package: str,
        version: str = "",
    ) -> None:
        """Declare a package dependency.

        Args:
            package: Package name.
            version: Version specification (e.g., ">=1.0.0").
        """
        self._declared_dependencies[package] = version
        self._save()

    def declare_dependencies_from_file(
        self,
        file_path: str,
        content: str,
    ) -> None:
        """Extract and declare dependencies from a dependency file.

        Supports common formats like package.json, requirements.txt.

        Args:
            file_path: Path to the dependency file.
            content: Content of the file.
        """
        if file_path.endswith("package.json"):
            self._parse_package_json(content)
        elif file_path.endswith("requirements.txt"):
            self._parse_requirements_txt(content)
        elif file_path.endswith("pyproject.toml"):
            self._parse_pyproject_toml(content)

    def _parse_package_json(self, content: str) -> None:
        """Parse package.json and extract dependencies."""
        try:
            data = json.loads(content)
            for dep_type in ["dependencies", "devDependencies"]:
                for pkg, version in data.get(dep_type, {}).items():
                    self._declared_dependencies[pkg] = version
        except json.JSONDecodeError:
            pass

    def _parse_requirements_txt(self, content: str) -> None:
        """Parse requirements.txt and extract dependencies."""
        import re
        for line in content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                # Handle various formats: pkg, pkg==1.0, pkg>=1.0
                match = re.match(r"([a-zA-Z0-9_-]+)([<>=!~]+.+)?", line)
                if match:
                    pkg = match.group(1)
                    version = match.group(2) or ""
                    self._declared_dependencies[pkg] = version

    def _parse_pyproject_toml(self, content: str) -> None:
        """Parse pyproject.toml and extract dependencies."""
        # Simple parsing without toml library
        import re
        # Match dependencies = [...] sections
        deps_match = re.search(
            r'dependencies\s*=\s*\[(.*?)\]',
            content,
            re.DOTALL
        )
        if deps_match:
            deps_str = deps_match.group(1)
            for match in re.finditer(r'"([^"]+)"', deps_str):
                dep = match.group(1)
                # Parse "pkg>=1.0" format
                pkg_match = re.match(r"([a-zA-Z0-9_-]+)([<>=!~]+.+)?", dep)
                if pkg_match:
                    pkg = pkg_match.group(1)
                    version = pkg_match.group(2) or ""
                    self._declared_dependencies[pkg] = version

    # ========== Contract Management ==========

    def register_contract(
        self,
        contract_dict: dict[str, Any],
        contract_id: str = "main",
    ) -> ArchitectureContract:
        """Register an architecture contract.

        Args:
            contract_dict: Contract data (e.g., from ArchitectAgent).
            contract_id: Unique identifier for the contract.

        Returns:
            The registered ArchitectureContract.
        """
        contract = ArchitectureContract.from_dict(contract_dict)
        contract.contract_id = contract_id
        self.contract_registry.register(contract)
        return contract

    def get_contract(self, contract_id: str = "main") -> ArchitectureContract | None:
        """Get a registered contract."""
        return self.contract_registry.get(contract_id)

    # ========== Validation ==========

    def validate(
        self,
        blueprint: dict[str, Any] | None = None,
        contract_id: str = "main",
    ) -> ValidationResult:
        """Run all validations.

        Args:
            blueprint: Optional blueprint to validate against contract.
            contract_id: ID of the contract to validate against.

        Returns:
            Aggregated ValidationResult.
        """
        result = ValidationResult(is_valid=True)

        # Create validation context
        context = ValidationContext(
            file_registry=self.file_registry,
            declared_dependencies=self._declared_dependencies,
            architecture_contract=None,  # Will use contract_registry
            blueprint=blueprint or {},
        )

        # Run dependency validation
        dep_result = self.validation_engine.validate(context)
        result.merge(dep_result)

        # Run contract validation if contract exists
        contract = self.contract_registry.get(contract_id)
        if contract:
            # Internal consistency
            internal = self.contract_validator.validate_contract_internal(contract)
            result.merge(internal)

            # Implementation check
            impl = self.contract_validator.validate_implementation(
                contract,
                self.file_registry,
                self._file_contents,
            )
            result.merge(impl)

            # Blueprint against contract
            if blueprint:
                bp_result = self.contract_validator.validate_blueprint_against_contract(
                    blueprint,
                    contract,
                )
                result.merge(bp_result)

        return result

    def validate_file(self, path: str) -> ValidationResult:
        """Validate a single file.

        Args:
            path: Path to the file to validate.

        Returns:
            ValidationResult for the file.
        """
        result = ValidationResult(is_valid=True)
        metadata = self.file_registry.get(path)

        if not metadata:
            result.add_issue(ValidationIssue(
                severity=IssueSeverity.ERROR,
                category=IssueCategory.MISSING_FILE,
                message=f"File '{path}' is not registered",
                source_file=path,
            ))
            return result

        # Check imports
        for imp in metadata.imports:
            resolved = self.file_registry._resolve_import(path, imp)
            if resolved and not self.file_registry.exists(resolved):
                result.add_issue(ValidationIssue(
                    severity=IssueSeverity.ERROR,
                    category=IssueCategory.MISSING_FILE,
                    message=f"Import '{imp}' does not resolve to an existing file",
                    source_file=path,
                    target=imp,
                ))

        return result

    # ========== Feedback Generation ==========

    def generate_round_feedback(
        self,
        requirement_id: str,
        round_index: int,
        blueprint: dict[str, Any] | None = None,
    ) -> RoundFeedback:
        """Generate structured feedback for a generation round.

        Args:
            requirement_id: ID of the requirement.
            round_index: Current round index.
            blueprint: Optional blueprint to validate.

        Returns:
            RoundFeedback with all validation results.
        """
        feedback = RoundFeedback(
            requirement_id=requirement_id,
            round_index=round_index,
            files_registered=len(self.file_registry.get_all()),
        )

        # Run validation
        result = self.validate(blueprint=blueprint)
        feedback.add_validation_result(result)

        # Check contract compliance
        contract = self.contract_registry.get("main")
        if contract:
            unimplemented = contract.get_unimplemented_items()
            feedback.unimplemented_items = [
                f"{item.item_type.value}: {item.identifier}"
                for item in unimplemented
            ]

            total = len(contract.get_all_items())
            implemented = total - len(unimplemented)
            feedback.contract_compliance = implemented / total if total > 0 else 1.0

        # Store feedback history
        self._round_feedbacks.append(feedback)

        return feedback

    def get_feedback_history(self) -> list[RoundFeedback]:
        """Get all round feedbacks."""
        return list(self._round_feedbacks)

    def get_latest_feedback(self) -> RoundFeedback | None:
        """Get the most recent feedback."""
        return self._round_feedbacks[-1] if self._round_feedbacks else None

    # ========== Context Generation ==========

    def get_context_for_prompt(self) -> str:
        """Generate context for agent prompts.

        This includes file registry summary, validation status,
        and relevant project decisions.
        """
        lines = ["## Project Context", ""]

        # File statistics
        stats = self.file_registry.get_statistics()
        if stats["total_files"] > 0:
            lines.append(f"### Files ({stats['total_files']} total)")
            for lang, count in stats.get("by_language", {}).items():
                lines.append(f"- {lang}: {count} files")
            lines.append("")

        # Recent validation status
        latest = self.get_latest_feedback()
        if latest:
            if latest.is_successful():
                lines.append("### Validation: Passed")
            else:
                lines.append(f"### Validation: {len(latest.critical_issues)} errors")
                for issue in latest.critical_issues[:3]:
                    lines.append(f"- {issue}")
            lines.append("")

        # Contract compliance
        contract = self.contract_registry.get("main")
        if contract:
            unimplemented = contract.get_unimplemented_items()
            if unimplemented:
                lines.append(f"### Missing Implementations ({len(unimplemented)})")
                for item in unimplemented[:5]:
                    lines.append(f"- {item.item_type.value}: {item.identifier}")
                lines.append("")

        # Include ProjectMemory context if available
        if self._project_memory:
            memory_context = self._project_memory.get_context_for_prompt(
                include_instructions=False
            )
            if memory_context.strip():
                lines.append(memory_context)

        return "\n".join(lines)

    # ========== Listener Management ==========

    def add_file_listener(
        self,
        listener: Callable[[str, FileMetadata], None],
    ) -> None:
        """Add a listener for file registration events."""
        self._on_file_registered.append(listener)

    def remove_file_listener(
        self,
        listener: Callable[[str, FileMetadata], None],
    ) -> None:
        """Remove a file registration listener."""
        if listener in self._on_file_registered:
            self._on_file_registered.remove(listener)


# ========== Factory Function ==========

def create_project_context(
    project_id: str,
    workspace_dir: str | Path | None = None,
    project_memory: ProjectMemory | None = None,
) -> ProjectContext:
    """Create a ProjectContext with default configuration.

    This is the recommended way to create a ProjectContext.

    Args:
        project_id: Unique project identifier.
        workspace_dir: Optional workspace directory.
        project_memory: Optional existing ProjectMemory.

    Returns:
        Configured ProjectContext.
    """
    return ProjectContext(
        project_id=project_id,
        workspace_dir=workspace_dir,
        project_memory=project_memory,
    )
