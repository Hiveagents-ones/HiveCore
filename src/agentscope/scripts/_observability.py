# -*- coding: utf-8 -*-
"""Observability infrastructure for HiveCore execution.

This module provides:
- ObservabilityConfig: Configuration for logging, metrics, and tracing
- Logger: Unified logging with level support
- TokenTracker: LLM token consumption tracking
- TimingTracker: Execution timing with hierarchical structure
- ObservabilityContext: Global context for observability
"""
from __future__ import annotations

import json
import sys
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import IntEnum
from pathlib import Path
from typing import Any, TextIO, Generator


# ---------------------------------------------------------------------------
# Log Levels
# ---------------------------------------------------------------------------
class LogLevel(IntEnum):
    """Log level enumeration."""

    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40

    @classmethod
    def from_string(cls, level: str) -> "LogLevel":
        """Convert string to LogLevel."""
        mapping = {
            "DEBUG": cls.DEBUG,
            "INFO": cls.INFO,
            "WARN": cls.WARN,
            "WARNING": cls.WARN,
            "ERROR": cls.ERROR,
        }
        return mapping.get(level.upper(), cls.INFO)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
@dataclass
class ObservabilityConfig:
    """Configuration for observability features.

    Attributes:
        log_level: Minimum log level to display (DEBUG, INFO, WARN, ERROR)
        log_format: Output format (text, json, rich)
        log_destination: Output target (stdout, stderr, or file path)
        track_tokens: Whether to track LLM token consumption
        track_timing: Whether to track execution timing
        show_agent_thinking: Whether to show agent's thinking process
        show_progress: Whether to show progress indicators
        generate_report: Whether to generate execution report
        report_path: Path for execution report (Markdown)
        token_pricing: Pricing per 1M tokens {"input": $, "output": $}
    """

    log_level: str = "INFO"
    log_format: str = "text"  # text, json, rich
    log_destination: str = "stdout"  # stdout, stderr, or file path
    track_tokens: bool = True
    track_timing: bool = True
    show_agent_thinking: bool = False
    show_progress: bool = True
    generate_report: bool = False
    report_path: str | None = None
    token_pricing: dict[str, float] = field(
        default_factory=lambda: {"input": 3.0, "output": 15.0}
    )

    def get_log_level(self) -> LogLevel:
        """Get LogLevel enum from string."""
        return LogLevel.from_string(self.log_level)

    def get_output_stream(self) -> TextIO:
        """Get output stream based on destination."""
        if self.log_destination == "stdout":
            return sys.stdout
        elif self.log_destination == "stderr":
            return sys.stderr
        else:
            # File path - will be handled by Logger
            return sys.stdout


