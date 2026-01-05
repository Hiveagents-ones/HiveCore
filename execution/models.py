# -*- coding: utf-8 -*-
"""Execution models for tracking project execution state."""
import uuid
from django.db import models
from django.utils import timezone

from tenants.mixins import TenantModelMixin


class ExecutionRound(TenantModelMixin):
    """A single execution round of a project.

    Represents one complete cycle of agent execution, from start to completion.
    A project may have multiple rounds (retries, iterations).
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        'api.Project',
        on_delete=models.CASCADE,
        related_name='execution_rounds',
    )

    # Round tracking
    round_number = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Celery task tracking
    celery_task_id = models.CharField(max_length=255, blank=True, db_index=True)

    # Input
    requirement_text = models.TextField(blank=True, help_text='The requirement text for this execution')

    # Execution options
    options = models.JSONField(default=dict, help_text='Execution options (max_rounds, parallel, etc.)')

    # Results
    summary = models.TextField(blank=True, help_text='Execution summary')
    error_message = models.TextField(blank=True)

    # Aggregated stats (updated during execution)
    total_tokens = models.IntegerField(default=0)
    total_cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    total_llm_calls = models.IntegerField(default=0)

    # ============ 任务分片新增字段 ============
    # 内部轮次管理（区别于 round_number 是用户可见的轮次）
    current_inner_round = models.IntegerField(default=0, help_text='Current inner round number for task sharding')
    total_inner_rounds = models.IntegerField(default=0, help_text='Total completed inner rounds')

    # Spec 缓存（避免重复解析）
    parsed_spec = models.JSONField(null=True, blank=True, help_text='Parsed requirement specification')
    acceptance_map = models.JSONField(null=True, blank=True, help_text='Acceptance criteria map')

    # 汇总统计
    total_requirements = models.IntegerField(default=0, help_text='Total number of requirements')
    passed_requirements = models.IntegerField(default=0, help_text='Number of passed requirements')
    failed_requirements = models.IntegerField(default=0, help_text='Number of failed requirements')

    # 任务分片模式标志
    use_task_sharding = models.BooleanField(default=False, help_text='Whether to use task sharding mode')
    # ============ 任务分片新增字段结束 ============

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'round_number']),
            models.Index(fields=['status']),
            models.Index(fields=['celery_task_id']),
        ]

    def __str__(self):
        return f"Round #{self.round_number} for {self.project.name} ({self.status})"

    def start(self):
        """Mark the round as started."""
        self.status = 'running'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at', 'updated_at'])

    def complete(self, summary=''):
        """Mark the round as completed."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.summary = summary
        self.save(update_fields=['status', 'completed_at', 'summary', 'updated_at'])

    def fail(self, error_message):
        """Mark the round as failed."""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.save(update_fields=['status', 'completed_at', 'error_message', 'updated_at'])

    def cancel(self):
        """Mark the round as cancelled."""
        self.status = 'cancelled'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at', 'updated_at'])

    def update_stats(self, tokens=0, cost=0, llm_calls=0):
        """Update aggregated stats."""
        self.total_tokens += tokens
        self.total_cost_usd += cost
        self.total_llm_calls += llm_calls
        self.save(update_fields=['total_tokens', 'total_cost_usd', 'total_llm_calls', 'updated_at'])

    @property
    def duration_seconds(self):
        """Get execution duration in seconds."""
        if not self.started_at:
            return None
        end = self.completed_at or timezone.now()
        return (end - self.started_at).total_seconds()

    # ============ 任务分片辅助方法 ============
    def get_pending_requirements(self, inner_round: int):
        """Get pending requirements for a specific inner round."""
        return list(self.requirement_executions.filter(
            inner_round_number=inner_round,
            status='pending'
        ).values_list('requirement_id', flat=True))

    def get_failed_requirements(self, inner_round: int):
        """Get failed requirements for a specific inner round (need retry)."""
        return list(self.requirement_executions.filter(
            inner_round_number=inner_round,
            status='completed',
            is_passed=False
        ).values_list('requirement_id', flat=True))

    def update_requirement_stats(self):
        """Update requirement statistics from RequirementExecution records."""
        from django.db.models import Max

        # Get the latest inner round for each requirement
        latest_rounds = self.requirement_executions.values('requirement_id').annotate(
            max_round=Max('inner_round_number')
        )

        passed = 0
        failed = 0
        for item in latest_rounds:
            req = self.requirement_executions.filter(
                requirement_id=item['requirement_id'],
                inner_round_number=item['max_round']
            ).first()
            if req:
                if req.is_passed:
                    passed += 1
                else:
                    failed += 1

        self.passed_requirements = passed
        self.failed_requirements = failed
        self.save(update_fields=['passed_requirements', 'failed_requirements', 'updated_at'])
    # ============ 任务分片辅助方法结束 ============


