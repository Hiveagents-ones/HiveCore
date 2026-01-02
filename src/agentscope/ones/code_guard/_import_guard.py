# -*- coding: utf-8 -*-
"""ImportGuard: Validate import statements.

This module validates that import statements in code reference
files or modules that actually exist.
"""
from __future__ import annotations

import re
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
    from ..file_tracking import FileRegistry


class ImportGuard:
    """Guard for validating import statements.

    Checks that local imports can be resolved to known files.
    """

    # Regex patterns for import extraction
    _PYTHON_IMPORT_PATTERNS = [
        re.compile(r"^import\s+(\w+(?:\.\w+)*)", re.MULTILINE),
        re.compile(r"^from\s+(\w+(?:\.\w+)*)\s+import", re.MULTILINE),
        re.compile(r"^from\s+(\.+\w*(?:\.\w+)*)\s+import", re.MULTILINE),
    ]

    _JS_IMPORT_PATTERNS = [
        re.compile(r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE),
        re.compile(r"import\s+['\"]([^'\"]+)['\"]", re.MULTILINE),
        re.compile(r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", re.MULTILINE),
        re.compile(r"export\s+.*?\s+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE),
    ]

    # Standard library modules to skip validation
    _PYTHON_STDLIB = frozenset(
        {
            "os",
            "sys",
            "re",
            "json",
            "typing",
            "collections",
            "functools",
            "itertools",
            "pathlib",
            "datetime",
            "time",
            "math",
            "random",
            "hashlib",
            "base64",
            "urllib",
            "http",
            "socket",
            "threading",
            "multiprocessing",
            "subprocess",
            "logging",
            "unittest",
            "pytest",
            "abc",
            "dataclasses",
            "enum",
            "copy",
            "io",
            "pickle",
            "csv",
            "xml",
            "html",
            "email",
            "asyncio",
            "concurrent",
            "contextlib",
            "tempfile",
            "shutil",
            "glob",
            "fnmatch",
            "struct",
            "codecs",
            "string",
            "textwrap",
            "difflib",
            "operator",
            "inspect",
            "types",
            "importlib",
            "warnings",
            "traceback",
            "argparse",
            "getopt",
            "configparser",
            "pprint",
            "builtins",
            "__future__",
        }
    )

    _NODE_BUILTINS = frozenset(
        {
            "fs",
            "path",
            "http",
            "https",
            "os",
            "crypto",
            "stream",
            "buffer",
            "events",
            "util",
            "url",
            "querystring",
            "child_process",
            "cluster",
            "net",
            "dns",
            "readline",
            "zlib",
            "assert",
            "process",
            "console",
            "node:fs",
            "node:path",
            "node:http",
            "node:https",
            "node:os",
            "node:crypto",
        }
    )

    def __init__(
        self,
        config: "CodeGuardConfig",
        file_registry: "FileRegistry | None" = None,
    ) -> None:
        """Initialize ImportGuard.

        Args:
            config (`CodeGuardConfig`):
                The CodeGuard configuration.
            file_registry (`FileRegistry | None`, optional):
                The file registry to check against.
        """
        self.config = config
        self.file_registry = file_registry

    def validate_imports(
        self,
        file_path: str,
        content: str,
    ) -> ValidationResult:
        """Validate imports in a file.

        Args:
            file_path (`str`):
                Path of the file.
            content (`str`):
                The file content.

        Returns:
            `ValidationResult`:
                Validation result with any import issues.
        """
        result = ValidationResult(is_valid=True)

        if not self.config.import_guard_enabled:
            return result

        if not self.config.should_validate_file(file_path):
            return result

        ext = Path(file_path).suffix.lower()
        imports = self._extract_imports(content, ext)

        for import_path, line_num in imports:
            # Skip standard library/builtins
            if self._is_stdlib_or_external(import_path, ext):
                continue

            # Check if it's a local import
            if not self._is_local_import(import_path, ext):
                continue

            # Try to resolve the import
            resolved = self._resolve_import(file_path, import_path, ext)

            if resolved and self.file_registry:
                if not self.file_registry.exists(resolved):
                    suggestion = self._find_similar_file(import_path)

                    # Use ERROR for local imports that cannot be resolved
                    # This triggers immediate retry in stepwise generation
                    result.add_issue(
                        ValidationIssue(
                            severity=IssueSeverity.ERROR,
                            category=IssueCategory.MISSING_FILE,
                            message=(
                                f"Import '{import_path}' cannot be resolved "
                                "- module does not exist in project"
                            ),
                            source_file=file_path,
                            line_number=line_num,
                            target=import_path,
                            suggestion=suggestion,
                        )
                    )

        return result

    def _extract_imports(
        self,
        content: str,
        ext: str,
    ) -> list[tuple[str, int]]:
        """Extract import statements from content.

        Args:
            content (`str`):
                The file content.
            ext (`str`):
                The file extension.

        Returns:
            `list[tuple[str, int]]`:
                List of (import_path, line_number) tuples.
        """
        imports: list[tuple[str, int]] = []
        lines = content.split("\n")

        if ext in (".py", ".pyw"):
            patterns = self._PYTHON_IMPORT_PATTERNS
        elif ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
            patterns = self._JS_IMPORT_PATTERNS
        else:
            return imports

        for pattern in patterns:
            for match in pattern.finditer(content):
                import_path = match.group(1)
                line_num = content[: match.start()].count("\n") + 1
                imports.append((import_path, line_num))

        return imports

    def _is_stdlib_or_external(self, import_path: str, ext: str) -> bool:
        """Check if import is from standard library or external package.

        Args:
            import_path (`str`):
                The import path.
            ext (`str`):
                The file extension.

        Returns:
            `bool`:
                True if the import is from stdlib or external.
        """
        # Get the base module name
        base_module = import_path.split(".")[0].lstrip(".")

        if ext in (".py", ".pyw"):
            return base_module in self._PYTHON_STDLIB

        if ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
            # Node builtins
            if import_path in self._NODE_BUILTINS:
                return True
            # npm packages (don't start with . or /)
            if not import_path.startswith(".") and not import_path.startswith("/"):
                if not import_path.startswith("@/") and not import_path.startswith("~/"):
                    return True

        return False

    def _is_local_import(self, import_path: str, ext: str) -> bool:
        """Check if import is a local/relative import.

        Args:
            import_path (`str`):
                The import path.
            ext (`str`):
                The file extension.

        Returns:
            `bool`:
                True if the import is local.
        """
        if ext in (".py", ".pyw"):
            # Relative imports start with dots
            return import_path.startswith(".")

        if ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
            return (
                import_path.startswith(".")
                or import_path.startswith("@/")
                or import_path.startswith("~/")
                or import_path.startswith("/")
            )

        return False

    def _resolve_import(
        self,
        file_path: str,
        import_path: str,
        ext: str,
    ) -> str | None:
        """Resolve import path to a file path.

        Args:
            file_path (`str`):
                Path of the importing file.
            import_path (`str`):
                The import path.
            ext (`str`):
                The file extension.

        Returns:
            `str | None`:
                The resolved file path, or None if cannot resolve.
        """
        file_dir = Path(file_path).parent

        if ext in (".py", ".pyw"):
            # Handle relative imports
            if import_path.startswith("."):
                # Count dots
                dots = 0
                for char in import_path:
                    if char == ".":
                        dots += 1
                    else:
                        break

                relative_path = import_path[dots:]

                # Go up directories
                base_dir = file_dir
                for _ in range(dots - 1):
                    base_dir = base_dir.parent

                # Convert module path to file path
                if relative_path:
                    module_parts = relative_path.split(".")
                    resolved = base_dir / "/".join(module_parts)
                    return str(resolved) + ".py"

        elif ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
            if import_path.startswith("./") or import_path.startswith("../"):
                resolved = (file_dir / import_path).resolve()
                # Try common extensions
                for try_ext in (".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.js"):
                    candidate = str(resolved) + try_ext
                    return candidate

        return None

    def _find_similar_file(self, import_path: str) -> str | None:
        """Find a similar file name for suggestions.

        Args:
            import_path (`str`):
                The import path that failed to resolve.

        Returns:
            `str | None`:
                A suggestion string, or None.
        """
        if not self.file_registry:
            return None

        target_name = Path(import_path).stem or import_path.split(".")[-1]
        all_files = list(self.file_registry.get_all().keys())
        all_names = [Path(f).stem for f in all_files]

        matches = get_close_matches(target_name, all_names, n=1, cutoff=0.6)
        if matches:
            for f in all_files:
                if Path(f).stem == matches[0]:
                    return f"Did you mean to import '{f}'?"

        return None