# ---------------------------------------------------------------------------
# Token Tracking
# ---------------------------------------------------------------------------
@dataclass
class TokenUsage:
    """Token usage statistics.

    Attributes:
        prompt_tokens: Number of input/prompt tokens
        completion_tokens: Number of output/completion tokens
        total_tokens: Total tokens (prompt + completion)
        estimated_cost: Estimated cost in USD
        call_count: Number of LLM calls
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    call_count: int = 0

    def add(self, other: "TokenUsage") -> None:
        """Add another TokenUsage to this one."""
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens
        self.total_tokens += other.total_tokens
        self.estimated_cost += other.estimated_cost
        self.call_count += other.call_count


class TokenTracker:
    """Tracks LLM token consumption across the execution.

    Thread-safe implementation for concurrent LLM calls.
    """

    def __init__(self, pricing: dict[str, float] | None = None):
        """Initialize TokenTracker.

        Args:
            pricing: Pricing per 1M tokens {"input": $, "output": $}
        """
        self._lock = threading.Lock()
        self._pricing = pricing or {"input": 3.0, "output": 15.0}
        self._usage_by_label: dict[str, TokenUsage] = {}
        self._usage_by_phase: dict[str, TokenUsage] = {}
        self._total = TokenUsage()

    def track(
        self,
        label: str,
        prompt_tokens: int,
        completion_tokens: int,
        phase: str = "unknown",
    ) -> TokenUsage:
        """Record token usage for an LLM call.

        Args:
            label: Call label (e.g., "blueprint:REQ-001")
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            phase: Execution phase (e.g., "blueprint", "implementation", "qa")

        Returns:
            TokenUsage: The usage recorded for this call
        """
        total = prompt_tokens + completion_tokens
        cost = (
            prompt_tokens * self._pricing["input"] / 1_000_000
            + completion_tokens * self._pricing["output"] / 1_000_000
        )

        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
            estimated_cost=cost,
            call_count=1,
        )

        with self._lock:
            # By label
            if label not in self._usage_by_label:
                self._usage_by_label[label] = TokenUsage()
            self._usage_by_label[label].add(usage)

            # By phase
            if phase not in self._usage_by_phase:
                self._usage_by_phase[phase] = TokenUsage()
            self._usage_by_phase[phase].add(usage)

            # Total
            self._total.add(usage)

        return usage

    def get_total(self) -> TokenUsage:
        """Get total token usage."""
        with self._lock:
            return TokenUsage(
                prompt_tokens=self._total.prompt_tokens,
                completion_tokens=self._total.completion_tokens,
                total_tokens=self._total.total_tokens,
                estimated_cost=self._total.estimated_cost,
                call_count=self._total.call_count,
            )

    def get_by_phase(self) -> dict[str, TokenUsage]:
        """Get token usage by phase."""
        with self._lock:
            return {k: TokenUsage(**asdict(v)) for k, v in self._usage_by_phase.items()}

    def get_by_label(self) -> dict[str, TokenUsage]:
        """Get token usage by label."""
        with self._lock:
            return {k: TokenUsage(**asdict(v)) for k, v in self._usage_by_label.items()}

    def get_summary(self) -> dict[str, Any]:
        """Get complete token usage summary."""
        with self._lock:
            return {
                "total": asdict(self._total),
                "by_phase": {k: asdict(v) for k, v in self._usage_by_phase.items()},
                "by_label": {k: asdict(v) for k, v in self._usage_by_label.items()},
            }

    def format_summary(self) -> str:
        """Format token usage as human-readable string."""
        total = self.get_total()
        by_phase = self.get_by_phase()

        lines = [
            f"总计: {total.total_tokens:,} tokens (~${total.estimated_cost:.2f})",
        ]

        if by_phase:
            for phase, usage in sorted(by_phase.items()):
                pct = usage.total_tokens / total.total_tokens * 100 if total.total_tokens > 0 else 0
                lines.append(f"  {phase}: {usage.total_tokens:,} ({pct:.1f}%)")

        return "\n".join(lines)

    def reset(self) -> None:
        """Reset all tracking data."""
        with self._lock:
            self._usage_by_label.clear()
            self._usage_by_phase.clear()
            self._total = TokenUsage()


# ---------------------------------------------------------------------------
# Timing Tracking
# ---------------------------------------------------------------------------
@dataclass
class TimingEntry:
    """A timing entry with hierarchical structure.

    Attributes:
        name: Name of the timed operation
        duration: Duration in seconds
        start_time: Start timestamp
        children: Child timing entries
    """

    name: str
    duration: float = 0.0
    start_time: float = 0.0
    children: list["TimingEntry"] = field(default_factory=list)


class TimingTracker:
    """Tracks execution timing with hierarchical structure.

    Supports nested timing contexts for detailed performance analysis.
    """

    def __init__(self):
        """Initialize TimingTracker."""
        self._lock = threading.Lock()
        self._stack: list[TimingEntry] = []
        self._roots: list[TimingEntry] = []
        self._flat: dict[str, list[float]] = {}
        self._total_start: float | None = None
        self._total_duration: float = 0.0

    def start_total(self) -> None:
        """Start total execution timer."""
        self._total_start = time.perf_counter()

    def stop_total(self) -> None:
        """Stop total execution timer."""
        if self._total_start is not None:
            self._total_duration = time.perf_counter() - self._total_start

    @contextmanager
    def measure(self, name: str) -> Generator[None, None, None]:
        """Context manager to measure execution time.

        Args:
            name: Name of the operation being timed

        Yields:
            None
        """
        entry = TimingEntry(name=name, start_time=time.perf_counter())

        with self._lock:
            if self._stack:
                self._stack[-1].children.append(entry)
            else:
                self._roots.append(entry)
            self._stack.append(entry)

        try:
            yield
        finally:
            entry.duration = time.perf_counter() - entry.start_time

            with self._lock:
                self._stack.pop()

                # Record flat timing
                if name not in self._flat:
                    self._flat[name] = []
                self._flat[name].append(entry.duration)

    def record(self, name: str, duration: float) -> None:
        """Manually record a timing entry.

        Args:
            name: Name of the operation
            duration: Duration in seconds
        """
        with self._lock:
            if name not in self._flat:
                self._flat[name] = []
            self._flat[name].append(duration)

    def get_total_duration(self) -> float:
        """Get total execution duration."""
        return self._total_duration

    def get_flat_summary(self) -> dict[str, dict[str, float]]:
        """Get flat timing summary with statistics."""
        with self._lock:
            result = {}
            for name, durations in self._flat.items():
                result[name] = {
                    "count": len(durations),
                    "total": sum(durations),
                    "avg": sum(durations) / len(durations) if durations else 0,
                    "min": min(durations) if durations else 0,
                    "max": max(durations) if durations else 0,
                }
            return result

    def format_tree(self, indent: str = "  ") -> str:
        """Format timing as tree structure.

        Args:
            indent: Indentation string for each level

        Returns:
            str: Tree-formatted timing information
        """
        lines: list[str] = []

        def format_node(node: TimingEntry, prefix: str, is_last: bool) -> None:
            connector = "└─" if is_last else "├─"
            lines.append(f"{prefix}{connector} {node.name}: {node.duration:.2f}s")

            child_prefix = prefix + ("   " if is_last else "│  ")
            for i, child in enumerate(node.children):
                format_node(child, child_prefix, i == len(node.children) - 1)

        with self._lock:
            for i, root in enumerate(self._roots):
                format_node(root, "", i == len(self._roots) - 1)

        return "\n".join(lines)

    def format_summary(self) -> str:
        """Format timing as summary string."""
        lines = []

        if self._total_duration > 0:
            lines.append(f"总耗时: {self._format_duration(self._total_duration)}")

        flat = self.get_flat_summary()
        if flat:
            lines.append("阶段耗时:")
            for name, stats in sorted(flat.items(), key=lambda x: -x[1]["total"]):
                lines.append(
                    f"  {name}: {self._format_duration(stats['total'])} "
                    f"({stats['count']} 次, 平均 {stats['avg']:.2f}s)"
                )

        return "\n".join(lines)

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration as human-readable string."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}m {secs:.0f}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"

    def reset(self) -> None:
        """Reset all tracking data."""
        with self._lock:
            self._stack.clear()
            self._roots.clear()
            self._flat.clear()
            self._total_start = None
            self._total_duration = 0.0


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
class Logger:
    """Unified logger with level support and multiple output formats.

    Supports text, JSON, and rich (colored) output formats.
    """

    # ANSI color codes for rich format
    _COLORS = {
        LogLevel.DEBUG: "\033[90m",  # Gray
        LogLevel.INFO: "\033[0m",    # Default
        LogLevel.WARN: "\033[33m",   # Yellow
        LogLevel.ERROR: "\033[31m",  # Red
    }
    _RESET = "\033[0m"

    def __init__(self, config: ObservabilityConfig):
        """Initialize Logger.

        Args:
            config: Observability configuration
        """
        self.config = config
        self._level = config.get_log_level()
        self._format = config.log_format
        self._lock = threading.Lock()
        self._file_handle: TextIO | None = None

        # Open file if destination is a path
        if config.log_destination not in ("stdout", "stderr"):
            try:
                self._file_handle = open(config.log_destination, "a", encoding="utf-8")
            except Exception:
                pass  # Fall back to stdout

    def _get_output(self) -> TextIO:
        """Get output stream."""
        if self._file_handle:
            return self._file_handle
        elif self.config.log_destination == "stderr":
            return sys.stderr
        return sys.stdout

    def _log(self, level: LogLevel, message: str, **context: Any) -> None:
        """Internal log method.

        Args:
            level: Log level
            message: Log message
            **context: Additional context fields
        """
        if level < self._level:
            return

        timestamp = datetime.now().isoformat()
        level_name = level.name

        with self._lock:
            output = self._get_output()

            if self._format == "json":
                log_entry = {
                    "ts": timestamp,
                    "level": level_name,
                    "msg": message,
                    **context,
                }
                print(json.dumps(log_entry, ensure_ascii=False), file=output, flush=True)

            elif self._format == "rich":
                color = self._COLORS.get(level, "")
                prefix = f"[{level_name:5}]" if level != LogLevel.INFO else ""
                if prefix:
                    print(f"{color}{prefix}{self._RESET} {message}", file=output, flush=True)
                else:
                    print(message, file=output, flush=True)

            else:  # text format
                if level == LogLevel.INFO:
                    # Clean output for INFO level
                    print(message, file=output, flush=True)
                else:
                    print(f"[{level_name}] {message}", file=output, flush=True)

    def debug(self, message: str, **context: Any) -> None:
        """Log debug message."""
        self._log(LogLevel.DEBUG, message, **context)

    def info(self, message: str, **context: Any) -> None:
        """Log info message."""
        self._log(LogLevel.INFO, message, **context)

    def warn(self, message: str, **context: Any) -> None:
        """Log warning message."""
        self._log(LogLevel.WARN, message, **context)

    def error(self, message: str, **context: Any) -> None:
        """Log error message."""
        self._log(LogLevel.ERROR, message, **context)

    def stream(self, text: str, *, end: str = "", flush: bool = True) -> None:
        """Output streaming text without prefix or formatting.

        Used for real-time LLM response streaming where formatting
        would interfere with the user experience.

        Args:
            text: Text to output
            end: String appended after text (default: no newline)
            flush: Whether to flush output immediately
        """
        with self._lock:
            output = self._get_output()
            print(text, end=end, file=output, flush=flush)

    def close(self) -> None:
        """Close file handle if open."""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None


# ---------------------------------------------------------------------------
# Observability Context
# ---------------------------------------------------------------------------
class ObservabilityContext:
    """Global context for observability features.

    Provides unified access to logger, token tracker, and timing tracker.
    Thread-safe singleton pattern.
    """

    _instance: "ObservabilityContext | None" = None
    _lock = threading.Lock()

    def __init__(self, config: ObservabilityConfig | None = None):
        """Initialize ObservabilityContext.

        Args:
            config: Observability configuration (uses defaults if None)
        """
        self.config = config or ObservabilityConfig()
        self.logger = Logger(self.config)
        self.token_tracker = TokenTracker(self.config.token_pricing)
        self.timing_tracker = TimingTracker()
        self._current_phase: str = "unknown"
        self._current_requirement: str | None = None

    @classmethod
    def get_instance(cls) -> "ObservabilityContext":
        """Get or create singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def initialize(cls, config: ObservabilityConfig) -> "ObservabilityContext":
        """Initialize singleton with configuration.

        Args:
            config: Observability configuration

        Returns:
            ObservabilityContext: Initialized context
        """
        with cls._lock:
            if cls._instance is not None:
                cls._instance.logger.close()
            cls._instance = cls(config)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.logger.close()
                cls._instance = None

    def set_phase(self, phase: str) -> None:
        """Set current execution phase.

        Args:
            phase: Phase name (e.g., "blueprint", "implementation", "qa")
        """
        self._current_phase = phase

    def set_requirement(self, req_id: str | None) -> None:
        """Set current requirement being processed.

        Args:
            req_id: Requirement ID or None
        """
        self._current_requirement = req_id

    def get_phase(self) -> str:
        """Get current execution phase."""
        return self._current_phase

    def get_requirement(self) -> str | None:
        """Get current requirement ID."""
        return self._current_requirement

    @contextmanager
    def span(self, name: str, phase: str | None = None) -> Generator[None, None, None]:
        """Create a tracked execution span.

        Args:
            name: Span name
            phase: Optional phase override

        Yields:
            None
        """
        if phase:
            old_phase = self._current_phase
            self._current_phase = phase

        with self.timing_tracker.measure(name):
            try:
                yield
            finally:
                if phase:
                    self._current_phase = old_phase

    def track_llm_call(
        self,
        label: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration: float | None = None,
    ) -> None:
        """Track an LLM call.

        Args:
            label: Call label
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            duration: Optional call duration in seconds
        """
        if self.config.track_tokens:
            usage = self.token_tracker.track(
                label=label,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                phase=self._current_phase,
            )

            self.logger.debug(
                f"[LLM:{label}] tokens: {usage.total_tokens:,} "
                f"(prompt={prompt_tokens:,}, completion={completion_tokens:,})"
            )

    def get_execution_summary(self) -> dict[str, Any]:
        """Get complete execution summary.

        Returns:
            dict: Summary with tokens, timing, and metadata
        """
        return {
            "tokens": self.token_tracker.get_summary(),
            "timing": {
                "total_duration": self.timing_tracker.get_total_duration(),
                "by_operation": self.timing_tracker.get_flat_summary(),
            },
        }

    def print_summary(self) -> None:
        """Print execution summary to logger."""
        self.logger.info("\n" + "=" * 40)
        self.logger.info("执行摘要")
        self.logger.info("=" * 40)

        # Timing
        if self.config.track_timing:
            self.logger.info(self.timing_tracker.format_summary())

        # Tokens
        if self.config.track_tokens:
            self.logger.info("")
            self.logger.info("Token 消耗:")
            self.logger.info(self.token_tracker.format_summary())


