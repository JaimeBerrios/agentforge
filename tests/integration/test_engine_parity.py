"""Pruebas de paridad funcional estricta: Motor nuevo vs. Línea base legacy."""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

from agentforge.core.types import LogStatus
from agentforge.logs.service import LogEngineService, extraer_log as nuevo_extraer_log
from legacy.ai_first_log_analyzer.log_analyzer import (
    analizar_archivo as legacy_analizar_archivo,
    extraer_log as legacy_extraer_log,
)


class TestEngineParity(unittest.TestCase):
    """Comprueba que el motor refactorizado replica exactamente el comportamiento del legado."""

    def setUp(self) -> None:
        self.fixtures_dir = Path(__file__).resolve().parent.parent / "fixtures"
        self.ruta_validos = self.fixtures_dir / "logs_validos.txt"
        self.ruta_invalidos = self.fixtures_dir / "logs_invalidos.txt"
        self.service = LogEngineService()

    def test_paridad_linea_por_linea_logs_validos(self) -> None:
        """Compara la extracción línea por línea del archivo logs_validos.txt."""
        lineas = self.ruta_validos.read_text(encoding="utf-8").splitlines()
        for idx, linea in enumerate(lineas, 1):
            with self.subTest(linea_idx=idx, linea=linea):
                resultado_legacy = legacy_extraer_log(linea)
                resultado_nuevo = nuevo_extraer_log(linea)
                resultado_service = self.service.process_line(linea).to_dict()

                self.assertEqual(resultado_nuevo, resultado_legacy)
                self.assertEqual(resultado_service, resultado_legacy)

    def test_paridad_linea_por_linea_logs_invalidos(self) -> None:
        """Compara la extracción línea por línea del archivo logs_invalidos.txt."""
        lineas = self.ruta_invalidos.read_text(encoding="utf-8").splitlines()
        for idx, linea in enumerate(lineas, 1):
            with self.subTest(linea_idx=idx, linea=linea):
                resultado_legacy = legacy_extraer_log(linea)
                resultado_nuevo = nuevo_extraer_log(linea)
                resultado_service = self.service.process_line(linea).to_dict()

                self.assertEqual(resultado_nuevo, resultado_legacy)
                self.assertEqual(resultado_service, resultado_legacy)

    def test_paridad_metricas_agregadas_logs_validos(self) -> None:
        """Compara las métricas agregadas producidas en logs_validos.txt."""
        stdout_trap = io.StringIO()
        orig_stdout = sys.stdout
        try:
            sys.stdout = stdout_trap
            legacy_res = legacy_analizar_archivo(self.ruta_validos)
        finally:
            sys.stdout = orig_stdout

        assert legacy_res is not None

        lineas = self.ruta_validos.read_text(encoding="utf-8").splitlines()
        nuevo_res = self.service.analyze_stream(lineas).to_dict()

        self.assertEqual(nuevo_res["total_eventos"], legacy_res["total_eventos"])
        self.assertEqual(nuevo_res["total_validas"], legacy_res["total_validas"])
        self.assertEqual(nuevo_res["total_anomalas"], legacy_res["total_anomalas"])
        self.assertEqual(
            nuevo_res["total_con_fecha_valida"],
            legacy_res["total_con_fecha_valida"],
        )
        self.assertEqual(
            nuevo_res["total_sin_fecha_valida"],
            legacy_res["total_sin_fecha_valida"],
        )
        self.assertEqual(nuevo_res["desglose_severidad"], legacy_res["desglose_severidad"])
        self.assertEqual(nuevo_res["desglose_anomalias"], legacy_res["desglose_anomalias"])

    def test_paridad_metricas_agregadas_logs_invalidos(self) -> None:
        """Compara las métricas agregadas producidas en logs_invalidos.txt."""
        stdout_trap = io.StringIO()
        orig_stdout = sys.stdout
        try:
            sys.stdout = stdout_trap
            legacy_res = legacy_analizar_archivo(self.ruta_invalidos)
        finally:
            sys.stdout = orig_stdout

        assert legacy_res is not None

        lineas = self.ruta_invalidos.read_text(encoding="utf-8").splitlines()
        nuevo_res = self.service.analyze_stream(lineas).to_dict()

        self.assertEqual(nuevo_res["total_eventos"], legacy_res["total_eventos"])
        self.assertEqual(nuevo_res["total_validas"], legacy_res["total_validas"])
        self.assertEqual(nuevo_res["total_anomalas"], legacy_res["total_anomalas"])
        self.assertEqual(
            nuevo_res["total_con_fecha_valida"],
            legacy_res["total_con_fecha_valida"],
        )
        self.assertEqual(
            nuevo_res["total_sin_fecha_valida"],
            legacy_res["total_sin_fecha_valida"],
        )
        self.assertEqual(nuevo_res["desglose_severidad"], legacy_res["desglose_severidad"])
        self.assertEqual(nuevo_res["desglose_anomalias"], legacy_res["desglose_anomalias"])


