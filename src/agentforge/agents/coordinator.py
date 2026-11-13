"""Coordinador determinista de agentes especializados para AgentForge."""

from __future__ import annotations

from typing import Any

from agentforge.agents.analysis_agent import LogAnalysisAgent
from agentforge.agents.triage_agent import IncidentTriageAgent
from agentforge.agents.types import CoordinatedExecutionResult, TriageResult


class AgentCoordinator:
    """Coordinador secuencial entre LogAnalysisAgent e IncidentTriageAgent."""

    def __init__(
        self,
        analysis_agent: LogAnalysisAgent | None = None,
        triage_agent: IncidentTriageAgent | None = None,
    ) -> None:
        self._analysis_agent = analysis_agent or LogAnalysisAgent()
        self._triage_agent = triage_agent or IncidentTriageAgent()

    @property
    def analysis_agent(self) -> LogAnalysisAgent:
        return self._analysis_agent

    @property
    def triage_agent(self) -> IncidentTriageAgent:
        return self._triage_agent

    def coordinate(self, log_input: Any) -> CoordinatedExecutionResult:
        """Coordina el flujo completo: análisis de logs seguido de triaje de incidentes.

        Garantías:
        1. No utiliza variables globales para transmitir datos entre agentes.
        2. Preserva de forma inmutable los resultados de ambos agentes.
        3. Maneja fallos explícitamente: si el análisis falla, el triaje no se ejecuta.
        """
        # Paso 1: Ejecución de LogAnalysisAgent
        analysis_result = self._analysis_agent.run(log_input)

        if not analysis_result.success:
            return CoordinatedExecutionResult(
                success=False,
                analysis_result=analysis_result,
                triage_result=None,
                errors=analysis_result.errors,
            )

        # Paso 2: Ejecución de IncidentTriageAgent consumiendo la salida del paso 1
        triage_agent_result = self._triage_agent.run(analysis_result)

        if not triage_agent_result.success:
            return CoordinatedExecutionResult(
                success=False,
                analysis_result=analysis_result,
                triage_result=None,
                errors=triage_agent_result.errors,
            )

        final_triage: TriageResult = triage_agent_result.final_output

        return CoordinatedExecutionResult(
            success=True,
            analysis_result=analysis_result,
            triage_result=final_triage,
            errors=(),
        )
