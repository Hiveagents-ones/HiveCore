# -*- coding: utf-8 -*-
"""Language-agnostic dependency validation system.

This module provides a pluggable system for validating dependencies
between files, packages, and contracts in a language-agnostic way.

Design Principles:
1. Language-agnostic core with pluggable validators
2. Extensible validation rules
3. Clear separation between validation logic and reporting
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from .file_tracking import FileMetadata, FileRegistry


class IssueSeverity(str, Enum):
    """Severity levels for validation issues."""

    ERROR = "error"       # Must be fixed before proceeding
    WARNING = "warning"   # Should be fixed, but can continue
    INFO = "info"         # Informational only


class IssueCategory(str, Enum):
    """Categories of validation issues."""

    # File-level issues
    MISSING_FILE = "missing_file"           # Referenced file doesn't exist
    CIRCULAR_DEPENDENCY = "circular_dep"    # Circular import detected
    UNUSED_FILE = "unused_file"             # File exists but not imported

    # Package-level issues
    MISSING_PACKAGE = "missing_package"     # Package not in dependencies
    VERSION_CONFLICT = "version_conflict"   # Incompatible versions
    UNDECLARED_PACKAGE = "undeclared_pkg"   # Used but not declared

    # Contract-level issues
    CONTRACT_VIOLATION = "contract_violation"  # Doesn't follow contract
    MISSING_ENDPOINT = "missing_endpoint"      # API endpoint not implemented
    SCHEMA_MISMATCH = "schema_mismatch"        # Data model mismatch

    # Generic issues
    SYNTAX_ERROR = "syntax_error"           # File has syntax errors
    INVALID_REFERENCE = "invalid_ref"       # Invalid reference


@dataclass
class ValidationIssue:
    """Represents a single validation issue.

    This is a language-agnostic representation of any validation problem.
    """

    severity: IssueSeverity
    category: IssueCategory
    message: str
    source_file: str | None = None   # File where issue was found
    target: str | None = None        # Target of the issue (e.g., import path)
    line_number: int | None = None   # Line number if applicable
    suggestion: str | None = None    # Suggested fix
    context: dict[str, Any] = field(default_factory=dict)  # Additional context

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "source_file": self.source_file,
            "target": self.target,
            "line_number": self.line_number,
            "suggestion": self.suggestion,
            "context": self.context,
        }

    def format_message(self) -> str:
        """Format issue as human-readable message."""
        parts = [f"[{self.severity.value.upper()}]"]

        if self.source_file:
            if self.line_number:
                parts.append(f"{self.source_file}:{self.line_number}")
            else:
                parts.append(self.source_file)

        parts.append(self.message)

        if self.suggestion:
            parts.append(f"(Suggestion: {self.suggestion})")

        return " ".join(parts)


@dataclass
class ValidationResult:
    """Result of a validation run."""

    is_valid: bool                    # True if no errors
    issues: list[ValidationIssue] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)  # Issue counts

    @property
    def errors(self) -> list[ValidationIssue]:
        """Get all error-level issues."""
        return [i for i in self.issues if i.severity == IssueSeverity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Get all warning-level issues."""
        return [i for i in self.issues if i.severity == IssueSeverity.WARNING]

    def add_issue(self, issue: ValidationIssue) -> None:
        """Add an issue to the result."""
        self.issues.append(issue)
        self.stats[issue.category.value] = self.stats.get(issue.category.value, 0) + 1
        if issue.severity == IssueSeverity.ERROR:
            self.is_valid = False

    def merge(self, other: "ValidationResult") -> None:
        """Merge another result into this one."""
        for issue in other.issues:
            self.add_issue(issue)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "is_valid": self.is_valid,
            "issues": [i.to_dict() for i in self.issues],
            "stats": self.stats,
        }

    def format_report(self) -> str:
        """Format as human-readable report."""
        lines = []

        if self.is_valid:
            lines.append("Validation passed with no errors.")
        else:
            lines.append(f"Validation failed with {len(self.errors)} error(s).")

        if self.warnings:
            lines.append(f"Found {len(self.warnings)} warning(s).")

        lines.append("")

        # Group by severity
        for severity in [IssueSeverity.ERROR, IssueSeverity.WARNING, IssueSeverity.INFO]:
            issues = [i for i in self.issues if i.severity == severity]
            if issues:
                lines.append(f"## {severity.value.upper()}S ({len(issues)})")
                for issue in issues:
                    lines.append(f"  - {issue.format_message()}")
                lines.append("")

        return "\n".join(lines)


class Validator(Protocol):
    """Protocol for validators.

    Implement this protocol to add new validation rules.
    """

    def validate(self, context: "ValidationContext") -> ValidationResult:
        """Run validation and return results."""
        ...


