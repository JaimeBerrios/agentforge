"""Implementación de la skill anomaly-detector."""

from __future__ import annotations

from typing import Any

from agentforge.core.contracts import ExecutionContext, SkillProtocol, SkillResult
from agentforge.core.types import LogMetrics, LogStatus, ParsedLogEntry, SeverityLevel
from agentforge.skills.types import AnomalyDetectorOutput, LogParserOutput


class AnomalyDetectorSkill(SkillProtocol):
    """Capacidad modular para detección y categorización determinista de anomalías."""

    @property
    def name(self) -> str:
        return "anomaly-detector"

    @property
    def description(self) -> str:
        return (
            "Analiza entradas de log identificando anomalías estructurales "
            "y diferenciando severidad de negocio frente a validez de formato."
        )

    def _extract_entries(self, raw_input: Any) -> tuple[tuple[ParsedLogEntry, ...], LogMetrics]:
        """Extrae de forma segura las entradas parseadas y métricas desde la salida anterior."""
        if isinstance(raw_input, LogParserOutput):
            return raw_input.entries, raw_input.metrics

        if isinstance(raw_input, dict):
            raw_entries = raw_input.get("entries")
            if raw_entries is None or not isinstance(raw_entries, (list, tuple)):
                raise TypeError(
                    "La entrada no contiene una colección válida bajo la clave 'entries'."
                )
            metrics = raw_input.get("metrics")
            if not isinstance(metrics, LogMetrics):
                metrics = LogMetrics()
            return tuple(raw_entries), metrics

        raise TypeError(
            f"Tipo de entrada no compatible para anomaly-detector: {type(raw_input).__name__}. "
            "Se requiere LogParserOutput o un diccionario con 'entries'."
        )

    def execute(self, context: ExecutionContext) -> SkillResult:
        """Clasifica registros distinguiendo anomalías de eventos de error de negocio."""
        raw_input = context.get_latest_output()

        try:
            entries, metrics = self._extract_entries(raw_input)
        except Exception as err:
            return SkillResult(
                skill_name=self.name,
                success=False,
                error=f"Error de entrada en {self.name}: {err}",
            )

        incomplete: list[ParsedLogEntry] = []
        malformed: list[ParsedLogEntry] = []
        valid_errors: list[ParsedLogEntry] = []
        valid_warnings: list[ParsedLogEntry] = []
        valid_info: list[ParsedLogEntry] = []

        for entry in entries:
            # Validación de estado determinista
            if entry.estado == LogStatus.INCOMPLETA:
                incomplete.append(entry)
            elif entry.estado == LogStatus.MAL_FORMATEADA:
                malformed.append(entry)
            elif entry.estado == LogStatus.VALIDA:
                # Distinción crítica: un evento ERROR u operativamente crítico
                # en un log válido NO es una anomalía de formato.
                if entry.severidad == SeverityLevel.ERROR.value:
                    valid_errors.append(entry)
                elif entry.severidad == SeverityLevel.WARNING.value:
                    valid_warnings.append(entry)
                elif entry.severidad == SeverityLevel.INFO.value:
                    valid_info.append(entry)

        total_analyzed = len(entries)
        total_valid = len(valid_errors) + len(valid_warnings) + len(valid_info)
        total_anomalies = len(incomplete) + len(malformed)
        anomaly_rate = (total_anomalies / total_analyzed * 100) if total_analyzed > 0 else 0.0

        output = AnomalyDetectorOutput(
            total_analyzed=total_analyzed,
            total_valid=total_valid,
            total_anomalies=total_anomalies,
            anomaly_rate=anomaly_rate,
            incomplete_entries=tuple(incomplete),
            malformed_entries=tuple(malformed),
            valid_error_events=tuple(valid_errors),
            valid_warning_events=tuple(valid_warnings),
            valid_info_events=tuple(valid_info),
            metrics=metrics,
        )

        return SkillResult(
            skill_name=self.name,
            success=True,
            output=output,
            metadata={
                "anomalies_detected": total_anomalies,
                "operational_errors_detected": len(valid_errors),
            },
        )
