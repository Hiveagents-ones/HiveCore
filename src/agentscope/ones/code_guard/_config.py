# -*- coding: utf-8 -*-
"""Configuration for CodeGuard system."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StrictnessLevel(str, Enum):
    """Strictness level for validation.

    Attributes:
        RELAXED: Only log issues, never block operations.
        NORMAL: Warn about issues but only block critical violations.
        STRICT: Block operations on any validation error.
    """

    RELAXED = "relaxed"
    NORMAL = "normal"
    STRICT = "strict"


@dataclass
class CodeGuardConfig:
    """Configuration for CodeGuard system.

    Attributes:
        enabled (`bool`):
            Master switch for the entire CodeGuard system.
        read_guard_enabled (`bool`):
            Enable ReadGuard to track file reads.
        block_unread_writes (`bool`):
            If True, block write operations to files that haven't been read.
            This is the core anti-hallucination mechanism.
        write_guard_enabled (`bool`):
            Enable WriteGuard for syntax checking.
        check_syntax (`bool`):
            Perform basic syntax validation (bracket matching, etc.).
        check_ranges_match (`bool`):
            Verify content matches when using range-based writes.
        import_guard_enabled (`bool`):
            Enable ImportGuard to validate imports.
        warn_unresolved_imports (`bool`):
            Warn when local imports cannot be resolved.
        hallucination_detector_enabled (`bool`):
            Enable HallucinationDetector to check function calls.
        warn_unknown_calls (`bool`):
            Warn when calling unknown functions.
        strictness (`StrictnessLevel`):
            Overall strictness level for validation.
        language_configs (`dict[str, Any]`):
            Language-specific configuration overrides.
        exclude_patterns (`list[str]`):
            File patterns to exclude from validation (glob format).
    """

    # Master switch
    enabled: bool = True

    # ReadGuard configuration
    read_guard_enabled: bool = True
    block_unread_writes: bool = True

    # WriteGuard configuration
    write_guard_enabled: bool = True
    check_syntax: bool = True
    check_ranges_match: bool = True

    # ImportGuard configuration
    import_guard_enabled: bool = True
    warn_unresolved_imports: bool = True

    # HallucinationDetector configuration
    hallucination_detector_enabled: bool = True
    warn_unknown_calls: bool = True

    # Overall strictness
    strictness: StrictnessLevel = StrictnessLevel.NORMAL

    # Language-specific overrides
    language_configs: dict[str, Any] = field(default_factory=dict)

    # Exclusion patterns (glob format)
    exclude_patterns: list[str] = field(
        default_factory=lambda: [
            # Documentation and text files
            "*.md",
            "*.txt",
            "*.rst",
            "*.rtf",
            "*.doc",
            "*.docx",
            # Configuration files
            "*.json",
            "*.yaml",
            "*.yml",
            "*.toml",
            "*.ini",
            "*.cfg",
            "*.conf",
            "*.config",
            "*.env",
            "*.env.*",
            # Data files
            "*.csv",
            "*.xml",
            "*.svg",
            # Lock files
            "*.lock",
            "*-lock.json",
            # Generated/vendor directories
            "**/node_modules/**",
            "**/__pycache__/**",
            "**/.git/**",
            "**/dist/**",
            "**/build/**",
            "**/vendor/**",
            "**/.venv/**",
            "**/venv/**",
            # Static assets
            "*.html",
            "*.css",
            "*.scss",
            "*.less",
            # Images
            "*.png",
            "*.jpg",
            "*.jpeg",
            "*.gif",
            "*.ico",
            "*.webp",
        ]
    )

    # Code file extensions that SHOULD be validated
    code_extensions: list[str] = field(
        default_factory=lambda: [
            ".py",
            ".pyi",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".mjs",
            ".cjs",
            ".vue",
            ".go",
            ".rs",
            ".java",
            ".kt",
            ".swift",
            ".rb",
            ".php",
        ]
    )

    def should_validate_file(self, file_path: str) -> bool:
        """Check if a file should be validated.

        Uses both whitelist (code_extensions) and blacklist (exclude_patterns)
        to determine if a file should be validated:
        1. If file matches exclude_patterns -> skip validation
        2. If file has a known code extension -> validate
        3. Otherwise -> skip validation (safe default for unknown files)

        Args:
            file_path (`str`):
                The file path to check.

        Returns:
            `bool`:
                True if the file should be validated, False if excluded.
        """
        import fnmatch
        from pathlib import Path

        # First check exclusion patterns (blacklist)
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(file_path, pattern):
                return False

        # Then check if it's a known code file (whitelist)
        ext = Path(file_path).suffix.lower()
        if ext in self.code_extensions:
            return True

        # Unknown file type - skip validation to be safe
        # This prevents false positives on files like novels, logs, etc.
        return False

    def get_language_config(self, language: str) -> dict[str, Any]:
        """Get language-specific configuration.

        Args:
            language (`str`):
                The language name (e.g., 'python', 'typescript').

        Returns:
            `dict[str, Any]`:
                Language-specific configuration or empty dict if not found.
        """
        return self.language_configs.get(language, {})
