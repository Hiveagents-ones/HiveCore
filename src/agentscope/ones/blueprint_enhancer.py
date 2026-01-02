# -*- coding: utf-8 -*-
"""Blueprint Enhancer for improved code generation (language agnostic).

This module provides a generic blueprint enhancement mechanism that uses
Agent manifest configurations. It maps acceptance criteria to specific
functions/APIs that must be implemented, ensuring no functionality is missed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from .._logging import logger

if TYPE_CHECKING:
    from .manifest import AgentManifest, BlueprintConfig
    from .intent import AcceptanceCriteria


@dataclass
class RequiredFunction:
    """A function/method that must be implemented.

    Attributes:
        name (`str`):
            The function name.
        file_path (`str`):
            Suggested file path for this function.
        signature (`str`):
            Function signature (language-specific).
        criteria_id (`str`):
            The acceptance criteria ID this fulfills.
        description (`str`):
            Description of what this function should do.
        logic_points (`list[str]`):
            Key logic points to implement.
    """

    name: str
    file_path: str = ""
    signature: str = ""
    criteria_id: str = ""
    description: str = ""
    logic_points: list[str] = field(default_factory=list)


@dataclass
class EnhancedBlueprint:
    """An enhanced blueprint with explicit function requirements.

    Attributes:
        original_blueprint (`dict`):
            The original blueprint data.
        required_functions (`list[RequiredFunction]`):
            Functions that must be implemented.
        file_structure (`dict[str, list[str]]`):
            Mapping of file paths to function names.
        entity_map (`dict[str, str]`):
            Mapping of entity names to their types.
        validation_points (`list[str]`):
            Points to validate during QA.
    """

    original_blueprint: dict[str, Any] = field(default_factory=dict)
    required_functions: list[RequiredFunction] = field(default_factory=list)
    file_structure: dict[str, list[str]] = field(default_factory=dict)
    entity_map: dict[str, str] = field(default_factory=dict)
    validation_points: list[str] = field(default_factory=list)

    def get_functions_for_file(self, file_path: str) -> list[RequiredFunction]:
        """Get all required functions for a specific file."""
        return [f for f in self.required_functions if f.file_path == file_path]

    def get_functions_for_criteria(self, criteria_id: str) -> list[RequiredFunction]:
        """Get all required functions for a specific criteria."""
        return [f for f in self.required_functions if f.criteria_id == criteria_id]

    def to_prompt_section(self) -> str:
        """Generate a prompt section describing required functions."""
        if not self.required_functions:
            return ""

        lines = ["## 必须实现的函数/API"]
        for func in self.required_functions:
            lines.append(f"\n### {func.name}")
            if func.file_path:
                lines.append(f"文件: `{func.file_path}`")
            if func.signature:
                lines.append(f"签名: `{func.signature}`")
            if func.criteria_id:
                lines.append(f"验收标准: {func.criteria_id}")
            if func.description:
                lines.append(f"描述: {func.description}")
            if func.logic_points:
                lines.append("关键逻辑:")
                for point in func.logic_points:
                    lines.append(f"  - {point}")

        return "\n".join(lines)


class BlueprintEnhancer:
    """Generic blueprint enhancer using manifest configuration.

    This enhancer analyzes requirements and acceptance criteria to generate
    explicit function/API requirements. It uses patterns defined in the
    Agent manifest to ensure completeness.

    Example usage:
        ```python
        enhancer = BlueprintEnhancer(manifest)

        # Classify the requirement type
        req_type = enhancer.classify_requirement(requirement)

        # Extract entity names
        entities = enhancer.extract_entities(requirement)

        # Generate required functions based on patterns
        functions = enhancer.generate_required_functions(req_type, entities, criteria)

        # Create enhanced blueprint
        enhanced = enhancer.enhance_blueprint(original_blueprint, functions)
        ```
    """

    # Default requirement type patterns (can be overridden by manifest)
    DEFAULT_TYPE_PATTERNS = {
        "crud": [
            r"管理",
            r"增删改查",
            r"CRUD",
            r"create.*read.*update.*delete",
        ],
        "auth": [
            r"认证",
            r"授权",
            r"登录",
            r"注册",
            r"authentication",
            r"authorization",
        ],
        "list": [
            r"列表",
            r"查询",
            r"搜索",
            r"list",
            r"query",
        ],
        "status": [
            r"状态",
            r"激活",
            r"暂停",
            r"status",
            r"activate",
            r"suspend",
        ],
        "log": [
            r"日志",
            r"记录",
            r"历史",
            r"log",
            r"history",
        ],
    }

    # Default function patterns per requirement type
    DEFAULT_FUNCTION_PATTERNS = {
        "crud": [
            "create_{entity}",
            "get_{entity}",
            "get_{entity}_list",
            "update_{entity}",
            "delete_{entity}",
        ],
        "auth": [
            "login",
            "logout",
            "register",
            "get_current_user",
            "refresh_token",
        ],
        "status": [
            "activate_{entity}",
            "suspend_{entity}",
            "get_{entity}_status",
            "update_{entity}_status",
        ],
        "log": [
            "log_{entity}_operation",
            "get_{entity}_history",
        ],
    }

    def __init__(self, manifest: "AgentManifest"):
        """Initialize the blueprint enhancer.

        Args:
            manifest: The agent manifest containing blueprint configuration.
        """
        self.manifest = manifest
        self.bp_config = manifest.blueprint_config

    def classify_requirement(self, requirement: str) -> list[str]:
        """Classify a requirement into types based on patterns.

        Args:
            requirement: The requirement description.

        Returns:
            List of matching requirement types.
        """
        types: list[str] = []
        patterns = self.DEFAULT_TYPE_PATTERNS.copy()

        # Merge with manifest patterns if available
        if self.bp_config and self.bp_config.required_patterns:
            # If manifest has patterns, use them to infer types
            for req_type in self.bp_config.required_patterns:
                if req_type not in patterns:
                    patterns[req_type] = []

        for req_type, type_patterns in patterns.items():
            for pattern in type_patterns:
                if re.search(pattern, requirement, re.IGNORECASE):
                    if req_type not in types:
                        types.append(req_type)
                    break

        return types if types else ["crud"]  # Default to crud

    def extract_entities(self, requirement: str) -> list[str]:
        """Extract entity names from a requirement.

        Args:
            requirement: The requirement description.

        Returns:
            List of entity names.
        """
        entities: list[str] = []

        # Common entity patterns
        patterns = [
            r"(会员|用户|课程|预约|订单|商品|卡)",  # Chinese
            r"(member|user|course|reservation|order|product|card)",  # English
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, requirement, re.IGNORECASE):
                entity = match.group(1).lower()
                # Normalize Chinese to English
                entity_map = {
                    "会员": "member",
                    "用户": "user",
                    "课程": "course",
                    "预约": "reservation",
                    "订单": "order",
                    "商品": "product",
                    "卡": "card",
                }
                entity = entity_map.get(entity, entity)
                if entity not in entities:
                    entities.append(entity)

        return entities if entities else ["item"]

    def generate_required_functions(
        self,
        req_types: list[str],
        entities: list[str],
        criteria: list["AcceptanceCriteria"] | None = None,
    ) -> list[RequiredFunction]:
        """Generate required functions based on types, entities, and criteria.

        Args:
            req_types: List of requirement types.
            entities: List of entity names.
            criteria: Optional list of acceptance criteria.

        Returns:
            List of required functions.
        """
        functions: list[RequiredFunction] = []
        seen: set[str] = set()

        # Get patterns from manifest or defaults
        all_patterns: dict[str, list[str]] = self.DEFAULT_FUNCTION_PATTERNS.copy()
        if self.bp_config and self.bp_config.required_patterns:
            all_patterns.update(self.bp_config.required_patterns)

        # Generate functions for each type and entity
        for req_type in req_types:
            patterns = all_patterns.get(req_type, [])
            for pattern in patterns:
                for entity in entities:
                    func_name = pattern.format(entity=entity)
                    if func_name in seen:
                        continue
                    seen.add(func_name)

                    functions.append(RequiredFunction(
                        name=func_name,
                        description=f"{req_type.upper()} operation for {entity}",
                    ))

        # Add functions from criteria if provided
        if criteria:
            for criterion in criteria:
                funcs = self._extract_functions_from_criterion(criterion, entities)
                for func in funcs:
                    if func.name not in seen:
                        seen.add(func.name)
                        functions.append(func)

        return functions

    def _extract_functions_from_criterion(
        self,
        criterion: "AcceptanceCriteria",
        entities: list[str],
    ) -> list[RequiredFunction]:
        """Extract required functions from a single criterion.

        Args:
            criterion: An acceptance criterion.
            entities: List of entity names.

        Returns:
            List of required functions.
        """
        functions: list[RequiredFunction] = []
        description = criterion.description

        # Pattern matching for common functionality
        func_patterns = [
            (r"创建|新增|添加", "create"),
            (r"查询|获取|读取|列表", "get"),
            (r"更新|修改|编辑", "update"),
            (r"删除|移除", "delete"),
            (r"激活", "activate"),
            (r"暂停|冻结", "suspend"),
            (r"续费|延期", "renew"),
            (r"注销|关闭", "cancel"),
            (r"日志|记录", "log"),
            (r"验证|检查|校验", "validate"),
        ]

        for pattern, action in func_patterns:
            if re.search(pattern, description, re.IGNORECASE):
                for entity in entities:
                    func_name = f"{action}_{entity}"
                    logic_points = self._extract_logic_points(description)

                    functions.append(RequiredFunction(
                        name=func_name,
                        criteria_id=criterion.id if hasattr(criterion, "id") else "",
                        description=description[:100],
                        logic_points=logic_points,
                    ))
                break

        return functions

    def _extract_logic_points(self, description: str) -> list[str]:
        """Extract key logic points from a description.

        Args:
            description: The criterion description.

        Returns:
            List of logic points.
        """
        points: list[str] = []

        # Look for enumerated items
        for match in re.finditer(r"[、,，]\s*([^、,，。]+)", description):
            point = match.group(1).strip()
            if len(point) > 2 and len(point) < 50:
                points.append(point)

        # Look for parenthetical items
        for match in re.finditer(r"[（(]([^）)]+)[）)]", description):
            items = match.group(1).split("、")
            points.extend(item.strip() for item in items if len(item.strip()) > 1)

        return points[:5]  # Limit to 5 points

    def enhance_blueprint(
        self,
        original: dict[str, Any],
        required_functions: list[RequiredFunction],
    ) -> EnhancedBlueprint:
        """Enhance a blueprint with explicit function requirements.

        Args:
            original: The original blueprint dict.
            required_functions: List of required functions.

        Returns:
            EnhancedBlueprint with added requirements.
        """
        enhanced = EnhancedBlueprint(
            original_blueprint=original,
            required_functions=required_functions,
        )

        # Build file structure from manifest patterns
        if self.bp_config and self.bp_config.file_patterns:
            for func in required_functions:
                for pattern_key, pattern_value in self.bp_config.file_patterns.items():
                    if pattern_key in func.name:
                        func.file_path = pattern_value.format(
                            entity=func.name.split("_")[-1]
                        )
                        break

        # Group functions by file
        for func in required_functions:
            if func.file_path:
                if func.file_path not in enhanced.file_structure:
                    enhanced.file_structure[func.file_path] = []
                enhanced.file_structure[func.file_path].append(func.name)

        return enhanced

    def build_enhanced_prompt(
        self,
        requirement: str,
        criteria: list["AcceptanceCriteria"],
        enhanced: EnhancedBlueprint,
    ) -> str:
        """Build an enhanced generation prompt.

        Args:
            requirement: The original requirement.
            criteria: List of acceptance criteria.
            enhanced: The enhanced blueprint.

        Returns:
            Enhanced prompt for code generation.
        """
        # Get extraction prompt from manifest or use default
        extraction_prompt = ""
        if self.bp_config and self.bp_config.function_extraction_prompt:
            extraction_prompt = self.bp_config.function_extraction_prompt

        prompt = f"""## 需求
{requirement}

