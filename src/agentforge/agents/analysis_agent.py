"""Agente especializado en análisis integral y determinista de logs."""

from __future__ import annotations

from typing import Any

from agentforge.core.config import AgentConfig
from agentforge.core.contracts import AgentProtocol, AgentRunResult
from agentforge.core.registry import SkillRegistry
from agentforge.core.runner import SequentialAgentRunner
from agentforge.skills.anomaly_detector import AnomalyDetectorSkill
from agentforge.skills.incident_reporter import IncidentReporterSkill
from agentforge.skills.log_parser import LogParserSkill

DEFAULT_ANALYSIS_AGENT_CONFIG = AgentConfig(
    agent_id="log_analysis_agent",
    name="Log Analysis Agent",
    description="Agente especializado en parsing, detección de anomalías y reporte de incidentes.",
    skills=("log-parser", "anomaly-detector", "incident-reporter"),
    execution_order=("log-parser", "anomaly-detector", "incident-reporter"),
    parameters={"strict_mode": True},
)


class LogAnalysisAgent(AgentProtocol):
    """Agente que coordina la ingestión, análisis y reporte de logs sin duplicar lógica."""

    def __init__(
        self,
        config: AgentConfig | None = None,
        registry: SkillRegistry | None = None,
    ) -> None:
        self._config = config or DEFAULT_ANALYSIS_AGENT_CONFIG
        self._registry = registry or SkillRegistry()
        self._ensure_skills_registered()
        self._runner = SequentialAgentRunner(self._config, self._registry)

    @property
    def agent_id(self) -> str:
        return self._config.agent_id

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def description(self) -> str:
        return self._config.description

    @property
    def config(self) -> AgentConfig:
        return self._config

    def _ensure_skills_registered(self) -> None:
        """Garantiza que las tres capacidades requeridas estén en el registro."""
        if not self._registry.has("log-parser"):
            self._registry.register(LogParserSkill())
        if not self._registry.has("anomaly-detector"):
            self._registry.register(AnomalyDetectorSkill())
        if not self._registry.has("incident-reporter"):
            self._registry.register(IncidentReporterSkill())

    def run(self, initial_input: Any = None) -> AgentRunResult:
        """Ejecuta el pipeline determinista sobre la entrada provista."""
        return self._runner.run(initial_input)
