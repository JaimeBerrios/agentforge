"""Definición de modelos de dominio y tipos base para AgentForge."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class SeverityLevel(StrEnum):
    """Niveles de severidad permitidos en los registros de log."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class LogStatus(StrEnum):
    """Taxonomía de estados del análisis determinista de logs."""

    VALIDA = "valida"
    INCOMPLETA = "incompleta"
    MAL_FORMATEADA = "mal_formateada"


@dataclass(frozen=True, slots=True)
class RawLogMatch:
    """Resultado intermedio de la extracción sintáctica mediante patrones."""

    raw_severity: str | None = None
    raw_date: str | None = None
    raw_message: str | None = None
    matched: bool = False


@dataclass(frozen=True, slots=True)
class ParsedLogEntry:
    """Entidad de dominio que representa un registro de log validado."""

    estado: LogStatus
    severidad: str | None = None
    fecha: str | None = None
    mensaje: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        """Exporta la entidad al formato de diccionario compatible con el legado."""
        return {
            "estado": str(self.estado.value if isinstance(self.estado, LogStatus) else self.estado),
            "severidad": self.severidad,
            "fecha": self.fecha,
            "mensaje": self.mensaje,
        }


@dataclass(slots=True)
class LogMetrics:
    """Contenedor de métricas agregadas del análisis determinista."""

    total_eventos: int = 0
    total_validas: int = 0
    total_con_fecha_valida: int = 0
    total_sin_fecha_valida: int = 0
    desglose_severidad: dict[str, int] = field(
        default_factory=lambda: {
            SeverityLevel.INFO.value: 0,
            SeverityLevel.WARNING.value: 0,
            SeverityLevel.ERROR.value: 0,
        }
    )
    total_anomalas: int = 0
    desglose_anomalias: dict[str, int] = field(
        default_factory=lambda: {
            LogStatus.INCOMPLETA.value: 0,
            LogStatus.MAL_FORMATEADA.value: 0,
        }
    )

    @property
    def porcentaje_validas(self) -> float:
        """Calcula el porcentaje de eventos válidos sobre el total."""
        return (self.total_validas / self.total_eventos * 100) if self.total_eventos > 0 else 0.0

    @property
    def porcentaje_anomalas(self) -> float:
        """Calcula el porcentaje de eventos anómalos sobre el total."""
        return (self.total_anomalas / self.total_eventos * 100) if self.total_eventos > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Exporta las métricas al formato de diccionario compatible con el orquestador legado."""
        return {
            "total_eventos": self.total_eventos,
            "total_validas": self.total_validas,
            "total_con_fecha_valida": self.total_con_fecha_valida,
            "total_sin_fecha_valida": self.total_sin_fecha_valida,
            "desglose_severidad": dict(self.desglose_severidad),
            "total_anomalas": self.total_anomalas,
            "desglose_anomalias": dict(self.desglose_anomalias),
            "porcentaje_validas": self.porcentaje_validas,
            "porcentaje_anomalas": self.porcentaje_anomalas,
        }
