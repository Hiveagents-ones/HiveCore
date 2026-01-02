# -*- coding: utf-8 -*-
"""HallucinationDetector: Detect calls to unknown functions.

This module checks if function calls in generated code reference
functions that exist in the InterfaceRegistry or are known builtins.
"""
from __future__ import annotations

from difflib import get_close_matches
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
    from ._interface_registry import InterfaceRegistry


class HallucinationDetector:
    """Detector for hallucinated function calls.

    Checks if code references functions or classes that haven't been
    defined in read files or known builtins.
    """

    # Common method names that shouldn't trigger warnings
    _COMMON_METHODS = frozenset(
        {
            # Object methods
            "get",
            "set",
            "update",
            "delete",
            "remove",
            "add",
            "append",
            "extend",
            "insert",
            "pop",
            "clear",
            "copy",
            "keys",
            "values",
            "items",
            "find",
            "index",
            "count",
            "sort",
            "reverse",
            "split",
            "join",
            "strip",
            "replace",
            "format",
            "encode",
            "decode",
            "lower",
            "upper",
            "title",
            "capitalize",
            "startswith",
            "endswith",
            "isdigit",
            "isalpha",
            "isalnum",
            # Common framework methods
            "render",
            "save",
            "load",
            "create",
            "read",
            "write",
            "close",
            "open",
            "execute",
            "run",
            "start",
            "stop",
            "init",
            "setup",
            "teardown",
            "connect",
            "disconnect",
            "send",
            "receive",
            "publish",
            "subscribe",
            "log",
            "debug",
            "info",
            "warning",
            "error",
            "critical",
            # Test methods
            "assertEqual",
            "assertTrue",
            "assertFalse",
            "assertRaises",
            "assertIn",
            "assertNotIn",
            "assertIsNone",
            "assertIsNotNone",
            # React hooks/methods
            "useState",
            "useEffect",
            "useCallback",
            "useMemo",
            "useRef",
            "useContext",
            "useReducer",
            "map",
            "filter",
            "reduce",
            "forEach",
            "some",
            "every",
            "includes",
            "slice",
            "concat",
            "push",
            "shift",
            "unshift",
            "splice",
        }
    )

    def __init__(
        self,
        config: "CodeGuardConfig",
        interface_registry: "InterfaceRegistry",
    ) -> None:
        """Initialize HallucinationDetector.

        Args:
            config (`CodeGuardConfig`):
                The CodeGuard configuration.
            interface_registry (`InterfaceRegistry`):
                The interface registry to check against.
        """
        self.config = config
        self.interface_registry = interface_registry

    def check_function_calls(
        self,
        file_path: str,
        content: str,
    ) -> ValidationResult:
        """Check function calls for potential hallucinations.

        Args:
            file_path (`str`):
                Path of the file.
            content (`str`):
                The file content.

        Returns:
            `ValidationResult`:
                Validation result with any hallucination warnings.
        """
        result = ValidationResult(is_valid=True)

        if not self.config.hallucination_detector_enabled:
            return result

        if not self.config.should_validate_file(file_path):
            return result

        if not self.config.warn_unknown_calls:
            return result

        extractor = self.interface_registry.get_extractor(file_path)
        if not extractor:
            return result

        # Extract function calls
        calls = extractor.extract_function_calls(content)

        # Check each call
        unknown_calls: dict[str, list[int]] = {}  # name -> [line_numbers]

        for func_name, line_num in calls:
            if self._should_skip(func_name):
                continue

            if not self.interface_registry.exists(func_name):
                if func_name not in unknown_calls:
                    unknown_calls[func_name] = []
                unknown_calls[func_name].append(line_num)

        # Report unknown calls (deduplicated)
        for func_name, line_nums in unknown_calls.items():
            first_line = line_nums[0]
            count = len(line_nums)

            suggestion = self._find_similar_function(func_name)

            message = f"Call to unknown function '{func_name}'"
            if count > 1:
                message += f" ({count} occurrences)"
            message += " - may be external library or not yet defined"

            result.add_issue(
                ValidationIssue(
                    severity=IssueSeverity.INFO,
                    category=IssueCategory.INVALID_REFERENCE,
                    message=message,
                    source_file=file_path,
                    line_number=first_line,
                    target=func_name,
                    suggestion=suggestion,
                )
            )

        return result

    def _should_skip(self, name: str) -> bool:
        """Check if a name should be skipped from checking.

        Args:
            name (`str`):
                The function/method name.

        Returns:
            `bool`:
                True if should skip.
        """
        # Skip common methods
        if name in self._COMMON_METHODS:
            return True

        # Skip single-letter names (usually loop variables)
        if len(name) == 1:
            return True

        # Skip names that look like they're called on objects (method calls)
        # These are typically extracted without the object prefix
        if name.islower() and len(name) < 4:
            return True

        return False

    def _find_similar_function(self, name: str) -> str | None:
        """Find a similar function name for suggestions.

        Args:
            name (`str`):
                The unknown function name.

        Returns:
            `str | None`:
                A suggestion string, or None.
        """
        all_names = list(self.interface_registry._by_name.keys())
        matches = get_close_matches(name, all_names, n=1, cutoff=0.7)

        if matches:
            entries = self.interface_registry.lookup(matches[0])
            if entries:
                entry = entries[0]
                return (
                    f"Did you mean '{matches[0]}' "
                    f"(defined at {entry.file_path}:{entry.line_number})?"
                )

        return None

    def check_class_references(
        self,
        file_path: str,
        content: str,
    ) -> ValidationResult:
        """Check class references for potential hallucinations.

        Args:
            file_path (`str`):
                Path of the file.
            content (`str`):
                The file content.

        Returns:
            `ValidationResult`:
                Validation result with any issues.
        """
        result = ValidationResult(is_valid=True)

        if not self.config.hallucination_detector_enabled:
            return result

        # This is a simplified check for class instantiation patterns
        # A full implementation would need AST parsing
        ext = Path(file_path).suffix.lower()

        if ext in (".py", ".pyw"):
            # Look for class instantiation: ClassName(...)
            import re

            pattern = re.compile(r"\b([A-Z][a-zA-Z0-9]*)\s*\(")

            for match in pattern.finditer(content):
                class_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                # Skip common class names
                if class_name in ("Exception", "Error", "True", "False", "None"):
                    continue

                if not self.interface_registry.exists(class_name):
                    result.add_issue(
                        ValidationIssue(
                            severity=IssueSeverity.INFO,
                            category=IssueCategory.INVALID_REFERENCE,
                            message=(
                                f"Instantiation of unknown class '{class_name}' - "
                                "may be external or not yet defined"
                            ),
                            source_file=file_path,
                            line_number=line_num,
                            target=class_name,
                        )
                    )

        return result
