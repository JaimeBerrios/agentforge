"""Pruebas unitarias para adaptadores LLM (OllamaProvider y FakeLLMProvider)."""

from __future__ import annotations

import io
import json
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from agentforge.adapters.exceptions import (
    LLMConnectionError,
    LLMModelNotFoundError,
    LLMResponseError,
    LLMTimeoutError,
)
from agentforge.adapters.fake_llm import FakeLLMProvider
from agentforge.adapters.ollama import OllamaConfig, OllamaProvider
from agentforge.core.contracts import LLMProviderProtocol, LLMResponse


class TestLLMAdaptersProtocol(unittest.TestCase):
    """Verificación de conformidad con LLMProviderProtocol sin llamadas a red."""

    def test_conformidad_de_protocolos(self) -> None:
        fake = FakeLLMProvider()
        ollama = OllamaProvider()

        self.assertIsInstance(fake, LLMProviderProtocol)
        self.assertIsInstance(ollama, LLMProviderProtocol)
        self.assertEqual(fake.name, "fake_llm")
        self.assertEqual(ollama.name, "ollama")


class TestFakeLLMProvider(unittest.TestCase):
    """Verificación del comportamiento de FakeLLMProvider."""

    def test_generacion_default_y_conteo_de_llamadas(self) -> None:
        provider = FakeLLMProvider(default_response="Hola desde el mock.")
        self.assertEqual(provider.calls_count, 0)
        self.assertIsNone(provider.last_prompt)

        response = provider.generate("Analiza estos logs:")
        self.assertIsInstance(response, LLMResponse)
        self.assertEqual(response.content, "Hola desde el mock.")
        self.assertEqual(provider.calls_count, 1)
        self.assertEqual(provider.last_prompt, "Analiza estos logs:")

    def test_cola_de_respuestas_secuenciales(self) -> None:
        provider = FakeLLMProvider()
        provider.enqueue_response("Respuesta 1")
        provider.enqueue_response("Respuesta 2")

        r1 = provider.generate("prompt 1")
        r2 = provider.generate("prompt 2")
        r3 = provider.generate("prompt 3")

        self.assertEqual(r1.content, "Respuesta 1")
        self.assertEqual(r2.content, "Respuesta 2")
        self.assertEqual(r3.content, "Respuesta simulada del modelo.")

    def test_lanzamiento_controlado_de_excepciones(self) -> None:
        provider = FakeLLMProvider()
        provider.set_raise_error(LLMConnectionError("Servidor simulado caído."))

        with self.assertRaises(LLMConnectionError) as ctx:
            provider.generate("Hola")
        self.assertIn("Servidor simulado caído", str(ctx.exception))

    def test_reset(self) -> None:
        provider = FakeLLMProvider()
        provider.generate("test")
        self.assertEqual(provider.calls_count, 1)

        provider.reset()
        self.assertEqual(provider.calls_count, 0)
        self.assertEqual(len(provider.prompts_received), 0)


