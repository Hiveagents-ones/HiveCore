# HiveCore 系统改进方案

## 一、问题诊断

### 1.1 根本原因

经过对生成代码的部署验证，发现以下系统性问题：

| 问题类型 | 具体表现 | 根本原因 |
|---------|---------|---------|
| 路由引用不存在的组件 | `router/index.js` 引用 `ProfileView.vue` 但文件不存在 | Agent 之间没有共享实际生成的文件列表 |
| API 命名不一致 | `member.js` vs `members` | 没有强制的命名契约 |
| 缺少依赖包 | `unplugin-auto-import` 未在 package.json | 没有追踪组件实际使用的包 |
| 后端导入不存在模块 | `from fastapi.metrics import metrics` | 没有验证 import 语句的有效性 |

### 1.2 架构缺陷

```
当前信息流（单向，无验证）：
ArchitectAgent → BackendAgent → FrontendAgent → QAAgent
     ↓               ↓               ↓              ↓
  声明契约        实现(可能偏离)   假设契约存在    事后发现问题

期望信息流（双向，有验证）：
ArchitectAgent ←→ BackendAgent ←→ FrontendAgent ←→ QAAgent
     ↓               ↓               ↓               ↓
  定义契约     验证→实现→注册   验证→使用→注册   实时验证
```

---

## 二、改进方案概览

### 2.1 三层验证机制

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: 文件注册追踪 (File Registry)                      │
│  - 自动追踪生成的每个文件                                    │
│  - 记录文件来源 Agent 和时间戳                               │
│  - 支持文件变更历史审计                                      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: 依赖验证系统 (Dependency Validation)              │
│  - 验证 import 路径是否指向已注册的文件                      │
│  - 验证 npm/pip 依赖版本一致性                               │
│  - 检测循环依赖和缺失依赖                                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: 契约一致性检查 (Contract Validation)              │
│  - 验证 Blueprint 是否遵循 ArchitectAgent 契约              │
│  - 验证 API 端点实际存在且签名匹配                           │
│  - 验证数据模型在前后端一致                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、详细设计

### 3.1 自动文件注册机制

#### 3.1.1 扩展 ProjectMemory

**文件**: `src/agentscope/ones/memory.py`

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import hashlib

@dataclass
class FileRecord:
    """文件注册记录"""
    path: str
    description: str
    created_by: str  # Agent ID
    created_at: datetime
    content_hash: str  # SHA256 of content
    dependencies: list[str] = field(default_factory=list)  # 引用的其他文件
    exports: list[str] = field(default_factory=list)  # 导出的符号
    imports: list[str] = field(default_factory=list)  # 导入的符号

