# -*- coding: utf-8 -*-
"""CodeGuard: Anti-hallucination system for code generation.

This module provides real-time validation during code generation to prevent:
- Modifying files that haven't been read
- Calling non-existent interfaces
- Importing non-existent modules

Usage:
    from agentscope.ones.code_guard import (
        CodeGuardManager,
        CodeGuardConfig,
        StrictnessLevel,
    )

    # Create manager
    config = CodeGuardConfig(strictness=StrictnessLevel.NORMAL)
    code_guard = CodeGuardManager(config)

    # Register with toolkit
    toolkit.register_tool_function(
        view_text_file,
        postprocess_func=code_guard.create_view_postprocess(),
    )
    toolkit.register_tool_function(
        write_text_file,
        postprocess_func=code_guard.create_write_postprocess(),
    )
"""
from ._config import CodeGuardConfig, StrictnessLevel
from ._read_guard import FileReadLog, FileReadRecord, ReadGuard
from ._write_guard import WriteGuard
from ._import_guard import ImportGuard
from ._interface_registry import (
    InterfaceRegistry,
    InterfaceEntry,
    SymbolType,
    FunctionSignature,
    ClassDefinition,
    LanguageInterfaceExtractor,
    PythonInterfaceExtractor,
    TypeScriptInterfaceExtractor,
)
from ._hallucination_detector import HallucinationDetector
from ._manager import CodeGuardManager, create_code_guard_manager

__all__ = [
    # Config
    "CodeGuardConfig",
    "StrictnessLevel",
    # ReadGuard
    "FileReadLog",
    "FileReadRecord",
    "ReadGuard",
    # WriteGuard
    "WriteGuard",
    # ImportGuard
    "ImportGuard",
    # InterfaceRegistry
    "InterfaceRegistry",
    "InterfaceEntry",
    "SymbolType",
    "FunctionSignature",
    "ClassDefinition",
    "LanguageInterfaceExtractor",
    "PythonInterfaceExtractor",
    "TypeScriptInterfaceExtractor",
    # HallucinationDetector
    "HallucinationDetector",
    # Manager
    "CodeGuardManager",
    "create_code_guard_manager",
]