class ValidationContext:
    """Context for validation, containing all necessary data.

    This provides validators access to project state without
    coupling them to specific implementations.
    """

    def __init__(
        self,
        file_registry: FileRegistry,
        declared_dependencies: dict[str, str] | None = None,
        architecture_contract: dict[str, Any] | None = None,
        blueprint: dict[str, Any] | None = None,
    ) -> None:
        self.file_registry = file_registry
        self.declared_dependencies = declared_dependencies or {}
        self.architecture_contract = architecture_contract or {}
        self.blueprint = blueprint or {}

    def get_all_files(self) -> dict[str, FileMetadata]:
        """Get all registered files."""
        return self.file_registry.get_all()

    def file_exists(self, path: str) -> bool:
        """Check if a file exists in registry."""
        return self.file_registry.exists(path)

    def get_file(self, path: str) -> FileMetadata | None:
        """Get metadata for a file."""
        return self.file_registry.get(path)


class BaseValidator(ABC):
    """Base class for validators with common utilities."""

    @abstractmethod
    def get_name(self) -> str:
        """Return the validator name."""
        ...

    @abstractmethod
    def validate(self, context: ValidationContext) -> ValidationResult:
        """Run validation and return results."""
        ...


class ImportPathValidator(BaseValidator):
    """Validates that all import paths resolve to existing files.

    This is a language-agnostic validator that checks if imports
    reference files that exist in the registry.
    """

    def get_name(self) -> str:
        return "import_path_validator"

    def validate(self, context: ValidationContext) -> ValidationResult:
        result = ValidationResult(is_valid=True)

        for path, metadata in context.get_all_files().items():
            for import_path in metadata.imports:
                # Skip external packages (non-relative imports)
                if not self._is_local_import(import_path):
                    continue

                # Try to resolve the import
                resolved = context.file_registry._resolve_import(path, import_path)

                if resolved and not context.file_exists(resolved):
                    # Try to find similar files
                    suggestion = self._find_similar(context, import_path)

                    result.add_issue(ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        category=IssueCategory.MISSING_FILE,
                        message=f"Import '{import_path}' does not resolve to an existing file",
                        source_file=path,
                        target=import_path,
                        suggestion=suggestion,
                    ))

        return result

    def _is_local_import(self, import_path: str) -> bool:
        """Check if import is a local file reference."""
        # Relative imports
        if import_path.startswith("."):
            return True
        # Project-relative imports (common patterns)
        if import_path.startswith("@/") or import_path.startswith("~/"):
            return True
        # Path-like imports
        if "/" in import_path and not import_path.startswith("@"):
            return True
        return False

    def _find_similar(self, context: ValidationContext, import_path: str) -> str | None:
        """Find similar file paths to suggest."""
        from difflib import get_close_matches
        from pathlib import Path

        target_name = Path(import_path).name
        all_files = list(context.get_all_files().keys())
        all_names = [Path(f).name for f in all_files]

        matches = get_close_matches(target_name, all_names, n=1, cutoff=0.6)
        if matches:
            for f in all_files:
                if Path(f).name == matches[0]:
                    return f"Did you mean '{f}'?"
        return None


class CircularDependencyValidator(BaseValidator):
    """Detects circular dependencies between files."""

    def get_name(self) -> str:
        return "circular_dependency_validator"

    def validate(self, context: ValidationContext) -> ValidationResult:
        result = ValidationResult(is_valid=True)

        # Build dependency graph
        graph = self._build_dependency_graph(context)

        # Detect cycles using DFS
        cycles = self._detect_cycles(graph)

        for cycle in cycles:
            cycle_str = " -> ".join(cycle + [cycle[0]])
            result.add_issue(ValidationIssue(
                severity=IssueSeverity.WARNING,
                category=IssueCategory.CIRCULAR_DEPENDENCY,
                message=f"Circular dependency detected: {cycle_str}",
                context={"cycle": cycle},
            ))

        return result

    def _build_dependency_graph(self, context: ValidationContext) -> dict[str, list[str]]:
        """Build a dependency graph from file metadata."""
        graph: dict[str, list[str]] = {}

        for path, metadata in context.get_all_files().items():
            deps = context.file_registry.get_dependencies(path)
            graph[path] = deps

        return graph

    def _detect_cycles(self, graph: dict[str, list[str]]) -> list[list[str]]:
        """Detect all cycles in the dependency graph."""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:])

            path.pop()
            rec_stack.remove(node)
            return False

        for node in graph:
            if node not in visited:
                dfs(node)

        return cycles


