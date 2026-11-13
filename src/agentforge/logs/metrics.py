"""Módulo de agregación de métricas deterministas para análisis de logs."""

from __future__ import annotations

from agentforge.core.types import LogMetrics, LogStatus, ParsedLogEntry


class LogMetricsAccumulator:
    """Acumulador determinista de métricas y contadores estadísticos."""

    def __init__(self) -> None:
        self._metrics = LogMetrics()

    @property
    def metrics(self) -> LogMetrics:
        """Obtiene las métricas actuales acumuladas."""
        return self._metrics

    def process_entry(self, entry: ParsedLogEntry) -> None:
        """Procesa una entrada validada actualizando los contadores independientes."""
        self._metrics.total_eventos += 1

        # Conteo de severidad identificada
        if entry.severidad is not None and entry.severidad in self._metrics.desglose_severidad:
            self._metrics.desglose_severidad[entry.severidad] += 1

        # Validación de presencia y validez de fecha
        if entry.fecha is not None and entry.estado != LogStatus.MAL_FORMATEADA:
            self._metrics.total_con_fecha_valida += 1
        else:
            self._metrics.total_sin_fecha_valida += 1

        # Conteo de validez general
        if entry.estado == LogStatus.VALIDA:
            self._metrics.total_validas += 1
        elif entry.estado in (LogStatus.INCOMPLETA, LogStatus.MAL_FORMATEADA):
            self._metrics.total_anomalas += 1
            estado_key = str(entry.estado.value if hasattr(entry.estado, "value") else entry.estado)
            if estado_key in self._metrics.desglose_anomalias:
                self._metrics.desglose_anomalias[estado_key] += 1

    def reset(self) -> None:
        """Reinicia todos los contadores de métricas."""
        self._metrics = LogMetrics()
