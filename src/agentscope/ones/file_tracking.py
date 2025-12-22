# -*- coding: utf-8 -*-
"""Language-agnostic file tracking and metadata extraction.

This module provides a pluggable system for tracking generated files
and extracting their metadata (imports, exports, dependencies) in a
language-agnostic way.

Design Principles:
1. Language-agnostic core with pluggable analyzers
2. Modular and extensible architecture
3. No hardcoded language-specific logic in core classes
"""
from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Protocol


class FileType(str, Enum):
    """General file type categories."""

    SOURCE_CODE = "source_code"
    CONFIG = "config"
    DOCUMENTATION = "documentation"
    ASSET = "asset"
    DATA = "data"
    UNKNOWN = "unknown"


@dataclass
class FileMetadata:
    """Metadata extracted from a file.

    This is a language-agnostic representation of file metadata.
    Language-specific analyzers populate these fields.
    """

    # Basic info
    path: str
    file_type: FileType
    language: str  # e.g., "python", "javascript", "unknown"

    # Content tracking
    content_hash: str  # SHA256 hash for change detection
    size_bytes: int
    line_count: int

    # Dependency info (language-agnostic representation)
    imports: list[str] = field(default_factory=list)  # What this file imports
    exports: list[str] = field(default_factory=list)  # What this file exports

    # Provenance
    created_by: str = ""  # Agent or process that created this
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    description: str = ""

    # Optional structured data
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "path": self.path,
            "file_type": self.file_type.value,
            "language": self.language,
            "content_hash": self.content_hash,
            "size_bytes": self.size_bytes,
            "line_count": self.line_count,
            "imports": self.imports,
            "exports": self.exports,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "description": self.description,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileMetadata":
        """Deserialize from dictionary."""
        return cls(
            path=data["path"],
            file_type=FileType(data.get("file_type", "unknown")),
            language=data.get("language", "unknown"),
            content_hash=data.get("content_hash", ""),
            size_bytes=data.get("size_bytes", 0),
            line_count=data.get("line_count", 0),
            imports=data.get("imports", []),
            exports=data.get("exports", []),
            created_by=data.get("created_by", ""),
            created_at=datetime.fromisoformat(data["created_at"])
                if "created_at" in data else datetime.now(timezone.utc),
            description=data.get("description", ""),
            extra=data.get("extra", {}),
        )


class FileAnalyzer(Protocol):
    """Protocol for language-specific file analyzers.

    Implement this protocol to add support for new languages.
    """

    def can_analyze(self, path: str, content: str) -> bool:
        """Check if this analyzer can handle the given file."""
        ...

    def analyze(self, path: str, content: str) -> FileMetadata:
        """Analyze file and extract metadata."""
        ...


class BaseFileAnalyzer(ABC):
    """Base class for file analyzers with common utilities."""

    @abstractmethod
    def get_supported_extensions(self) -> list[str]:
        """Return list of file extensions this analyzer supports."""
        ...

    @abstractmethod
    def get_language_name(self) -> str:
        """Return the language name (e.g., 'python', 'javascript')."""
        ...

    def can_analyze(self, path: str, content: str) -> bool:
        """Check if this analyzer can handle the given file."""
        ext = Path(path).suffix.lower()
        return ext in self.get_supported_extensions()

    def analyze(self, path: str, content: str) -> FileMetadata:
        """Analyze file and extract metadata."""
        return FileMetadata(
            path=path,
            file_type=self._detect_file_type(path),
            language=self.get_language_name(),
            content_hash=self._compute_hash(content),
            size_bytes=len(content.encode("utf-8")),
            line_count=content.count("\n") + 1 if content else 0,
            imports=self._extract_imports(content),
            exports=self._extract_exports(content),
        )

    @abstractmethod
    def _extract_imports(self, content: str) -> list[str]:
        """Extract import statements from content."""
        ...

    @abstractmethod
    def _extract_exports(self, content: str) -> list[str]:
        """Extract exported symbols from content."""
        ...

    def _compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def _detect_file_type(self, path: str) -> FileType:
        """Detect file type from path."""
        ext = Path(path).suffix.lower()

        source_exts = {
            ".py", ".js", ".ts", ".jsx", ".tsx", ".vue", ".java",
            ".go", ".rs", ".rb", ".php", ".cs", ".cpp", ".c", ".h",
            ".swift", ".kt", ".scala", ".clj", ".ex", ".exs",
        }
        config_exts = {
            ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
            ".xml", ".env", ".properties",
        }
        doc_exts = {".md", ".rst", ".txt", ".adoc"}
        asset_exts = {".css", ".scss", ".sass", ".less", ".svg", ".png", ".jpg"}

        if ext in source_exts:
            return FileType.SOURCE_CODE
        elif ext in config_exts:
            return FileType.CONFIG
        elif ext in doc_exts:
            return FileType.DOCUMENTATION
        elif ext in asset_exts:
            return FileType.ASSET
        return FileType.UNKNOWN