class TestOllamaProvider(unittest.TestCase):
    """Pruebas unitarias de OllamaProvider aislando la capa de red con mocks."""

    def setUp(self) -> None:
        self.config = OllamaConfig(
            host="http://127.0.0.1:11434",
            model="qwen2.5-coder:3b",
            timeout=5.0,
        )
        self.provider = OllamaProvider(self.config)

    def test_inicializacion_no_realiza_conexiones(self) -> None:
        # La creación de OllamaProvider no debe invocar la red
        with patch("urllib.request.urlopen") as mock_url:
            config = OllamaConfig(
                host="http://10.255.255.1:11434",
                allowed_hosts=("10.255.255.1",),
            )
            provider = OllamaProvider(config)
            self.assertEqual(provider.host, "http://10.255.255.1:11434")
            mock_url.assert_not_called()

    def test_generacion_exitosa_parsea_json_y_uso(self) -> None:
        fake_api_response = {
            "model": "qwen2.5-coder:3b",
            "created_at": "2026-11-13T12:00:00Z",
            "response": "Hipótesis: Sobrecarga en la base de datos.",
            "done": True,
            "total_duration": 500000000,
            "prompt_eval_count": 25,
            "eval_count": 10,
        }
        raw_bytes = json.dumps(fake_api_response).encode("utf-8")

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = raw_bytes
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            result = self.provider.generate("¿Cuál es la causa?")

            self.assertIsInstance(result, LLMResponse)
            self.assertEqual(result.content, "Hipótesis: Sobrecarga en la base de datos.")
            self.assertEqual(result.model, "qwen2.5-coder:3b")
            self.assertEqual(result.usage["prompt_eval_count"], 25)
            self.assertEqual(result.usage["eval_count"], 10)
            mock_urlopen.assert_called_once()

    def test_rechazo_de_prompt_vacio(self) -> None:
        with self.assertRaises(LLMResponseError):
            self.provider.generate("")

        with self.assertRaises(LLMResponseError):
            self.provider.generate("   ")

    def test_modelo_inexistente_retorna_404_y_lanza_model_not_found(self) -> None:
        err_msg = json.dumps({"error": "model 'non-existent' not found"}).encode("utf-8")
        http_err = urllib.error.HTTPError(
            url="http://127.0.0.1:11434/api/generate",
            code=404,
            msg="Not Found",
            hdrs={},  # type: ignore[arg-type]
            fp=io.BytesIO(err_msg),
        )

        with patch("urllib.request.urlopen", side_effect=http_err):
            with self.assertRaises(LLMModelNotFoundError) as ctx:
                self.provider.generate("test prompt", model="non-existent")
            self.assertIn("non-existent", str(ctx.exception))

    def test_error_http_500_lanza_response_error(self) -> None:
        err_msg = json.dumps({"error": "internal error"}).encode("utf-8")
        http_err = urllib.error.HTTPError(
            url="http://127.0.0.1:11434/api/generate",
            code=500,
            msg="Internal Server Error",
            hdrs={},  # type: ignore[arg-type]
            fp=io.BytesIO(err_msg),
        )

        with patch("urllib.request.urlopen", side_effect=http_err):
            with self.assertRaises(LLMResponseError) as ctx:
                self.provider.generate("test prompt")
            self.assertIn("Error HTTP 500", str(ctx.exception))

    def test_conexion_rechazada_lanza_connection_error(self) -> None:
        url_err = urllib.error.URLError(reason=ConnectionRefusedError("Connection refused"))

        with patch("urllib.request.urlopen", side_effect=url_err):
            with self.assertRaises(LLMConnectionError) as ctx:
                self.provider.generate("test prompt")
            self.assertIn("No se pudo conectar", str(ctx.exception))

    def test_timeout_de_red_lanza_timeout_error(self) -> None:
        url_err = urllib.error.URLError(reason=TimeoutError("timed out"))

        with patch("urllib.request.urlopen", side_effect=url_err):
            with self.assertRaises(LLMTimeoutError) as ctx:
                self.provider.generate("test prompt")
            self.assertIn("Tiempo de espera agotado", str(ctx.exception))

    def test_timeout_directo_lanza_timeout_error(self) -> None:
        with patch("urllib.request.urlopen", side_effect=TimeoutError("socket timeout")):
            with self.assertRaises(LLMTimeoutError):
                self.provider.generate("test prompt")

    def test_json_corrupto_lanza_response_error(self) -> None:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b"<html>Not JSON</html>"
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            with self.assertRaises(LLMResponseError) as ctx:
                self.provider.generate("test prompt")
            self.assertIn("JSON corrupto", str(ctx.exception))

    def test_is_available_exitoso_y_fallido(self) -> None:
        # Caso 1: 200 OK
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            self.assertTrue(self.provider.is_available())

        # Caso 2: Error de conexión
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("refused"),
        ):
            self.assertFalse(self.provider.is_available())