class ProjectMemory:
    def __init__(self, ...):
        # 现有代码...
        self._file_records: dict[str, FileRecord] = {}  # 新增

    def register_file_with_metadata(
        self,
        path: str,
        content: str,
        description: str,
        created_by: str,
        dependencies: list[str] | None = None,
        exports: list[str] | None = None,
        imports: list[str] | None = None,
    ) -> FileRecord:
        """注册文件并提取元数据"""
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # 自动提取 imports/exports (如果未提供)
        if imports is None:
            imports = self._extract_imports(path, content)
        if exports is None:
            exports = self._extract_exports(path, content)

        record = FileRecord(
            path=path,
            description=description,
            created_by=created_by,
            created_at=datetime.now(),
            content_hash=content_hash,
            dependencies=dependencies or [],
            exports=exports,
            imports=imports,
        )

        self._file_records[path] = record
        self._save()
        return record

    def _extract_imports(self, path: str, content: str) -> list[str]:
        """从文件内容提取 import 语句"""
        imports = []

        if path.endswith(('.js', '.ts', '.vue', '.jsx', '.tsx')):
            # JavaScript/TypeScript imports
            import re
            patterns = [
                r"import\s+.*?\s+from\s+['\"](.+?)['\"]",
                r"import\s*\(['\"](.+?)['\"]\)",
                r"require\s*\(['\"](.+?)['\"]\)",
            ]
            for pattern in patterns:
                imports.extend(re.findall(pattern, content))

        elif path.endswith('.py'):
            # Python imports
            import re
            patterns = [
                r"from\s+(\S+)\s+import",
                r"import\s+(\S+)",
            ]
            for pattern in patterns:
                imports.extend(re.findall(pattern, content))

        return imports

    def _extract_exports(self, path: str, content: str) -> list[str]:
        """从文件内容提取导出的符号"""
        exports = []

        if path.endswith(('.js', '.ts', '.vue', '.jsx', '.tsx')):
            import re
            patterns = [
                r"export\s+(?:default\s+)?(?:class|function|const|let|var)\s+(\w+)",
                r"export\s+\{\s*(.+?)\s*\}",
            ]
            for pattern in patterns:
                matches = re.findall(pattern, content)
                for m in matches:
                    if isinstance(m, str):
                        exports.extend([x.strip() for x in m.split(',')])

        elif path.endswith('.py'):
            import re
            # Python: class, def, and __all__
            patterns = [
                r"^class\s+(\w+)",
                r"^def\s+(\w+)",
                r"^(\w+)\s*=",
            ]
            for pattern in patterns:
                exports.extend(re.findall(pattern, content, re.MULTILINE))

        return exports

    def get_file_record(self, path: str) -> FileRecord | None:
        """获取文件记录"""
        return self._file_records.get(path)

    def get_all_file_records(self) -> dict[str, FileRecord]:
        """获取所有文件记录"""
        return dict(self._file_records)

    def validate_import_path(self, from_file: str, import_path: str) -> bool:
        """验证 import 路径是否指向已注册的文件"""
        # 处理相对路径
        if import_path.startswith('.'):
            from pathlib import Path
            base_dir = Path(from_file).parent
            resolved = (base_dir / import_path).resolve()
            # 尝试多种扩展名
            for ext in ['', '.js', '.ts', '.vue', '.jsx', '.tsx', '/index.js', '/index.ts']:
                candidate = str(resolved) + ext
                if candidate in self._file_records:
                    return True
            return False

        # npm 包或绝对路径 - 假设有效
        return True
```

#### 3.1.2 集成到执行流程

**文件**: `src/agentscope/scripts/_execution.py`

在文件写入后添加注册：

```python
# 在 run_execution 函数中，文件写入后 (约第 534 行)
for file_info in files_list:
    file_path = file_info.get("path", "")
    file_content = file_info.get("content", "")
    if not file_path:
        continue

    full_path = workspace_dir / file_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(str(file_content), encoding="utf-8")
    written_files.append(file_path)
    observer.on_file_written(rid, file_path)

    # ✅ 新增：注册文件到 ProjectMemory
    if project_memory:
        project_memory.register_file_with_metadata(
            path=file_path,
            content=str(file_content),
            description=file_info.get("description", "Generated file"),
            created_by=f"requirement_{rid}",
            dependencies=file_info.get("dependencies", []),
        )
