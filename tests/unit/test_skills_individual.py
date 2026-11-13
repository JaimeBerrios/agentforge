"""Pruebas unitarias para las skills log-parser, anomaly-detector e incident-reporter."""

from __future__ import annotations

import unittest

from agentforge.core.contracts import ExecutionContext
from agentforge.core.types import LogStatus
from agentforge.skills.anomaly_detector import AnomalyDetectorSkill
from agentforge.skills.incident_reporter import IncidentReporterSkill
from agentforge.skills.log_parser import LogParserSkill
from agentforge.skills.types import AnomalyDetectorOutput, IncidentReport, LogParserOutput


class TestLogParserSkill(unittest.TestCase):
    """Pruebas unitarias aisladas para LogParserSkill."""

    def setUp(self) -> None:
        self.skill = LogParserSkill()

    def test_metadatos_de_skill(self) -> None:
        self.assertEqual(self.skill.name, "log-parser")
        self.assertTrue(len(self.skill.description) > 10)

    def test_procesamiento_lista_de_cadenas(self) -> None:
        lineas = [
            "[INFO] 2024-05-10 Inicio del sistema",
            "[ERROR] 2024-05-10 Fallo en la base de datos",
        ]
        context = ExecutionContext("agent_test", initial_input=lineas)
        result = self.skill.execute(context)

        self.assertTrue(result.success)
        output = result.output
        self.assertIsInstance(output, LogParserOutput)
        self.assertEqual(output.total_lines, 2)
        self.assertEqual(len(output.entries), 2)
        self.assertEqual(output.metrics.total_validas, 2)
        self.assertEqual(output.metrics.total_eventos, 2)

    def test_procesamiento_cadena_multilinea(self) -> None:
        raw_text = "[INFO] 2024-05-10 Linea 1\n[WARNING] 2024-05-10 Linea 2"
        context = ExecutionContext("agent_test", initial_input=raw_text)
        result = self.skill.execute(context)

        self.assertTrue(result.success)
        self.assertEqual(result.output.total_lines, 2)

    def test_procesamiento_diccionario_con_clave_lines(self) -> None:
        dict_input = {"lines": ["[INFO] 2024-05-10 Evento"]}
        context = ExecutionContext("agent_test", initial_input=dict_input)
        result = self.skill.execute(context)

        self.assertTrue(result.success)
        self.assertEqual(result.output.total_lines, 1)

    def test_entrada_vacia_produce_resultado_exitoso_en_cero(self) -> None:
        context = ExecutionContext("agent_test", initial_input=[])
        result = self.skill.execute(context)

        self.assertTrue(result.success)
        self.assertEqual(result.output.total_lines, 0)
        self.assertEqual(result.output.metrics.total_eventos, 0)

    def test_entrada_invalida_retorna_error_controlado(self) -> None:
        casos_invalidos = [
            12345,
            [1, 2, 3],
            {"clave_incorrecta": []},
            True,
        ]
        for caso in casos_invalidos:
            with self.subTest(caso=caso):
                context = ExecutionContext("agent_test", initial_input=caso)
                result = self.skill.execute(context)
                self.assertFalse(result.success)
                self.assertIsNotNone(result.error)
                self.assertIn("Error de validación de entrada", result.error or "")


class TestAnomalyDetectorSkill(unittest.TestCase):
    """Pruebas unitarias aisladas para AnomalyDetectorSkill."""

    def setUp(self) -> None:
        self.parser_skill = LogParserSkill()
        self.detector_skill = AnomalyDetectorSkill()

    def test_distincion_severidad_error_vs_validez(self) -> None:
        """Verifica que un log con severidad ERROR no se clasifique como anomalía si es válido."""
        lineas = [
            # 1 válido con ERROR operacional
            "[ERROR] 2024-05-10 Conexión rechazada por base de datos",
            # 1 incompleto
            "· [WARNING] Invalid password attempt",
            # 1 mal formateado por fecha inexistente
            "[ERROR] 2024-02-30 Fallo fecha inexistente",
        ]
        ctx1 = ExecutionContext("agent_test", initial_input=lineas)
        res_parser = self.parser_skill.execute(ctx1)

        ctx2 = ExecutionContext("agent_test", previous_results=(res_parser,))
        res_detector = self.detector_skill.execute(ctx2)

        self.assertTrue(res_detector.success)
        output = res_detector.output
        self.assertIsInstance(output, AnomalyDetectorOutput)

        self.assertEqual(output.total_analyzed, 3)
        self.assertEqual(output.total_valid, 1)
        self.assertEqual(output.total_anomalies, 2)
        # El ERROR válido está en valid_error_events, NO en malformed ni incomplete
        self.assertEqual(len(output.valid_error_events), 1)
        self.assertEqual(output.valid_error_events[0].estado, LogStatus.VALIDA)
        self.assertEqual(output.valid_error_events[0].severidad, "ERROR")

        self.assertEqual(len(output.incomplete_entries), 1)
        self.assertEqual(len(output.malformed_entries), 1)

    def test_entrada_incompatible_retorna_error(self) -> None:
        context = ExecutionContext("agent_test", initial_input="texto_plano_no_parseado")
        result = self.detector_skill.execute(context)
        self.assertFalse(result.success)
        self.assertIn("Error de entrada", result.error or "")


class TestIncidentReporterSkill(unittest.TestCase):
    """Pruebas unitarias aisladas para IncidentReporterSkill."""

    def setUp(self) -> None:
        self.parser = LogParserSkill()
        self.detector = AnomalyDetectorSkill()
        self.reporter = IncidentReporterSkill()

    def test_generacion_reporte_hechos_objetivos(self) -> None:
        lineas = [
            "[INFO] 2024-05-10 Sistema levantado",
            "[ERROR] 2024-05-10 Fallo servicio autenticación",
        ]
        c1 = ExecutionContext("audit_agent", initial_input=lineas)
        r1 = self.parser.execute(c1)

        c2 = ExecutionContext("audit_agent", previous_results=(r1,))
        r2 = self.detector.execute(c2)

        c3 = ExecutionContext("audit_agent", previous_results=(r1, r2))
        r3 = self.reporter.execute(c3)

        self.assertTrue(r3.success)
        report = r3.output
        self.assertIsInstance(report, IncidentReport)
        self.assertEqual(report.facts["total_events"], 2)
        self.assertEqual(report.facts["valid_events"], 2)
        self.assertEqual(report.facts["valid_percentage"], 100.0)
        self.assertEqual(report.facts["anomalous_events"], 0)
        self.assertEqual(report.facts["operational_errors"], 1)

        # Las observaciones deben ser factuales
        obs_total = " ".join(report.observations)
        self.assertIn("Integridad estructural del 100%", obs_total)
        self.assertIn("ERROR en registros estructuralmente válidos", obs_total)
        self.assertIn("REPORTE DE INCIDENTE AGÉNTICO", report.summary_text)

    def test_rechazo_entrada_invalida(self) -> None:
        c = ExecutionContext("audit_agent", initial_input={"datos": 123})
        res = self.reporter.execute(c)
        self.assertFalse(res.success)
        self.assertIn("Error de entrada", res.error or "")


if __name__ == "__main__":
    unittest.main()
