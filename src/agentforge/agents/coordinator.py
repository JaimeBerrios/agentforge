"""Coordinador determinista de agentes especializados para AgentForge."""

from __future__ import annotations

from typing import Any

from agentforge.agents.analysis_agent import LogAnalysisAgent
from agentforge.agents.llm_agent import LLMAnalysisAgent
from agentforge.agents.triage_agent import IncidentTriageAgent
from agentforge.agents.types import CoordinatedExecutionResult, LLMAnalysisResult, TriageResult


class AgentCoordinator:
    """Coordinador secuencial entre LogAnalysisAgent, IncidentTriageAgent y LLMAnalysisAgent."""

    def __init__(
        self,
        analysis_agent: LogAnalysisAgent | None = None,
        triage_agent: IncidentTriageAgent | None = None,
        llm_agent: LLMAnalysisAgent | None = None,
    ) -> None:
        self._analysis_agent = analysis_agent or LogAnalysisAgent()
        self._triage_agent = triage_agent or IncidentTriageAgent()
        self._llm_agent = llm_agent

    @property
    def analysis_agent(self) -> LogAnalysisAgent:
        return self._analysis_agent

    @property
    def triage_agent(self) -> IncidentTriageAgent:
        return self._triage_agent

    @property
    def llm_agent(self) -> LLMAnalysisAgent | None:
        return self._llm_agent

    def coordinate(self, log_input: Any) -> CoordinatedExecutionResult:
        """Coordina el flujo: análisis de logs, triaje determinista y asistencia LLM opcional.

        Garantías:
        1. No utiliza variables globales para transmitir datos entre agentes.
        2. Preserva de forma inmutable los resultados de todos los agentes.
        3. Maneja fallos explícitamente: si el análisis falla, el triaje no se ejecuta.
        4. Si el agente LLM falla, el resultado determinista previo permanece intacto.
        """
        # Paso 1: Ejecución de LogAnalysisAgent
        analysis_result = self._analysis_agent.run(log_input)

        if not analysis_result.success:
            return CoordinatedExecutionResult(
                success=False,
                analysis_result=analysis_result,
                triage_result=None,
                llm_result=None,
                execution_order=("log_analysis_agent",),
                errors=analysis_result.errors,
            )

        # Paso 2: Ejecución de IncidentTriageAgent consumiendo la salida del paso 1
        triage_agent_result = self._triage_agent.run(analysis_result)

        if not triage_agent_result.success:
            return CoordinatedExecutionResult(
                success=False,
                analysis_result=analysis_result,
                triage_result=None,
                llm_result=None,
                execution_order=("log_analysis_agent", "incident_triage_agent"),
                errors=triage_agent_result.errors,
            )

        final_triage: TriageResult = triage_agent_result.final_output

        # Paso 3 (Opcional): Ejecución de LLMAnalysisAgent asistido
        llm_result: LLMAnalysisResult | None = None
        execution_order = ("log_analysis_agent", "incident_triage_agent")

        if self._llm_agent is not None:
            execution_order = (
                "log_analysis_agent",
                "incident_triage_agent",
                "llm_analysis_agent",
            )
            intermediate_result = CoordinatedExecutionResult(
                success=True,
                analysis_result=analysis_result,
                triage_result=final_triage,
                llm_result=None,
                execution_order=("log_analysis_agent", "incident_triage_agent"),
                errors=(),
            )
            llm_agent_run = self._llm_agent.run(intermediate_result)
            if isinstance(llm_agent_run.final_output, LLMAnalysisResult):
                llm_result = llm_agent_run.final_output

        return CoordinatedExecutionResult(
            success=True,
            analysis_result=analysis_result,
            triage_result=final_triage,
            llm_result=llm_result,
            execution_order=execution_order,
            errors=(),
        )