```

---

### 3.2 依赖验证系统

#### 3.2.1 新建验证模块

**文件**: `src/agentscope/scripts/_dependency_validator.py`

```python
"""
依赖验证模块

验证层次：
1. 文件级依赖 - import 路径是否指向存在的文件
2. 包级依赖 - npm/pip 包是否在依赖声明中
3. 符号级依赖 - 导入的符号是否被目标文件导出
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any
import re

class DependencyType(Enum):
    FILE = "file"           # 本地文件
    PACKAGE = "package"     # npm/pip 包
    SYMBOL = "symbol"       # 导出的符号

class ConflictSeverity(Enum):
    ERROR = "error"         # 必须修复
    WARNING = "warning"     # 建议修复
    INFO = "info"           # 仅供参考

@dataclass
class DependencyIssue:
    """依赖问题"""
    severity: ConflictSeverity
    issue_type: str
    source_file: str
    target: str
    message: str
    suggestion: str | None = None

class DependencyValidator:
    """依赖验证器"""

    def __init__(self, project_memory: "ProjectMemory"):
        self.memory = project_memory

    def validate_all(self) -> list[DependencyIssue]:
        """验证所有已注册文件的依赖"""
        issues = []

        for path, record in self.memory.get_all_file_records().items():
            issues.extend(self.validate_file(path, record))

        return issues

    def validate_file(self, path: str, record: "FileRecord") -> list[DependencyIssue]:
        """验证单个文件的依赖"""
        issues = []

        for import_path in record.imports:
            # 跳过外部包
            if not import_path.startswith('.') and not import_path.startswith('@/'):
                continue

            # 验证本地 import
            if not self.memory.validate_import_path(path, import_path):
                issues.append(DependencyIssue(
                    severity=ConflictSeverity.ERROR,
                    issue_type="missing_file",
                    source_file=path,
                    target=import_path,
                    message=f"导入的文件不存在: {import_path}",
                    suggestion=self._suggest_similar_file(import_path),
                ))

        return issues

    def _suggest_similar_file(self, import_path: str) -> str | None:
        """建议相似的文件路径"""
        from difflib import get_close_matches

        # 提取文件名
        filename = import_path.split('/')[-1]

        # 在已注册文件中查找相似的
        all_files = list(self.memory.get_all_file_records().keys())
        all_filenames = [f.split('/')[-1] for f in all_files]

        matches = get_close_matches(filename, all_filenames, n=1, cutoff=0.6)
        if matches:
            # 找到完整路径
            for f in all_files:
                if f.endswith(matches[0]):
                    return f"建议使用: {f}"

        return None

    def validate_package_dependencies(
        self,
        declared_deps: dict[str, str],  # {package: version}
        used_imports: list[str],
    ) -> list[DependencyIssue]:
        """验证包依赖是否声明"""
        issues = []

        # 常见的包名映射
        package_aliases = {
            "element-plus": ["el-", "ElMessage", "ElButton"],
            "vue": ["ref", "reactive", "computed", "watch", "onMounted"],
            "vue-router": ["useRouter", "useRoute", "RouterView", "RouterLink"],
            "pinia": ["defineStore", "storeToRefs"],
            "axios": ["axios"],
        }

        for import_name in used_imports:
            # 跳过本地导入
            if import_name.startswith('.') or import_name.startswith('@/'):
                continue

            # 检查是否已声明
            if import_name not in declared_deps:
                # 检查是否是已声明包的子模块
                is_submodule = False
                for pkg in declared_deps:
                    if import_name.startswith(pkg + '/'):
                        is_submodule = True
                        break

                if not is_submodule:
                    issues.append(DependencyIssue(
                        severity=ConflictSeverity.WARNING,
                        issue_type="undeclared_package",
                        source_file="package.json / requirements.txt",
                        target=import_name,
                        message=f"使用了未声明的包: {import_name}",
                        suggestion=f"请在依赖中添加 {import_name}",
                    ))

        return issues


def validate_before_generation(
    blueprint: dict[str, Any],
    project_memory: "ProjectMemory",
) -> list[DependencyIssue]:
    """在生成前验证 Blueprint 的依赖声明"""
    issues = []

    files_plan = blueprint.get("files_plan", [])

    # 收集所有声明的依赖
    all_deps = set()
    file_paths = set()

    for file_plan in files_plan:
        file_paths.add(file_plan.get("path", ""))
        for dep in file_plan.get("dependencies", []):
            all_deps.add(dep)

    # 验证依赖是否在文件计划中
    for dep in all_deps:
        if dep.startswith('./') or dep.startswith('../'):
            # 相对路径依赖 - 检查是否在计划中
            # 简化：只检查文件名匹配
            dep_filename = dep.split('/')[-1]
            found = False
            for fp in file_paths:
                if fp.endswith(dep_filename) or fp.endswith(dep_filename + '.vue') or fp.endswith(dep_filename + '.js'):
                    found = True
                    break

            if not found:
                issues.append(DependencyIssue(
                    severity=ConflictSeverity.WARNING,
                    issue_type="missing_in_plan",
                    source_file="blueprint.files_plan",
                    target=dep,
                    message=f"依赖 {dep} 不在文件生成计划中",
                ))

    return issues
```

#### 3.2.2 集成到生成流程

**文件**: `src/agentscope/scripts/_agent_roles.py`

```python
# 在 stepwise_generate_files 开始时 (约第 660 行)
async def stepwise_generate_files(
    llm: Any,
    requirement: dict[str, Any],
    blueprint: dict[str, Any],
    contextual_notes: str | None = None,
    runtime_workspace: "RuntimeWorkspace | None" = None,
    feedback: str = "",
    failed_criteria: list[dict[str, Any]] | None = None,
    previous_errors: list[str] | None = None,
    project_memory: "ProjectMemory | None" = None,  # ✅ 新增参数
    *,
    verbose: bool = False,
) -> dict[str, Any]:
    files_plan = blueprint.get("files_plan", [])
    if not files_plan:
        raise ValueError("Blueprint 缺少 files_plan 字段")

    # ✅ 新增：生成前依赖验证
    if project_memory:
        from ._dependency_validator import validate_before_generation
        pre_issues = validate_before_generation(blueprint, project_memory)
        if pre_issues:
            error_issues = [i for i in pre_issues if i.severity == ConflictSeverity.ERROR]
            if error_issues:
                raise ValueError(
                    f"Blueprint 依赖验证失败:\n" +
                    "\n".join(f"- {i.message}" for i in error_issues)
                )
            # 警告级别问题记录但继续
            for issue in pre_issues:
                logger.warning(f"依赖警告: {issue.message}")

    # 继续现有逻辑...
```

---

### 3.3 契约一致性检查

#### 3.3.1 契约验证模块

**文件**: `src/agentscope/scripts/_contract_validator.py`

```python
"""
架构契约验证模块

