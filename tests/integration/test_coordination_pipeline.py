"""Pruebas de integración para la coordinación entre LogAnalysisAgent e IncidentTriageAgent."""

from __future__ import annotations

import unittest
from pathlib import Path

from agentforge.agents.analysis_agent import LogAnalysisAgent
from agentforge.agents.coordinator import AgentCoordinator
from agentforge.agents.triage_agent import IncidentTriageAgent
from agentforge.agents.types import CoordinatedExecutionResult, TriagePriority


class TestAgentCoordinationPipeline(unittest.TestCase):
    """Verificación de extremo a extremo de la orquestación coordinada entre agentes."""

    def setUp(self) -> None:
        self.fixtures_dir = Path(__file__).resolve().parent.parent / "fixtures"
        self.coordinator = AgentCoordinator(
            analysis_agent=LogAnalysisAgent(),
            triage_agent=IncidentTriageAgent(),
        )

    def test_coordinacion_logs_validos_asigna_prioridad_high(self) -> None:
        """3 eventos ERROR operacionales en fixture logs_validos.txt -> Prioridad HIGH."""
        lineas = (self.fixtures_dir / "logs_validos.txt").read_text(encoding="utf-8").splitlines()

        result: CoordinatedExecutionResult = self.coordinator.coordinate(lineas)

        self.assertTrue(result.success)
        self.assertTrue(result.analysis_result.success)
        self.assertIsNotNone(result.triage_result)

        triage = result.triage_result
        assert triage is not None  # type narrowing

        # El fixture tiene 3 eventos ERROR operacionales (supera umbral high de 1)
        self.assertEqual(triage.priority, TriagePriority.HIGH)
        self.assertEqual(triage.operational_error_count, 3)
        self.assertEqual(triage.format_anomaly_count, 0)
        self.assertTrue(any("3 eventos operacionales ERROR" in r for r in triage.reasons))
        self.assertTrue(any("Auditar los componentes" in rec for rec in triage.recommendations))

        # Preservación de trazabilidad de los dos agentes
        self.assertEqual(
            result.execution_order,
            ("log_analysis_agent", "incident_triage_agent"),
        )

    def test_coordinacion_logs_invalidos_asigna_prioridad_critical(self) -> None:
        """Tasa de anomalías del 100% en logs_invalidos.txt (>= 50%) -> Prioridad CRITICAL."""
        lineas = (self.fixtures_dir / "logs_invalidos.txt").read_text(encoding="utf-8").splitlines()

        result: CoordinatedExecutionResult = self.coordinator.coordinate(lineas)

        self.assertTrue(result.success)
        self.assertTrue(result.analysis_result.success)
        self.assertIsNotNone(result.triage_result)

        triage = result.triage_result
        assert triage is not None

        self.assertEqual(triage.priority, TriagePriority.CRITICAL)
        self.assertEqual(triage.format_anomaly_count, 16)
        self.assertEqual(triage.operational_error_count, 0)
        self.assertTrue(
            any("tasa de anomalías estructurales (100.0%)" in r for r in triage.reasons)
        )
        self.assertTrue(any("Revisar emisores de logs" in rec for rec in triage.recommendations))
        self.assertTrue(
            any("Inspeccionar el mecanismo de recolección" in rec for rec in triage.recommendations)
        )

    def test_coordinacion_lote_nominal_asigna_prioridad_low(self) -> None:
        """Un lote limpio sin errores ni anomalías asigna prioridad LOW."""
        lineas = [
            "[INFO] 2024-05-10 Servicio A activo",
            "[INFO] 2024-05-10 Servicio B activo",
        ]
        result = self.coordinator.coordinate(lineas)

        self.assertTrue(result.success)
        assert result.triage_result is not None
        self.assertEqual(result.triage_result.priority, TriagePriority.LOW)
        self.assertTrue(any("Lote nominal" in r for r in result.triage_result.reasons))

    def test_coordinacion_manejo_defensivo_de_fallo_inicial(self) -> None:
        """Si la entrada causa fallo en LogAnalysisAgent, el triaje se aborta de forma segura."""
        entrada_invalida = 123456  # Tipo no iterable

        result = self.coordinator.coordinate(entrada_invalida)

        self.assertFalse(result.success)
        self.assertFalse(result.analysis_result.success)
        self.assertIsNone(result.triage_result)
        self.assertTrue(len(result.errors) > 0)


if __name__ == "__main__":
    unittest.main()
