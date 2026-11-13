"""Pruebas unitarias para la interfaz de línea de comandos (CLI) de AgentForge."""

from __future__ import annotations

import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from agentforge.cli.main import build_parser, run_cli


class TestAgentForgeCLI(unittest.TestCase):
    """Verificación de argumentos, salida estructurada y códigos de salida de la CLI."""

    def setUp(self) -> None:
        self.fixtures_dir = Path(__file__).resolve().parent.parent / "fixtures"
        self.valid_logs = str(self.fixtures_dir / "logs_validos.txt")
        self.invalid_logs = str(self.fixtures_dir / "logs_invalidos.txt")

    def test_parser_construccion_y_argumentos(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            ["analyze", "--file", "dummy.log", "--llm", "fake", "--format", "json"]
        )
        self.assertEqual(args.command, "analyze")
        self.assertEqual(args.file, "dummy.log")
        self.assertEqual(args.llm, "fake")
        self.assertEqual(args.format, "json")

    def test_analyze_logs_validos_salida_texto(self) -> None:
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            exit_code = run_cli(["analyze", "--file", self.valid_logs])

        self.assertEqual(exit_code, 0)
        output = stdout_buf.getvalue()
        self.assertIn("AGENTFORGE - REPORTE DE ANÁLISIS DE INCIDENTES", output)
        self.assertIn("PRIORIDAD DETERMINISTA ASIGNADA: [HIGH]", output)
        self.assertIn("Errores operacionales en logs válidos: 3", output)

    def test_analyze_logs_invalidos_salida_json(self) -> None:
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            exit_code = run_cli(["analyze", "--file", self.invalid_logs, "--format", "json"])

        self.assertEqual(exit_code, 0)
        output = stdout_buf.getvalue()
        data = json.loads(output)

        self.assertTrue(data["coordinated_result"]["success"])
        self.assertEqual(data["triage"]["priority"], "CRITICAL")
        self.assertEqual(data["triage"]["format_anomaly_count"], 16)
        self.assertEqual(data["triage"]["operational_error_count"], 0)

    def test_analyze_con_llm_fake(self) -> None:
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            exit_code = run_cli(["analyze", "--file", self.valid_logs, "--llm", "fake"])

        self.assertEqual(exit_code, 0)
        output = stdout_buf.getvalue()
        self.assertIn("ASISTENCIA ANALÍTICA LLM", output)
        self.assertIn("fake_llm", output)
        self.assertIn("[Hipótesis no confirmada]", output)

    def test_archivo_no_existente_retorna_error(self) -> None:
        stderr_buf = io.StringIO()
        with patch("sys.stderr", stderr_buf):
            exit_code = run_cli(["analyze", "--file", "archivo_inexistente_123.log"])

        self.assertEqual(exit_code, 1)
        self.assertIn("no existe", stderr_buf.getvalue())

    def test_directorio_en_vez_de_archivo_retorna_error(self) -> None:
        stderr_buf = io.StringIO()
        with patch("sys.stderr", stderr_buf):
            exit_code = run_cli(["analyze", "--file", str(self.fixtures_dir)])

        self.assertEqual(exit_code, 1)
        self.assertIn("no es un archivo regular", stderr_buf.getvalue())

    def test_sin_subcomando_imprime_ayuda_y_retorna_cero(self) -> None:
        stdout_buf = io.StringIO()
        with patch("sys.stdout", stdout_buf):
            exit_code = run_cli([])
        self.assertEqual(exit_code, 0)
