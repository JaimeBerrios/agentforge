"""Contratos, protocolos y modelos de ejecución para AgentForge."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class SkillResult:
    """Resultado estructurado e inmutable de la ejecución de una skill."""

    skill_name: str
    success: bool
    output: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """Contexto de ejecución inmutable provisto a cada skill durante el pipeline."""

    agent_id: str
    initial_input: Any = None
    parameters: Mapping[str, Any] = field(default_factory=dict)
    previous_results: tuple[SkillResult, ...] = field(default_factory=tuple)

    def get_latest_output(self) -> Any:
        """Retorna la salida de la última skill ejecutada con éxito, o la entrada inicial."""
        for result in reversed(self.previous_results):
            if result.success and result.output is not None:
                return result.output
        return self.initial_input

    def get_result(self, skill_name: str) -> SkillResult | None:
        """Busca el resultado histórico de una skill específica."""
        for result in reversed(self.previous_results):
            if result.skill_name == skill_name:
                return result
        return None


@runtime_checkable
class SkillProtocol(Protocol):
    """Contrato que define una capacidad modular ejecutable en AgentForge."""

    @property
    def name(self) -> str:
        """Identificador único de la skill."""
        ...

    @property
    def description(self) -> str:
        """Descripción del propósito y capacidades de la skill."""
        ...

    def execute(self, context: ExecutionContext) -> SkillResult:
        """Ejecuta la lógica de la skill sobre un contexto inmutable."""
        ...


@dataclass(frozen=True, slots=True)
class AgentRunResult:
    """Resultado final estructurado e inmutable de la ejecución de un agente."""

    agent_id: str
    success: bool
    step_results: tuple[SkillResult, ...]
    final_output: Any = None
    errors: tuple[str, ...] = field(default_factory=tuple)


@runtime_checkable
class AgentProtocol(Protocol):
    """Contrato que define un agente configurable en AgentForge."""

    @property
    def agent_id(self) -> str:
        """Identificador único del agente."""
        ...

    @property
    def name(self) -> str:
        """Nombre legible del agente."""
        ...

    @property
    def description(self) -> str:
        """Propósito y rol del agente."""
        ...

    def run(self, initial_input: Any = None) -> AgentRunResult:
        """Ejecuta el ciclo de vida del agente sobre una entrada inicial."""
        ...


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Respuesta abstracta e inmutable de un proveedor de modelos de lenguaje."""

    content: str
    model: str
    usage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Retorna una copia serializable de la respuesta del modelo."""
        return {
            "content": self.content,
            "model": self.model,
            "usage": dict(self.usage),
        }


@runtime_checkable
class LLMProviderProtocol(Protocol):
    """Contrato abstracto para proveedores LLM (sin conexión activa en Fase 2)."""

    @property
    def name(self) -> str:
        """Nombre del proveedor (ej. 'ollama', 'gemini', 'mock')."""
        ...

    def generate(self, prompt: str, **kwargs: Any) -> LLMResponse:
        """Genera una respuesta de lenguaje a partir de un prompt."""
        ...
