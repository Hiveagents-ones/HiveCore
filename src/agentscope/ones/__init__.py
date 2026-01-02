# -*- coding: utf-8 -*-
"""One·s / AgentScope system facade."""
from pathlib import Path

from ._system import SystemMission, SystemProfile, SystemRegistry, UserProfile

# Built-in agents directory containing framework expert manifests
BUILTIN_AGENTS_DIR = Path(__file__).parent / "agents"
from .memory import (
    DecisionCategory,
    MemoryEntry,
    MemoryPool,
    ProjectDecision,
    ProjectDescriptor,
    ProjectMemory,
    ProjectPool,
    ResourceHandle,
    ResourceLibrary,
)
from .intent import (
    AcceptanceCriteria,
    AssistantOrchestrator,
    IntentRequest,
    StrategyPlan,
)
from .task_graph import TaskGraph, TaskGraphBuilder, TaskNode, TaskStatus
from .delivery import (
    DeliveryStack,
    IntentLayer,
    SlaLayer,
    SupervisionLayer,
    CollaborationLayer,
    ExperienceLayer,
)
from .msghub import (
    AgentScopeMsgHubBroadcaster,
    InMemoryMsgHub,
    MsgHubBroadcaster,
    ProjectMsgHubRegistry,
    RoundUpdate,
)
from .artifacts import (
    ArtifactDeliveryManager,
    ArtifactDeliveryResult,
    ArtifactAdapter,
    WebDeployAdapter,
    MediaPackageAdapter,
)
from .execution import (
    ExecutionLoop,
    ExecutionReport,
    ExecutionContext,
    AgentOutput,
    ExecutionEnhancer,
)
from .repair_engine import (
    RepairEngine,
    RepairAction,
    FilePatch,
    RepairResult,
)
from .dependency_sync import (
    DependencySynchronizer,
    DependencyInfo,
    SyncResult,
)
from .blueprint_enhancer import (
    BlueprintEnhancer,
    EnhancedBlueprint,
    RequiredFunction,
)
from .collaboration import (
    CollaborativeAgent,
    CollaborativeExecutor,
    CollaborationMessage,
    MessageType,
    SharedWorkspace,
    AgentWorkState,
)
from .kpi import KPITracker, KPIRecord
from .questions import OpenQuestion, OpenQuestionTracker
from .task_board import (
    TaskItem,
    TaskItemStatus,
    AgentTaskBoard,
    ProjectTaskBoard,
    ProjectContext,
)
from .summary import SummaryReport, build_summary
from .aa_agent import AASystemAgent
from .storage import AAMemoryRecord, AAMemoryStore
from .architect_agent import ArchitectAgent
from .collaborative_execution import (
    CollaborativeExecution,
    CollaborativeCodeAgent,
    CollaborationHistory,
    execute_with_real_collaboration,
)
from .react_agents import (
    SpecialistReActAgent,
    StrategyReActAgent,
    BuilderReActAgent,
    ReviewerReActAgent,
    ProductReActAgent,
    UxReActAgent,
    FrontendReActAgent,
    BackendReActAgent,
    QAReActAgent,
    DeveloperReActAgent,
)
from .manifest import (
    AgentManifest,
    MCPServerConfig,
    PromptConfig,
    KnowledgeBaseConfig,
    MemoryConfig,
    TaskBoardConfig,
    DependencyConfig,
    ValidationConfig,
    RepairConfig,
    BlueprintConfig,
    load_manifests_from_directory,
)
from .sandbox import (
    SandboxExecutor,
    SandboxExecutionResult,
    SandboxManager,
)
from .sandbox_orchestrator import (
    SandboxOrchestrator,
    SandboxDecision,
    SandboxTypeEnum,
    SandboxCapability,
    SANDBOX_CAPABILITIES,
)
from .scaffold import (
    ScaffoldExecutor,
    ScaffoldResult,
    ScaffoldPlan,
    CommandCategory,
    CommandRisk,
    CommandValidator,
    CommandValidationResult,
)
from .task_executor import (
    SandboxTask,
    SandboxTaskExecutor,
    TaskStatus as SandboxTaskStatus,
    TaskPriority,
    MultiTenantTaskManager,
    is_long_running_command,
)
from .acceptance_agent import (
    AcceptanceAgent,
    AcceptanceResult,
    AcceptanceStatus,
    ValidationCheck,
    ValidationEnvironment,
)
from ._smithery_registry import (
    SmitheryRegistryClient,
    SmitheryServerInfo,
    search_and_get_mcp_configs,
)
from ._modular_agent import (
    ModularAgent,
    AgentMemory,
    AgentKnowledge,
    AgentTaskBoard as ModularAgentTaskBoard,
    AgentPrompt,
    create_modular_agent_from_manifest,
    spawn_modular_agent,
    load_modular_agent,
)
# File tracking and validation (new modules)
from .file_tracking import (
    FileType,
    FileMetadata,
    FileAnalyzer,
    BaseFileAnalyzer,
    GenericFileAnalyzer,
    FileAnalyzerRegistry,
    FileRegistry,
)
from .dependency_validation import (
    IssueSeverity,
    IssueCategory,
    ValidationIssue,
    ValidationResult,
    ValidationContext,
    BaseValidator,
    ImportPathValidator,
    CircularDependencyValidator,
    DeclaredDependencyValidator,
    BlueprintDependencyValidator,
    ValidationEngine,
    create_default_validation_engine,
)
from .contract_validation import (
    ContractItemType,
    ContractItem,
    ImplementationReference,
    ArchitectureContract,
    ContractMatcher,
    ApiEndpointMatcher,
    DataModelMatcher,
    ContractValidator,
    ContractRegistry,
)
from .project_context import (
    RoundFeedback,
    ProjectContext as EnhancedProjectContext,
    create_project_context,
)