# ---------------------------------------------------------------------------
# Hub Integration (for webhook support)
# ---------------------------------------------------------------------------
def _get_hub() -> "ObservabilityHub | None":
    """Get the ObservabilityHub singleton if available.

    Returns:
        ObservabilityHub | None: Hub instance or None if import fails.
    """
    try:
        from agentscope.observability import ObservabilityHub

        return ObservabilityHub()
    except ImportError:
        return None


def _record_timeline_event(
    event_type: str,
    project_id: str | None = None,
    agent_id: str | None = None,
    node_id: str | None = None,
    **metadata: Any,
) -> None:
    """Record a timeline event to ObservabilityHub.

    This function is called by Observer classes to push events
    to the webhook when configured.

    Args:
        event_type: Type of event (agent_start, agent_end, etc.)
        project_id: Project ID if available
        agent_id: Agent ID if available
        node_id: Task node ID if available
        **metadata: Additional event metadata
    """
    hub = _get_hub()
    if hub is None or hub._webhook is None:
        return

    try:
        from agentscope.observability import TimelineEvent

        event = TimelineEvent(
            timestamp=datetime.now(),
            event_type=event_type,  # type: ignore
            project_id=project_id,
            agent_id=agent_id,
            node_id=node_id,
            metadata=metadata,
        )
        hub.record_timeline_event(event)
    except Exception:
        pass  # Silently ignore errors to not disrupt execution


def _record_usage(
    agent_id: str,
    agent_name: str,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    duration_ms: float,
    project_id: str | None = None,
) -> None:
    """Record token usage to ObservabilityHub.

    Args:
        agent_id: Agent identifier
        agent_name: Human-readable agent name
        model_name: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        duration_ms: Duration in milliseconds
        project_id: Project ID if available
    """
    hub = _get_hub()
    if hub is None or hub._webhook is None:
        return

    try:
        from agentscope.observability import UsageCollector

        collector = UsageCollector(hub)
        collector.collect_raw(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration_seconds=duration_ms / 1000.0,
            agent_id=agent_id,
            agent_name=agent_name,
            model_name=model_name,
            project_id=project_id,
        )
    except Exception:
        pass  # Silently ignore errors


# ---------------------------------------------------------------------------
# Convenience Functions
# ---------------------------------------------------------------------------
def get_context() -> ObservabilityContext:
    """Get the global observability context.

    Returns:
        ObservabilityContext: Global context instance
    """
    return ObservabilityContext.get_instance()


def get_logger() -> Logger:
    """Get the global logger.

    Returns:
        Logger: Global logger instance
    """
    return get_context().logger


def init_observability(
    log_level: str = "INFO",
    log_format: str = "text",
    log_destination: str = "stdout",
    track_tokens: bool = True,
    track_timing: bool = True,
    **kwargs: Any,
) -> ObservabilityContext:
    """Initialize observability with configuration.

    Args:
        log_level: Minimum log level
        log_format: Output format (text, json, rich)
        log_destination: Output target
        track_tokens: Whether to track tokens
        track_timing: Whether to track timing
        **kwargs: Additional configuration options

    Returns:
        ObservabilityContext: Initialized context
    """
    config = ObservabilityConfig(
        log_level=log_level,
        log_format=log_format,
        log_destination=log_destination,
        track_tokens=track_tokens,
        track_timing=track_timing,
        **kwargs,
    )
    return ObservabilityContext.initialize(config)


# ---------------------------------------------------------------------------
# Domain Observers
# ---------------------------------------------------------------------------
class LLMObserver:
    """Observer for LLM calls.

    Provides detailed logging and metrics for LLM interactions.
    """

    def __init__(self, ctx: ObservabilityContext | None = None):
        """Initialize LLMObserver.

        Args:
            ctx: Observability context (uses global if None)
        """
        self._ctx = ctx

    @property
    def ctx(self) -> ObservabilityContext:
        """Get observability context."""
        return self._ctx or get_context()

    def on_call_start(self, label: str, message_count: int) -> float:
        """Called when LLM call starts.

        Args:
            label: Call label
            message_count: Number of messages in the request

        Returns:
            float: Start timestamp for duration calculation
        """
        self.ctx.logger.debug(f"[LLM:{label}] ▶ 调用开始 ({message_count} 条消息)")
        return time.perf_counter()

    def on_call_success(
        self,
        label: str,
        start_time: float,
        prompt_tokens: int,
        completion_tokens: int,
        response_length: int,
        model_name: str = "unknown",
        project_id: str | None = None,
    ) -> None:
        """Called when LLM call succeeds.

        Args:
            label: Call label
            start_time: Start timestamp from on_call_start
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            response_length: Length of response text
            model_name: Model name used for this call
            project_id: Project ID if available
        """
        duration = time.perf_counter() - start_time
        total_tokens = prompt_tokens + completion_tokens

        # Track in context
        self.ctx.track_llm_call(label, prompt_tokens, completion_tokens, duration)

        # Record to ObservabilityHub for webhook
        _record_usage(
            agent_id=label,
            agent_name=label,
            model_name=model_name,
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            duration_ms=duration * 1000,
            project_id=project_id,
        )

        # Log success
        if total_tokens > 0:
            self.ctx.logger.debug(
                f"[LLM:{label}] ✓ 完成 ({duration:.1f}s, {total_tokens:,} tokens)"
            )
        else:
            self.ctx.logger.debug(
                f"[LLM:{label}] ✓ 完成 ({duration:.1f}s, {response_length} chars)"
            )

    def on_call_error(self, label: str, error: Exception, attempt: int, max_attempts: int) -> None:
        """Called when LLM call fails.

        Args:
            label: Call label
            error: The exception that occurred
            attempt: Current attempt number (1-indexed)
            max_attempts: Maximum number of attempts
        """
        if attempt < max_attempts:
            self.ctx.logger.warn(
                f"[LLM:{label}] ⚠ 尝试 {attempt}/{max_attempts} 失败: {error}"
            )
        else:
            self.ctx.logger.error(
                f"[LLM:{label}] ✗ 全部 {max_attempts} 次尝试失败: {error}"
            )

    def on_json_parse_error(self, label: str, raw_length: int) -> None:
        """Called when JSON parsing fails.

        Args:
            label: Call label
            raw_length: Length of raw response
        """
        self.ctx.logger.warn(
            f"[LLM:{label}] ⚠ JSON 解析失败 (响应长度: {raw_length})"
        )