class RequirementExecution(TenantModelMixin):
    """Execution state for a single requirement.

    Each requirement may have multiple records across inner rounds.
    Supports fine-grained tracking of requirement progress.
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),       # Waiting to be executed
        ('scheduled', 'Scheduled'),   # Celery task scheduled
        ('running', 'Running'),       # Currently executing
        ('completed', 'Completed'),   # Execution finished (may or may not pass)
        ('failed', 'Failed'),         # Execution failed (exception)
        ('skipped', 'Skipped'),       # Skipped (dependency not met)
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationships
    execution_round = models.ForeignKey(
        ExecutionRound,
        on_delete=models.CASCADE,
        related_name='requirement_executions',
    )

    # Requirement identification
    requirement_id = models.CharField(max_length=50, db_index=True, help_text='e.g., REQ-001')
    requirement_content = models.TextField(help_text='Requirement description')
    requirement_type = models.CharField(max_length=50, blank=True, help_text='e.g., backend, frontend, database')

    # Round tracking (inner rounds for task sharding)
    inner_round_number = models.IntegerField(default=1, help_text='Inner round number for retries')
    attempt_number = models.IntegerField(default=1, help_text='Attempt number within this round')

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    celery_task_id = models.CharField(max_length=255, blank=True, db_index=True)

    # Dependencies
    depends_on = models.JSONField(default=list, help_text='List of requirement IDs this depends on')

    # Execution results
    blueprint = models.JSONField(null=True, blank=True, help_text='Blueprint design result')
    code_result = models.JSONField(null=True, blank=True, help_text='Code generation result')
    qa_result = models.JSONField(null=True, blank=True, help_text='QA acceptance result')
    validation_result = models.JSONField(null=True, blank=True, help_text='Code validation result')

    # QA statistics
    acceptance_criteria_total = models.IntegerField(default=0, help_text='Total acceptance criteria')
    acceptance_criteria_passed = models.IntegerField(default=0, help_text='Passed acceptance criteria')
    pass_rate = models.FloatField(default=0.0, help_text='Pass rate (0.0 - 1.0)')
    is_passed = models.BooleanField(default=False, help_text='Whether requirement passed (pass_rate >= threshold)')

    # Modified files
    modified_files = models.JSONField(default=list, help_text='List of files modified by this requirement')

    # Token/Cost statistics
    tokens_used = models.IntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    llm_calls = models.IntegerField(default=0)

    # Error information
    error_message = models.TextField(blank=True)
    error_traceback = models.TextField(blank=True)

    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['inner_round_number', 'requirement_id']
        indexes = [
            models.Index(fields=['execution_round', 'inner_round_number']),
            models.Index(fields=['execution_round', 'status']),
            models.Index(fields=['requirement_id']),
            models.Index(fields=['celery_task_id']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['execution_round', 'requirement_id', 'inner_round_number'],
                name='unique_req_per_inner_round'
            )
        ]

    def __str__(self):
        return f"{self.requirement_id} (Round {self.inner_round_number}, {self.status})"

    def start(self):
        """Mark as started."""
        self.status = 'running'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at', 'updated_at'])

    def complete(self, passed: bool, pass_rate: float = 0.0):
        """Mark as completed."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.is_passed = passed
        self.pass_rate = pass_rate
        self.save(update_fields=[
            'status', 'completed_at', 'is_passed', 'pass_rate', 'updated_at'
        ])

    def fail(self, error_message: str, traceback: str = ''):
        """Mark as failed."""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.error_traceback = traceback
        self.save(update_fields=[
            'status', 'completed_at', 'error_message', 'error_traceback', 'updated_at'
        ])

    def skip(self, reason: str = ''):
        """Mark as skipped."""
        self.status = 'skipped'
        self.completed_at = timezone.now()
        self.error_message = reason
        self.save(update_fields=['status', 'completed_at', 'error_message', 'updated_at'])

    @property
    def duration_seconds(self):
        """Get execution duration in seconds."""
        if not self.started_at:
            return None
        end = self.completed_at or timezone.now()
        return (end - self.started_at).total_seconds()

    def update_stats(self, tokens: int = 0, cost: float = 0, llm_calls: int = 0):
        """Update token/cost statistics."""
        self.tokens_used += tokens
        self.cost_usd += cost
        self.llm_calls += llm_calls
        self.save(update_fields=['tokens_used', 'cost_usd', 'llm_calls', 'updated_at'])


