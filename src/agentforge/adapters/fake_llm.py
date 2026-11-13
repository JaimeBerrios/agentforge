"""Proveedor simulado (FakeLLMProvider) para pruebas deterministas sin conexión."""

from __future__ import annotations

from typing import Any

from agentforge.core.contracts import LLMResponse


class FakeLLMProvider:
    """Proveedor LLM simulado para pruebas unitarias e integración aisladas.

    Satisface el protocolo `LLMProviderProtocol`.
    Permite emular respuestas exitosas, fallos de red, timeouts y salidas vacías.
    """

    def __init__(
        self,
        name: str = "fake_llm",
        model: str = "fake-model-v1",
        default_response: str = "Respuesta simulada del modelo.",
        responses: list[str] | None = None,
        raise_error: Exception | None = None,
    ) -> None:
        self._name = name
        self._model = model
        self._default_response = default_response
        self._responses = list(responses) if responses is not None else []
        self._raise_error = raise_error
        self._calls_count = 0
        self._prompts_received: list[str] = []

    @property
    def name(self) -> str:
        """Nombre identificador del proveedor simulado."""
        return self._name

    @property
    def model(self) -> str:
        """Nombre del modelo simulado."""
        return self._model

    @property
    def calls_count(self) -> int:
        """Cantidad de llamadas ejecutadas a generate()."""
        return self._calls_count

    @property
    def prompts_received(self) -> list[str]:
        """Historial de prompts recibidos en las invocaciones."""
        return list(self._prompts_received)

    @property
    def last_prompt(self) -> str | None:
        """Último prompt recibido."""
        return self._prompts_received[-1] if self._prompts_received else None

    def set_raise_error(self, error: Exception | None) -> None:
        """Configura una excepción a lanzar en las siguientes llamadas."""
        self._raise_error = error

    def enqueue_response(self, response: str) -> None:
        """Encola una respuesta para ser consumida secuencialmente."""
        self._responses.append(response)

    def reset(self) -> None:
        """Reinicia el contador y el historial de prompts."""
        self._calls_count = 0
        self._prompts_received.clear()
        self._responses.clear()
        self._raise_error = None

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Genera una respuesta simulada o lanza el error configurado."""
        self._calls_count += 1
        self._prompts_received.append(prompt)

        if self._raise_error is not None:
            raise self._raise_error

        if self._responses:
            content = self._responses.pop(0)
        else:
            content = self._default_response

        target_model = kwargs.get("model", self._model)
        usage = {
            "prompt_eval_count": len(prompt.split()),
            "eval_count": len(content.split()),
            "simulated": True,
        }

        return LLMResponse(
            content=content,
            model=target_model,
            usage=usage,
        )