class ExecutionObserver:
    """Observer for execution loop.

    Provides progress tracking and status updates for the main execution flow.
    """

    # Phase display names and icons
    PHASE_DISPLAY = {
        "blueprint": ("📋", "Blueprint 设计"),
        "implementation": ("⚙️", "代码实现"),
        "validation": ("🔍", "代码验证"),
        "qa": ("✅", "QA 验收"),
        "finalization": ("📦", "项目整合"),
    }

    def __init__(self, ctx: ObservabilityContext | None = None):
        """Initialize ExecutionObserver.

        Args:
            ctx: Observability context (uses global if None)
        """
        self._ctx = ctx
        self._round_start: float = 0
        self._req_start: float = 0
        self._current_round: int = 0
        self._current_req: str | None = None

    @property
    def ctx(self) -> ObservabilityContext:
        """Get observability context."""
        return self._ctx or get_context()

    def on_execution_start(self, total_requirements: int, max_rounds: int) -> None:
        """Called when execution starts.

        Args:
            total_requirements: Total number of requirements
            max_rounds: Maximum number of rounds
        """
        self.ctx.logger.info(f"\n{'=' * 60}")
        self.ctx.logger.info(f"开始执行: {total_requirements} 个需求, 最多 {max_rounds} 轮")
        self.ctx.logger.info(f"{'=' * 60}")

    def on_round_start(
        self,
        round_idx: int,
        pending_count: int,
        project_id: str | None = None,
    ) -> None:
        """Called when a round starts.

        Args:
            round_idx: Round number (1-indexed)
            pending_count: Number of pending requirements
            project_id: Project ID if available
        """
        self._round_start = time.perf_counter()
        self._current_round = round_idx
        self.ctx.logger.info(f"\n{'─' * 40}")
        self.ctx.logger.info(f"执行轮次 Round {round_idx} ({pending_count} 个需求待处理)")
        self.ctx.logger.info(f"{'─' * 40}")

        # Record timeline event
        _record_timeline_event(
            event_type="task_status",
            project_id=project_id,
            message=f"Round {round_idx} started",
            round_index=round_idx,
            pending_count=pending_count,
        )

    def on_requirement_start(
        self,
        req_id: str,
        title: str,
        project_id: str | None = None,
    ) -> None:
        """Called when requirement processing starts.

        Args:
            req_id: Requirement ID
            title: Requirement title
            project_id: Project ID if available
        """
        self._req_start = time.perf_counter()
        self._current_req = req_id
        self.ctx.set_requirement(req_id)

        # Truncate long titles
        display_title = title[:50] + "..." if len(title) > 50 else title
        self.ctx.logger.info(f"\n[{req_id}] ▶ {display_title}")

        # Record timeline event
        _record_timeline_event(
            event_type="agent_start",
            project_id=project_id,
            node_id=req_id,
            message=f"Processing requirement: {title[:100]}",
            title=title,
        )

    def on_requirement_skip(self, req_id: str, reason: str) -> None:
        """Called when requirement is skipped.

        Args:
            req_id: Requirement ID
            reason: Reason for skipping
        """
        self.ctx.logger.info(f"[{req_id}] ⏭ 跳过: {reason}")

    def on_phase_start(self, req_id: str, phase: str) -> None:
        """Called when a phase starts.

        Args:
            req_id: Requirement ID
            phase: Phase name
        """
        self.ctx.set_phase(phase)
        icon, name = self.PHASE_DISPLAY.get(phase, ("▸", phase))
        self.ctx.logger.info(f"[{req_id}] {icon} {name}...")

    def on_phase_complete(self, req_id: str, phase: str, summary: str = "") -> None:
        """Called when a phase completes.

        Args:
            req_id: Requirement ID
            phase: Phase name
            summary: Optional summary text
        """
        if summary:
            # Truncate long summaries
            display = summary[:80] + "..." if len(summary) > 80 else summary
            self.ctx.logger.info(f"[{req_id}] → {display}")

    def on_validation_result(
        self,
        req_id: str,
        is_valid: bool,
        score: float,
        error_count: int = 0,
    ) -> None:
        """Called when validation completes.

        Args:
            req_id: Requirement ID
            is_valid: Whether validation passed
            score: Validation score (0-1)
            error_count: Number of errors found
        """
        if is_valid:
            self.ctx.logger.info(f"[{req_id}] ✓ 验证通过 (score={score:.0%})")
        else:
            self.ctx.logger.info(
                f"[{req_id}] ✗ 验证未通过 (score={score:.0%}, {error_count} 个错误)"
            )

    def on_requirement_complete(
        self,
        req_id: str,
        passed: bool,
        scores: dict[str, float],
        project_id: str | None = None,
    ) -> None:
        """Called when requirement processing completes.

        Args:
            req_id: Requirement ID
            passed: Whether requirement passed
            scores: Score breakdown by category
            project_id: Project ID if available
        """
        duration = time.perf_counter() - self._req_start
        status = "✓ 通过" if passed else "✗ 未通过"

        # Format scores
        score_parts = [f"{k}={v:.0%}" for k, v in scores.items() if v is not None]
        score_str = f" [{'/'.join(score_parts)}]" if score_parts else ""

        self.ctx.logger.info(
            f"[{req_id}] ◀ {status}{score_str} ({duration:.1f}s)"
        )

        # Record timeline event
        _record_timeline_event(
            event_type="agent_end",
            project_id=project_id,
            node_id=req_id,
            message=f"Requirement {'passed' if passed else 'failed'}",
            passed=passed,
            scores=scores,
            duration_ms=duration * 1000,
        )

        self._current_req = None
        self.ctx.set_requirement(None)

    def on_round_end(
        self,
        round_idx: int,
        passed_count: int,
        total_count: int,
    ) -> None:
        """Called when a round ends (parallel mode).

        Args:
            round_idx: Round number
            passed_count: Number of passed requirements
            total_count: Total number of requirements
        """
        duration = time.perf_counter() - self._round_start
        self.ctx.logger.info(f"\n--- Round {round_idx} 完成 ({duration:.1f}s) ---")
        self.ctx.logger.info(f"通过: {passed_count}/{total_count}")

        if passed_count < total_count:
            self.ctx.logger.info(f"待重试: {total_count - passed_count} 个需求")

    def on_round_complete(
        self,
        round_idx: int,
        passed_reqs: list[str],
        failed_reqs: list[str],
    ) -> None:
        """Called when a round completes.

        Args:
            round_idx: Round number
            passed_reqs: List of passed requirement IDs
            failed_reqs: List of failed requirement IDs
        """
        duration = time.perf_counter() - self._round_start
        total = len(passed_reqs) + len(failed_reqs)

        self.ctx.logger.info(f"\n--- Round {round_idx} 完成 ({duration:.1f}s) ---")
        self.ctx.logger.info(f"通过: {len(passed_reqs)}/{total}")

        if failed_reqs:
            self.ctx.logger.info(f"待重试: {', '.join(failed_reqs)}")

    def on_execution_complete(self, total_rounds: int, all_passed: bool) -> None:
        """Called when execution completes.

        Args:
            total_rounds: Number of rounds executed
            all_passed: Whether all requirements passed
        """
        if all_passed:
            self.ctx.logger.info(f"\n✅ 所有需求均达标，共执行 {total_rounds} 轮")
        else:
            self.ctx.logger.info(f"\n⚠️ 执行完成 ({total_rounds} 轮)，仍有需求未达标")

    # -------------------------------------------------------------------------
    # Infrastructure Events
    # -------------------------------------------------------------------------
    def on_http_server_start(self, port: int, url: str) -> None:
        """Called when HTTP server starts.

        Args:
            port: Server port
            url: Server URL
        """
        self.ctx.logger.info(f"[HTTP] 服务器已启动: {url}/")

    def on_http_server_error(self, error: Exception) -> None:
        """Called when HTTP server fails to start.

        Args:
            error: The exception that occurred
        """
        self.ctx.logger.warn(f"[HTTP] 服务器启动失败: {error}")

    def on_http_server_stop(self) -> None:
        """Called when HTTP server stops."""
        self.ctx.logger.info("[HTTP] 服务器已关闭")

    # -------------------------------------------------------------------------
    # Project Setup Events
    # -------------------------------------------------------------------------
    def on_scaffolding_start(self) -> None:
        """Called when project scaffolding starts."""
        self.ctx.logger.info("\n---- 生成项目基础文件 ----")

    def on_scaffolding_complete(self, file_count: int, files: list[str]) -> None:
        """Called when project scaffolding completes.

        Args:
            file_count: Number of files generated
            files: List of file paths
        """
        self.ctx.logger.info(f"[SCAFFOLD] 生成了 {file_count} 个基础文件:")
        for f in files[:5]:
            self.ctx.logger.info(f"  - {f}")
        if len(files) > 5:
            self.ctx.logger.info(f"  ... 及其他 {len(files) - 5} 个文件")

    def on_memory_initialized(self) -> None:
        """Called when project memory is initialized."""
        self.ctx.logger.info("[MEMORY] 项目记忆已初始化")

    def on_architecture_start(self) -> None:
        """Called when architecture contract generation starts."""
        self.ctx.logger.info("\n---- 生成架构契约 ----")

    def on_architecture_complete(self, endpoint_count: int) -> None:
        """Called when architecture contract generation completes.

        Args:
            endpoint_count: Number of API endpoints defined
        """
        self.ctx.logger.info(f"[ARCH] 架构契约已生成，包含 {endpoint_count} 个 API 端点")

    def on_skeleton_start(self) -> None:
        """Called when unified skeleton generation starts."""
        self.ctx.logger.info("\n---- 生成统一代码骨架 ----")

    def on_skeleton_complete(self, file_count: int, shared_count: int) -> None:
        """Called when skeleton generation completes.

        Args:
            file_count: Number of skeleton files generated
            shared_count: Number of files shared by multiple requirements
        """
        self.ctx.logger.info(
            f"[SKELETON] 生成了 {file_count} 个骨架文件 ({shared_count} 个共享模块)"
        )

    # -------------------------------------------------------------------------
    # Implementation Events
    # -------------------------------------------------------------------------
    def on_scaffold_mode_start(self, req_id: str) -> None:
        """Called when scaffold mode starts for a requirement.

        Args:
            req_id: Requirement ID
        """
        self.ctx.logger.info(f"[{req_id}] 使用脚手架模式初始化项目...")

    def on_scaffold_mode_fallback(self, req_id: str) -> None:
        """Called when scaffold mode falls back to stepwise.

        Args:
            req_id: Requirement ID
        """
        self.ctx.logger.info(f"[{req_id}] ⚠ 脚手架初始化失败，回退到 stepwise 模式")

    def on_scaffold_skip(self, req_id: str, reason: str) -> None:
        """Called when scaffold initialization is skipped (already initialized).

        Args:
            req_id: Requirement ID
            reason: Reason for skipping
        """
        self.ctx.logger.debug(f"[{req_id}] 跳过脚手架初始化: {reason}")

    def on_scaffold_sync(self, req_id: str, synced: int, source_files: int) -> None:
        """Called when scaffold files are synced.

        Args:
            req_id: Requirement ID
            synced: Total files synced
            source_files: Source files count (excluding node_modules etc)
        """
        self.ctx.logger.info(f"[{req_id}] 脚手架同步了 {synced} 个文件 (源文件: {source_files})")

    def on_agent_mode_start(self, req_id: str) -> None:
        """Called when agent mode starts.

        Args:
            req_id: Requirement ID
        """
        self.ctx.logger.info(f"[{req_id}] 使用 Agent 模式（ReActAgent + 文件工具）")

    def on_stepwise_mode_start(self, req_id: str, file_count: int, mode: str) -> None:
        """Called when stepwise generation mode starts.

        Args:
            req_id: Requirement ID
            file_count: Number of files to generate
            mode: Generation mode description
        """
        self.ctx.logger.info(f"[{req_id}] 使用{mode}模式，共 {file_count} 个文件待生成")

    def on_implementation_summary(self, req_id: str, summary: str) -> None:
        """Called with implementation summary.

        Args:
            req_id: Requirement ID
            summary: Developer summary text
        """
        self.ctx.logger.info(f"[{req_id}] Developer Summary：{summary}")

    def on_decisions_recorded(self, req_id: str, count: int) -> None:
        """Called when technical decisions are recorded.

        Args:
            req_id: Requirement ID
            count: Number of decisions recorded
        """
        self.ctx.logger.debug(f"[{req_id}] 记录了 {count} 个技术决策")

    # -------------------------------------------------------------------------
    # File Operations
    # -------------------------------------------------------------------------
    def on_multifile_start(self, req_id: str, file_count: int) -> None:
        """Called when multi-file mode starts.

        Args:
            req_id: Requirement ID
            file_count: Number of files to write
        """
        self.ctx.logger.info(f"[{req_id}] 多文件模式，共 {file_count} 个文件")

    def on_file_written(self, req_id: str, path: str, mode: str = "") -> None:
        """Called when a file is written.

        Args:
            req_id: Requirement ID
            path: File path
            mode: Write mode description (e.g., "Runtime")
        """
        suffix = f" ({mode})" if mode else ""
        self.ctx.logger.debug(f"[{req_id}]   -> {path}{suffix}")

    def on_files_synced(self, req_id: str, count: int) -> None:
        """Called when files are synced to local.

        Args:
            req_id: Requirement ID
            count: Number of files synced
        """
        self.ctx.logger.info(f"[{req_id}] 同步了 {count} 个文件")

    def on_setup_commands(self, req_id: str, count: int) -> None:
        """Called when setup commands are executed.

        Args:
            req_id: Requirement ID
            count: Number of commands
        """
        self.ctx.logger.info(f"[{req_id}] 执行初始化命令 ({count} 条)...")

    # -------------------------------------------------------------------------
    # Validation Events
    # -------------------------------------------------------------------------
    def on_validation_start(self, req_id: str) -> None:
        """Called when code validation starts.

        Args:
            req_id: Requirement ID
        """
        self.ctx.logger.info(f"[{req_id}] 执行代码验证...")

    def on_debug_start(self, req_id: str) -> None:
        """Called when debug analysis starts.

        Args:
            req_id: Requirement ID
        """
        self.ctx.logger.info(f"[{req_id}] Agent 分析并修复错误...")

    def on_debug_action(self, req_id: str, action: str) -> None:
        """Called for each debug action taken.

        Args:
            req_id: Requirement ID
            action: Description of the action
        """
        self.ctx.logger.debug(f"[{req_id}]   {action}")

    def on_revalidation_start(self, req_id: str) -> None:
        """Called when revalidation starts after debug.

        Args:
            req_id: Requirement ID
        """
        self.ctx.logger.info(f"[{req_id}] 重新验证...")

    def on_validation_error(self, req_id: str, error: str) -> None:
        """Called for each validation error.

        Args:
            req_id: Requirement ID
            error: Error description
        """
        self.ctx.logger.info(f"[{req_id}]   ❌ {error}")

    # -------------------------------------------------------------------------
    # Regression Detection Events
    # -------------------------------------------------------------------------
    def on_regression_check_batch_start(self, count: int, rids: list[str]) -> None:
        """Called when regression check batch starts.

        Args:
            count: Number of requirements to check
            rids: List of requirement IDs to check
        """
        self.ctx.logger.info(f"\n[REGRESSION] 检测回归影响，共 {count} 个已通过需求待验证")
        for rid in rids[:5]:
            self.ctx.logger.debug(f"[REGRESSION]   - {rid}")
        if len(rids) > 5:
            self.ctx.logger.debug(f"[REGRESSION]   ... 及其他 {len(rids) - 5} 个需求")

    def on_regression_check_start(self, req_id: str) -> None:
        """Called when regression check starts for a requirement.

        Args:
            req_id: Requirement ID being checked
        """
        self.ctx.logger.info(f"[{req_id}] 🔄 回归验证...")

    def on_regression_detected(self, req_id: str, prev_score: float, current_score: float) -> None:
        """Called when regression is detected.

        Args:
            req_id: Requirement ID with regression
            prev_score: Previous validation score
            current_score: Current validation score
        """
        self.ctx.logger.warn(
            f"[{req_id}] ⚠️ 检测到回归! 验证分数从 {prev_score:.0%} 降至 {current_score:.0%}"
        )
        self.ctx.logger.info(f"[{req_id}] 需要在下一轮重新实现")

    def on_regression_check_pass(self, req_id: str, score: float) -> None:
        """Called when regression check passes.

        Args:
            req_id: Requirement ID that passed
            score: Current validation score
        """
        self.ctx.logger.info(f"[{req_id}] ✓ 回归验证通过 (score={score:.0%})")

    def on_regression_batch_complete(self, regressed_count: int, regressed_rids: list[str]) -> None:
        """Called when regression check batch completes.

        Args:
            regressed_count: Number of regressions detected
            regressed_rids: List of requirement IDs with regression
        """
        if regressed_count > 0:
            self.ctx.logger.warn(
                f"[REGRESSION] ⚠️ 发现 {regressed_count} 个回归需求: {', '.join(regressed_rids)}"
            )
        else:
            self.ctx.logger.info("[REGRESSION] ✓ 无回归问题")

    # -------------------------------------------------------------------------
    # Finalization Events
    # -------------------------------------------------------------------------
    def on_finalization_start(self) -> None:
        """Called when project finalization starts."""
        self.ctx.logger.info("\n---- 项目整合与验证 ----")

    def on_finalization_complete(
        self,
        copied: int,
        merged: int,
        conflicts: int = 0,
    ) -> None:
        """Called when finalization completes.

        Args:
            copied: Number of files copied
            merged: Number of files merged
            conflicts: Number of conflicts resolved
        """
        self.ctx.logger.info(f"[FINALIZE] 已复制 {copied} 个文件，合并 {merged} 个文件")
        if conflicts > 0:
            self.ctx.logger.warn(f"[WARN] 发现 {conflicts} 个文件冲突，已选择最完整版本")

    def on_finalization_errors(self, count: int) -> None:
        """Called when file errors are found during finalization.

        Args:
            count: Number of file errors
        """
        self.ctx.logger.info(f"[FINALIZE] 发现 {count} 个文件操作错误，使用 LLM 分析...")

    def on_finalization_error_resolved(
        self,
        ignored: int,
        manual: int,
        manual_files: list[tuple[str, str]] | None = None,
    ) -> None:
        """Called when file errors are resolved.

        Args:
            ignored: Number of ignored errors
            manual: Number requiring manual attention
            manual_files: List of (path, reason) for manual files
        """
        if ignored > 0:
            self.ctx.logger.info(f"[FINALIZE] ⊘ 已忽略 {ignored} 个非关键文件错误")
        if manual > 0:
            self.ctx.logger.warn(f"[FINALIZE] ⚠ 有 {manual} 个文件需要人工处理")
            if manual_files:
                for path, reason in manual_files:
                    self.ctx.logger.warn(f"[FINALIZE]   - {path}: {reason}")

    def on_project_validation(self, passed: bool, missing: list[str] | None = None) -> None:
        """Called with project validation result.

        Args:
            passed: Whether validation passed
            missing: List of missing files (if failed)
        """
        if passed:
            self.ctx.logger.info("[VALIDATE] ✓ 项目完整性验证通过")
        else:
            if missing:
                self.ctx.logger.warn(f"[VALIDATE] ✗ 缺失文件: {', '.join(missing[:5])}")

    def on_supplemental_files(self, count: int) -> None:
        """Called when supplemental files are generated.

        Args:
            count: Number of files generated
        """
        self.ctx.logger.info(f"[SCAFFOLD] 补充生成了 {count} 个缺失文件")

    def on_project_warning(self, warning: str) -> None:
        """Called for project warnings.

        Args:
            warning: Warning message
        """
        self.ctx.logger.warn(f"[WARN] {warning}")

    def on_finalization_error(self, error: Exception) -> None:
        """Called when finalization fails.

        Args:
            error: The exception that occurred
        """
        self.ctx.logger.error(f"[ERROR] 项目整合失败: {error}")


