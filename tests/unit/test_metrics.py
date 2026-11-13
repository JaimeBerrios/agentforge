"""Pruebas unitarias para el componente LogMetricsAccumulator."""

from __future__ import annotations

import unittest

from agentforge.core.types import LogStatus, ParsedLogEntry
from agentforge.logs.metrics import LogMetricsAccumulator


class TestLogMetricsAccumulator(unittest.TestCase):
    """Verificación de la agregación de métricas y cálculos porcentuales."""

    def setUp(self) -> None:
        self.accumulator = LogMetricsAccumulator()

    def test_acumulador_vacio_porcentajes_cero(self) -> None:
        metrics = self.accumulator.metrics
        self.assertEqual(metrics.total_eventos, 0)
        self.assertEqual(metrics.porcentaje_validas, 0.0)
        self.assertEqual(metrics.porcentaje_anomalas, 0.0)

    def test_procesamiento_entradas_mixtas(self) -> None:
        # 1 válida
        self.accumulator.process_entry(
            ParsedLogEntry(
                estado=LogStatus.VALIDA,
                severidad="INFO",
                fecha="2024-05-10",
                mensaje="Evento válido",
            )
        )
        # 1 incompleta (con fecha válida pero sin mensaje)
        self.accumulator.process_entry(
            ParsedLogEntry(
                estado=LogStatus.INCOMPLETA,
                severidad="ERROR",
                fecha="2024-05-10",
                mensaje="",
            )
        )
        # 1 mal formateada (con fecha inválida)
        self.accumulator.process_entry(
            ParsedLogEntry(
                estado=LogStatus.MAL_FORMATEADA,
                severidad="WARNING",
                fecha="2024-02-30",
                mensaje="Fallo 30 feb",
            )
        )
        # 1 mal formateada (sin severidad ni fecha)
        self.accumulator.process_entry(
            ParsedLogEntry(
                estado=LogStatus.MAL_FORMATEADA,
                severidad=None,
                fecha=None,
                mensaje=None,
            )
        )

        metrics = self.accumulator.metrics
        self.assertEqual(metrics.total_eventos, 4)
        self.assertEqual(metrics.total_validas, 1)
        self.assertEqual(metrics.total_anomalas, 3)
        self.assertEqual(metrics.total_con_fecha_valida, 2)  # La válida y la incompleta
        self.assertEqual(metrics.total_sin_fecha_valida, 2)  # Las 2 mal formateadas
        self.assertEqual(
            metrics.desglose_severidad,
            {"INFO": 1, "WARNING": 1, "ERROR": 1},
        )
        self.assertEqual(
            metrics.desglose_anomalias,
            {"incompleta": 1, "mal_formateada": 2},
        )
        self.assertAlmostEqual(metrics.porcentaje_validas, 25.0)
        self.assertAlmostEqual(metrics.porcentaje_anomalas, 75.0)

    def test_reset_reinicia_contadores(self) -> None:
        self.accumulator.process_entry(
            ParsedLogEntry(
                estado=LogStatus.VALIDA,
                severidad="INFO",
                fecha="2024-05-10",
                mensaje="Ok",
            )
        )
        self.assertEqual(self.accumulator.metrics.total_eventos, 1)
        self.accumulator.reset()
        self.assertEqual(self.accumulator.metrics.total_eventos, 0)
        self.assertEqual(self.accumulator.metrics.total_validas, 0)


if __name__ == "__main__":
    unittest.main()