class TestBoundaryCases(unittest.TestCase):
    """Casos límite adicionales para certificar la solidez del motor."""

    def setUp(self) -> None:
        self.service = LogEngineService()

    def test_bisiestos_regla_gregoriana_completa(self) -> None:
        casos = [
            ("[INFO] 2024-02-29 Bisiesto divisible por 4", True),
            ("[INFO] 2023-02-29 No bisiesto no divisible por 4", False),
            ("[INFO] 2000-02-29 Bisiesto fin de siglo divisible por 400", True),
            ("[INFO] 1900-02-29 No bisiesto fin de siglo no divisible por 400", False),
            ("[INFO] 2100-02-29 No bisiesto fin de siglo futuro", False),
        ]
        for linea, es_valido in casos:
            with self.subTest(linea=linea, es_valido=es_valido):
                entry = self.service.process_line(linea)
                legacy_dict = legacy_extraer_log(linea)
                self.assertEqual(entry.to_dict(), legacy_dict)
                esperado = LogStatus.VALIDA if es_valido else LogStatus.MAL_FORMATEADA
                self.assertEqual(entry.estado, esperado)

    def test_limite_dias_meses_30_vs_31(self) -> None:
        # Abril tiene 30 días
        valido_abril = "[INFO] 2024-04-30 Último día de abril"
        invalido_abril = "[INFO] 2024-04-31 Día 31 inexistente en abril"

        self.assertEqual(self.service.process_line(valido_abril).estado, LogStatus.VALIDA)
        self.assertEqual(
            self.service.process_line(invalido_abril).estado,
            LogStatus.MAL_FORMATEADA,
        )

        # Mayo tiene 31 días
        valido_mayo = "[INFO] 2024-05-31 Día 31 válido en mayo"
        invalido_mayo = "[INFO] 2024-05-32 Día 32 inexistente"

        self.assertEqual(self.service.process_line(valido_mayo).estado, LogStatus.VALIDA)
        self.assertEqual(
            self.service.process_line(invalido_mayo).estado,
            LogStatus.MAL_FORMATEADA,
        )

    def test_mensajes_con_caracteres_especiales_y_unicode(self) -> None:
        lineas = [
            "[INFO] 2024-05-10 Transacción #9941 exitosa: $100.50 USD (OK)",
            "[WARNING] 2024-05-10 CPU al 99% — ¡Alerta crítica de rendimiento!",
            "· [ERROR] 2024-05-10 JSON inválido: {'key': 'val', syntax_error}",
        ]
        for linea in lineas:
            with self.subTest(linea=linea):
                entry = self.service.process_line(linea)
                legacy_dict = legacy_extraer_log(linea)
                self.assertEqual(entry.to_dict(), legacy_dict)
                self.assertEqual(entry.estado, LogStatus.VALIDA)


if __name__ == "__main__":
    unittest.main()
