"""Adaptador para el proveedor local de LLM mediante la API HTTP de Ollama."""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from agentforge.adapters.exceptions import (
    LLMConnectionError,
    LLMModelNotFoundError,
    LLMResponseError,
    LLMTimeoutError,
)
from agentforge.core.contracts import LLMResponse


@dataclass(frozen=True, slots=True)
class OllamaConfig:
    """Configuración inmutable para la conexión con el servidor Ollama."""

    host: str = "http://127.0.0.1:11434"
    model: str = "qwen2.5-coder:3b"
    timeout: float = 30.0
    max_retries: int = 0
    temperature: float = 0.2
    options: dict[str, Any] = field(default_factory=dict)

    def normalized_host(self) -> str:
        """Retorna la URL del host sin barra final."""
        return self.host.rstrip("/")


class OllamaProvider:
    """Proveedor LLM que se comunica con la API HTTP local de Ollama.

    Satisface el protocolo `LLMProviderProtocol`.
    No realiza conexiones durante la inicialización de la clase.
    """

    def __init__(self, config: OllamaConfig | None = None) -> None:
        self._config = config or OllamaConfig()

    @property
    def name(self) -> str:
        """Nombre identificador del proveedor."""
        return "ollama"

    @property
    def model(self) -> str:
        """Modelo configurado para inferencia."""
        return self._config.model

    @property
    def host(self) -> str:
        """Host del servidor Ollama."""
        return self._config.normalized_host()

    @property
    def timeout(self) -> float:
        """Tiempo máximo de espera en segundos."""
        return self._config.timeout

    def is_available(self, timeout: float = 2.0) -> bool:
        """Comprueba de forma no invasiva si el servidor Ollama responde.

        No lanza excepciones; retorna False ante cualquier fallo de conexión.
        """
        url = f"{self.host}/api/tags"
        req = urllib.request.Request(url, headers={"User-Agent": "AgentForge/0.1"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return bool(resp.status == 200)
        except Exception:
            return False

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Genera una respuesta textual usando el endpoint `/api/generate` de Ollama.

        Args:
            prompt: Texto de entrada para el modelo.
            **kwargs: Parámetros adicionales (ej. temperature, model alternativo).

        Returns:
            LLMResponse con el contenido generado y metadatos de uso.

        Raises:
            LLMConnectionError: Si el servidor Ollama no responde o rechaza la conexión.
            LLMTimeoutError: Si la petición excede el tiempo límite configurado.
            LLMModelNotFoundError: Si el modelo solicitado no existe en Ollama (HTTP 404).
            LLMResponseError: Si la respuesta es corrupta o devuelve un código HTTP erróneo.
        """
        if not prompt or not prompt.strip():
            raise LLMResponseError("El prompt proporcionado no puede estar vacío.")

        target_model = kwargs.get("model", self.model)
        temperature = kwargs.get("temperature", self._config.temperature)
        timeout = kwargs.get("timeout", self.timeout)

        merged_options = dict(self._config.options)
        if "temperature" not in merged_options:
            merged_options["temperature"] = temperature
        if "options" in kwargs and isinstance(kwargs["options"], dict):
            merged_options.update(kwargs["options"])

        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": merged_options,
        }

        url = f"{self.host}/api/generate"
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "AgentForge/0.1",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw_body = response.read().decode("utf-8")

        except urllib.error.HTTPError as err:
            err_body = ""
            try:
                err_body = err.read().decode("utf-8")
            except Exception:
                pass

            if err.code == 404:
                raise LLMModelNotFoundError(
                    f"Modelo '{target_model}' no encontrado en Ollama ({self.host}). "
                    f"Detalle: {err.reason}. {err_body}".strip()
                ) from err

            msg = f"Error HTTP {err.code} desde Ollama ({self.host}): {err.reason}. {err_body}"
            raise LLMResponseError(msg.strip()) from err

        except urllib.error.URLError as err:
            # Distinguir timeout vs conexión rechazada
            reason = err.reason
            if isinstance(reason, (socket.timeout, TimeoutError)):
                raise LLMTimeoutError(
                    f"Tiempo de espera agotado ({timeout}s) conectando a Ollama ({self.host})."
                ) from err

            raise LLMConnectionError(
                f"No se pudo conectar al servidor Ollama en {self.host}: {reason}."
            ) from err

        except TimeoutError as err:
            raise LLMTimeoutError(
                f"Tiempo de espera agotado ({timeout}s) en la comunicación con Ollama."
            ) from err

        except Exception as err:
            raise LLMResponseError(
                f"Error inesperado de comunicación con Ollama: {type(err).__name__}: {err}"
            ) from err

        # Decodificación y validación de respuesta JSON
        try:
            parsed = json.loads(raw_body)
        except json.JSONDecodeError as err:
            raise LLMResponseError(f"Respuesta no válida de Ollama (JSON corrupto): {err}") from err

        if not isinstance(parsed, dict):
            received_type = type(parsed).__name__
            raise LLMResponseError(
                f"Estructura de respuesta inesperada (se esperaba dict, recibido {received_type})."
            )

        content = parsed.get("response")
        if content is None:
            # Si el modelo terminó con error reportado en JSON
            if "error" in parsed:
                raise LLMResponseError(f"Ollama reportó error: {parsed['error']}")
            raise LLMResponseError("Respuesta de Ollama no contiene el campo 'response'.")

        usage = {
            "total_duration": parsed.get("total_duration", 0),
            "prompt_eval_count": parsed.get("prompt_eval_count", 0),
            "eval_count": parsed.get("eval_count", 0),
            "done": parsed.get("done", True),
        }

        return LLMResponse(
            content=str(content),
            model=parsed.get("model", target_model),
            usage=usage,
        )