class GenericFileAnalyzer(BaseFileAnalyzer):
    """Generic analyzer for unknown file types.

    This serves as a fallback when no specific analyzer is available.
    It performs basic analysis without language-specific parsing.
    """

    def get_supported_extensions(self) -> list[str]:
        return []  # Matches nothing directly, used as fallback

    def get_language_name(self) -> str:
        return "unknown"

    def can_analyze(self, path: str, content: str) -> bool:
        return True  # Always can analyze as fallback

    def _extract_imports(self, content: str) -> list[str]:
        """Generic import detection using common patterns."""
        imports = []

        # Common import patterns across languages
        patterns = [
            r'import\s+["\']([^"\']+)["\']',  # import "..."
            r'from\s+["\']([^"\']+)["\']',    # from "..."
            r'require\s*\(["\']([^"\']+)["\']\)',  # require("...")
            r'@import\s+["\']([^"\']+)["\']',  # @import "..." (CSS/SCSS)
            r'#include\s*[<"]([^>"]+)[>"]',   # #include <...> or "..."
        ]

        for pattern in patterns:
            imports.extend(re.findall(pattern, content))

        return list(set(imports))

    def _extract_exports(self, content: str) -> list[str]:
        """Generic export detection using common patterns."""
        exports = []

        # Common export patterns
        patterns = [
            r'export\s+(?:default\s+)?(?:class|function|const|let|var|interface|type|enum)\s+(\w+)',
            r'module\.exports\s*=\s*(\w+)',
            r'exports\.(\w+)\s*=',
        ]

        for pattern in patterns:
            exports.extend(re.findall(pattern, content))

        return list(set(exports))


class FileAnalyzerRegistry:
    """Registry for file analyzers.

    This class manages a collection of file analyzers and provides
    a unified interface for analyzing files.
    """

    def __init__(self) -> None:
        self._analyzers: list[BaseFileAnalyzer] = []
        self._fallback = GenericFileAnalyzer()

    def register(self, analyzer: BaseFileAnalyzer) -> None:
        """Register a file analyzer."""
        self._analyzers.append(analyzer)

    def unregister(self, analyzer: BaseFileAnalyzer) -> None:
        """Unregister a file analyzer."""
        if analyzer in self._analyzers:
            self._analyzers.remove(analyzer)

    def get_analyzer(self, path: str, content: str) -> BaseFileAnalyzer:
        """Get the appropriate analyzer for a file."""
        for analyzer in self._analyzers:
            if analyzer.can_analyze(path, content):
                return analyzer
        return self._fallback

    def analyze(self, path: str, content: str) -> FileMetadata:
        """Analyze a file using the appropriate analyzer."""
        analyzer = self.get_analyzer(path, content)
        return analyzer.analyze(path, content)


