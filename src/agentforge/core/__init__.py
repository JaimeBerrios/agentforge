"""Módulo core de AgentForge: contratos, modelos de dominio, configuración y runner."""

from __future__ import annotations

from agentforge.core.config import (
    AgentConfig,
    load_agent_config,
    parse_agent_config,
)
from agentforge.core.contracts import (
    AgentProtocol,
    AgentRunResult,
    ExecutionContext,
    LLMProviderProtocol,
    LLMResponse,
    SkillProtocol,
    SkillResult,
)
from agentforge.core.exceptions import (
    AgentForgeError,
    ConfigError,
    DuplicateSkillError,
    ExecutionError,
    InvalidConfigError,
    SkillNotFoundError,
    SkillRegistryError,
    UnauthorizedSkillError,
)
from agentforge.core.registry import SkillRegistry
from agentforge.core.runner import (
    ConfigurableAgent,
    SequentialAgentRunner,
)
from agentforge.core.types import (
    LogMetrics,
    LogStatus,
    ParsedLogEntry,
    RawLogMatch,
    SeverityLevel,
)

__all__ = [
    "AgentConfig",
    "AgentForgeError",
    "AgentProtocol",
    "AgentRunResult",
    "ConfigError",
    "ConfigurableAgent",
    "DuplicateSkillError",
    "ExecutionContext",
    "ExecutionError",
    "InvalidConfigError",
    "LLMProviderProtocol",
    "LLMResponse",
    "LogMetrics",
    "LogStatus",
    "ParsedLogEntry",
    "RawLogMatch",
    "SequentialAgentRunner",
    "SeverityLevel",
    "SkillNotFoundError",
    "SkillProtocol",
    "SkillRegistry",
    "SkillRegistryError",
    "SkillResult",
    "UnauthorizedSkillError",
    "load_agent_config",
    "parse_agent_config",
]
