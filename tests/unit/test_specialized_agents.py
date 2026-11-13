"""Pruebas unitarias para los agentes especializados LogAnalysisAgent e IncidentTriageAgent."""

from __future__ import annotations

import unittest

from agentforge.agents.analysis_agent import LogAnalysisAgent
from agentforge.agents.triage_agent import IncidentTriageAgent
from agentforge.agents.types import TriagePriority, TriageResult, TriageThresholds
from agentforge.skills.types import IncidentReport


class TestLogAnalysisAgent(unittest.TestCase):
    """Pruebas unitarias para LogAnalysisAgent."""

    def setUp(self) -> None:
        self.agent = LogAnalysisAgent()

    def test_metadatos_del_agente(self) -> None:
        self.assertEqual(self.agent.agent_id, "log_analysis_agent")
        self.assertEqual(self.agent.name, "Log Analysis Agent")

    def test_ejecucion_individual_valida(self) -> None:
        lineas = [
            "[INFO] 2024-05-10 Inicio de servicio",
            "[WARNING] 2024-05-10 Consumo de memoria alto",
        ]
        result = self.agent.run(lineas)
        self.assertTrue(result.success)
        self.assertEqual(len(result.step_results), 3)

        # Trazabilidad de los tres pasos
        step_names = [step.skill_name for step in result.step_results]
        self.assertEqual(step_names, ["log-parser", "anomaly-detector", "incident-reporter"])

        # Salida final es un IncidentReport
        self.assertIsInstance(result.final_output, IncidentReport)
        self.assertEqual(result.final_output.facts["total_events"], 2)

    def test_entrada_vacia_no_falla(self) -> None:
        result = self.agent.run([])
        self.assertTrue(result.success)
        self.assertEqual(result.final_output.facts["total_events"], 0)

    def test_entrada_invalida_retorna_error_controlado(self) -> None:
        result = self.agent.run(99999)
        self.assertFalse(result.success)
        self.assertTrue(len(result.errors) > 0)


class TestIncidentTriageAgent(unittest.TestCase):
    """Pruebas unitarias para IncidentTriageAgent y reglas de priorización."""

    def setUp(self) -> None:
        self.triage_agent = IncidentTriageAgent()

    def _crear_reporte_sintetico(
        self,
        total: int = 10,
        op_errors: int = 0,
        op_warnings: int = 0,
        anom_percentage: float = 0.0,
        incomplete: int = 0,
        malformed: int = 0,
    ) -> IncidentReport:
        facts = {
            "total_events": total,
            "valid_events": total - (incomplete + malformed),
            "valid_percentage": 100.0 - anom_percentage,
            "anomalous_events": incomplete + malformed,
            "anomalous_percentage": anom_percentage,
            "incomplete_records": incomplete,
            "malformed_records": malformed,
            "calendar_valid_dates": total,
            "calendar_invalid_dates": 0,
            "operational_errors": op_errors,
            "operational_warnings": op_warnings,
        }
        return IncidentReport(
            report_id=f"TEST-REP-{total}",
            facts=facts,
            observations=("Observación sintética de prueba",),
            summary_text="Resumen de prueba",
        )

    def test_validacion_de_umbrales_invalidos(self) -> None:
        # Error si critical <= high
        with self.assertRaises(ValueError):
            TriageThresholds(critical_operational_errors=1, high_operational_errors=1)

        # Error si tasas desordenadas
        with self.assertRaises(ValueError):
            TriageThresholds(critical_anomaly_rate=10.0, high_anomaly_rate=20.0)

        # Error si valores negativos
        with self.assertRaises(ValueError):
            TriageThresholds(critical_operational_errors=-1)

    def test_priorizacion_low(self) -> None:
        reporte = self._crear_reporte_sintetico(
            total=10, op_errors=0, op_warnings=0, anom_percentage=0.0
        )
        result = self.triage_agent.run(reporte)

        self.assertTrue(result.success)
        triage: TriageResult = result.final_output
        self.assertEqual(triage.priority, TriagePriority.LOW)
        self.assertTrue(any("Lote nominal" in r for r in triage.reasons))

    def test_priorizacion_medium_por_advertencias_o_incompletos(self) -> None:
        # 1 advertencia WARNING en registro válido
        reporte = self._crear_reporte_sintetico(total=10, op_warnings=2, incomplete=1)
        result = self.triage_agent.run(reporte)

        self.assertTrue(result.success)
        triage: TriageResult = result.final_output
        self.assertEqual(triage.priority, TriagePriority.MEDIUM)
        self.assertTrue(any("advertencias operacionales" in r for r in triage.reasons))

    def test_priorizacion_high_por_error_operacional_valido(self) -> None:
        # 2 eventos operacionales ERROR en logs bien formados
        reporte = self._crear_reporte_sintetico(total=10, op_errors=2, anom_percentage=0.0)
        result = self.triage_agent.run(reporte)

        self.assertTrue(result.success)
        triage: TriageResult = result.final_output
        self.assertEqual(triage.priority, TriagePriority.HIGH)
        self.assertTrue(any("eventos operacionales ERROR" in r for r in triage.reasons))

    def test_priorizacion_critical_por_errores_masivos(self) -> None:
        # 6 errores operacionales (supera umbral crítico de 5)
        reporte = self._crear_reporte_sintetico(total=20, op_errors=6)
        result = self.triage_agent.run(reporte)

        self.assertTrue(result.success)
        triage: TriageResult = result.final_output
        self.assertEqual(triage.priority, TriagePriority.CRITICAL)

    def test_priorizacion_critical_por_tasa_de_anomalias_extrema(self) -> None:
        # Tasa de anomalías del 75% (supera umbral crítico del 50%)
        reporte = self._crear_reporte_sintetico(total=10, anom_percentage=75.0, malformed=7)
        result = self.triage_agent.run(reporte)

        self.assertTrue(result.success)
        triage: TriageResult = result.final_output
        self.assertEqual(triage.priority, TriagePriority.CRITICAL)
        self.assertTrue(any("tasa de anomalías estructurales" in r for r in triage.reasons))

    def test_rechazo_entrada_invalida(self) -> None:
        result = self.triage_agent.run("texto_no_compatible")
        self.assertFalse(result.success)
        self.assertTrue(len(result.errors) > 0)

    def test_preservacion_de_disclaimer_y_recomendaciones(self) -> None:
        reporte = self._crear_reporte_sintetico(total=10, op_errors=1, malformed=2)
        result = self.triage_agent.run(reporte)
        triage: TriageResult = result.final_output

        self.assertIn("disclaimer", triage.metadata)
        self.assertIn("propuesta operativa", triage.metadata["disclaimer"])
        self.assertTrue(len(triage.recommendations) >= 2)


if __name__ == "__main__":
    unittest.main()
