"""Pruebas de integración del pipeline completo de skills mediante el orquestador real."""

from __future__ import annotations

import unittest
from pathlib import Path

from agentforge.core.config import load_agent_config
from agentforge.core.registry import SkillRegistry
from agentforge.core.runner import ConfigurableAgent
from agentforge.skills.anomaly_detector import AnomalyDetectorSkill
from agentforge.skills.incident_reporter import IncidentReporterSkill
from agentforge.skills.log_parser import LogParserSkill
from agentforge.skills.types import IncidentReport


class TestSkillsPipelineIntegration(unittest.TestCase):
    """Verificación de extremo a extremo del pipeline secuencial de las tres skills."""

    def setUp(self) -> None:
        self.fixtures_dir = Path(__file__).resolve().parent.parent / "fixtures"
        self.configs_dir = Path(__file__).resolve().parent.parent.parent / "configs"

        self.registry = SkillRegistry()
        self.registry.register(LogParserSkill())
        self.registry.register(AnomalyDetectorSkill())
        self.registry.register(IncidentReporterSkill())

        self.config = load_agent_config(self.configs_dir / "agent_analyzer_example.toml")
        self.agent = ConfigurableAgent(self.config, self.registry)

    def test_pipeline_completo_logs_validos(self) -> None:
        """Ejecuta el pipeline de 3 skills sobre el fixture de 10 logs válidos."""
        lineas = (self.fixtures_dir / "logs_validos.txt").read_text(encoding="utf-8").splitlines()

        result = self.agent.run(initial_input=lineas)

        self.assertTrue(result.success)
        self.assertEqual(len(result.step_results), 3)

        # Verificación del paso 1: log-parser
        res_parser = result.step_results[0]
        self.assertEqual(res_parser.skill_name, "log-parser")
        self.assertTrue(res_parser.success)
        self.assertEqual(res_parser.output.total_lines, 10)
        self.assertEqual(res_parser.output.metrics.total_validas, 10)

        # Verificación del paso 2: anomaly-detector
        res_detector = result.step_results[1]
        self.assertEqual(res_detector.skill_name, "anomaly-detector")
        self.assertTrue(res_detector.success)
        self.assertEqual(res_detector.output.total_valid, 10)
        self.assertEqual(res_detector.output.total_anomalies, 0)
        self.assertEqual(len(res_detector.output.valid_error_events), 3)

        # Verificación del paso 3: incident-reporter
        res_reporter = result.step_results[2]
        self.assertEqual(res_reporter.skill_name, "incident-reporter")
        self.assertTrue(res_reporter.success)
        report = res_reporter.output
        self.assertIsInstance(report, IncidentReport)
        self.assertEqual(report.facts["total_events"], 10)
        self.assertEqual(report.facts["valid_percentage"], 100.0)
        self.assertEqual(report.facts["anomalous_events"], 0)
        self.assertEqual(report.facts["operational_errors"], 3)

        # Confirmación de salida final del agente
        self.assertEqual(result.final_output, report)

    def test_pipeline_completo_logs_invalidos(self) -> None:
        """Ejecuta el pipeline de 3 skills sobre el fixture de 16 logs con anomalías."""
        lineas = (self.fixtures_dir / "logs_invalidos.txt").read_text(encoding="utf-8").splitlines()

        result = self.agent.run(initial_input=lineas)

        self.assertTrue(result.success)
        self.assertEqual(len(result.step_results), 3)

        report = result.final_output
        self.assertIsInstance(report, IncidentReport)

        facts = report.facts
        self.assertEqual(facts["total_events"], 16)
        self.assertEqual(facts["valid_events"], 0)
        self.assertEqual(facts["valid_percentage"], 0.0)
        self.assertEqual(facts["anomalous_events"], 16)
        self.assertEqual(facts["anomalous_percentage"], 100.0)
        self.assertEqual(facts["incomplete_records"], 4)
        self.assertEqual(facts["malformed_records"], 12)
        self.assertEqual(facts["calendar_valid_dates"], 2)
        self.assertEqual(facts["calendar_invalid_dates"], 14)

        # Observaciones factuales precisas
        obs_text = " ".join(report.observations)
        self.assertIn("16 anomalías", obs_text)
        self.assertIn("4 registros incompletos", obs_text)
        self.assertIn("12 registros mal formateados", obs_text)

    def test_pipeline_preserva_inmutabilidad_entre_pasos(self) -> None:
        """Certifica que los resultados del paso 1 no son modificados por los pasos posteriores."""
        lineas = ["[INFO] 2024-05-10 Evento de prueba"]
        result = self.agent.run(initial_input=lineas)

        # Los tres pasos se completan
        self.assertEqual(len(result.step_results), 3)
        self.assertTrue(result.step_results[0].success)
        self.assertTrue(result.step_results[1].success)
        self.assertTrue(result.step_results[2].success)

        # El resultado del paso 1 permanece inalterado
        self.assertEqual(result.step_results[0].output.total_lines, 1)


if __name__ == "__main__":
    unittest.main()
