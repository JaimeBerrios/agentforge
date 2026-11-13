"""Módulo de validación semántica determinista y catalogación de estados."""

from __future__ import annotations

from datetime import datetime

from agentforge.core.types import LogStatus, ParsedLogEntry, RawLogMatch


class LogValidator:
    """Validador de reglas semánticas, calendario real y completitud de datos."""

    def __init__(self, date_format: str = "%Y-%m-%d") -> None:
        self._date_format = date_format

    def validate(self, match: RawLogMatch) -> ParsedLogEntry:
        """Aplica las reglas deterministas para clasificar el estado del registro.

        Reglas aplicadas:
        1. Si la línea no coincidió morfológicamente, es MAL_FORMATEADA (sin campos).
        2. Si la fecha está presente, se valida astronómicamente con strptime en calendario real.
           Si la fecha no existe (ej. 30 feb, 29 feb en no bisiesto), pasa a MAL_FORMATEADA.
        3. Si la fecha o el mensaje están ausentes o vacíos y la fecha era sintácticamente válida,
           pasa a INCOMPLETA.
        4. Si cumple fecha válida y mensaje presente, se clasifica como VALIDA.
        """
        if not match.matched:
            return ParsedLogEntry(
                estado=LogStatus.MAL_FORMATEADA,
                severidad=None,
                fecha=None,
                mensaje=None,
            )

        mensaje = (match.raw_message or "").strip()
        fecha = match.raw_date
        estado = LogStatus.VALIDA

        if fecha is not None:
            try:
                datetime.strptime(fecha, self._date_format)
            except ValueError:
                estado = LogStatus.MAL_FORMATEADA

        if estado == LogStatus.VALIDA and (fecha is None or not mensaje):
            estado = LogStatus.INCOMPLETA

        return ParsedLogEntry(
            estado=estado,
            severidad=match.raw_severity,
            fecha=fecha,
            mensaje=mensaje,
        )


def validate_match(match: RawLogMatch) -> ParsedLogEntry:
    """Función de conveniencia para validación semántica directa de un match."""
    return LogValidator().validate(match)