class AgentSelectionDecision(TenantModelMixin):
    """Records AA system's agent selection decision.

    Tracks which agents were selected for an execution round and why.
    Corresponds to AgentScope's SelectionDecision and CandidateRanking.
    """

    DECISION_SOURCE_CHOICES = [
        ('system', 'System'),
        ('user', 'User'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    execution_round = models.ForeignKey(
        ExecutionRound,
        on_delete=models.CASCADE,
        related_name='agent_selections',
    )
    agent = models.ForeignKey(
        'api.Agent',
        on_delete=models.SET_NULL,
        null=True,
        related_name='selection_decisions',
    )
    agent_name = models.CharField(max_length=100, blank=True, help_text='Cached agent name')

    # Scoring details
    s_base_score = models.FloatField(default=0, help_text='Base capability score')
    requirement_fit_score = models.FloatField(default=0, help_text='Requirement fit score')
    total_score = models.FloatField(default=0, help_text='Combined total score')

    # Detailed scoring breakdown (matches AgentScope CandidateRanking)
    scoring_breakdown = models.JSONField(default=dict, help_text='Detailed scoring breakdown')

    # Requirement fit details (from RequirementFitBreakdown)
    requirement_fit_matched = models.JSONField(
        default=dict,
        help_text='Matched capabilities by field {field: [values]}'
    )
    requirement_fit_missing = models.JSONField(
        default=dict,
        help_text='Missing capabilities by field {field: [values]}'
    )
    requirement_fit_partial = models.JSONField(
        default=dict,
        help_text='Partial match scores by field {field: score}'
    )
    requirement_fit_rationales = models.JSONField(
        default=list,
        help_text='Explanation rationales for requirement fit'
    )

    # Cold start handling
    is_cold_start = models.BooleanField(default=False, help_text='Whether agent was in cold start')
    cold_start_slot_reserved = models.BooleanField(
        default=False,
        help_text='Whether cold start bonus was applied'
    )

    # Risk notes
    risk_notes = models.JSONField(default=list, help_text='Risk notes for this candidate')

    # Selection outcome
    is_selected = models.BooleanField(default=False, help_text='Whether this agent was actually selected')
    decision_source = models.CharField(
        max_length=10,
        choices=DECISION_SOURCE_CHOICES,
        default='system',
        help_text='How the selection was made'
    )

    # Legacy fields for compatibility
    reasons = models.TextField(blank=True, help_text='Selection reasons (legacy)')
    role_assigned = models.CharField(max_length=100, blank=True, help_text='Role assigned to agent')

    # Order in ranking
    selection_order = models.IntegerField(default=0, help_text='Rank order (0 = best)')
    batch_index = models.IntegerField(default=0, help_text='Selection batch index')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['selection_order']
        indexes = [
            models.Index(fields=['execution_round', 'selection_order']),
            models.Index(fields=['execution_round', 'is_selected']),
            models.Index(fields=['agent', 'created_at']),
        ]

    def __str__(self):
        agent_display = self.agent_name or (self.agent.name if self.agent else 'Unknown')
        selected = '✓' if self.is_selected else ''
        return f"{selected}{agent_display} for {self.execution_round} (score: {self.total_score:.2f})"

    def save(self, *args, **kwargs):
        # Cache agent name
        if self.agent and not self.agent_name:
            self.agent_name = self.agent.name
        super().save(*args, **kwargs)


class ExecutionArtifact(TenantModelMixin):
    """Generated artifacts (code, config, documents) from execution."""

    ARTIFACT_TYPE_CHOICES = [
        ('code', 'Code'),
        ('config', 'Config'),
        ('document', 'Document'),
        ('test', 'Test'),
        ('style', 'Style'),
        ('asset', 'Asset'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    execution_round = models.ForeignKey(
        ExecutionRound,
        on_delete=models.CASCADE,
        related_name='artifacts',
    )

    # Optional: link to specific requirement execution
    requirement_execution = models.ForeignKey(
        RequirementExecution,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='artifacts',
        help_text='The requirement execution that generated this artifact'
    )

    # File info
    artifact_type = models.CharField(max_length=20, choices=ARTIFACT_TYPE_CHOICES, default='code')
    file_path = models.CharField(max_length=500, help_text='Relative path in workspace')
    file_name = models.CharField(max_length=255)
    language = models.CharField(max_length=50, blank=True, help_text='Programming language if code')

    # Content (for small files, store directly; large files use S3)
    content = models.TextField(blank=True)
    content_hash = models.CharField(max_length=64, blank=True, help_text='SHA256 hash of content')
    size_bytes = models.IntegerField(default=0)

    # S3 storage for large files
    s3_key = models.CharField(max_length=500, blank=True, help_text='S3 key if stored externally')

    # Generation info
    generated_by_agent = models.ForeignKey(
        'api.Agent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_artifacts',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['file_path']
        indexes = [
            models.Index(fields=['execution_round', 'artifact_type']),
            models.Index(fields=['file_path']),
        ]

    def __str__(self):
        return f"{self.file_path} ({self.artifact_type})"


class ExecutionLog(TenantModelMixin):
    """Detailed execution logs for debugging and analysis."""

    LEVEL_CHOICES = [
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    execution_round = models.ForeignKey(
        ExecutionRound,
        on_delete=models.CASCADE,
        related_name='logs',
    )

    # Optional: link to specific requirement execution
    requirement_execution = models.ForeignKey(
        RequirementExecution,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs',
        help_text='The requirement execution this log belongs to'
    )

    # Log details
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='info')
    message = models.TextField()
    metadata = models.JSONField(default=dict)

    # Source
    agent = models.ForeignKey(
        'api.Agent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='execution_logs',
    )
    source = models.CharField(max_length=100, blank=True, help_text='Log source (e.g., module name)')

    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['execution_round', 'level']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"[{self.level.upper()}] {self.message[:50]}..."


class ExecutionProgress(models.Model):
    """Real-time progress tracking for SSE updates.

    This is a lightweight model for tracking current progress state.
    """

    execution_round = models.OneToOneField(
        ExecutionRound,
        on_delete=models.CASCADE,
        related_name='progress',
        primary_key=True,
    )

    # Current state
    current_phase = models.CharField(max_length=50, default='initializing')
    current_agent = models.CharField(max_length=100, blank=True)
    current_task = models.CharField(max_length=255, blank=True)

    # Progress percentage (0-100)
    progress_percent = models.IntegerField(default=0)

    # Counts
    completed_tasks = models.IntegerField(default=0)
    total_tasks = models.IntegerField(default=0)
    completed_requirements = models.IntegerField(default=0)
    total_requirements = models.IntegerField(default=0)

    # Current requirement being processed (for task sharding)
    current_requirement_id = models.CharField(max_length=50, blank=True)
    current_inner_round = models.IntegerField(default=0)

    # Last update
    last_event = models.CharField(max_length=50, blank=True)
    last_event_data = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Progress for {self.execution_round}: {self.progress_percent}%"

    def update_phase(self, phase, agent='', task=''):
        """Update current execution phase."""
        self.current_phase = phase
        self.current_agent = agent
        self.current_task = task
        self.save(update_fields=['current_phase', 'current_agent', 'current_task', 'updated_at'])

    def update_progress(self, percent, completed_tasks=None, total_tasks=None):
        """Update progress percentage."""
        self.progress_percent = min(100, max(0, percent))
        if completed_tasks is not None:
            self.completed_tasks = completed_tasks
        if total_tasks is not None:
            self.total_tasks = total_tasks
        self.save(update_fields=['progress_percent', 'completed_tasks', 'total_tasks', 'updated_at'])

    def set_event(self, event_type, event_data=None):
        """Record last event for SSE broadcast."""
        self.last_event = event_type
        self.last_event_data = event_data or {}
        self.save(update_fields=['last_event', 'last_event_data', 'updated_at'])

    def update_requirement(self, requirement_id: str, inner_round: int):
        """Update current requirement being processed."""
        self.current_requirement_id = requirement_id
        self.current_inner_round = inner_round
        self.save(update_fields=['current_requirement_id', 'current_inner_round', 'updated_at'])
