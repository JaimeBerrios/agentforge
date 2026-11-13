"""Pruebas de integración para la coordinación con asistencia LLM (Phase 5)."""

from __future__ import annotations

import unittest
from pathlib import Path

from agentforge.adapters.exceptions import LLMConnectionError
from agentforge.adapters.fake_llm import FakeLLMProvider
from agentforge.agents.analysis_agent import LogAnalysisAgent
from agentforge.agents.coordinator import AgentCoordinator
from agentforge.agents.llm_agent import LLMAnalysisAgent
from agentforge.agents.triage_agent import IncidentTriageAgent
from agentforge.agents.types import CoordinatedExecutionResult, TriagePriority


class TestLLMCoordinationPipeline(unittest.TestCase):
    """Verificación de extremo a extremo del pipeline determinista con LLM integrado."""

    def setUp(self) -> None:
        self.fixtures_dir = Path(__file__).resolve().parent.parent / "fixtures"
        self.fake_provider = FakeLLMProvider(
            default_response=(
                "Hipótesis: Sobrecarga transitoria en el backend o timeout de red.\n"
                "Recomendación: Monitorear latencias y verificar pool de conexiones."
            )
        )
        self.llm_agent = LLMAnalysisAgent(llm_provider=self.fake_provider)
        self.coordinator = AgentCoordinator(
            analysis_agent=LogAnalysisAgent(),
            triage_agent=IncidentTriageAgent(),
            llm_agent=self.llm_agent,
        )

    def test_pipeline_completo_con_logs_validos(self) -> None:
        """Verifica que el pipeline de 3 agentes procese logs_validos.txt coordinadamente."""
        lineas = (self.fixtures_dir / "logs_validos.txt").read_text(encoding="utf-8").splitlines()

        result: CoordinatedExecutionResult = self.coordinator.coordinate(lineas)

        self.assertTrue(result.success)
        self.assertTrue(result.analysis_result.success)
        self.assertIsNotNone(result.triage_result)
        self.assertIsNotNone(result.llm_result)

        # 1. Triaje determinista asigna HIGH por 3 eventos ERROR operacionales
        triage = result.triage_result
        assert triage is not None
        self.assertEqual(triage.priority, TriagePriority.HIGH)
        self.assertEqual(triage.operational_error_count, 3)

        # 2. Análisis LLM preserva la prioridad determinista y los hechos
        llm = result.llm_result
        assert llm is not None
        self.assertTrue(llm.success)
        self.assertEqual(llm.triage_priority, TriagePriority.HIGH)
        self.assertEqual(llm.confirmed_facts["operational_errors"], 3)

        # 3. Hipótesis generadas por LLM están marcadas como no confirmadas
        self.assertTrue(len(llm.hypotheses) > 0)
        self.assertTrue(all("[Hipótesis no confirmada]" in h for h in llm.hypotheses))
        self.assertTrue(len(llm.recommendations) > 0)

        # 4. Trazabilidad completa del orden de ejecución
        self.assertEqual(
            result.execution_order,
            ("log_analysis_agent", "incident_triage_agent", "llm_analysis_agent"),
        )

    def test_pipeline_completo_con_logs_invalidos(self) -> None:
        """Verifica que logs_invalidos.txt produzca prioridad CRITICAL y asistencia LLM."""
        lineas = (self.fixtures_dir / "logs_invalidos.txt").read_text(encoding="utf-8").splitlines()

        result: CoordinatedExecutionResult = self.coordinator.coordinate(lineas)

        self.assertTrue(result.success)
        triage = result.triage_result
        assert triage is not None
        self.assertEqual(triage.priority, TriagePriority.CRITICAL)
        self.assertEqual(triage.format_anomaly_count, 16)

        llm = result.llm_result
        assert llm is not None
        self.assertTrue(llm.success)
        self.assertEqual(llm.triage_priority, TriagePriority.CRITICAL)
        self.assertEqual(llm.confirmed_facts["format_anomalies"], 16)

    def test_pipeline_continua_exitosamente_cuando_llm_falla(self) -> None:
        """La caída del proveedor LLM no rompe el pipeline determinista."""
        self.fake_provider.set_raise_error(LLMConnectionError("Ollama caído en 127.0.0.1:11434"))

        lineas = (self.fixtures_dir / "logs_validos.txt").read_text(encoding="utf-8").splitlines()
        result: CoordinatedExecutionResult = self.coordinator.coordinate(lineas)

        # El pipeline global reporta éxito porque la verdad determinista fue completada
        self.assertTrue(result.success)

        # Triaje determinista intacto
        assert result.triage_result is not None
        self.assertEqual(result.triage_result.priority, TriagePriority.HIGH)

        # Componente LLM degradó graciosamente
        assert result.llm_result is not None
        self.assertFalse(result.llm_result.success)
        self.assertEqual(result.llm_result.triage_priority, TriagePriority.HIGH)
        self.assertTrue(len(result.llm_result.warnings) > 0)
        self.assertIn("Ollama caído", result.llm_result.warnings[0])
