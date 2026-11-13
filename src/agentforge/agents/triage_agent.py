"""Agente especializado en triaje operativo y priorización determinista de incidentes."""

from __future__ import annotations

from typing import Any

from agentforge.agents.types import TriagePriority, TriageResult, TriageThresholds
from agentforge.core.contracts import AgentProtocol, AgentRunResult, SkillResult
from agentforge.skills.types import IncidentReport


class IncidentTriageAgent(AgentProtocol):
    """Agente que evalúa reportes de incidentes y asigna niveles de prioridad basados en reglas."""

    def __init__(
        self,
        agent_id: str = "incident_triage_agent",
        name: str = "Incident Triage Agent",
        description: str = "Agente de triaje y priorización operativa determinista.",
        thresholds: TriageThresholds | None = None,
    ) -> None:
        self._agent_id = agent_id
        self._name = name
        self._description = description
        self._thresholds = thresholds or TriageThresholds()

    @property
    def agent_id(self) -> str:
        return self._agent_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def thresholds(self) -> TriageThresholds:
        return self._thresholds

    def _extract_report(self, raw_input: Any) -> IncidentReport:
        """Extrae y valida el IncidentReport desde la entrada provista."""
        if isinstance(raw_input, AgentRunResult):
            if not raw_input.success:
                raise ValueError("El resultado del análisis previo indica fallo en la ejecución.")
            raw_input = raw_input.final_output

        if isinstance(raw_input, IncidentReport):
            return raw_input

        raise TypeError(
            f"Entrada incompatible para {self.name}: se esperaba AgentRunResult o "
            f"IncidentReport, se recibió {type(raw_input).__name__}."
        )

    def evaluate_triage(self, report: IncidentReport) -> TriageResult:
        """Aplica reglas deterministas cuantitativas para asignar prioridad y recomendaciones."""
        facts = report.facts
        op_errors = int(facts.get("operational_errors", 0))
        op_warnings = int(facts.get("operational_warnings", 0))
        anom_rate = float(facts.get("anomalous_percentage", 0.0))
        anom_events = int(facts.get("anomalous_events", 0))
        incomplete = int(facts.get("incomplete_records", 0))
        malformed = int(facts.get("malformed_records", 0))
        total_events = int(facts.get("total_events", 0))

        reasons: list[str] = []
        recommendations: list[str] = []
        priority: TriagePriority

        # Regla 1: CRITICAL
        if (
            op_errors >= self._thresholds.critical_operational_errors
            or anom_rate >= self._thresholds.critical_anomaly_rate
        ):
            priority = TriagePriority.CRITICAL
            if op_errors >= self._thresholds.critical_operational_errors:
                reasons.append(
                    f"Eventos operacionales ERROR ({op_errors}) superan el umbral crítico "
                    f"({self._thresholds.critical_operational_errors})."
                )
            if anom_rate >= self._thresholds.critical_anomaly_rate:
                reasons.append(
                    f"La tasa de anomalías estructurales ({anom_rate:.1f}%) supera o iguala el "
                    f"umbral crítico ({self._thresholds.critical_anomaly_rate:.1f}%)."
                )

        # Regla 2: HIGH
        elif (
            op_errors >= self._thresholds.high_operational_errors
            or anom_rate >= self._thresholds.high_anomaly_rate
        ):
            priority = TriagePriority.HIGH
            if op_errors >= self._thresholds.high_operational_errors:
                reasons.append(
                    f"Se detectaron {op_errors} eventos operacionales ERROR en registros válidos "
                    f"(umbral alto: {self._thresholds.high_operational_errors})."
                )
            if anom_rate >= self._thresholds.high_anomaly_rate:
                reasons.append(
                    f"La tasa de anomalías ({anom_rate:.1f}%) supera el umbral alto "
                    f"({self._thresholds.high_anomaly_rate:.1f}%)."
                )

        # Regla 3: MEDIUM
        elif (
            anom_rate >= self._thresholds.medium_anomaly_rate
            or op_warnings >= self._thresholds.medium_warnings_count
            or incomplete > 0
        ):
            priority = TriagePriority.MEDIUM
            if anom_rate >= self._thresholds.medium_anomaly_rate:
                reasons.append(
                    f"Tasa de anomalías moderada ({anom_rate:.1f}%) detectada "
                    f"(umbral medio: {self._thresholds.medium_anomaly_rate:.1f}%)."
                )
            if op_warnings >= self._thresholds.medium_warnings_count:
                reasons.append(
                    f"Presencia de {op_warnings} advertencias operacionales WARNING registradas."
                )
            if incomplete > 0:
                reasons.append(
                    f"Presencia de {incomplete} registros incompletos que requieren revisión."
                )

        # Regla 4: LOW
        else:
            priority = TriagePriority.LOW
            reasons.append(
                f"Lote nominal: {total_events} registros procesados sin errores operacionales "
                f"críticos ni anomalías significativas (tasa: {anom_rate:.1f}%)."
            )

        # Generación determinista de recomendaciones basadas exclusivamente en hechos
        if op_errors > 0:
            recommendations.append(
                f"Auditar los componentes que emitieron los {op_errors} eventos ERROR válidos "
                "para identificar fallos en servicios o dependencias."
            )

        if malformed > 0:
            recommendations.append(
                f"Revisar emisores de logs que produjeron {malformed} registros mal formateados "
                "por corchetes rotos o fechas inexistentes."
            )

        if incomplete > 0:
            recommendations.append(
                f"Inspeccionar el mecanismo de recolección de logs para evitar el truncamiento "
                f"de {incomplete} eventos que carecen de fecha o mensaje."
            )

        if not recommendations:
            recommendations.append(
                "No se requieren acciones correctivas inmediatas; continuar monitoreo rutinario."
            )

        return TriageResult(
            priority=priority,
            reasons=tuple(reasons),
            operational_error_count=op_errors,
            format_anomaly_count=anom_events,
            recommendations=tuple(recommendations),
        )

    def run(self, initial_input: Any = None) -> AgentRunResult:
        """Ejecuta el triaje operativo sobre el reporte analizado."""
        try:
            report = self._extract_report(initial_input)
            triage_result = self.evaluate_triage(report)
        except Exception as err:
            error_msg = f"Error en ejecución de {self.name}: {err}"
            return AgentRunResult(
                agent_id=self.agent_id,
                success=False,
                step_results=(),
                final_output=None,
                errors=(error_msg,),
            )

        step_result = SkillResult(
            skill_name="incident_triage",
            success=True,
            output=triage_result,
            metadata={"priority": triage_result.priority.value},
        )

        return AgentRunResult(
            agent_id=self.agent_id,
            success=True,
            step_results=(step_result,),
            final_output=triage_result,
        )
