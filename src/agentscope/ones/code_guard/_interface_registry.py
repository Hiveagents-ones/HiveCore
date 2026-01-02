# -*- coding: utf-8 -*-
"""InterfaceRegistry: Extract and track interface definitions from code.

This module provides language-agnostic interface extraction to build a registry
of known functions, classes, and other symbols that can be referenced.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class SymbolType(str, Enum):
    """Types of code symbols that can be extracted.

    Attributes:
        FUNCTION: A function definition.
        CLASS: A class definition.
        METHOD: A method within a class.
        VARIABLE: A variable declaration.
        CONSTANT: A constant declaration.
        INTERFACE: A TypeScript interface.
        TYPE_ALIAS: A type alias definition.
    """

    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    INTERFACE = "interface"
    TYPE_ALIAS = "type_alias"


@dataclass
class FunctionSignature:
    """Represents a function signature.

    Attributes:
        name (`str`):
            The function name.
        parameters (`list[tuple[str, str | None]]`):
            List of (param_name, type_hint) tuples.
        return_type (`str | None`):
            The return type annotation if present.
        is_async (`bool`):
            Whether the function is async.
        decorators (`list[str]`):
            List of decorator names applied to the function.
    """

    name: str
    parameters: list[tuple[str, str | None]] = field(default_factory=list)
    return_type: str | None = None
    is_async: bool = False
    decorators: list[str] = field(default_factory=list)


@dataclass
class ClassDefinition:
    """Represents a class definition.

    Attributes:
        name (`str`):
            The class name.
        base_classes (`list[str]`):
            List of base class names.
        methods (`list[FunctionSignature]`):
            List of method signatures.
        attributes (`list[tuple[str, str | None]]`):
            List of (attr_name, type_hint) tuples.
    """

    name: str
    base_classes: list[str] = field(default_factory=list)
    methods: list[FunctionSignature] = field(default_factory=list)
    attributes: list[tuple[str, str | None]] = field(default_factory=list)


@dataclass
class InterfaceEntry:
    """Represents a registered interface entry.

    Attributes:
        symbol_type (`SymbolType`):
            The type of symbol.
        name (`str`):
            The symbol name.
        file_path (`str`):
            Path to the file where the symbol is defined.
        line_number (`int`):
            Line number where the symbol is defined.
        signature (`FunctionSignature | ClassDefinition | None`):
            The signature or definition details.
        exported (`bool`):
            Whether the symbol is exported/public.
    """

    symbol_type: SymbolType
    name: str
    file_path: str
    line_number: int
    signature: FunctionSignature | ClassDefinition | None = None
    exported: bool = True

    @property
    def qualified_name(self) -> str:
        """Get the fully qualified name.

        Returns:
            `str`:
                The qualified name in format 'file_path:name'.
        """
        return f"{self.file_path}:{self.name}"


class LanguageInterfaceExtractor(ABC):
    """Abstract base class for language-specific interface extractors.

    Subclasses should implement extraction logic for specific languages.
    """

    @abstractmethod
    def get_language(self) -> str:
        """Get the language name.

        Returns:
            `str`:
                The language name (e.g., 'python', 'typescript').
        """
        ...

    @abstractmethod
    def get_file_extensions(self) -> list[str]:
        """Get supported file extensions.

        Returns:
            `list[str]`:
                List of file extensions (e.g., ['.py']).
        """
        ...

    @abstractmethod
    def extract_interfaces(
        self,
        file_path: str,
        content: str,
    ) -> list[InterfaceEntry]:
        """Extract interface definitions from file content.

        Args:
            file_path (`str`):
                Path to the file.
            content (`str`):
                The file content.

        Returns:
            `list[InterfaceEntry]`:
                List of extracted interface entries.
        """
        ...

    @abstractmethod
    def extract_function_calls(
        self,
        content: str,
    ) -> list[tuple[str, int]]:
        """Extract function calls from content.

        Args:
            content (`str`):
                The code content.

        Returns:
            `list[tuple[str, int]]`:
                List of (function_name, line_number) tuples.
        """
        ...


class PythonInterfaceExtractor(LanguageInterfaceExtractor):
    """Interface extractor for Python code."""

    # Regex patterns
    _FUNC_PATTERN = re.compile(
        r"^(\s*)(async\s+)?def\s+(\w+)\s*\((.*?)\)\s*(?:->\s*(.+?))?:",
        re.MULTILINE,
    )
    _CLASS_PATTERN = re.compile(
        r"^(\s*)class\s+(\w+)\s*(?:\((.*?)\))?:",
        re.MULTILINE,
    )
    _DECORATOR_PATTERN = re.compile(r"^(\s*)@(\w+)", re.MULTILINE)
    _CALL_PATTERN = re.compile(r"(\w+)\s*\(")

    # Keywords to exclude from function calls
    _PYTHON_KEYWORDS = frozenset(
        {
            "if",
            "for",
            "while",
            "with",
            "except",
            "assert",
            "return",
            "yield",
            "raise",
            "del",
            "pass",
            "break",
            "continue",
            "lambda",
            "and",
            "or",
            "not",
            "in",
            "is",
            "True",
            "False",
            "None",
        }
    )

    def get_language(self) -> str:
        """Get the language name."""
        return "python"

    def get_file_extensions(self) -> list[str]:
        """Get supported file extensions."""
        return [".py", ".pyw"]

    def extract_interfaces(
        self,
        file_path: str,
        content: str,
    ) -> list[InterfaceEntry]:
        """Extract interface definitions from Python code."""
        entries: list[InterfaceEntry] = []

        # Extract functions
        for match in self._FUNC_PATTERN.finditer(content):
            indent = match.group(1)
            is_async = match.group(2) is not None
            name = match.group(3)
            params_str = match.group(4)
            return_type = match.group(5)

            line_num = content[: match.start()].count("\n") + 1
            is_top_level = len(indent) == 0
            symbol_type = SymbolType.FUNCTION if is_top_level else SymbolType.METHOD

            sig = FunctionSignature(
                name=name,
                parameters=self._parse_params(params_str),
                return_type=return_type.strip() if return_type else None,
                is_async=is_async,
            )

            entries.append(
                InterfaceEntry(
                    symbol_type=symbol_type,
                    name=name,
                    file_path=file_path,
                    line_number=line_num,
                    signature=sig,
                    exported=not name.startswith("_"),
                )
            )

        # Extract classes
        for match in self._CLASS_PATTERN.finditer(content):
            name = match.group(2)
            bases_str = match.group(3) or ""
            line_num = content[: match.start()].count("\n") + 1

            bases = [b.strip() for b in bases_str.split(",") if b.strip()]

            class_def = ClassDefinition(
                name=name,
                base_classes=bases,
            )

            entries.append(
                InterfaceEntry(
                    symbol_type=SymbolType.CLASS,
                    name=name,
                    file_path=file_path,
                    line_number=line_num,
                    signature=class_def,
                    exported=not name.startswith("_"),
                )
            )

        return entries

    def extract_function_calls(
        self,
        content: str,
    ) -> list[tuple[str, int]]:
        """Extract function calls from Python code."""
        calls: list[tuple[str, int]] = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith("#"):
                continue

            # Find calls (simple heuristic)
            for match in self._CALL_PATTERN.finditer(line):
                name = match.group(1)
                if name not in self._PYTHON_KEYWORDS:
                    calls.append((name, line_num))

        return calls

    def _parse_params(self, params_str: str) -> list[tuple[str, str | None]]:
        """Parse parameter string into list of (name, type) tuples."""
        if not params_str.strip():
            return []

        params: list[tuple[str, str | None]] = []
        depth = 0
        current = ""

        for char in params_str:
            if char in "([{":
                depth += 1
            elif char in ")]}":
                depth -= 1
            elif char == "," and depth == 0:
                self._add_param(current, params)
                current = ""
                continue
            current += char

        if current.strip():
            self._add_param(current, params)

        return params

    def _add_param(
        self,
        param_str: str,
        params: list[tuple[str, str | None]],
    ) -> None:
        """Add a parsed parameter to the list."""
        param = param_str.strip()
        if not param or param in ("self", "cls"):
            return

        # Handle type annotation
        if ":" in param:
            name, type_hint = param.split(":", 1)
            if "=" in type_hint:
                type_hint = type_hint.split("=")[0]
            params.append((name.strip(), type_hint.strip()))
        else:
            name = param.split("=")[0].strip()
            params.append((name, None))


class TypeScriptInterfaceExtractor(LanguageInterfaceExtractor):
    """Interface extractor for TypeScript/JavaScript code."""

    _FUNC_PATTERN = re.compile(
        r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*[<(]",
        re.MULTILINE,
    )
    _CLASS_PATTERN = re.compile(
        r"(?:export\s+)?class\s+(\w+)",
        re.MULTILINE,
    )
    _INTERFACE_PATTERN = re.compile(
        r"(?:export\s+)?interface\s+(\w+)",
        re.MULTILINE,
    )
    _ARROW_FUNC_PATTERN = re.compile(
        r"(?:export\s+)?(?:const|let)\s+(\w+)\s*=\s*(?:async\s*)?\(",
        re.MULTILINE,
    )
    _TYPE_ALIAS_PATTERN = re.compile(
        r"(?:export\s+)?type\s+(\w+)\s*=",
        re.MULTILINE,
    )
    _CALL_PATTERN = re.compile(r"(\w+)\s*[<(]")

    _JS_KEYWORDS = frozenset(
        {
            "if",
            "for",
            "while",
            "switch",
            "function",
            "class",
            "interface",
            "type",
            "const",
            "let",
            "var",
            "import",
            "export",
            "return",
            "new",
            "async",
            "await",
            "try",
            "catch",
            "throw",
            "typeof",
            "instanceof",
        }
    )

    def get_language(self) -> str:
        """Get the language name."""
        return "typescript"

    def get_file_extensions(self) -> list[str]:
        """Get supported file extensions."""
        return [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]

    def extract_interfaces(
        self,
        file_path: str,
        content: str,
    ) -> list[InterfaceEntry]:
        """Extract interface definitions from TypeScript code."""
        entries: list[InterfaceEntry] = []

        # Extract functions
        for match in self._FUNC_PATTERN.finditer(content):
            name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1
            exported = "export" in content[max(0, match.start() - 15) : match.start()]

            entries.append(
                InterfaceEntry(
                    symbol_type=SymbolType.FUNCTION,
                    name=name,
                    file_path=file_path,
                    line_number=line_num,
                    exported=exported,
                )
            )

        # Extract arrow functions
        for match in self._ARROW_FUNC_PATTERN.finditer(content):
            name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1
            exported = "export" in content[max(0, match.start() - 15) : match.start()]

            entries.append(
                InterfaceEntry(
                    symbol_type=SymbolType.FUNCTION,
                    name=name,
                    file_path=file_path,
                    line_number=line_num,
                    exported=exported,
                )
            )

        # Extract classes
        for match in self._CLASS_PATTERN.finditer(content):
            name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1

            entries.append(
                InterfaceEntry(
                    symbol_type=SymbolType.CLASS,
                    name=name,
                    file_path=file_path,
                    line_number=line_num,
                )
            )

        # Extract interfaces
        for match in self._INTERFACE_PATTERN.finditer(content):
            name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1

            entries.append(
                InterfaceEntry(
                    symbol_type=SymbolType.INTERFACE,
                    name=name,
                    file_path=file_path,
                    line_number=line_num,
                )
            )

        # Extract type aliases
        for match in self._TYPE_ALIAS_PATTERN.finditer(content):
            name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1

            entries.append(
                InterfaceEntry(
                    symbol_type=SymbolType.TYPE_ALIAS,
                    name=name,
                    file_path=file_path,
                    line_number=line_num,
                )
            )

        return entries

    def extract_function_calls(
        self,
        content: str,
    ) -> list[tuple[str, int]]:
        """Extract function calls from TypeScript code."""
        calls: list[tuple[str, int]] = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith("//"):
                continue

            for match in self._CALL_PATTERN.finditer(line):
                name = match.group(1)
                if name not in self._JS_KEYWORDS:
                    calls.append((name, line_num))

        return calls


class InterfaceRegistry:
    """Registry of known interface definitions.

    This registry tracks all function, class, and interface definitions
    extracted from files that have been read. It's used to detect
    hallucinations when code references unknown symbols.
    """

    # Built-in functions that don't need to be tracked
    PYTHON_BUILTINS = frozenset(
        {
            "print",
            "len",
            "range",
            "str",
            "int",
            "float",
            "list",
            "dict",
            "set",
            "tuple",
            "bool",
            "type",
            "isinstance",
            "issubclass",
            "hasattr",
            "getattr",
            "setattr",
            "delattr",
            "open",
            "input",
            "zip",
            "map",
            "filter",
            "sorted",
            "reversed",
            "enumerate",
            "sum",
            "min",
            "max",
            "abs",
            "round",
            "all",
            "any",
            "ord",
            "chr",
            "hex",
            "oct",
            "bin",
            "format",
            "repr",
            "id",
            "hash",
            "super",
            "staticmethod",
            "classmethod",
            "property",
            "dataclass",
            "field",
            "object",
            "Exception",
            "BaseException",
            "ValueError",
            "TypeError",
            "KeyError",
            "IndexError",
            "AttributeError",
            "RuntimeError",
            "StopIteration",
            "iter",
            "next",
            "callable",
            "vars",
            "dir",
            "globals",
            "locals",
            "exec",
            "eval",
            "compile",
            "__import__",
        }
    )

    JS_BUILTINS = frozenset(
        {
            "console",
            "Math",
            "Date",
            "JSON",
            "Object",
            "Array",
            "String",
            "Number",
            "Boolean",
            "Promise",
            "Set",
            "Map",
            "WeakMap",
            "WeakSet",
            "Error",
            "TypeError",
            "SyntaxError",
            "ReferenceError",
            "fetch",
            "setTimeout",
            "setInterval",
            "clearTimeout",
            "clearInterval",
            "parseInt",
            "parseFloat",
            "encodeURI",
            "decodeURI",
            "encodeURIComponent",
            "decodeURIComponent",
            "require",
            "module",
            "exports",
            "process",
            "Buffer",
            "window",
            "document",
            "navigator",
            "location",
            "history",
            "localStorage",
            "sessionStorage",
            "alert",
            "confirm",
            "prompt",
            "React",
            "useState",
            "useEffect",
            "useCallback",
            "useMemo",
            "useRef",
            "useContext",
            "useReducer",
        }
    )

    def __init__(self) -> None:
        """Initialize the interface registry."""
        self._entries: dict[str, InterfaceEntry] = {}  # qualified_name -> entry
        self._by_file: dict[str, list[str]] = {}  # file_path -> [qualified_names]
        self._by_name: dict[str, list[str]] = {}  # name -> [qualified_names]
        self._extractors: dict[str, LanguageInterfaceExtractor] = {}
        self._register_default_extractors()

    def _register_default_extractors(self) -> None:
        """Register default language extractors."""
        self.register_extractor(PythonInterfaceExtractor())
        self.register_extractor(TypeScriptInterfaceExtractor())

    def register_extractor(self, extractor: LanguageInterfaceExtractor) -> None:
        """Register a language-specific extractor.

        Args:
            extractor (`LanguageInterfaceExtractor`):
                The extractor to register.
        """
        for ext in extractor.get_file_extensions():
            self._extractors[ext] = extractor

    def get_extractor(self, file_path: str) -> LanguageInterfaceExtractor | None:
        """Get the extractor for a file.

        Args:
            file_path (`str`):
                The file path.

        Returns:
            `LanguageInterfaceExtractor | None`:
                The extractor, or None if no extractor matches.
        """
        ext = Path(file_path).suffix.lower()
        return self._extractors.get(ext)

    def extract_and_register(
        self,
        file_path: str,
        content: str,
    ) -> list[InterfaceEntry]:
        """Extract interfaces from a file and register them.

        Args:
            file_path (`str`):
                Path to the file.
            content (`str`):
                The file content.

        Returns:
            `list[InterfaceEntry]`:
                List of extracted and registered entries.
        """
        extractor = self.get_extractor(file_path)
        if not extractor:
            return []

        entries = extractor.extract_interfaces(file_path, content)

        # Clear old entries for this file
        if file_path in self._by_file:
            for qname in self._by_file[file_path]:
                if qname in self._entries:
                    entry = self._entries[qname]
                    # Remove from by_name index
                    if entry.name in self._by_name:
                        self._by_name[entry.name] = [
                            q for q in self._by_name[entry.name] if q != qname
                        ]
                        # Clean up empty list
                        if not self._by_name[entry.name]:
                            del self._by_name[entry.name]
                    del self._entries[qname]

        self._by_file[file_path] = []

        # Register new entries
        for entry in entries:
            qname = entry.qualified_name
            self._entries[qname] = entry
            self._by_file[file_path].append(qname)

            if entry.name not in self._by_name:
                self._by_name[entry.name] = []
            if qname not in self._by_name[entry.name]:
                self._by_name[entry.name].append(qname)

        return entries

    def lookup(self, name: str) -> list[InterfaceEntry]:
        """Look up entries by name.

        Args:
            name (`str`):
                The symbol name to look up.

        Returns:
            `list[InterfaceEntry]`:
                List of matching entries.
        """
        qnames = self._by_name.get(name, [])
        return [self._entries[qn] for qn in qnames if qn in self._entries]

    def exists(self, name: str) -> bool:
        """Check if a symbol exists.

        Args:
            name (`str`):
                The symbol name to check.

        Returns:
            `bool`:
                True if the symbol exists in registry or is a builtin.
        """
        return name in self._by_name or self._is_builtin(name)

    def _is_builtin(self, name: str) -> bool:
        """Check if a name is a builtin function/class."""
        return name in self.PYTHON_BUILTINS or name in self.JS_BUILTINS

    def get_file_interfaces(self, file_path: str) -> list[InterfaceEntry]:
        """Get all interfaces defined in a file.

        Args:
            file_path (`str`):
                Path to the file.

        Returns:
            `list[InterfaceEntry]`:
                List of entries defined in the file.
        """
        qnames = self._by_file.get(file_path, [])
        return [self._entries[qn] for qn in qnames if qn in self._entries]

    def get_all_entries(self) -> list[InterfaceEntry]:
        """Get all registered entries.

        Returns:
            `list[InterfaceEntry]`:
                All registered interface entries.
        """
        return list(self._entries.values())

    def get_statistics(self) -> dict[str, int]:
        """Get registry statistics.

        Returns:
            `dict[str, int]`:
                Statistics about registered entries.
        """
        by_type: dict[str, int] = {}
        for entry in self._entries.values():
            type_name = entry.symbol_type.value
            by_type[type_name] = by_type.get(type_name, 0) + 1

        return {
            "total": len(self._entries),
            "files": len(self._by_file),
            **by_type,
        }

    def clear(self) -> None:
        """Clear all registered entries."""
        self._entries.clear()
        self._by_file.clear()
        self._by_name.clear()
