"""Servicio de dominio para el motor de análisis y validación de logs."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from agentforge.core.types import LogMetrics, ParsedLogEntry
from agentforge.logs.metrics import LogMetricsAccumulator
from agentforge.logs.parser import LogParser
from agentforge.logs.validator import LogValidator


class LogEngineService:
    """Servicio orquestador del ciclo de vida determinista de análisis de logs."""

    def __init__(
        self,
        parser: LogParser | None = None,
        validator: LogValidator | None = None,
    ) -> None:
        self._parser = parser or LogParser()
        self._validator = validator or LogValidator()

    def process_line(self, line: str) -> ParsedLogEntry:
        """Parsea y valida una línea de log individual."""
        raw_match = self._parser.parse_line(line)
        return self._validator.validate(raw_match)

    def analyze_stream(self, lines: Iterable[str]) -> LogMetrics:
        """Analiza una secuencia iterable de líneas acumulando métricas estadísticas."""
        accumulator = LogMetricsAccumulator()
        for line in lines:
            entry = self.process_line(line)
            accumulator.process_entry(entry)
        return accumulator.metrics


# Instancia por defecto para reutilización
_default_service = LogEngineService()


def extraer_log(linea: str) -> dict[str, str | None]:
    """Función de compatibilidad directa con la firma de ai-first-log-analyzer."""
    return _default_service.process_line(linea).to_dict()


def analizar_lineas(lineas: Iterable[str]) -> dict[str, Any]:
    """Analiza una colección de líneas retornando el diccionario de métricas."""
    return _default_service.analyze_stream(lineas).to_dict()