def load_builtin_agent_manifests() -> list["AgentManifest"]:
    """Load all built-in framework expert agent manifests.

    Returns:
        List of AgentManifest for framework experts (Django, FastAPI, Vite, Express, etc.).
    """
    return load_manifests_from_directory(BUILTIN_AGENTS_DIR)

__all__ = [
    "SystemMission",
    "SystemProfile",
    "SystemRegistry",
    "UserProfile",
    "DecisionCategory",
    "ProjectDecision",
    "ProjectDescriptor",
    "ProjectMemory",
    "ProjectPool",
    "MemoryEntry",
    "MemoryPool",
    "ResourceHandle",
    "ResourceLibrary",
    "AcceptanceCriteria",
    "AssistantOrchestrator",
    "IntentRequest",
    "StrategyPlan",
    "TaskGraph",
    "TaskGraphBuilder",
    "TaskNode",
    "TaskStatus",
    "DeliveryStack",
    "IntentLayer",
    "SlaLayer",
    "SupervisionLayer",
    "CollaborationLayer",
    "ExperienceLayer",
    "ExecutionLoop",
    "ExecutionReport",
    "ExecutionContext",
    "AgentOutput",
    "ExecutionEnhancer",
    # Repair Engine
    "RepairEngine",
    "RepairAction",
    "FilePatch",
    "RepairResult",
    # Dependency Sync
    "DependencySynchronizer",
    "DependencyInfo",
    "SyncResult",
    # Blueprint Enhancer
    "BlueprintEnhancer",
    "EnhancedBlueprint",
    "RequiredFunction",
    "CollaborativeAgent",
    "CollaborativeExecutor",
    "CollaborationMessage",
    "MessageType",
    "SharedWorkspace",
    "AgentWorkState",
    "AASystemAgent",
    "AAMemoryRecord",
    "AAMemoryStore",
    "ArchitectAgent",
    "CollaborativeExecution",
    "execute_with_real_collaboration",
    "CollaborativeCodeAgent",
    "CollaborationHistory",
    "MsgHubBroadcaster",
    "InMemoryMsgHub",
    "ProjectMsgHubRegistry",
    "AgentScopeMsgHubBroadcaster",
    "RoundUpdate",
    "ArtifactDeliveryManager",
    "ArtifactDeliveryResult",
    "ArtifactAdapter",
    "WebDeployAdapter",
    "MediaPackageAdapter",
    "SpecialistReActAgent",
    "StrategyReActAgent",
    "BuilderReActAgent",
    "ReviewerReActAgent",
    "ProductReActAgent",
    "UxReActAgent",
    "FrontendReActAgent",
    "BackendReActAgent",
    "QAReActAgent",
    "DeveloperReActAgent",
    "KPITracker",
    "KPIRecord",
    "OpenQuestion",
    "OpenQuestionTracker",
    "SummaryReport",
    "build_summary",
    "TaskItem",
    "TaskItemStatus",
    "AgentTaskBoard",
    "ProjectTaskBoard",
    "ProjectContext",
    "AgentManifest",
    "MCPServerConfig",
    "PromptConfig",
    "KnowledgeBaseConfig",
    "MemoryConfig",
    "TaskBoardConfig",
    "DependencyConfig",
    "ValidationConfig",
    "RepairConfig",
    "BlueprintConfig",
    "load_manifests_from_directory",
    "SandboxExecutor",
    "SandboxExecutionResult",
    "SandboxManager",
    # Sandbox Orchestrator
    "SandboxOrchestrator",
    "SandboxDecision",
    "SandboxTypeEnum",
    "SandboxCapability",
    "SANDBOX_CAPABILITIES",
    # Scaffold Executor
    "ScaffoldExecutor",
    "ScaffoldResult",
    "ScaffoldPlan",
    "CommandCategory",
    "CommandRisk",
    "CommandValidator",
    "CommandValidationResult",
    # Task Executor (for long-running commands)
    "SandboxTask",
    "SandboxTaskExecutor",
    "SandboxTaskStatus",
    "TaskPriority",
    "MultiTenantTaskManager",
    "is_long_running_command",
    # Acceptance Agent
    "AcceptanceAgent",
    "AcceptanceResult",
    "AcceptanceStatus",
    "ValidationCheck",
    "ValidationEnvironment",
    "SmitheryRegistryClient",
    "SmitheryServerInfo",
    "search_and_get_mcp_configs",
    # Modular Agent
    "ModularAgent",
    "AgentMemory",
    "AgentKnowledge",
    "ModularAgentTaskBoard",
    "AgentPrompt",
    "create_modular_agent_from_manifest",
    "spawn_modular_agent",
    "load_modular_agent",
    # Built-in Agents
    "BUILTIN_AGENTS_DIR",
    "load_builtin_agent_manifests",
    # File Tracking
    "FileType",
    "FileMetadata",
    "FileAnalyzer",
    "BaseFileAnalyzer",
    "GenericFileAnalyzer",
    "FileAnalyzerRegistry",
    "FileRegistry",
    # Dependency Validation
    "IssueSeverity",
    "IssueCategory",
    "ValidationIssue",
    "ValidationResult",
    "ValidationContext",
    "BaseValidator",
    "ImportPathValidator",
    "CircularDependencyValidator",
    "DeclaredDependencyValidator",
    "BlueprintDependencyValidator",
    "ValidationEngine",
    "create_default_validation_engine",
    # Contract Validation
    "ContractItemType",
    "ContractItem",
    "ImplementationReference",
    "ArchitectureContract",
    "ContractMatcher",
    "ApiEndpointMatcher",
    "DataModelMatcher",
    "ContractValidator",
    "ContractRegistry",
    # Enhanced Project Context
    "RoundFeedback",
    "EnhancedProjectContext",
    "create_project_context",
]
