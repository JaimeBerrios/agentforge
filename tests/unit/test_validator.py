"""Pruebas unitarias para el componente LogValidator."""

from __future__ import annotations

import unittest

from agentforge.core.types import LogStatus, RawLogMatch
from agentforge.logs.validator import LogValidator, validate_match


class TestLogValidator(unittest.TestCase):
    """Verificación de las reglas semánticas, calendario real y completitud."""

    def setUp(self) -> None:
        self.validator = LogValidator()

    def test_validacion_evento_completo_valido(self) -> None:
        raw = RawLogMatch(
            raw_severity="INFO",
            raw_date="2024-05-10",
            raw_message="Operación exitosa",
            matched=True,
        )
        entry = self.validator.validate(raw)
        self.assertEqual(entry.estado, LogStatus.VALIDA)
        self.assertEqual(entry.severidad, "INFO")
        self.assertEqual(entry.fecha, "2024-05-10")
        self.assertEqual(entry.mensaje, "Operación exitosa")

    def test_validacion_fecha_inexistente_30_febrero(self) -> None:
        raw = RawLogMatch(
            raw_severity="ERROR",
            raw_date="2024-02-30",
            raw_message="Error de fecha",
            matched=True,
        )
        entry = self.validator.validate(raw)
        self.assertEqual(entry.estado, LogStatus.MAL_FORMATEADA)
        self.assertEqual(entry.severidad, "ERROR")
        self.assertEqual(entry.fecha, "2024-02-30")

    def test_validacion_fecha_ano_no_bisiesto_29_febrero(self) -> None:
        raw = RawLogMatch(
            raw_severity="WARNING",
            raw_date="2023-02-29",
            raw_message="No bisiesto",
            matched=True,
        )
        entry = self.validator.validate(raw)
        self.assertEqual(entry.estado, LogStatus.MAL_FORMATEADA)

    def test_validacion_fecha_ano_bisiesto_valido_29_febrero(self) -> None:
        raw = RawLogMatch(
            raw_severity="INFO",
            raw_date="2024-02-29",
            raw_message="Bisiesto válido",
            matched=True,
        )
        entry = validate_match(raw)
        self.assertEqual(entry.estado, LogStatus.VALIDA)

    def test_incompleta_por_falta_de_fecha(self) -> None:
        raw = RawLogMatch(
            raw_severity="WARNING",
            raw_date=None,
            raw_message="Alerta sin fecha",
            matched=True,
        )
        entry = self.validator.validate(raw)
        self.assertEqual(entry.estado, LogStatus.INCOMPLETA)
        self.assertEqual(entry.severidad, "WARNING")
        self.assertIsNone(entry.fecha)

    def test_incompleta_por_mensaje_vacio_o_espacios(self) -> None:
        raw = RawLogMatch(
            raw_severity="INFO",
            raw_date="2024-05-10",
            raw_message="   ",
            matched=True,
        )
        entry = self.validator.validate(raw)
        self.assertEqual(entry.estado, LogStatus.INCOMPLETA)
        self.assertEqual(entry.mensaje, "")

    def test_no_coincidente_sintacticamente_produce_mal_formateada(self) -> None:
        raw = RawLogMatch(matched=False)
        entry = self.validator.validate(raw)
        self.assertEqual(entry.estado, LogStatus.MAL_FORMATEADA)
        self.assertIsNone(entry.severidad)
        self.assertIsNone(entry.fecha)
        self.assertIsNone(entry.mensaje)


if __name__ == "__main__":
    unittest.main()
