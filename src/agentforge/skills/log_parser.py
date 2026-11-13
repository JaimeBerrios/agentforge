"""Implementación de la skill log-parser."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from agentforge.core.contracts import ExecutionContext, SkillProtocol, SkillResult
from agentforge.logs.metrics import LogMetricsAccumulator
from agentforge.logs.service import LogEngineService
from agentforge.skills.types import LogParserOutput


class LogParserSkill(SkillProtocol):
    """Capacidad modular para parseo y validación de logs en memoria."""

    def __init__(self, service: LogEngineService | None = None) -> None:
        self._service = service or LogEngineService()

    @property
    def name(self) -> str:
        return "log-parser"

    @property
    def description(self) -> str:
        return (
            "Procesa secuencias de texto de logs mediante el motor determinista LogEngineService."
        )

    def _extract_lines(self, raw_input: Any) -> list[str]:
        """Extrae y valida una lista de cadenas de texto a partir de la entrada recibida."""
        if raw_input is None:
            return []

        if isinstance(raw_input, str):
            return raw_input.splitlines()

        if isinstance(raw_input, dict):
            candidate = raw_input.get("lines", raw_input.get("logs"))
            if candidate is None:
                raise TypeError(
                    "El diccionario de entrada debe contener la clave 'lines' o 'logs'."
                )
            raw_input = candidate

        if isinstance(raw_input, Iterable) and not isinstance(raw_input, (bytes, bytearray)):
            lines: list[str] = []
            for idx, item in enumerate(raw_input):
                if not isinstance(item, str):
                    tipo_recibido = type(item).__name__
                    raise TypeError(
                        f"El elemento en el índice {idx} no es texto (tipo: {tipo_recibido})."
                    )
                lines.append(item)
            return lines

        raise TypeError(
            f"Tipo de entrada no soportado para log-parser: {type(raw_input).__name__}. "
            "Se espera str, list[str] o dict con clave 'lines'."
        )

    def execute(self, context: ExecutionContext) -> SkillResult:
        """Ejecuta el parseo determinista sobre la entrada del contexto."""
        raw_input = context.get_latest_output()

        try:
            lines = self._extract_lines(raw_input)
        except Exception as err:
            return SkillResult(
                skill_name=self.name,
                success=False,
                error=f"Error de validación de entrada en {self.name}: {err}",
            )

        accumulator = LogMetricsAccumulator()
        parsed_entries = []

        for line in lines:
            entry = self._service.process_line(line)
            parsed_entries.append(entry)
            accumulator.process_entry(entry)

        output = LogParserOutput(
            entries=tuple(parsed_entries),
            metrics=accumulator.metrics,
            total_lines=len(parsed_entries),
        )

        return SkillResult(
            skill_name=self.name,
            success=True,
            output=output,
            metadata={"total_processed": len(parsed_entries)},
        )