class QAObserver:
    """Observer for QA validation.

    Provides detailed logging for QA file selection and validation.
    """

    def __init__(self, ctx: ObservabilityContext | None = None):
        """Initialize QAObserver.

        Args:
            ctx: Observability context (uses global if None)
        """
        self._ctx = ctx

    @property
    def ctx(self) -> ObservabilityContext:
        """Get observability context."""
        return self._ctx or get_context()

    def on_qa_start(self, req_id: str, title: str, criteria_count: int) -> None:
        """Called when QA validation starts.

        Args:
            req_id: Requirement ID
            title: Requirement title
            criteria_count: Number of acceptance criteria
        """
        display_title = title[:50] + "..." if len(title) > 50 else title
        self.ctx.logger.debug(
            f"[QA] ▶ 开始验收 {req_id}: {display_title} ({criteria_count} 条标准)"
        )

    def on_file_selection_start(self, total_files: int) -> None:
        """Called when file selection starts.

        Args:
            total_files: Total number of files to select from
        """
        self.ctx.logger.debug(f"[QA] LLM 文件选择: 从 {total_files} 个文件中选择...")

    def on_file_selection_complete(
        self,
        selected_files: list[tuple[str, float]],
        total_files: int,
    ) -> None:
        """Called when file selection completes.

        Args:
            selected_files: List of (file_path, relevance_score) tuples
            total_files: Total number of files considered
        """
        self.ctx.logger.debug(f"[QA] ✓ LLM 选择了 {len(selected_files)} 个相关文件:")

        # Show top files with relevance bars
        for path, score in selected_files[:10]:
            bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
            self.ctx.logger.debug(f"[QA]   [{bar}] {score:.2f} - {path}")

        if len(selected_files) > 10:
            self.ctx.logger.debug(f"[QA]   ... 及其他 {len(selected_files) - 10} 个文件")

    def on_file_selection_error(self, error: Exception) -> None:
        """Called when file selection fails.

        Args:
            error: The exception that occurred
        """
        self.ctx.logger.warn(f"[QA] ⚠️ LLM 文件选择失败: {error}")
        self.ctx.logger.debug("[QA] 回退到默认文件选择")

    def on_summary_built(self, file_count: int, total_files: int, char_count: int) -> None:
        """Called when file summary is built.

        Args:
            file_count: Number of files included in summary
            total_files: Total number of files
            char_count: Total characters in summary
        """
        self.ctx.logger.debug(
            f"[QA] ✓ 构建文件摘要完成: {file_count}/{total_files} 个文件, {char_count:,} 字符"
        )

    def on_playwright_test(self, url: str) -> None:
        """Called when Playwright test starts.

        Args:
            url: Test URL
        """
        self.ctx.logger.debug(f"[QA] 🎭 启动 Playwright 测试: {url}")

    def on_criterion_result(
        self,
        criterion_id: str,
        name: str,
        passed: bool,
        reason: str = "",
    ) -> None:
        """Called for each criterion result.

        Args:
            criterion_id: Criterion ID
            name: Criterion name
            passed: Whether criterion passed
            reason: Result reason
        """
        status = "✓" if passed else "✗"
        display_reason = reason[:60] + "..." if len(reason) > 60 else reason
        self.ctx.logger.debug(f"[QA]   {status} {criterion_id}: {display_reason}")

    def on_qa_complete(
        self,
        req_id: str,
        passed: bool,
        passed_count: int,
        total_count: int,
    ) -> None:
        """Called when QA validation completes.

        Args:
            req_id: Requirement ID
            passed: Overall pass status
            passed_count: Number of criteria passed
            total_count: Total number of criteria
        """
        status = "✓ 通过" if passed else "✗ 未通过"
        self.ctx.logger.debug(
            f"[QA] ◀ 验收完成 {req_id}: {status} ({passed_count}/{total_count} 标准通过)"
        )


