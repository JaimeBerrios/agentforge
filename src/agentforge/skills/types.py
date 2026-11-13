"""Tipos y modelos de datos estructurados para las skills de AgentForge."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agentforge.core.types import LogMetrics, ParsedLogEntry


@dataclass(frozen=True, slots=True)
class LogParserOutput:
    """Salida estructurada e inmutable de la skill log-parser."""

    entries: tuple[ParsedLogEntry, ...]
    metrics: LogMetrics
    total_lines: int

    def to_dict(self) -> dict[str, Any]:
        """Convierte la salida a un diccionario serializable."""
        return {
            "entries": [entry.to_dict() for entry in self.entries],
            "metrics": self.metrics.to_dict(),
            "total_lines": self.total_lines,
        }


@dataclass(frozen=True, slots=True)
class AnomalyDetectorOutput:
    """Salida estructurada de la skill anomaly-detector diferenciando severidad de validez."""

    total_analyzed: int
    total_valid: int
    total_anomalies: int
    anomaly_rate: float
    incomplete_entries: tuple[ParsedLogEntry, ...]
    malformed_entries: tuple[ParsedLogEntry, ...]
    valid_error_events: tuple[ParsedLogEntry, ...]
    valid_warning_events: tuple[ParsedLogEntry, ...]
    valid_info_events: tuple[ParsedLogEntry, ...]
    metrics: LogMetrics

    def to_dict(self) -> dict[str, Any]:
        """Convierte el análisis a diccionario serializable."""
        return {
            "total_analyzed": self.total_analyzed,
            "total_valid": self.total_valid,
            "total_anomalies": self.total_anomalies,
            "anomaly_rate": self.anomaly_rate,
            "incomplete_count": len(self.incomplete_entries),
            "malformed_count": len(self.malformed_entries),
            "valid_errors_count": len(self.valid_error_events),
            "valid_warnings_count": len(self.valid_warning_events),
            "valid_info_count": len(self.valid_info_events),
            "metrics": self.metrics.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class IncidentReport:
    """Reporte estructurado e inmutable de la skill incident-reporter basado en hechos."""

    report_id: str
    facts: dict[str, Any]
    observations: tuple[str, ...]
    summary_text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convierte el reporte a formato de diccionario."""
        return {
            "report_id": self.report_id,
            "facts": dict(self.facts),
            "observations": list(self.observations),
            "summary_text": self.summary_text,
            "metadata": dict(self.metadata),
        }