验证层次：
1. 契约内部一致性 - API 与数据模型的引用关系
2. 契约与实现一致性 - 实际代码是否遵循契约
3. 历史一致性 - 新契约是否与历史决策冲突
"""

from dataclasses import dataclass
from typing import Any
import re

@dataclass
class ContractViolation:
    """契约违规"""
    violation_type: str
    severity: str  # "error", "warning"
    contract_item: str
    actual_item: str | None
    message: str
    file_path: str | None = None

class ContractValidator:
    """契约验证器"""

    def __init__(
        self,
        architecture_contract: dict[str, Any],
        project_memory: "ProjectMemory",
    ):
        self.contract = architecture_contract
        self.memory = project_memory

    def validate_internal_consistency(self) -> list[ContractViolation]:
        """验证契约内部一致性"""
        violations = []

        # 收集所有数据模型
        models = {m.get("name"): m for m in self.contract.get("data_models", [])}

        # 验证 API 引用的模型是否存在
        for endpoint in self.contract.get("api_endpoints", []):
            path = endpoint.get("path", "")

            req_schema = endpoint.get("request_schema")
            if req_schema and req_schema not in models:
                violations.append(ContractViolation(
                    violation_type="undefined_model",
                    severity="error",
                    contract_item=f"API {path}",
                    actual_item=req_schema,
                    message=f"API {path} 引用了未定义的请求模型: {req_schema}",
                ))

            res_schema = endpoint.get("response_schema")
            if res_schema and res_schema not in models:
                violations.append(ContractViolation(
                    violation_type="undefined_model",
                    severity="error",
                    contract_item=f"API {path}",
                    actual_item=res_schema,
                    message=f"API {path} 引用了未定义的响应模型: {res_schema}",
                ))

        return violations

    def validate_implementation(self) -> list[ContractViolation]:
        """验证实现是否遵循契约"""
        violations = []

        # 获取所有已注册的文件
        files = self.memory.get_all_file_records()

        # 检查后端路由文件是否实现了契约中的 API
        backend_files = {k: v for k, v in files.items() if 'backend' in k and 'router' in k}

        for endpoint in self.contract.get("api_endpoints", []):
            path = endpoint.get("path", "")
            methods = endpoint.get("methods", ["GET"])

            # 简化检查：在后端代码中搜索路由定义
            found = False
            for file_path, record in backend_files.items():
                # 这里需要实际读取文件内容
                # 简化：假设如果文件存在且名称匹配，则认为实现了
                route_name = path.split('/')[-1] if '/' in path else path
                if route_name in file_path or route_name.replace('-', '_') in file_path:
                    found = True
                    break

            if not found:
                violations.append(ContractViolation(
                    violation_type="missing_implementation",
                    severity="warning",
                    contract_item=f"{methods} {path}",
                    actual_item=None,
                    message=f"契约中定义的 API {path} 可能未实现",
                ))

        return violations

    def validate_against_blueprint(
        self,
        blueprint: dict[str, Any],
    ) -> list[ContractViolation]:
        """验证 Blueprint 是否遵循契约"""
        violations = []

        files_plan = blueprint.get("files_plan", [])

        # 检查文件结构是否符合契约
        expected_structure = self.contract.get("file_structure", {})

        if expected_structure.get("frontend"):
            fe = expected_structure["frontend"]
            views_dir = fe.get("views_dir", "frontend/src/views")

            # 检查是否有视图文件在正确目录
            view_files = [f for f in files_plan if views_dir in f.get("path", "")]
            if not view_files:
                violations.append(ContractViolation(
                    violation_type="structure_mismatch",
                    severity="warning",
                    contract_item=f"views_dir: {views_dir}",
                    actual_item=None,
                    message=f"Blueprint 中没有符合契约目录结构的视图文件",
                ))

        return violations


def validate_architecture_contract(
    contract: dict[str, Any],
    project_memory: "ProjectMemory",
) -> tuple[bool, list[ContractViolation]]:
    """验证架构契约"""
    validator = ContractValidator(contract, project_memory)

    violations = []
    violations.extend(validator.validate_internal_consistency())
    violations.extend(validator.validate_implementation())

    errors = [v for v in violations if v.severity == "error"]
    is_valid = len(errors) == 0

    return is_valid, violations
```

#### 3.3.2 集成到架构生成后

**文件**: `src/agentscope/scripts/_execution.py`

```python
# 在 generate_architecture_contract 调用后 (约第 178 行)
if architecture_contract:
    contract_text = format_architecture_contract(architecture_contract)
    if contract_text:
        contextual_notes = contract_text + "\n\n" + contextual_notes if contextual_notes else contract_text
        observer.on_architecture_complete(len(architecture_contract.get("api_endpoints", [])))

    # ✅ 新增：验证契约一致性
    if project_memory:
        from ._contract_validator import validate_architecture_contract
        is_valid, violations = validate_architecture_contract(
            architecture_contract,
            project_memory
        )

        if violations:
            for v in violations:
                if v.severity == "error":
                    observer.on_contract_error(v.message)
                else:
                    observer.on_contract_warning(v.message)

        if not is_valid:
            raise ValueError(
                "架构契约验证失败:\n" +
                "\n".join(f"- {v.message}" for v in violations if v.severity == "error")
            )
```

---

## 四、执行流程改进

### 4.1 改进后的执行流程

```
┌─────────────────────────────────────────────────────────────┐
│  1. 需求收集 (Specification Collection)                     │
│     └─ 输出: requirements, acceptance_criteria              │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  2. 架构设计 (Architecture Contract)                        │
│     ├─ 输出: api_endpoints, data_models, file_structure     │
│     └─ ✅ 新增: validate_internal_consistency()             │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Blueprint 设计 (Design Requirement)                     │
│     ├─ 输出: files_plan, generation_mode, dependencies      │
│     └─ ✅ 新增: validate_against_contract()                 │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  4. 依赖预验证 (Pre-generation Validation)                  │
│     ├─ ✅ 新增: validate_before_generation()                │
│     └─ 如果有 ERROR 级别问题，终止生成                       │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  5. 分步生成 (Stepwise Generation)                          │
│     ├─ 按依赖顺序生成文件                                    │
│     ├─ ✅ 新增: 每个文件生成后 register_file_with_metadata() │
│     └─ ✅ 新增: 实时验证 import 路径                         │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  6. 后验证 (Post-generation Validation)                     │
│     ├─ 现有: static_validation, import_validation           │
│     ├─ ✅ 新增: validate_all_dependencies()                 │
│     └─ ✅ 新增: validate_implementation()                   │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  7. QA 验收 (QA Acceptance)                                 │
│     ├─ 现有: 运行测试、浏览器沙盒                            │
│     └─ ✅ 新增: 契约合规报告                                 │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 反馈循环改进

当验证失败时，提供结构化的反馈：

```python
@dataclass
class RoundFeedback:
    """每轮执行后的结构化反馈"""
    requirement_id: str
    round_index: int

    # 验证结果
    dependency_issues: list[DependencyIssue]
    contract_violations: list[ContractViolation]
    validation_errors: list[str]

    # 生成统计
    files_generated: int
    files_registered: int

    def build_feedback_prompt(self) -> str:
        """构建给下一轮的反馈提示"""
        lines = []

        if self.dependency_issues:
            lines.append("## 依赖问题（必须修复）")
            for issue in self.dependency_issues:
                lines.append(f"- [{issue.severity.value}] {issue.message}")
                if issue.suggestion:
                    lines.append(f"  建议: {issue.suggestion}")

        if self.contract_violations:
            lines.append("\n## 契约违规")
            for v in self.contract_violations:
                lines.append(f"- [{v.severity}] {v.message}")

        if self.validation_errors:
            lines.append("\n## 代码验证错误")
            for err in self.validation_errors[:10]:
                lines.append(f"- {err}")

        return "\n".join(lines)
```

---

## 五、实施计划

### 5.1 阶段一：文件注册追踪（预计 2-3 小时）

**目标**: 让系统能够追踪每个生成的文件

**任务**:
1. 扩展 `ProjectMemory` 添加 `FileRecord` 数据结构
2. 添加 `register_file_with_metadata()` 方法
3. 在 `_execution.py` 文件写入后调用注册
4. 更新 `.project_memory.json` 持久化格式

**验证**: 运行生成后检查 `.project_memory.json` 包含所有文件记录

### 5.2 阶段二：依赖验证系统（预计 3-4 小时）

**目标**: 在生成前后验证依赖关系

**任务**:
1. 创建 `_dependency_validator.py` 模块
2. 实现 `validate_before_generation()`
3. 实现 `validate_all()` 后验证
4. 集成到 `stepwise_generate_files` 和执行循环

**验证**: 故意引入错误的 import 路径，检查是否被检测

### 5.3 阶段三：契约一致性检查（预计 4-5 小时）

**目标**: 确保实现遵循架构契约

**任务**:
1. 创建 `_contract_validator.py` 模块
2. 实现契约内部一致性验证
3. 实现 Blueprint vs 契约验证
4. 实现实现 vs 契约验证
5. 集成到架构生成和 Blueprint 设计后

**验证**: 创建与契约冲突的 Blueprint，检查是否被拒绝

### 5.4 阶段四：结构化反馈（预计 2-3 小时）

**目标**: 让失败反馈更有针对性

**任务**:
1. 创建 `RoundFeedback` 数据结构
2. 在每轮执行后收集所有验证结果
3. 改进 `build_feedback_prompt()` 使用结构化信息
4. 更新 Observer 接口支持详细报告

**验证**: 检查失败轮次的反馈是否包含具体修复建议

---

## 六、预期效果

### 6.1 问题解决对照

| 原问题 | 改进后 |
|-------|-------|
| 路由引用不存在的组件 | 生成时验证 import 路径，不存在则报错 |
| API 命名不一致 | 契约定义统一命名，验证实现一致性 |
| 缺少依赖包 | 自动提取 import，与 package.json 对比 |
| 后端导入不存在模块 | Python import 验证，检测不存在的模块 |

### 6.2 质量指标

改进后预期：
- 文件引用错误检测率: **>95%**
- 依赖缺失检测率: **>90%**
- 契约违规检测率: **>85%**
- 部署成功率: 从 **~30%** 提升到 **>80%**

---

## 七、后续优化方向

1. **符号级验证**: 不仅验证文件存在，还验证导入的类/函数是否被导出
2. **类型一致性**: 验证 TypeScript 接口与 Python Pydantic 模型的字段匹配
3. **增量验证**: 仅验证变更的文件，提高效率
4. **自动修复**: 对于简单问题（如路径拼写错误）自动修复
5. **可视化报告**: 生成依赖关系图和契约合规报告