class CLIObserver:
    """Observer for CLI entry point.

    Provides logging for initialization, component lifecycle, and results.
    """

    def __init__(self, ctx: ObservabilityContext | None = None):
        """Initialize CLIObserver.

        Args:
            ctx: Observability context (uses global if None)
        """
        self._ctx = ctx

    @property
    def ctx(self) -> ObservabilityContext:
        """Get observability context."""
        return self._ctx or get_context()

    # -------------------------------------------------------------------------
    # Initialization Events
    # -------------------------------------------------------------------------
    def on_llm_provider(self, provider: str) -> None:
        """Called when LLM provider is selected.

        Args:
            provider: Provider name
        """
        self.ctx.logger.info(f"使用 LLM 提供方: {provider}")

    def on_workspace_dir(self, path: str) -> None:
        """Called when workspace directory is set.

        Args:
            path: Workspace directory path
        """
        self.ctx.logger.info(f"[CLI] 工作区目录: {path}")

    def on_cleanup_old_files(self, count: int) -> None:
        """Called when old files are cleaned up.

        Args:
            count: Number of files cleaned
        """
        self.ctx.logger.info(f"[CLI] 清理工作区遗留文件: {count} 个项目")

    # -------------------------------------------------------------------------
    # Component Lifecycle Events
    # -------------------------------------------------------------------------
    def on_component_start(self, name: str) -> None:
        """Called when a component starts.

        Args:
            name: Component name
        """
        self.ctx.logger.info(f"[CLI] {name} 已启动")

    def on_component_connect(self, name: str) -> None:
        """Called when a component connects.

        Args:
            name: Component name
        """
        self.ctx.logger.info(f"[CLI] {name} 已连接")

    def on_component_stop(self, name: str) -> None:
        """Called when a component stops.

        Args:
            name: Component name
        """
        self.ctx.logger.info(f"[CLI] {name} 已停止")

    def on_component_disconnect(self, name: str) -> None:
        """Called when a component disconnects.

        Args:
            name: Component name
        """
        self.ctx.logger.info(f"[CLI] {name} 已断开")

    def on_component_cleanup(self, name: str) -> None:
        """Called when a component is cleaned up.

        Args:
            name: Component name
        """
        self.ctx.logger.info(f"[CLI] {name} 已清理")

    def on_component_error(self, name: str, error: Exception, action: str = "创建") -> None:
        """Called when a component fails.

        Args:
            name: Component name
            error: The exception that occurred
            action: Action that failed (e.g., "创建", "启动")
        """
        self.ctx.logger.warn(f"[CLI] {action} {name} 失败: {error}")

    def on_component_created(self, name: str) -> None:
        """Called when a component is created.

        Args:
            name: Component name
        """
        self.ctx.logger.info(f"[CLI] {name} 已创建")

    # -------------------------------------------------------------------------
    # Runtime Events
    # -------------------------------------------------------------------------
    def on_runtime_output(self, title: str, text: str) -> None:
        """Called to display runtime output.

        Args:
            title: Section title
            text: Output text
        """
        self.ctx.logger.info(f"\n========== {title} ==========")
        self.ctx.logger.info(text or "[无文本]")

    def on_deliverables_header(self) -> None:
        """Called before listing deliverables."""
        self.ctx.logger.info("\n========== 最终交付 ==========")

    def on_deliverable(
        self,
        req_id: str,
        path: str | None,
        project_id: str | None = None,
    ) -> None:
        """Called for each deliverable.

        Args:
            req_id: Requirement ID
            path: File path or None
            project_id: Project ID if available
        """
        if path:
            self.ctx.logger.info(f"- {req_id}: file://{path}")
        else:
            self.ctx.logger.info(f"- {req_id}: (无交付文件)")

        # Record timeline event for deliverable
        _record_timeline_event(
            event_type="task_status",
            project_id=project_id,
            node_id=req_id,
            message=f"Deliverable {'ready' if path else 'missing'}",
            deliverable_path=path,
        )

    def on_acceptance_header(self) -> None:
        """Called before listing acceptance results."""
        self.ctx.logger.info("\n========== 验收结果 ==========")

    def on_requirement_result(self, req_id: str) -> None:
        """Called for each requirement result header.

        Args:
            req_id: Requirement ID
        """
        self.ctx.logger.info(f"\n[{req_id}]")

    def on_criterion_result(self, passed: bool, name: str, reason: str) -> None:
        """Called for each criterion result.

        Args:
            passed: Whether criterion passed
            name: Criterion name
            reason: Result reason
        """
        status = "通过" if passed else "不通过"
        self.ctx.logger.info(f"{status} - {name}: {reason}")

    def on_pass_ratio(self, ratio: float) -> None:
        """Called to display pass ratio.

        Args:
            ratio: Pass ratio (0-1)
        """
        self.ctx.logger.info(f"通过率: {ratio:.2%}")

    # -------------------------------------------------------------------------
    # Error Events
    # -------------------------------------------------------------------------
    def on_runtime_workspace_error(self) -> None:
        """Called when RuntimeWorkspace fails to start."""
        self.ctx.logger.error("[CLI] RuntimeWorkspace 启动失败")
        self.ctx.logger.error("[CLI] 多租户模式要求所有文件操作在容器中进行")
        self.ctx.logger.error("[CLI] 请确保 Docker 正在运行")

    def on_docker_error(self) -> None:
        """Called to display Docker-related error."""
        self.ctx.logger.info("\n" + "=" * 50)
        self.ctx.logger.error("错误: 多租户模式要求 RuntimeWorkspace")
        self.ctx.logger.info("=" * 50)
        self.ctx.logger.info("请确保:")
        self.ctx.logger.info("  1. Docker Desktop 正在运行")
        self.ctx.logger.info("  2. Docker 镜像已构建 (agentscope/runtime-sandbox-filesystem)")
        self.ctx.logger.info("  3. 用户有权限访问 Docker")
        self.ctx.logger.info("=" * 50)

    def on_invalid_mcp_param(self, param: str, error: Exception) -> None:
        """Called when MCP parameter is invalid.

        Args:
            param: Invalid parameter value
            error: The exception that occurred
        """
        self.ctx.logger.warn(f"[CLI] 忽略无效 MCP 参数 '{param}': {error}")


