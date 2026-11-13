"""Módulo de parsing sintáctico determinista de líneas de log."""

from __future__ import annotations

import re

from agentforge.core.types import RawLogMatch

# Expresión regular canónica preservada del proyecto original
LOG_LINE_PATTERN: re.Pattern[str] = re.compile(
    r"(?:·[ \t]*)?\[(INFO|WARNING|ERROR)\]"
    r"(?:[ \t]+([0-9]{4}-[0-9]{2}-[0-9]{2})(?=[ \t]|$))?"
    r"(?:[ \t]+([^\r\n]*))?"
)


class LogParser:
    """Parser morfológico responsable exclusivamente de la extracción sintáctica."""

    def __init__(self, pattern: re.Pattern[str] | None = None) -> None:
        self._pattern = pattern or LOG_LINE_PATTERN

    def parse_line(self, line: str) -> RawLogMatch:
        """Extrae los componentes sintácticos de una línea sin validar semántica."""
        coincidencia = self._pattern.fullmatch(line.rstrip("\r\n"))
        if coincidencia is None:
            return RawLogMatch(matched=False)

        severidad, fecha, mensaje = coincidencia.groups()
        return RawLogMatch(
            raw_severity=severidad,
            raw_date=fecha,
            raw_message=mensaje,
            matched=True,
        )


def parse_line(line: str) -> RawLogMatch:
    """Función de conveniencia para parseo de una línea individual."""
    return LogParser().parse_line(line)
