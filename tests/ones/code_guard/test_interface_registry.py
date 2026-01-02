# -*- coding: utf-8 -*-
"""Tests for InterfaceRegistry module."""
import pytest

from agentscope.ones.code_guard import (
    InterfaceRegistry,
    InterfaceEntry,
    SymbolType,
    PythonInterfaceExtractor,
    TypeScriptInterfaceExtractor,
)


class TestPythonInterfaceExtractor:
    """Tests for Python interface extraction."""

    @pytest.fixture
    def extractor(self) -> PythonInterfaceExtractor:
        """Create a Python extractor."""
        return PythonInterfaceExtractor()

    def test_extract_function(self, extractor: PythonInterfaceExtractor) -> None:
        """Test extracting a simple function."""
        content = '''def hello(name: str) -> str:
    return f"Hello, {name}"
'''
        entries = extractor.extract_interfaces("/test.py", content)

        assert len(entries) == 1
        entry = entries[0]
        assert entry.name == "hello"
        assert entry.symbol_type == SymbolType.FUNCTION
        assert entry.exported is True
        assert entry.signature is not None
        assert entry.signature.return_type == "str"

    def test_extract_async_function(self, extractor: PythonInterfaceExtractor) -> None:
        """Test extracting an async function."""
        content = '''
async def fetch_data(url: str) -> dict:
    pass
'''
        entries = extractor.extract_interfaces("/test.py", content)

        assert len(entries) == 1
        entry = entries[0]
        assert entry.name == "fetch_data"
        assert entry.signature.is_async is True

    def test_extract_private_function(self, extractor: PythonInterfaceExtractor) -> None:
        """Test private function detection."""
        content = '''
def _private_func():
    pass
'''
        entries = extractor.extract_interfaces("/test.py", content)

        assert len(entries) == 1
        assert entries[0].exported is False

    def test_extract_class(self, extractor: PythonInterfaceExtractor) -> None:
        """Test extracting a class."""
        content = '''
class MyClass(BaseClass, Mixin):
    def method(self):
        pass
'''
        entries = extractor.extract_interfaces("/test.py", content)

        classes = [e for e in entries if e.symbol_type == SymbolType.CLASS]
        assert len(classes) == 1
        assert classes[0].name == "MyClass"
        assert classes[0].signature.base_classes == ["BaseClass", "Mixin"]

    def test_extract_method(self, extractor: PythonInterfaceExtractor) -> None:
        """Test extracting a method within a class."""
        content = '''
class MyClass:
    def method(self, arg: int) -> bool:
        pass
'''
        entries = extractor.extract_interfaces("/test.py", content)

        methods = [e for e in entries if e.symbol_type == SymbolType.METHOD]
        assert len(methods) == 1
        assert methods[0].name == "method"

    def test_extract_function_calls(self, extractor: PythonInterfaceExtractor) -> None:
        """Test extracting function calls."""
        content = '''
result = process_data(input)
value = calculate(x, y)
# comment with func()
'''
        calls = extractor.extract_function_calls(content)

        names = [c[0] for c in calls]
        assert "process_data" in names
        assert "calculate" in names


class TestTypeScriptInterfaceExtractor:
    """Tests for TypeScript interface extraction."""

    @pytest.fixture
    def extractor(self) -> TypeScriptInterfaceExtractor:
        """Create a TypeScript extractor."""
        return TypeScriptInterfaceExtractor()

    def test_extract_function(self, extractor: TypeScriptInterfaceExtractor) -> None:
        """Test extracting a function."""
        content = '''
export function greet(name: string): string {
    return `Hello, ${name}`;
}
'''
        entries = extractor.extract_interfaces("/test.ts", content)

        functions = [e for e in entries if e.symbol_type == SymbolType.FUNCTION]
        assert len(functions) == 1
        assert functions[0].name == "greet"

    def test_extract_arrow_function(self, extractor: TypeScriptInterfaceExtractor) -> None:
        """Test extracting arrow function."""
        content = '''
export const add = (a: number, b: number) => a + b;
'''
        entries = extractor.extract_interfaces("/test.ts", content)

        assert len(entries) == 1
        assert entries[0].name == "add"

    def test_extract_interface(self, extractor: TypeScriptInterfaceExtractor) -> None:
        """Test extracting TypeScript interface."""
        content = '''
export interface User {
    id: string;
    name: string;
}
'''
        entries = extractor.extract_interfaces("/test.ts", content)

        interfaces = [e for e in entries if e.symbol_type == SymbolType.INTERFACE]
        assert len(interfaces) == 1
        assert interfaces[0].name == "User"

    def test_extract_type_alias(self, extractor: TypeScriptInterfaceExtractor) -> None:
        """Test extracting type alias."""
        content = '''
export type ID = string | number;
'''
        entries = extractor.extract_interfaces("/test.ts", content)

        types = [e for e in entries if e.symbol_type == SymbolType.TYPE_ALIAS]
        assert len(types) == 1
        assert types[0].name == "ID"


class TestInterfaceRegistry:
    """Tests for InterfaceRegistry class."""

    def test_extract_and_register(self) -> None:
        """Test extracting and registering interfaces."""
        registry = InterfaceRegistry()

        content = '''
def func1():
    pass

class MyClass:
    pass
'''
        entries = registry.extract_and_register("/test.py", content)

        assert len(entries) == 2
        assert registry.exists("func1")
        assert registry.exists("MyClass")

    def test_lookup(self) -> None:
        """Test looking up interfaces by name."""
        registry = InterfaceRegistry()

        content = '''
def process():
    pass
'''
        registry.extract_and_register("/test.py", content)

        entries = registry.lookup("process")
        assert len(entries) == 1
        assert entries[0].file_path == "/test.py"

    def test_builtin_exists(self) -> None:
        """Test that builtins are recognized."""
        registry = InterfaceRegistry()

        assert registry.exists("print")
        assert registry.exists("len")
        assert registry.exists("dict")

    def test_js_builtin_exists(self) -> None:
        """Test that JS builtins are recognized."""
        registry = InterfaceRegistry()

        assert registry.exists("console")
        assert registry.exists("Math")
        assert registry.exists("Promise")

    def test_update_file(self) -> None:
        """Test updating a file replaces old entries."""
        registry = InterfaceRegistry()

        # Initial registration
        registry.extract_and_register("/test.py", "def old_func(): pass")
        assert registry.exists("old_func")

        # Update file
        registry.extract_and_register("/test.py", "def new_func(): pass")
        assert not registry.exists("old_func")
        assert registry.exists("new_func")

    def test_get_file_interfaces(self) -> None:
        """Test getting all interfaces from a file."""
        registry = InterfaceRegistry()

        content = '''
def func1(): pass
def func2(): pass
class Class1: pass
'''
        registry.extract_and_register("/test.py", content)

        entries = registry.get_file_interfaces("/test.py")
        names = {e.name for e in entries}
        assert names == {"func1", "func2", "Class1"}

    def test_get_statistics(self) -> None:
        """Test getting registry statistics."""
        registry = InterfaceRegistry()

        content = '''def func1(): pass
class Class1: pass
'''
        registry.extract_and_register("/test.py", content)

        stats = registry.get_statistics()
        assert stats["total"] == 2
        assert stats["files"] == 1
        assert stats.get("function", 0) == 1
        assert stats.get("class", 0) == 1

    def test_clear(self) -> None:
        """Test clearing the registry."""
        registry = InterfaceRegistry()
        registry.extract_and_register("/test.py", "def func(): pass")

        assert registry.exists("func")
        registry.clear()
        assert not registry.exists("func")