class AgentReActObserver:
    """Observer for Agent ReAct loop execution.

    Provides detailed logging for agent's thinking, tool calls, and task board updates.
    """

    def __init__(self, ctx: ObservabilityContext | None = None):
        """Initialize AgentReActObserver.

        Args:
            ctx: Observability context (uses global if None)
        """
        self._ctx = ctx
        self._current_agent: str | None = None
        self._current_task: str | None = None

    @property
    def ctx(self) -> ObservabilityContext:
        """Get observability context."""
        return self._ctx or get_context()

    # -------------------------------------------------------------------------
    # ReAct Loop Events
    # -------------------------------------------------------------------------
    def on_react_start(self, agent_id: str, task_id: str, query: str) -> None:
        """Called when ReAct loop starts.

        Args:
            agent_id: Agent identifier
            task_id: Task/requirement ID
            query: User query or task description
        """
        self._current_agent = agent_id
        self._current_task = task_id
        query_preview = query[:100] + "..." if len(query) > 100 else query
        self.ctx.logger.info(f"\n[{agent_id}] ▶ 开始处理任务 {task_id}")
        self.ctx.logger.debug(f"[{agent_id}]   查询: {query_preview}")

    def on_thinking(self, agent_id: str, thought: str) -> None:
        """Called when agent produces thinking/reasoning.

        Args:
            agent_id: Agent identifier
            thought: Agent's thinking content
        """
        thought_preview = thought[:120] + "..." if len(thought) > 120 else thought
        # Clean up thought for display
        thought_clean = thought_preview.replace("\n", " ").strip()
        if thought_clean:
            self.ctx.logger.info(f"[{agent_id}]   💭 {thought_clean}")

    def on_tool_call_start(self, agent_id: str, tool_name: str, tool_input: dict) -> None:
        """Called when tool call starts.

        Args:
            agent_id: Agent identifier
            tool_name: Name of the tool being called
            tool_input: Tool input parameters
        """
        # Format tool input for display
        if tool_name == "claude_code_edit":
            prompt = tool_input.get("prompt", "")[:80]
            self.ctx.logger.info(f"[{agent_id}]   🔧 {tool_name}: {prompt}...")
        else:
            input_preview = str(tool_input)[:60]
            self.ctx.logger.info(f"[{agent_id}]   🔧 {tool_name}({input_preview}...)")

    def on_tool_call_end(
        self,
        agent_id: str,
        tool_name: str,
        result: str,
        success: bool,
        duration: float = 0.0,
    ) -> None:
        """Called when tool call completes.

        Args:
            agent_id: Agent identifier
            tool_name: Name of the tool
            result: Tool execution result
            success: Whether tool call succeeded
            duration: Execution duration in seconds
        """
        status = "✓" if success else "✗"
        result_preview = result[:80] + "..." if len(result) > 80 else result
        result_clean = result_preview.replace("\n", " ").strip()

        duration_str = f" ({duration:.1f}s)" if duration > 0 else ""
        self.ctx.logger.info(f"[{agent_id}]   {status} {tool_name}{duration_str}: {result_clean}")

    def on_iteration(self, agent_id: str, iteration: int, max_iters: int) -> None:
        """Called at each ReAct iteration.

        Args:
            agent_id: Agent identifier
            iteration: Current iteration number (1-indexed)
            max_iters: Maximum iterations allowed
        """
        self.ctx.logger.debug(f"[{agent_id}]   ⟳ 迭代 {iteration}/{max_iters}")

    def on_react_complete(
        self,
        agent_id: str,
        task_id: str,
        success: bool,
        summary: str,
        iterations: int = 0,
    ) -> None:
        """Called when ReAct loop completes.

        Args:
            agent_id: Agent identifier
            task_id: Task/requirement ID
            success: Whether task completed successfully
            summary: Summary of the result
            iterations: Number of iterations used
        """
        status = "✓ 完成" if success else "✗ 失败"
        summary_preview = summary[:100] + "..." if len(summary) > 100 else summary
        summary_clean = summary_preview.replace("\n", " ").strip()

        iter_str = f" ({iterations} 次迭代)" if iterations > 0 else ""
        self.ctx.logger.info(f"[{agent_id}] ◀ {status}{iter_str}")
        if summary_clean:
            self.ctx.logger.info(f"[{agent_id}]   结果: {summary_clean}")

        self._current_agent = None
        self._current_task = None

    # -------------------------------------------------------------------------
    # Task Board Events
    # -------------------------------------------------------------------------
    def on_task_board_update(self, agent_id: str, tasks: list[dict]) -> None:
        """Called when agent's task board is updated.

        Args:
            agent_id: Agent identifier
            tasks: List of task dictionaries with 'content' and 'status' keys
        """
        if not tasks:
            return

        self.ctx.logger.info(f"[{agent_id}]   📋 任务板 ({len(tasks)} 个任务):")
        status_icons = {
            "pending": "○",
            "in_progress": "◐",
            "completed": "●",
        }
        for task in tasks[:5]:
            status = task.get("status", "pending")
            icon = status_icons.get(status, "?")
            content = task.get("content", "")[:50]
            self.ctx.logger.info(f"[{agent_id}]     {icon} {content}")
        if len(tasks) > 5:
            self.ctx.logger.info(f"[{agent_id}]     ... 及其他 {len(tasks) - 5} 个任务")

    # -------------------------------------------------------------------------
    # Error Events
    # -------------------------------------------------------------------------
    def on_error(self, agent_id: str, error: Exception, context: str = "") -> None:
        """Called when an error occurs during ReAct execution.

        Args:
            agent_id: Agent identifier
            error: The exception that occurred
            context: Additional context about where the error occurred
        """
        ctx_str = f" ({context})" if context else ""
        self.ctx.logger.error(f"[{agent_id}]   ❌ 错误{ctx_str}: {error}")

    def on_fallback(self, agent_id: str, reason: str, fallback_action: str) -> None:
        """Called when agent falls back to alternative strategy.

        Args:
            agent_id: Agent identifier
            reason: Reason for fallback
            fallback_action: Description of fallback action
        """
        self.ctx.logger.warn(f"[{agent_id}]   ⚠ 回退: {reason}")
        self.ctx.logger.info(f"[{agent_id}]   → {fallback_action}")


