"""Shared data models for cmdo."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(Enum):
    SAFE = "safe"
    CAUTION = "caution"
    DANGEROUS = "dangerous"


class UserAction(Enum):
    EXECUTE = "execute"
    EXECUTE_STEPWISE = "step"
    EDIT = "edit"
    COPY = "copy"
    CANCEL = "cancel"


@dataclass
class ShellContext:
    os: str = ""
    shell: str = ""
    cwd: str = ""
    cwd_listing: list[str] = field(default_factory=list)
    user: str = ""
    path_tools: list[str] = field(default_factory=list)
    env_hints: dict[str, str] = field(default_factory=dict)
    git_branch: str | None = None


@dataclass
class CommandResult:
    command: str = ""
    explanation: str = ""
    risk_level: RiskLevel = RiskLevel.SAFE
    risk_reason: str | None = None
    alternatives: list[str] = field(default_factory=list)
    is_multi_step: bool = False
    estimated_duration: str | None = None
    confidence: float = 1.0


@dataclass
class ExecutionResult:
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    duration: float = 0.0
    was_interrupted: bool = False


@dataclass
class Config:
    provider: str = "openai"
    api_key: str = ""
    model: str = "gpt-5-mini"
    base_url: str = ""
    auto_confirm_safe: bool = False
    danger_confirmation: str = "type"
    color: bool = True
    explanation: bool = True