class FileRegistry:
    """Central registry for tracking all project files.

    This class maintains a registry of all files in the project,
    their metadata, and provides query capabilities.
    """

    def __init__(self, analyzer_registry: FileAnalyzerRegistry | None = None) -> None:
        self._files: dict[str, FileMetadata] = {}
        self._analyzer_registry = analyzer_registry or FileAnalyzerRegistry()
        self._change_listeners: list[Callable[[str, FileMetadata], None]] = []

    def register(
        self,
        path: str,
        content: str,
        created_by: str = "",
        description: str = "",
        **extra: Any,
    ) -> FileMetadata:
        """Register a file with automatic metadata extraction.

        Args:
            path: Relative file path.
            content: File content.
            created_by: Agent or process that created this file.
            description: Human-readable description.
            **extra: Additional metadata to store.

        Returns:
            FileMetadata for the registered file.
        """
        metadata = self._analyzer_registry.analyze(path, content)
        metadata.created_by = created_by
        metadata.description = description
        metadata.extra.update(extra)

        old_metadata = self._files.get(path)
        self._files[path] = metadata

        # Notify listeners
        for listener in self._change_listeners:
            listener(path, metadata)

        return metadata

    def unregister(self, path: str) -> bool:
        """Unregister a file."""
        if path in self._files:
            del self._files[path]
            return True
        return False

    def get(self, path: str) -> FileMetadata | None:
        """Get metadata for a specific file."""
        return self._files.get(path)

    def exists(self, path: str) -> bool:
        """Check if a file is registered."""
        return path in self._files

    def get_all(self) -> dict[str, FileMetadata]:
        """Get all registered files."""
        return dict(self._files)

    def query(
        self,
        *,
        file_type: FileType | None = None,
        language: str | None = None,
        created_by: str | None = None,
        path_pattern: str | None = None,
    ) -> list[FileMetadata]:
        """Query files by criteria.

        Args:
            file_type: Filter by file type.
            language: Filter by language.
            created_by: Filter by creator.
            path_pattern: Regex pattern to match paths.

        Returns:
            List of matching FileMetadata.
        """
        results = []
        path_regex = re.compile(path_pattern) if path_pattern else None

        for metadata in self._files.values():
            if file_type and metadata.file_type != file_type:
                continue
            if language and metadata.language != language:
                continue
            if created_by and metadata.created_by != created_by:
                continue
            if path_regex and not path_regex.search(metadata.path):
                continue
            results.append(metadata)

        return results

    def get_importers(self, path: str) -> list[str]:
        """Get all files that import a given file.

        Args:
            path: Path of the file to check.

        Returns:
            List of file paths that import the given file.
        """
        importers = []
        for file_path, metadata in self._files.items():
            if file_path == path:
                continue
            # Check if any import resolves to the target path
            for imp in metadata.imports:
                if self._import_resolves_to(file_path, imp, path):
                    importers.append(file_path)
                    break
        return importers

    def get_dependencies(self, path: str) -> list[str]:
        """Get all files that a given file depends on (imports).

        Args:
            path: Path of the file to check.

        Returns:
            List of file paths that the given file imports.
        """
        metadata = self._files.get(path)
        if not metadata:
            return []

        dependencies = []
        for imp in metadata.imports:
            resolved = self._resolve_import(path, imp)
            if resolved and resolved in self._files:
                dependencies.append(resolved)
        return dependencies

    def _import_resolves_to(self, from_file: str, import_path: str, target: str) -> bool:
        """Check if an import resolves to a target file."""
        resolved = self._resolve_import(from_file, import_path)
        if resolved == target:
            return True

        # Also check with common extensions
        target_stem = Path(target).stem
        resolved_stem = Path(resolved).stem if resolved else ""
        return target_stem == resolved_stem and Path(target).parent == Path(resolved).parent if resolved else False

    def _resolve_import(self, from_file: str, import_path: str) -> str | None:
        """Resolve an import path to an absolute file path.

        This is a simplified resolver. Language-specific resolvers
        can be implemented as extensions.
        """
        if not import_path.startswith("."):
            # Absolute import - return as-is for external packages
            return None

        from_dir = Path(from_file).parent

        # Handle relative imports
        if import_path.startswith("./"):
            resolved = from_dir / import_path[2:]
        elif import_path.startswith("../"):
            resolved = from_dir / import_path
        else:
            resolved = from_dir / import_path

        # Normalize path
        resolved_str = str(resolved.resolve()).replace("\\", "/")

        # Try with common extensions
        for ext in ["", ".js", ".ts", ".vue", ".jsx", ".tsx", ".py", "/index.js", "/index.ts"]:
            candidate = resolved_str + ext
            if candidate in self._files:
                return candidate

        return resolved_str

    def add_change_listener(self, listener: Callable[[str, FileMetadata], None]) -> None:
        """Add a listener for file changes."""
        self._change_listeners.append(listener)

    def remove_change_listener(self, listener: Callable[[str, FileMetadata], None]) -> None:
        """Remove a change listener."""
        if listener in self._change_listeners:
            self._change_listeners.remove(listener)

    def to_dict(self) -> dict[str, Any]:
        """Serialize registry to dictionary."""
        return {
            "files": {path: meta.to_dict() for path, meta in self._files.items()}
        }

    def from_dict(self, data: dict[str, Any]) -> None:
        """Load registry from dictionary."""
        self._files.clear()
        for path, meta_data in data.get("files", {}).items():
            self._files[path] = FileMetadata.from_dict(meta_data)

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about registered files."""
        stats = {
            "total_files": len(self._files),
            "by_type": {},
            "by_language": {},
            "total_lines": 0,
            "total_bytes": 0,
        }

        for metadata in self._files.values():
            # By type
            type_key = metadata.file_type.value
            stats["by_type"][type_key] = stats["by_type"].get(type_key, 0) + 1

            # By language
            lang_key = metadata.language
            stats["by_language"][lang_key] = stats["by_language"].get(lang_key, 0) + 1

            # Totals
            stats["total_lines"] += metadata.line_count
            stats["total_bytes"] += metadata.size_bytes

        return stats