## 验收标准
"""
        for i, c in enumerate(criteria, 1):
            desc = c.description if hasattr(c, "description") else str(c)
            prompt += f"{i}. {desc}\n"

        prompt += f"""
{enhanced.to_prompt_section()}

## 生成要求
1. 必须实现上述所有函数/API
2. 每个函数必须满足对应的验收标准
3. 确保函数签名与描述一致
4. 实现所有关键逻辑点

"""

        if extraction_prompt:
            prompt += f"""## 特殊说明
{extraction_prompt}
"""

        return prompt

    async def analyze_and_enhance(
        self,
        requirement: str,
        criteria: list["AcceptanceCriteria"],
        original_blueprint: dict[str, Any] | None = None,
    ) -> EnhancedBlueprint:
        """Analyze requirement and create enhanced blueprint.

        This is the main entry point for blueprint enhancement.

        Args:
            requirement: The requirement description.
            criteria: List of acceptance criteria.
            original_blueprint: Optional original blueprint to enhance.

        Returns:
            EnhancedBlueprint with all requirements.
        """
        # Classify requirement
        req_types = self.classify_requirement(requirement)
        logger.debug("[BlueprintEnhancer] Requirement types: %s", req_types)

        # Extract entities
        entities = self.extract_entities(requirement)
        logger.debug("[BlueprintEnhancer] Entities: %s", entities)

        # Generate required functions
        functions = self.generate_required_functions(req_types, entities, criteria)
        logger.debug(
            "[BlueprintEnhancer] Generated %d required functions",
            len(functions),
        )

        # Enhance blueprint
        enhanced = self.enhance_blueprint(
            original_blueprint or {},
            functions,
        )

        return enhanced
