"""Pruebas unitarias para el componente LogParser."""

from __future__ import annotations

import unittest

from agentforge.logs.parser import LogParser, parse_line


class TestLogParser(unittest.TestCase):
    """Verificación aislada de la extracción sintáctica de patrones de log."""

    def setUp(self) -> None:
        self.parser = LogParser()

    def test_linea_estandar_completa(self) -> None:
        raw = self.parser.parse_line("[INFO] 2024-05-10 Servicio iniciado")
        self.assertTrue(raw.matched)
        self.assertEqual(raw.raw_severity, "INFO")
        self.assertEqual(raw.raw_date, "2024-05-10")
        self.assertEqual(raw.raw_message, "Servicio iniciado")

    def test_linea_con_prefijo_vineta(self) -> None:
        raw = parse_line("· [WARNING] 2025-01-10 Alerta de disco")
        self.assertTrue(raw.matched)
        self.assertEqual(raw.raw_severity, "WARNING")
        self.assertEqual(raw.raw_date, "2025-01-10")
        self.assertEqual(raw.raw_message, "Alerta de disco")

    def test_linea_solo_severidad_sin_fecha_ni_mensaje(self) -> None:
        raw = self.parser.parse_line("[ERROR]")
        self.assertTrue(raw.matched)
        self.assertEqual(raw.raw_severity, "ERROR")
        self.assertIsNone(raw.raw_date)
        self.assertIsNone(raw.raw_message)

    def test_linea_sin_fecha_con_mensaje(self) -> None:
        raw = self.parser.parse_line("· [WARNING] Intento fallido de login")
        self.assertTrue(raw.matched)
        self.assertEqual(raw.raw_severity, "WARNING")
        self.assertIsNone(raw.raw_date)
        self.assertEqual(raw.raw_message, "Intento fallido de login")

    def test_linea_no_coincidente_sin_corchetes(self) -> None:
        raw = self.parser.parse_line("INFO 2024-05-10 Sin corchetes")
        self.assertFalse(raw.matched)
        self.assertIsNone(raw.raw_severity)
        self.assertIsNone(raw.raw_date)
        self.assertIsNone(raw.raw_message)

    def test_linea_no_coincidente_espacios_internos_corchetes(self) -> None:
        raw = self.parser.parse_line("[ INFO ] 2024-05-10 Espacios internos")
        self.assertFalse(raw.matched)

    def test_linea_vacia(self) -> None:
        raw = self.parser.parse_line("")
        self.assertFalse(raw.matched)


if __name__ == "__main__":
    unittest.main()
