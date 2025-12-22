# -*- coding: utf-8 -*-
"""Architecture contract validation system.

This module validates consistency between architecture contracts,
blueprints, and actual implementations in a language-agnostic way.

Design Principles:
1. Contract-first validation
2. Language-agnostic rules with pluggable matchers
3. Clear traceability from contract to implementation
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .file_tracking import FileRegistry, FileMetadata
from .dependency_validation import (
    ValidationResult,
    ValidationIssue,
    IssueSeverity,
    IssueCategory,
)


class ContractItemType(str, Enum):
    """Types of items in an architecture contract."""

    API_ENDPOINT = "api_endpoint"
    DATA_MODEL = "data_model"
    FILE_STRUCTURE = "file_structure"
    TECH_STACK = "tech_stack"
    DEPENDENCY = "dependency"
    CONSTRAINT = "constraint"


@dataclass
class ContractItem:
    """Represents a single item in an architecture contract.

    This is a language-agnostic representation of any contract element.
    """

    item_type: ContractItemType
    identifier: str               # Unique identifier within type
    specification: dict[str, Any]  # Type-specific specification
    required: bool = True          # Whether implementation is required

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "item_type": self.item_type.value,
            "identifier": self.identifier,
            "specification": self.specification,
            "required": self.required,
        }


@dataclass
class ImplementationReference:
    """Reference to an implementation of a contract item.

    Links a contract item to its actual implementation in code.
    """

    contract_item_id: str         # ID of the contract item
    file_path: str                # File implementing the item
    location: str | None = None   # Specific location (e.g., function name)
    confidence: float = 1.0       # Confidence of the match (0-1)
    notes: str = ""               # Additional notes


class ArchitectureContract:
    """Represents an architecture contract.

    An architecture contract defines what should be implemented,
    including APIs, data models, file structure, etc.
    """

    def __init__(self, contract_id: str = "") -> None:
        self.contract_id = contract_id
        self._items: dict[str, ContractItem] = {}
        self._implementations: dict[str, list[ImplementationReference]] = {}

    def add_item(self, item: ContractItem) -> None:
        """Add an item to the contract."""
        key = f"{item.item_type.value}:{item.identifier}"
        self._items[key] = item

    def get_item(self, item_type: ContractItemType, identifier: str) -> ContractItem | None:
        """Get a specific contract item."""
        key = f"{item_type.value}:{identifier}"
        return self._items.get(key)

    def get_items_by_type(self, item_type: ContractItemType) -> list[ContractItem]:
        """Get all items of a specific type."""
        prefix = f"{item_type.value}:"
        return [item for key, item in self._items.items() if key.startswith(prefix)]

    def get_all_items(self) -> list[ContractItem]:
        """Get all contract items."""
        return list(self._items.values())

    def register_implementation(
        self,
        item_type: ContractItemType,
        identifier: str,
        file_path: str,
        location: str | None = None,
        confidence: float = 1.0,
    ) -> None:
        """Register an implementation of a contract item."""
        key = f"{item_type.value}:{identifier}"
        if key not in self._implementations:
            self._implementations[key] = []

        ref = ImplementationReference(
            contract_item_id=key,
            file_path=file_path,
            location=location,
            confidence=confidence,
        )
        self._implementations[key].append(ref)

    def get_implementations(
        self,
        item_type: ContractItemType,
        identifier: str,
    ) -> list[ImplementationReference]:
        """Get implementations for a contract item."""
        key = f"{item_type.value}:{identifier}"
        return self._implementations.get(key, [])

    def get_unimplemented_items(self) -> list[ContractItem]:
        """Get all contract items without implementations."""
        return [
            item for key, item in self._items.items()
            if item.required and key not in self._implementations
        ]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ArchitectureContract":
        """Create contract from dictionary (e.g., from ArchitectAgent output)."""
        contract = cls(contract_id=data.get("id", ""))

        # Parse API endpoints
        for endpoint in data.get("api_endpoints", []):
            contract.add_item(ContractItem(
                item_type=ContractItemType.API_ENDPOINT,
                identifier=endpoint.get("path", ""),
                specification={
                    "methods": endpoint.get("methods", ["GET"]),
                    "description": endpoint.get("description", ""),
                    "request_schema": endpoint.get("request_schema"),
                    "response_schema": endpoint.get("response_schema"),
                },
            ))

        # Parse data models
        for model in data.get("data_models", []):
            contract.add_item(ContractItem(
                item_type=ContractItemType.DATA_MODEL,
                identifier=model.get("name", ""),
                specification={
                    "fields": model.get("fields", []),
                    "description": model.get("description", ""),
                },
            ))

        # Parse file structure
        file_struct = data.get("file_structure", {})
        for layer, config in file_struct.items():
            if isinstance(config, dict):
                for key, value in config.items():
                    contract.add_item(ContractItem(
                        item_type=ContractItemType.FILE_STRUCTURE,
                        identifier=f"{layer}:{key}",
                        specification={"path": value},
                        required=False,
                    ))

        # Parse tech stack
        tech_stack = data.get("tech_stack", {})
        for category, tech in tech_stack.items():
            contract.add_item(ContractItem(
                item_type=ContractItemType.TECH_STACK,
                identifier=category,
                specification={"technology": tech},
                required=False,
            ))

        # Parse dependencies
        for dep in data.get("dependencies", []):
            if isinstance(dep, str):
                contract.add_item(ContractItem(
                    item_type=ContractItemType.DEPENDENCY,
                    identifier=dep,
                    specification={},
                ))
            elif isinstance(dep, dict):
                contract.add_item(ContractItem(
                    item_type=ContractItemType.DEPENDENCY,
                    identifier=dep.get("name", ""),
                    specification=dep,
                ))

        return contract

    def to_dict(self) -> dict[str, Any]:
        """Serialize contract to dictionary."""
        return {
            "contract_id": self.contract_id,
            "items": {k: v.to_dict() for k, v in self._items.items()},
            "implementations": {
                k: [ref.__dict__ for ref in refs]
                for k, refs in self._implementations.items()
            },
        }


class ContractMatcher(ABC):
    """Base class for contract item matchers.

    Matchers determine if a file implements a contract item.
    Different matchers can be implemented for different item types.
    """

    @abstractmethod
    def get_item_type(self) -> ContractItemType:
        """Return the contract item type this matcher handles."""
        ...

    @abstractmethod
    def matches(
        self,
        item: ContractItem,
        file_path: str,
        metadata: FileMetadata,
        content: str | None = None,
    ) -> tuple[bool, float]:
        """Check if a file implements the contract item.

        Returns:
            Tuple of (matches, confidence).
            confidence is 0-1, with 1 being certain match.
        """
        ...


class ApiEndpointMatcher(ContractMatcher):
    """Matcher for API endpoints.

    This is a generic matcher that looks for common patterns.
    Language-specific matchers can be more precise.
    """

    def get_item_type(self) -> ContractItemType:
        return ContractItemType.API_ENDPOINT

    def matches(
        self,
        item: ContractItem,
        file_path: str,
        metadata: FileMetadata,
        content: str | None = None,
    ) -> tuple[bool, float]:
        if not content:
            return False, 0.0

        api_path = item.identifier
        methods = item.specification.get("methods", ["GET"])

        # Look for common route definition patterns
        # This is language-agnostic, looking for the path string
        path_pattern = api_path.replace("{", "").replace("}", "")

        if path_pattern in content:
            # Check for method definitions
            for method in methods:
                method_lower = method.lower()
                # Common patterns: @app.get, .get(, @Get(, @RequestMapping
                method_patterns = [
                    f".{method_lower}(",
                    f"@{method_lower}",
                    f'"{method}"',
                    f"'{method}'",
                    f"method: '{method_lower}'",
                    f'method: "{method_lower}"',
                ]
                for pattern in method_patterns:
                    if pattern.lower() in content.lower():
                        return True, 0.8

            # Path found but method not confirmed
            return True, 0.5

        return False, 0.0


class DataModelMatcher(ContractMatcher):
    """Matcher for data models."""

    def get_item_type(self) -> ContractItemType:
        return ContractItemType.DATA_MODEL

    def matches(
        self,
        item: ContractItem,
        file_path: str,
        metadata: FileMetadata,
        content: str | None = None,
    ) -> tuple[bool, float]:
        if not content:
            return False, 0.0

        model_name = item.identifier
        fields = item.specification.get("fields", [])

        # Look for class/interface/type definition with the model name
        class_patterns = [
            f"class {model_name}",
            f"interface {model_name}",
            f"type {model_name}",
            f"struct {model_name}",
            f"@dataclass\nclass {model_name}",
        ]

        for pattern in class_patterns:
            if pattern in content:
                # Check for fields
                field_matches = 0
                for field_def in fields:
                    field_name = field_def.get("name", "")
                    if field_name and field_name in content:
                        field_matches += 1

                if fields:
                    confidence = field_matches / len(fields)
                else:
                    confidence = 0.7

                return True, confidence

        return False, 0.0


class ContractValidator:
    """Validates implementations against architecture contracts.

    This class checks that all required contract items have
    corresponding implementations in the codebase.
    """

    def __init__(self) -> None:
        self._matchers: dict[ContractItemType, ContractMatcher] = {}
        # Register default matchers
        self.register_matcher(ApiEndpointMatcher())
        self.register_matcher(DataModelMatcher())

    def register_matcher(self, matcher: ContractMatcher) -> None:
        """Register a contract item matcher."""
        self._matchers[matcher.get_item_type()] = matcher

    def validate_contract_internal(
        self,
        contract: ArchitectureContract,
    ) -> ValidationResult:
        """Validate internal consistency of a contract.

        Checks:
        - API endpoints reference defined data models
        - No duplicate definitions
        - Required fields are present
        """
        result = ValidationResult(is_valid=True)

        # Collect all data model names
        models = {
            item.identifier
            for item in contract.get_items_by_type(ContractItemType.DATA_MODEL)
        }

        # Check API endpoints reference valid models
        for endpoint in contract.get_items_by_type(ContractItemType.API_ENDPOINT):
            spec = endpoint.specification

            req_schema = spec.get("request_schema")
            if req_schema and req_schema not in models:
                result.add_issue(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.SCHEMA_MISMATCH,
                    message=f"API endpoint '{endpoint.identifier}' references undefined request schema '{req_schema}'",
                    target=endpoint.identifier,
                    context={"schema": req_schema},
                ))

            res_schema = spec.get("response_schema")
            if res_schema and res_schema not in models:
                result.add_issue(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.SCHEMA_MISMATCH,
                    message=f"API endpoint '{endpoint.identifier}' references undefined response schema '{res_schema}'",
                    target=endpoint.identifier,
                    context={"schema": res_schema},
                ))

        return result

    def validate_implementation(
        self,
        contract: ArchitectureContract,
        file_registry: FileRegistry,
        file_contents: dict[str, str] | None = None,
    ) -> ValidationResult:
        """Validate that contract items are implemented.

        Args:
            contract: The architecture contract to validate against.
            file_registry: Registry of implemented files.
            file_contents: Optional dict of file path -> content for deeper analysis.

        Returns:
            ValidationResult with any issues found.
        """
        result = ValidationResult(is_valid=True)
        file_contents = file_contents or {}

        for item in contract.get_all_items():
            if not item.required:
                continue

            # Get existing implementations
            existing = contract.get_implementations(item.item_type, item.identifier)
            if existing:
                continue  # Already has implementation registered

            # Try to find implementation
            matcher = self._matchers.get(item.item_type)
            if not matcher:
                continue  # No matcher for this type

            found = False
            for path, metadata in file_registry.get_all().items():
                content = file_contents.get(path)
                matches, confidence = matcher.matches(item, path, metadata, content)

                if matches and confidence >= 0.5:
                    found = True
                    contract.register_implementation(
                        item.item_type,
                        item.identifier,
                        path,
                        confidence=confidence,
                    )
                    break

            if not found:
                result.add_issue(ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.MISSING_ENDPOINT
                        if item.item_type == ContractItemType.API_ENDPOINT
                        else IssueCategory.CONTRACT_VIOLATION,
                    message=f"{item.item_type.value} '{item.identifier}' is defined in contract but no implementation found",
                    target=item.identifier,
                    context={"item_type": item.item_type.value},
                ))

        return result

    def validate_blueprint_against_contract(
        self,
        blueprint: dict[str, Any],
        contract: ArchitectureContract,
    ) -> ValidationResult:
        """Validate that a blueprint follows the contract.

        Checks:
        - Planned files align with contract file structure
        - Dependencies match contract requirements
        """
        result = ValidationResult(is_valid=True)

        files_plan = blueprint.get("files_plan", [])
        planned_paths = {f.get("path") for f in files_plan if f.get("path")}

        # Check file structure requirements
        for item in contract.get_items_by_type(ContractItemType.FILE_STRUCTURE):
            expected_path = item.specification.get("path", "")
            if expected_path and item.required:
                # Check if any planned file is in the expected directory
                found = any(
                    p.startswith(expected_path) or expected_path in p
                    for p in planned_paths
                )
                if not found:
                    result.add_issue(ValidationIssue(
                        severity=IssueSeverity.INFO,
                        category=IssueCategory.CONTRACT_VIOLATION,
                        message=f"Contract specifies '{expected_path}' but no matching files in blueprint",
                        target=expected_path,
                    ))

        # Check dependencies
        blueprint_deps = set(blueprint.get("dependencies", []))
        for item in contract.get_items_by_type(ContractItemType.DEPENDENCY):
            if item.identifier not in blueprint_deps:
                result.add_issue(ValidationIssue(
                    severity=IssueSeverity.INFO,
                    category=IssueCategory.MISSING_PACKAGE,
                    message=f"Contract requires dependency '{item.identifier}' but not in blueprint",
                    target=item.identifier,
                ))

        return result


class ContractRegistry:
    """Registry for managing multiple architecture contracts.

    Useful when a project has multiple contracts (e.g., for
    different services or modules).
    """

    def __init__(self) -> None:
        self._contracts: dict[str, ArchitectureContract] = {}

    def register(self, contract: ArchitectureContract) -> None:
        """Register a contract."""
        self._contracts[contract.contract_id] = contract

    def get(self, contract_id: str) -> ArchitectureContract | None:
        """Get a contract by ID."""
        return self._contracts.get(contract_id)

    def get_all(self) -> list[ArchitectureContract]:
        """Get all registered contracts."""
        return list(self._contracts.values())

    def validate_all(
        self,
        file_registry: FileRegistry,
        validator: ContractValidator | None = None,
    ) -> dict[str, ValidationResult]:
        """Validate all contracts against implementations."""
        validator = validator or ContractValidator()
        results = {}

        for contract_id, contract in self._contracts.items():
            result = ValidationResult(is_valid=True)

            # Internal consistency
            internal = validator.validate_contract_internal(contract)
            result.merge(internal)

            # Implementation check
            impl = validator.validate_implementation(contract, file_registry)
            result.merge(impl)

            results[contract_id] = result

        return results
