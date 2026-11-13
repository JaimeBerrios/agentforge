"""Implementación de la skill incident-reporter."""

from __future__ import annotations

from typing import Any

from agentforge.core.contracts import ExecutionContext, SkillProtocol, SkillResult
from agentforge.skills.types import AnomalyDetectorOutput, IncidentReport


class IncidentReporterSkill(SkillProtocol):
    """Capacidad modular para consolidar hechos objetivos y reportar incidentes."""

    @property
    def name(self) -> str:
        return "incident-reporter"

    @property
    def description(self) -> str:
        return (
            "Genera reportes estructurados basados estrictamente en hechos observados "
            "y métricas cuantitativas, sin suposiciones ni invención de causas."
        )

    def _extract_anomaly_data(self, raw_input: Any) -> AnomalyDetectorOutput:
        """Valida que la entrada corresponda al análisis previo de anomalías."""
        if isinstance(raw_input, AnomalyDetectorOutput):
            return raw_input

        raise TypeError(
            f"Tipo de entrada no compatible para incident-reporter: {type(raw_input).__name__}. "
            "Se requiere un objeto AnomalyDetectorOutput generado por anomaly-detector."
        )

    def execute(self, context: ExecutionContext) -> SkillResult:
        """Construye un reporte objetivo distinguiendo métricas de hechos observados."""
        raw_input = context.get_latest_output()

        try:
            data = self._extract_anomaly_data(raw_input)
        except Exception as err:
            return SkillResult(
                skill_name=self.name,
                success=False,
                error=f"Error de entrada en {self.name}: {err}",
            )

        m = data.metrics

        facts = {
            "total_events": data.total_analyzed,
            "valid_events": data.total_valid,
            "valid_percentage": round(m.porcentaje_validas, 2),
            "anomalous_events": data.total_anomalies,
            "anomalous_percentage": round(m.porcentaje_anomalas, 2),
            "incomplete_records": len(data.incomplete_entries),
            "malformed_records": len(data.malformed_entries),
            "calendar_valid_dates": m.total_con_fecha_valida,
            "calendar_invalid_dates": m.total_sin_fecha_valida,
            "severity_counts": dict(m.desglose_severidad),
            "operational_errors": len(data.valid_error_events),
            "operational_warnings": len(data.valid_warning_events),
        }

        # Generación de observaciones estrictamente factuales (sin conjeturas)
        observations: list[str] = []

        if data.total_analyzed == 0:
            observations.append("El lote de entrada está vacío; no se procesaron registros.")
        else:
            if data.total_valid == data.total_analyzed:
                observations.append(
                    f"Integridad estructural del 100%: los {data.total_analyzed} eventos "
                    "cumplen con el formato y calendario gregoriano."
                )
            else:
                observations.append(
                    f"Se detectaron {data.total_anomalies} anomalías ({m.porcentaje_anomalas:.1f}% "
                    f"del total de {data.total_analyzed} registros)."
                )

            if data.incomplete_entries:
                observations.append(
                    f"Existen {len(data.incomplete_entries)} registros incompletos "
                    "que carecen de fecha válida o mensaje."
                )

            if data.malformed_entries:
                observations.append(
                    f"Existen {len(data.malformed_entries)} registros mal formateados por "
                    "violación de corchetes, delimitadores o fechas astronómicamente inexistentes."
                )

            if data.valid_error_events:
                observations.append(
                    f"Se identificaron {len(data.valid_error_events)} eventos operacionales "
                    "con severidad ERROR en registros estructuralmente válidos."
                )

        # Construcción de resumen textual estructurado
        lineas_resumen = [
            f"=== REPORTE DE INCIDENTE AGÉNTICO (Agente: {context.agent_id}) ===",
            f"Total analizado: {data.total_analyzed} registros",
            f"  - Válidos y completos : {data.total_valid} ({m.porcentaje_validas:.1f}%)",
            f"  - Registros anómalos  : {data.total_anomalies} ({m.porcentaje_anomalas:.1f}%)",
            "Validación cronológica:",
            f"  - Fechas válidas en calendario : {m.total_con_fecha_valida}",
            f"  - Fechas inválidas o ausentes  : {m.total_sin_fecha_valida}",
            "Eventos operacionales en registros válidos:",
            f"  - ERROR   : {len(data.valid_error_events)}",
            f"  - WARNING : {len(data.valid_warning_events)}",
            f"  - INFO    : {len(data.valid_info_events)}",
            "Observaciones factuales:",
        ]
        for obs in observations:
            lineas_resumen.append(f"  • {obs}")
        lineas_resumen.append("=" * 64)

        summary_text = "\n".join(lineas_resumen)
        report_id = f"REP-{context.agent_id}-{data.total_analyzed}"

        report = IncidentReport(
            report_id=report_id,
            facts=facts,
            observations=tuple(observations),
            summary_text=summary_text,
            metadata={"agent_id": context.agent_id},
        )

        return SkillResult(
            skill_name=self.name,
            success=True,
            output=report,
            metadata={"report_id": report_id},
        )
