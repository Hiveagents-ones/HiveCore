# -*- coding: utf-8 -*-
"""Architecture contract generation and formatting.

This module provides:
- Architecture contract generation via LLM
- Contract formatting for agent context
- Integration with ProjectMemory for cross-agent context sharing
"""
from __future__ import annotations

import json
import textwrap
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from agentscope.ones.memory import ProjectMemory


async def generate_architecture_contract(
    llm: Any,
    spec: dict[str, Any],
    *,
    project_memory: "ProjectMemory | None" = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Generate architecture contract for consistent agent interfaces.

    The contract is generated before requirement implementation and includes:
    - API path definitions
    - Data model definitions
    - File structure conventions
    - Frontend-backend interface mapping

    Args:
        llm: LLM model instance
        spec: Requirement specification dict
        verbose: Whether to print debug info

    Returns:
        dict: Architecture contract JSON object
    """
    from ._llm_utils import call_llm_json

    requirements = spec.get("requirements", [])

    prompt = textwrap.dedent(f"""
        你是一位资深架构师。请根据以下需求列表，生成一份统一的架构契约。
        这份契约将作为所有开发 Agent（前端、后端）的共同参考，确保接口一致性。

        【需求列表】
        {json.dumps(requirements, ensure_ascii=False, indent=2)}

        【输出格式】
        请输出 JSON 格式的架构契约：
        {{
            "project_name": "项目名称",
            "file_structure": {{
                "backend": {{
                    "root": "backend",
                    "app_entry": "backend/app/main.py",
                    "routers_dir": "backend/app/routers",
                    "models_dir": "backend/app/models",
                    "schemas_dir": "backend/app/schemas",
                    "database": "backend/app/database.py"
                }},
                "frontend": {{
                    "root": "frontend",
                    "src_dir": "frontend/src",
                    "views_dir": "frontend/src/views",
                    "components_dir": "frontend/src/components",
                    "api_dir": "frontend/src/api"
                }}
            }},
            "api_endpoints": [
                {{
                    "path": "/api/v1/members",
                    "methods": ["GET", "POST"],
                    "description": "会员管理接口",
                    "request_schema": "MemberCreate",
                    "response_schema": "Member"
                }}
            ],
            "data_models": [
                {{
                    "name": "Member",
                    "fields": [
                        {{"name": "id", "type": "int", "description": "主键"}},
                        {{"name": "name", "type": "str", "description": "姓名"}}
                    ]
                }}
            ],
            "frontend_api_mapping": [
                {{
                    "frontend_function": "getMembers",
                    "backend_endpoint": "/api/v1/members",
                    "method": "GET"
                }}
            ],
            "import_conventions": {{
                "backend_router_import": "from .routers import members, courses",
                "backend_db_import": "from .database import engine, Base, get_db"
            }}
        }}

        【重要约束】
        1. 文件结构必须一致：所有需求生成的代码都必须遵循 file_structure 中定义的路径
        2. API 路径必须统一：前端调用的路径必须与后端定义的路径完全一致
        3. 数据模型必须共享：前后端使用相同的字段名和类型
        4. 导入约定必须一致：所有模块的导入路径都遵循 import_conventions

        【API 文件命名约定 - 前后端必须一致】
        后端 Router 文件与前端 API 文件必须使用统一的命名模式：
        - 后端: backend/app/routers/{{resource}}.py（如 members.py, courses.py, coaches.py）
        - 前端: frontend/src/api/{{resource}}.js 或 {{resource}}.ts（如 members.js, courses.js）
        - 命名规则：使用资源的复数形式（members 而非 member，courses 而非 course）
        - 禁止使用：route.py, routes.py, api.js 等模糊命名
        - 前端 API 函数命名：get{{Resource}}s, create{{Resource}}, update{{Resource}}, delete{{Resource}}

        只输出 JSON，不要其他内容。
    """)

    from ._observability import get_logger
    logger = get_logger()

    if verbose:
        logger.debug("[ARCH] 生成架构契约中...")

    try:
        result, _ = await call_llm_json(
            llm,
            [{"role": "user", "content": prompt}],
            temperature=0.25,
            label="architecture_contract",
            verbose=verbose,
        )
        if verbose:
            logger.debug(f"[ARCH] 架构契约生成完成: {len(result.get('api_endpoints', []))} 个 API 端点")

        # Save contract to ProjectMemory for cross-agent context sharing
        if project_memory and result:
            project_memory.import_from_contract(result)
            if verbose:
                logger.debug("[ARCH] 架构契约已写入项目记忆")

        return result
    except Exception as exc:
        if verbose:
            logger.debug(f"[ARCH] 架构契约生成失败: {exc}")
        return {}


def format_architecture_contract(contract: dict[str, Any]) -> str:
    """Format architecture contract as readable context annotation.

    Args:
        contract: Architecture contract dict

    Returns:
        str: Formatted contract text
    """
    if not contract:
        return ""

    parts = ["【架构契约 - 请严格遵循】"]

    # File structure
    file_struct = contract.get("file_structure", {})
    if file_struct:
        parts.append("\n文件结构约定:")
        if "backend" in file_struct:
            be = file_struct["backend"]
            parts.append(f"  后端入口: {be.get('app_entry', 'backend/app/main.py')}")
            parts.append(f"  路由目录: {be.get('routers_dir', 'backend/app/routers')}")
            parts.append(f"  数据库模块: {be.get('database', 'backend/app/database.py')}")
        if "frontend" in file_struct:
            fe = file_struct["frontend"]
            parts.append(f"  前端视图: {fe.get('views_dir', 'frontend/src/views')}")
            parts.append(f"  前端API: {fe.get('api_dir', 'frontend/src/api')}")

    # API endpoints
    endpoints = contract.get("api_endpoints", [])
    if endpoints:
        parts.append("\nAPI 端点定义:")
        for ep in endpoints[:10]:  # Limit count
            methods = ", ".join(ep.get("methods", ["GET"]))
            parts.append(f"  {methods} {ep.get('path', '')} - {ep.get('description', '')}")

    # Import conventions
    imports = contract.get("import_conventions", {})
    if imports:
        parts.append("\n导入约定:")
        for key, value in imports.items():
            parts.append(f"  {key}: {value}")

    # Data models
    models = contract.get("data_models", [])
    if models:
        parts.append("\n数据模型:")
        for model in models[:5]:  # Limit count
            fields = ", ".join([f.get("name", "") for f in model.get("fields", [])[:5]])
            parts.append(f"  {model.get('name', '')}: {fields}")

    return "\n".join(parts)


__all__ = [
    "generate_architecture_contract",
    "format_architecture_contract",
]
