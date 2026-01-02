# -*- coding: utf-8 -*-
"""Dependency Synchronizer for managing project dependencies (language agnostic).

This module provides a generic dependency synchronization mechanism that uses
Agent manifest configurations. All language-specific logic (file formats,
package managers) is defined in the manifest, not in this module.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from .._logging import logger

if TYPE_CHECKING:
    from .manifest import AgentManifest, DependencyConfig


@dataclass
class DependencyInfo:
    """Information about a dependency.

    Attributes:
        name (`str`):
            The package/module name.
        version (`str`):
            Version specifier (e.g., ">=2.0", "^1.0.0").
        source (`str`):
            Where this dependency was found (file path).
        is_dev (`bool`):
            Whether this is a development dependency.
    """

    name: str
    version: str = ""
    source: str = ""
    is_dev: bool = False


@dataclass
class SyncResult:
    """Result of a dependency synchronization.

    Attributes:
        success (`bool`):
            Whether synchronization was successful.
        added (`list[DependencyInfo]`):
            Dependencies that were added.
        updated (`list[DependencyInfo]`):
            Dependencies that were updated.
        errors (`list[str]`):
            Any errors encountered.
        dependency_file (`str`):
            Path to the dependency file that was updated.
    """

    success: bool
    added: list[DependencyInfo] = field(default_factory=list)
    updated: list[DependencyInfo] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    dependency_file: str = ""


class DependencySynchronizer:
    """Generic dependency synchronizer using manifest configuration.

    This synchronizer analyzes code files for imports/requires and ensures
    they are present in the dependency file. It uses the manifest's
    dependency_config for language-specific details.

    Example usage:
        ```python
        sync = DependencySynchronizer(manifest)

        # Analyze code for dependencies
        deps = sync.extract_dependencies_from_code(code_content, "python")

        # Check what's missing from dependency file
        missing = sync.find_missing_dependencies(deps, dep_file_content)

        # Generate update for dependency file
        update = sync.generate_dependency_update(missing)

        # Apply update
        result = await sync.apply_update(update, workspace)
        ```
    """

    # Common import patterns for different file formats
    # These are used as fallbacks; manifest can override
    IMPORT_PATTERNS = {
        "python": [
            r"^import\s+(\w+)",
            r"^from\s+(\w+)",
        ],
        "javascript": [
            r"require\(['\"]([^'\"]+)['\"]\)",
            r"from\s+['\"]([^'\"]+)['\"]",
            r"import\s+.*\s+from\s+['\"]([^'\"]+)['\"]",
        ],
        "go": [
            r"import\s+\"([^\"]+)\"",
            r"import\s+\(\s*\"([^\"]+)\"",
        ],
    }

    # Standard library modules to exclude (partial list)
    STDLIB_MODULES = {
        "python": {
            "os", "sys", "re", "json", "typing", "dataclasses", "pathlib",
            "collections", "functools", "itertools", "datetime", "time",
            "asyncio", "abc", "enum", "logging", "unittest", "io", "copy",
            "math", "random", "hashlib", "base64", "uuid", "threading",
            "multiprocessing", "subprocess", "shutil", "tempfile", "glob",
            "contextlib", "warnings", "traceback", "inspect", "operator",
        },
        "javascript": {
            "fs", "path", "http", "https", "url", "util", "events",
            "stream", "buffer", "crypto", "os", "child_process", "cluster",
        },
    }

    def __init__(self, manifest: "AgentManifest"):
        """Initialize the dependency synchronizer.

        Args:
            manifest: The agent manifest containing dependency configuration.
        """
        self.manifest = manifest
        self.dep_config = manifest.dependency_config

    def get_dependency_file(self) -> str:
        """Get the dependency file path from manifest.

        Returns:
            The dependency file path, or empty string if not configured.
        """
        if self.dep_config:
            return self.dep_config.dependency_file
        return ""

    def get_file_format(self) -> str:
        """Get the dependency file format from manifest.

        Returns:
            The file format identifier.
        """
        if self.dep_config:
            return self.dep_config.file_format
        return ""

    def extract_dependencies_from_code(
        self,
        code_content: str,
        language: str | None = None,
    ) -> list[DependencyInfo]:
        """Extract dependencies from source code.

        Args:
            code_content: The source code content.
            language: Optional language override (defaults to manifest detection).

        Returns:
            List of extracted dependencies.
        """
        # Determine language from manifest or parameter
        if not language:
            # Infer from manifest skills
            skills = self.manifest.skills
            if "python" in skills or "fastapi" in skills or "django" in skills:
                language = "python"
            elif "javascript" in skills or "typescript" in skills:
                language = "javascript"
            elif "go" in skills or "golang" in skills:
                language = "go"
            else:
                language = "python"  # Default fallback

        patterns = self.IMPORT_PATTERNS.get(language, [])
        stdlib = self.STDLIB_MODULES.get(language, set())

        dependencies: list[DependencyInfo] = []
        seen: set[str] = set()

        for pattern in patterns:
            for match in re.finditer(pattern, code_content, re.MULTILINE):
                module_name = match.group(1)

                # Get top-level package name
                top_level = module_name.split(".")[0].split("/")[0]

                # Skip stdlib and already seen
                if top_level in stdlib or top_level in seen:
                    continue

                # Skip relative imports
                if top_level.startswith("."):
                    continue

                seen.add(top_level)
                dependencies.append(DependencyInfo(
                    name=top_level,
                    source="code",
                ))

        return dependencies

    def parse_dependency_file(
        self,
        content: str,
        file_format: str | None = None,
    ) -> list[DependencyInfo]:
        """Parse a dependency file to extract current dependencies.

        Args:
            content: The dependency file content.
            file_format: Optional format override (defaults to manifest config).

        Returns:
            List of dependencies in the file.
        """
        if not file_format:
            file_format = self.get_file_format()

        dependencies: list[DependencyInfo] = []

        if file_format == "pip-requirements":
            dependencies = self._parse_pip_requirements(content)
        elif file_format == "npm-package":
            dependencies = self._parse_npm_package(content)
        elif file_format == "go-mod":
            dependencies = self._parse_go_mod(content)
        else:
            # Try to auto-detect format
            if "require(" in content or '"dependencies"' in content:
                dependencies = self._parse_npm_package(content)
            elif "require " in content and "go " in content:
                dependencies = self._parse_go_mod(content)
            else:
                dependencies = self._parse_pip_requirements(content)

        return dependencies

    def _parse_pip_requirements(self, content: str) -> list[DependencyInfo]:
        """Parse pip requirements.txt format."""
        dependencies: list[DependencyInfo] = []

        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue

            # Handle various formats: package, package==1.0, package>=1.0
            match = re.match(r"^([a-zA-Z0-9_-]+)(.*)$", line)
            if match:
                name = match.group(1).lower().replace("-", "_")
                version = match.group(2).strip()
                dependencies.append(DependencyInfo(name=name, version=version))

        return dependencies

    def _parse_npm_package(self, content: str) -> list[DependencyInfo]:
        """Parse npm package.json format."""
        import json

        dependencies: list[DependencyInfo] = []

        try:
            data = json.loads(content)
            for name, version in data.get("dependencies", {}).items():
                dependencies.append(DependencyInfo(name=name, version=version))
            for name, version in data.get("devDependencies", {}).items():
                dependencies.append(DependencyInfo(name=name, version=version, is_dev=True))
        except json.JSONDecodeError:
            logger.warning("Failed to parse package.json")

        return dependencies

    def _parse_go_mod(self, content: str) -> list[DependencyInfo]:
        """Parse go.mod format."""
        dependencies: list[DependencyInfo] = []

        for match in re.finditer(r"require\s+(\S+)\s+(\S+)", content):
            dependencies.append(DependencyInfo(
                name=match.group(1),
                version=match.group(2),
            ))

        return dependencies

    def find_missing_dependencies(
        self,
        required: list[DependencyInfo],
        dep_file_content: str,
    ) -> list[DependencyInfo]:
        """Find dependencies that are required but not in the dependency file.

        Args:
            required: List of required dependencies.
            dep_file_content: Content of the dependency file.

        Returns:
            List of missing dependencies.
        """
        existing = self.parse_dependency_file(dep_file_content)
        existing_names = {d.name.lower().replace("-", "_") for d in existing}

        missing: list[DependencyInfo] = []
        for dep in required:
            normalized = dep.name.lower().replace("-", "_")
            if normalized not in existing_names:
                missing.append(dep)

        return missing

    def generate_dependency_update(
        self,
        dependencies: list[DependencyInfo],
        file_format: str | None = None,
    ) -> str:
        """Generate content to add to the dependency file.

        Args:
            dependencies: List of dependencies to add.
            file_format: Optional format override.

        Returns:
            Content to append/merge into the dependency file.
        """
        if not file_format:
            file_format = self.get_file_format()

        if file_format == "pip-requirements":
            return self._generate_pip_requirements(dependencies)
        elif file_format == "npm-package":
            return self._generate_npm_dependencies(dependencies)
        elif file_format == "go-mod":
            return self._generate_go_requires(dependencies)
        else:
            # Default to pip format
            return self._generate_pip_requirements(dependencies)

    def _generate_pip_requirements(self, dependencies: list[DependencyInfo]) -> str:
        """Generate pip requirements format."""
        lines = []
        for dep in dependencies:
            if dep.version:
                lines.append(f"{dep.name}{dep.version}")
            else:
                lines.append(dep.name)
        return "\n".join(lines)

    def _generate_npm_dependencies(self, dependencies: list[DependencyInfo]) -> str:
        """Generate npm package.json dependencies section."""
        import json

        deps = {}
        for dep in dependencies:
            deps[dep.name] = dep.version or "*"
        return json.dumps(deps, indent=2)

    def _generate_go_requires(self, dependencies: list[DependencyInfo]) -> str:
        """Generate go.mod require statements."""
        lines = []
        for dep in dependencies:
            version = dep.version or "latest"
            lines.append(f"require {dep.name} {version}")
        return "\n".join(lines)

    async def sync_dependencies(
        self,
        code_files: dict[str, str],
        workspace: Any,
    ) -> SyncResult:
        """Synchronize dependencies from code files to dependency file.

        Args:
            code_files: Dict of file_path -> content for code files.
            workspace: The RuntimeWorkspace to update.

        Returns:
            SyncResult with details of what was changed.
        """
        result = SyncResult(success=True)

        dep_file = self.get_dependency_file()
        if not dep_file:
            result.errors.append("No dependency file configured in manifest")
            result.success = False
            return result

        result.dependency_file = dep_file

        # Extract all dependencies from code
        all_deps: list[DependencyInfo] = []
        for file_path, content in code_files.items():
            deps = self.extract_dependencies_from_code(content)
            for dep in deps:
                dep.source = file_path
            all_deps.extend(deps)

        # Read current dependency file
        try:
            dep_content = workspace.read_file(dep_file)
        except Exception:
            dep_content = ""

        # Find missing dependencies
        missing = self.find_missing_dependencies(all_deps, dep_content)

        if not missing:
            logger.info("[DependencySync] No missing dependencies found")
            return result

        # Generate update content
        update = self.generate_dependency_update(missing)

        # Apply update based on file format
        try:
            if self.get_file_format() == "npm-package":
                # For npm, we need to merge JSON
                await self._update_npm_package(workspace, dep_file, missing)
            else:
                # For requirements.txt and go.mod, append
                if dep_content and not dep_content.endswith("\n"):
                    update = "\n" + update
                new_content = dep_content + update + "\n"

                if hasattr(workspace, "write_file"):
                    workspace.write_file(dep_file, new_content)
                else:
                    workspace.execute_command(
                        f"cat >> {dep_file} << 'EOF'\n{update}\nEOF"
                    )

            result.added = missing
            logger.info(
                "[DependencySync] Added %d dependencies to %s: %s",
                len(missing),
                dep_file,
                [d.name for d in missing],
            )

        except Exception as e:
            result.success = False
            result.errors.append(f"Failed to update {dep_file}: {e}")

        return result

    async def _update_npm_package(
        self,
        workspace: Any,
        file_path: str,
        dependencies: list[DependencyInfo],
    ) -> None:
        """Update package.json with new dependencies."""
        import json

        content = workspace.read_file(file_path)
        data = json.loads(content)

        if "dependencies" not in data:
            data["dependencies"] = {}

        for dep in dependencies:
            if not dep.is_dev:
                data["dependencies"][dep.name] = dep.version or "*"
            else:
                if "devDependencies" not in data:
                    data["devDependencies"] = {}
                data["devDependencies"][dep.name] = dep.version or "*"

        new_content = json.dumps(data, indent=2, ensure_ascii=False)

        if hasattr(workspace, "write_file"):
            workspace.write_file(file_path, new_content)
        else:
            workspace.execute_command(
                f"cat > {file_path} << 'EOF'\n{new_content}\nEOF"
            )

    def build_sync_prompt(
        self,
        missing_deps: list[DependencyInfo],
        error_context: str | None = None,
    ) -> str:
        """Build a prompt for LLM to help with dependency resolution.

        Args:
            missing_deps: List of potentially missing dependencies.
            error_context: Optional error message that triggered this.

        Returns:
            A prompt string for the LLM.
        """
        dep_file = self.get_dependency_file()

        prompt = f"""分析以下可能缺失的依赖并确定需要添加到 {dep_file} 的内容:

## 可能缺失的依赖
{chr(10).join(f'- {d.name} (from {d.source})' for d in missing_deps)}

"""

        if error_context:
            prompt += f"""## 错误上下文
```
{error_context}
```

"""

        prompt += f"""## 任务
1. 确认哪些依赖确实需要添加（排除标准库和项目内部模块）
2. 确定每个依赖的正确包名（例如 pydantic_settings 对应 pydantic-settings）
3. 建议合适的版本约束

## 输出格式
请输出需要添加到 {dep_file} 的内容:

```
package1>=1.0.0
package2
```
"""

        return prompt