class DeclaredDependencyValidator(BaseValidator):
    """Validates that used packages are declared in project dependencies."""

    def get_name(self) -> str:
        return "declared_dependency_validator"

    def validate(self, context: ValidationContext) -> ValidationResult:
        result = ValidationResult(is_valid=True)

        # Collect all external imports
        external_imports = set()
        for metadata in context.get_all_files().values():
            for imp in metadata.imports:
                if not self._is_local_import(imp):
                    # Extract package name
                    pkg = self._extract_package_name(imp)
                    if pkg:
                        external_imports.add(pkg)

        # Check against declared dependencies
        declared = set(context.declared_dependencies.keys())

        for pkg in external_imports:
            if pkg not in declared and not self._is_builtin(pkg):
                result.add_issue(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.UNDECLARED_PACKAGE,
                    message=f"Package '{pkg}' is used but not declared in dependencies",
                    target=pkg,
                    suggestion=f"Add '{pkg}' to your dependencies",
                ))

        return result

    def _is_local_import(self, import_path: str) -> bool:
        """Check if import is a local file reference."""
        return import_path.startswith(".") or import_path.startswith("@/")

    def _extract_package_name(self, import_path: str) -> str | None:
        """Extract package name from import path."""
        if not import_path:
            return None

        # Handle scoped packages (@org/package)
        if import_path.startswith("@"):
            parts = import_path.split("/")
            if len(parts) >= 2:
                return f"{parts[0]}/{parts[1]}"
            return None

        # Regular packages
        parts = import_path.split("/")
        return parts[0] if parts else None

    def _is_builtin(self, pkg: str) -> bool:
        """Check if package is a language builtin.

        This is a simplified check. Language-specific validators
        can override with complete lists.
        """
        # Common builtins across languages
        builtins = {
            # Node.js
            "fs", "path", "os", "http", "https", "url", "util", "stream",
            "events", "crypto", "child_process", "cluster", "net", "dns",
            # Python (though these wouldn't typically appear as string imports)
            "sys", "os", "re", "json", "datetime", "collections", "itertools",
        }
        return pkg in builtins


class BlueprintDependencyValidator(BaseValidator):
    """Validates dependencies declared in blueprint files_plan."""

    def get_name(self) -> str:
        return "blueprint_dependency_validator"

    def validate(self, context: ValidationContext) -> ValidationResult:
        result = ValidationResult(is_valid=True)

        files_plan = context.blueprint.get("files_plan", [])
        if not files_plan:
            return result

        # Collect all planned file paths
        planned_paths = {f.get("path") for f in files_plan if f.get("path")}

        # Check each file's dependencies
        for file_plan in files_plan:
            path = file_plan.get("path", "")
            deps = file_plan.get("dependencies", [])

            for dep in deps:
                if self._is_local_import(dep):
                    # Check if dependency is in planned files
                    resolved = self._resolve_to_planned(dep, path, planned_paths)
                    if not resolved:
                        result.add_issue(ValidationIssue(
                            severity=IssueSeverity.WARNING,
                            category=IssueCategory.MISSING_FILE,
                            message=f"Dependency '{dep}' is not in the files plan",
                            source_file=path,
                            target=dep,
                            suggestion="Add the missing file to files_plan or fix the dependency path",
                        ))

        return result

    def _is_local_import(self, import_path: str) -> bool:
        """Check if import is a local file reference."""
        return import_path.startswith("./") or import_path.startswith("../")

    def _resolve_to_planned(self, dep: str, from_path: str, planned: set[str]) -> bool:
        """Check if dependency resolves to a planned file."""
        from pathlib import Path

        from_dir = Path(from_path).parent

        if dep.startswith("./"):
            resolved = from_dir / dep[2:]
        elif dep.startswith("../"):
            resolved = from_dir / dep
        else:
            return True  # Non-local dependency

        resolved_str = str(resolved).replace("\\", "/")

        # Check with common extensions
        for ext in ["", ".js", ".ts", ".vue", ".jsx", ".tsx", ".py"]:
            candidate = resolved_str + ext
            if candidate in planned:
                return True

        return False


class ValidationEngine:
    """Engine that runs multiple validators.

    This class orchestrates validation by running registered
    validators and aggregating their results.
    """

    def __init__(self) -> None:
        self._validators: list[BaseValidator] = []

    def register(self, validator: BaseValidator) -> None:
        """Register a validator."""
        self._validators.append(validator)

    def unregister(self, validator: BaseValidator) -> None:
        """Unregister a validator."""
        if validator in self._validators:
            self._validators.remove(validator)

    def validate(self, context: ValidationContext) -> ValidationResult:
        """Run all validators and return aggregated results."""
        result = ValidationResult(is_valid=True)

        for validator in self._validators:
            try:
                validator_result = validator.validate(context)
                result.merge(validator_result)
            except Exception as e:
                # Don't let one validator crash the whole validation
                result.add_issue(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.SYNTAX_ERROR,
                    message=f"Validator '{validator.get_name()}' failed: {e}",
                ))

        return result

    def get_validators(self) -> list[BaseValidator]:
        """Get list of registered validators."""
        return list(self._validators)


def create_default_validation_engine() -> ValidationEngine:
    """Create a validation engine with default validators."""
    engine = ValidationEngine()
    engine.register(ImportPathValidator())
    engine.register(CircularDependencyValidator())
    engine.register(DeclaredDependencyValidator())
    engine.register(BlueprintDependencyValidator())
    return engine