# ---------------------------------------------------------------------------
# Observer Factories
# ---------------------------------------------------------------------------
def get_llm_observer() -> LLMObserver:
    """Get LLM observer using global context.

    Returns:
        LLMObserver: Observer instance
    """
    return LLMObserver()


def get_execution_observer() -> ExecutionObserver:
    """Get execution observer using global context.

    Returns:
        ExecutionObserver: Observer instance
    """
    return ExecutionObserver()


def get_qa_observer() -> QAObserver:
    """Get QA observer using global context.

    Returns:
        QAObserver: Observer instance
    """
    return QAObserver()


def get_cli_observer() -> CLIObserver:
    """Get CLI observer using global context.

    Returns:
        CLIObserver: Observer instance
    """
    return CLIObserver()


def get_agent_react_observer() -> AgentReActObserver:
    """Get agent ReAct observer using global context.

    Returns:
        AgentReActObserver: Observer instance
    """
    return AgentReActObserver()


class ClaudeCodeObserver:
    """Observer for Claude Code execution.

    Provides real-time logging during Claude Code CLI execution.
    """

    def __init__(self, ctx: ObservabilityContext | None = None):
        """Initialize ClaudeCodeObserver.

        Args:
            ctx: Observability context (uses global if None)
        """
        self._ctx = ctx
        self._current_agent: str | None = None
        self._message_count: int = 0

    @property
    def ctx(self) -> ObservabilityContext:
        """Get observability context."""
        return self._ctx or get_context()

    def set_agent(self, agent_id: str) -> None:
        """Set current agent for logging context.

        Args:
            agent_id: Agent identifier
        """
        self._current_agent = agent_id
        self._message_count = 0

    def on_progress(self, msg: dict) -> None:
        """Called for each stream-json message from Claude Code.

        Args:
            msg: JSON message from Claude Code CLI
        """
        self._message_count += 1
        msg_type = msg.get("type", "")
        agent_prefix = f"[{self._current_agent}]" if self._current_agent else "[ClaudeCode]"

        if msg_type == "assistant":
            # Assistant thinking/response
            content = msg.get("message", {}).get("content", [])
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        text = block.get("text", "")[:100]
                        if text:
                            self.ctx.logger.info(f"{agent_prefix}     📝 {text}...")
                    elif block.get("type") == "tool_use":
                        tool_name = block.get("name", "unknown")
                        self.ctx.logger.info(f"{agent_prefix}     🛠️ 调用工具: {tool_name}")

        elif msg_type == "user":
            # Tool results from Claude Code
            content = msg.get("message", {}).get("content", [])
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    tool_id = block.get("tool_use_id", "")[:8]
                    self.ctx.logger.debug(f"{agent_prefix}     ← 工具结果 ({tool_id})")

        elif msg_type == "system":
            # System messages
            subtype = msg.get("subtype", "")
            if subtype == "init":
                cwd = msg.get("cwd", "")
                self.ctx.logger.debug(f"{agent_prefix}     📂 工作目录: {cwd}")
            elif subtype:
                self.ctx.logger.debug(f"{agent_prefix}     ⚙️ {subtype}")

        elif msg_type == "result":
            # Final result
            result_text = msg.get("result", "")[:80]
            is_error = msg.get("is_error", False)
            if is_error:
                self.ctx.logger.info(f"{agent_prefix}     ❌ 错误: {result_text}")
            else:
                self.ctx.logger.info(f"{agent_prefix}     ✅ 完成 (共 {self._message_count} 条消息)")


def get_claude_code_observer() -> ClaudeCodeObserver:
    """Get Claude Code observer using global context.

    Returns:
        ClaudeCodeObserver: Observer instance
    """
    return ClaudeCodeObserver()


__all__ = [
    "LogLevel",
    "ObservabilityConfig",
    "TokenUsage",
    "TokenTracker",
    "TimingEntry",
    "TimingTracker",
    "Logger",
    "ObservabilityContext",
    "get_context",
    "get_logger",
    "init_observability",
    # Domain Observers
    "LLMObserver",
    "ExecutionObserver",
    "QAObserver",
    "CLIObserver",
    "AgentReActObserver",
    "ClaudeCodeObserver",
    "get_llm_observer",
    "get_execution_observer",
    "get_qa_observer",
    "get_cli_observer",
    "get_agent_react_observer",
    "get_claude_code_observer",
]
