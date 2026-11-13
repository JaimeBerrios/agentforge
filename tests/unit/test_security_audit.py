"""Pruebas unitarias para las correcciones de la auditoría de seguridad (Fase 6)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from agentforge.adapters.exceptions import LLMResponseError
from agentforge.adapters.fake_llm import FakeLLMProvider
from agentforge.adapters.ollama import MAX_HTTP_RESPONSE_BYTES, OllamaConfig, OllamaProvider
from agentforge.agents.llm_agent import LLMAnalysisAgent, LLMAnalysisAgentConfig
from agentforge.agents.triage_agent import IncidentTriageAgent
from agentforge.agents.types import TriagePriority, TriageResult
from agentforge.skills.types import IncidentReport


class TestOllamaSecurityHardening(unittest.TestCase):
    """Verificación de mitigaciones de seguridad en el adaptador OllamaProvider."""

    def test_prevencion_ssrf_rechaza_host_no_autorizado(self) -> None:
        # Intento de conexión a metadata de AWS / IP externa no permitida
        with self.assertRaises(ValueError) as ctx:
            OllamaConfig(host="http://169.254.169.254:80")
        self.assertIn("prevención SSRF", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            OllamaConfig(host="http://evil-attacker.com:11434")
        self.assertIn("prevención SSRF", str(ctx.exception))

        # 0.0.0.0 no es una dirección loopback de cliente válida y debe ser rechazada por defecto
        with self.assertRaises(ValueError) as ctx:
            OllamaConfig(host="http://0.0.0.0:11434")
        self.assertIn("prevención SSRF", str(ctx.exception))

    def test_hosts_loopback_permitidos_por_defecto(self) -> None:
        # localhost, 127.0.0.1 y ::1 son aceptados sin error
        cfg_localhost = OllamaConfig(host="http://localhost:11434")
        self.assertEqual(cfg_localhost.host, "http://localhost:11434")

        cfg_ipv4 = OllamaConfig(host="http://127.0.0.1:11434")
        self.assertEqual(cfg_ipv4.host, "http://127.0.0.1:11434")

        cfg_ipv6 = OllamaConfig(host="http://[::1]:11434")
        self.assertEqual(cfg_ipv6.host, "http://[::1]:11434")

    def test_rechazo_de_credenciales_en_url(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            OllamaConfig(host="http://admin:secret@127.0.0.1:11434")
        self.assertIn("credenciales incrustadas", str(ctx.exception))

    def test_rechazo_de_esquema_no_http(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            OllamaConfig(host="ftp://127.0.0.1:11434")
        self.assertIn("Esquema no permitido", str(ctx.exception))

    def test_validacion_de_rangos_timeout_y_temperatura(self) -> None:
        with self.assertRaises(ValueError):
            OllamaConfig(timeout=-1.0)
        with self.assertRaises(ValueError):
            OllamaConfig(timeout=301.0)
        with self.assertRaises(ValueError):
            OllamaConfig(temperature=-0.1)
        with self.assertRaises(ValueError):
            OllamaConfig(temperature=2.5)

    def test_validacion_de_nombre_de_modelo(self) -> None:
        with self.assertRaises(ValueError):
            OllamaConfig(model="")
        with self.assertRaises(ValueError):
            OllamaConfig(model="../../etc/passwd")

    def test_limite_defensivo_lectura_http_rechaza_respuesta_sobredimensionada(self) -> None:
        # Emular respuesta HTTP que supera MAX_HTTP_RESPONSE_BYTES (2 MB)
        oversized_bytes = b"A" * (MAX_HTTP_RESPONSE_BYTES + 10)
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = oversized_bytes
        mock_resp.__enter__.return_value = mock_resp

        provider = OllamaProvider()
        with patch("urllib.request.urlopen", return_value=mock_resp):
            with self.assertRaises(LLMResponseError) as ctx:
                provider.generate("test prompt")
            self.assertIn("límite defensivo", str(ctx.exception))


class TestMetricValidationAndSanitization(unittest.TestCase):
    """Verificación de validación estricta de métricas y prevención de datos corruptos."""

    def test_triage_agent_rechaza_metricas_nan_e_infinito(self) -> None:
        agent = IncidentTriageAgent()
        report_nan = IncidentReport(
            report_id="rep-1",
            facts={"operational_errors": float("nan")},
            observations=(),
            summary_text="test",
        )
        res = agent.run(report_nan)
        self.assertFalse(res.success)
        self.assertTrue(any("no puede ser NaN" in err for err in res.errors))

    def test_triage_agent_rechaza_metricas_negativas(self) -> None:
        agent = IncidentTriageAgent()
        report_neg = IncidentReport(
            report_id="rep-2",
            facts={"operational_errors": -3},
            observations=(),
            summary_text="test",
        )
        res = agent.run(report_neg)
        self.assertFalse(res.success)
        self.assertTrue(any("no puede ser negativa" in err for err in res.errors))

    def test_triage_agent_rechaza_porcentajes_fuera_de_rango(self) -> None:
        agent = IncidentTriageAgent()
        report_pct = IncidentReport(
            report_id="rep-3",
            facts={"anomalous_percentage": 150.0},
            observations=(),
            summary_text="test",
        )
        res = agent.run(report_pct)
        self.assertFalse(res.success)
        self.assertTrue(any("fuera de rango [0.0, 100.0]" in err for err in res.errors))

    def test_triage_result_post_init_valida_tipos(self) -> None:
        with self.assertRaises(TypeError):
            TriageResult(
                priority=TriagePriority.LOW,
                reasons=("ok",),
                operational_error_count=True,  # bool no permitido como int
                format_anomaly_count=0,
                recommendations=(),
            )


class TestPromptBudgetAndInstructionProtection(unittest.TestCase):
    """Verificación de que las instrucciones del sistema no sean truncadas."""

    def test_presupuesto_insuficiente_para_instrucciones_rechaza_limpiamente(self) -> None:
        # Un presupuesto ridículamente pequeño (ej. 100 caracteres) no cabe el prompt de seguridad
        config = LLMAnalysisAgentConfig(max_prompt_chars=100)
        agent = LLMAnalysisAgent(config=config)
        res = agent.run({"facts": {"total_events": 10}, "priority": "LOW"})

        # Resiliente: no rompe la ejecución global, registra advertencia
        self.assertTrue(res.success)
        llm_out = res.final_output
        self.assertFalse(llm_out.success)
        self.assertTrue(any("presupuesto" in w.lower() for w in llm_out.warnings))

    def test_reduccion_de_muestras_preserva_instrucciones_completas(self) -> None:
        fake_llm = FakeLLMProvider()
        # Presupuesto ajustado que requiere omitir muestras largas
        config = LLMAnalysisAgentConfig(
            max_sample_messages=5,
            max_message_chars=100,
            max_prompt_chars=1400,
        )
        agent = LLMAnalysisAgent(llm_provider=fake_llm, config=config)
        input_data = {
            "facts": {"total_events": 5},
            "priority": "HIGH",
            "samples": [
                "Mensaje de error muy largo que ocupará espacio 1...",
                "Mensaje de error muy largo que ocupará espacio 2...",
                "Mensaje de error muy largo que ocupará espacio 3...",
                "Mensaje de error muy largo que ocupará espacio 4...",
            ],
        }
        agent.run(input_data)
        last_prompt = fake_llm.last_prompt
        self.assertIsNotNone(last_prompt)

        # Las instrucciones de seguridad y el formato requerido deben estar completos
        self.assertIn("[ROL Y POLÍTICA DE SEGURIDAD]", last_prompt)
        self.assertIn("REGLAS OBLIGATORIAS:", last_prompt)
        self.assertIn("Con base EXCLUSIVAMENTE en la telemetría", last_prompt)
        expected_inst = 'Cada recomendación DEBE iniciar exactamente con: "Recomendación: "'
        self.assertIn(expected_inst, last_prompt)
