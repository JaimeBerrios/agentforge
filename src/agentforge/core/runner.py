"""Orquestador secuencial de agentes y ejecución de capacidades para AgentForge."""

from __future__ import annotations

import logging
from typing import Any

from agentforge.core.config import AgentConfig
from agentforge.core.contracts import (
    AgentProtocol,
    AgentRunResult,
    ExecutionContext,
    SkillProtocol,
    SkillResult,
)
from agentforge.core.exceptions import SkillNotFoundError, UnauthorizedSkillError
from agentforge.core.registry import SkillRegistry

logger = logging.getLogger(__name__)


class SequentialAgentRunner:
    """Ejecutor determinista de pipelines agénticos secuenciales.

    Garantías de diseño:
    1. Resuelve únicamente capacidades registradas y autorizadas.
    2. Ejecuta las skills estrictamente en el orden declarado en la configuración.
    3. Protege los resultados anteriores mediante contextos inmutables (ExecutionContext).
    4. Manejo explícito de excepciones sin interrumpir catastróficamente el orquestador.
    5. Funciona al 100% sin dependencias ni llamadas a modelos LLM.
    """

    def __init__(self, config: AgentConfig, registry: SkillRegistry) -> None:
        self._config = config
        self._registry = registry
        self._authorized_skills_set = set(config.skills)
        self._validate_configuration_against_registry()

    @property
    def config(self) -> AgentConfig:
        """Configuración del agente."""
        return self._config

    @property
    def registry(self) -> SkillRegistry:
        """Registro de skills utilizado."""
        return self._registry

    def _validate_configuration_against_registry(self) -> None:
        """Verifica que todas las skills autorizadas y configuradas existan en el registro."""
        for skill_name in self._config.skills:
            if not self._registry.has(skill_name):
                raise SkillNotFoundError(
                    f"La skill autorizada '{skill_name}' para el agente '{self._config.agent_id}' "
                    "no existe en el registro del framework."
                )

        for skill_name in self._config.execution_order:
            if skill_name not in self._authorized_skills_set:
                raise UnauthorizedSkillError(
                    f"La skill '{skill_name}' no está en la lista de skills autorizadas del agente."
                )

    def run(self, initial_input: Any = None) -> AgentRunResult:
        """Ejecuta secuencialmente las skills autorizadas del agente.

        Retorna:
            AgentRunResult: Resultado estructurado e inmutable de la ejecución.
        """
        step_results: list[SkillResult] = []
        errors: list[str] = []

        for skill_name in self._config.execution_order:
            # Doble verificación de autorización en tiempo de ejecución
            if skill_name not in self._authorized_skills_set:
                error_msg = (
                    f"Violación de seguridad: Skill no autorizada '{skill_name}' "
                    f"interceptada durante la ejecución del agente '{self._config.agent_id}'."
                )
                logger.error(error_msg)
                raise UnauthorizedSkillError(error_msg)

            skill: SkillProtocol = self._registry.get(skill_name)

            # Construcción de contexto inmutable con los resultados de pasos previos
            context = ExecutionContext(
                agent_id=self._config.agent_id,
                initial_input=initial_input,
                parameters=self._config.parameters,
                previous_results=tuple(step_results),
            )

            try:
                result = skill.execute(context)
                if not isinstance(result, SkillResult):
                    error_msg = (
                        f"La skill '{skill_name}' retornó un resultado inválido "
                        f"de tipo {type(result)!r} en lugar de SkillResult."
                    )
                    result = SkillResult(
                        skill_name=skill_name,
                        success=False,
                        error=error_msg,
                    )
            except Exception as err:
                error_msg = f"Error no controlado en skill '{skill_name}': {err}"
                logger.exception(error_msg)
                result = SkillResult(
                    skill_name=skill_name,
                    success=False,
                    error=error_msg,
                )

            step_results.append(result)

            if not result.success:
                if result.error:
                    errors.append(result.error)
                # Al fallar un paso crítico, detenemos la ejecución del pipeline
                break

        overall_success = bool(step_results and all(r.success for r in step_results))
        final_output = step_results[-1].output if (overall_success and step_results) else None

        return AgentRunResult(
            agent_id=self._config.agent_id,
            success=overall_success,
            step_results=tuple(step_results),
            final_output=final_output,
            errors=tuple(errors),
        )


class ConfigurableAgent(AgentProtocol):
    """Implementación de referencia para agentes configurables."""

    def __init__(self, config: AgentConfig, registry: SkillRegistry) -> None:
        self._runner = SequentialAgentRunner(config, registry)

    @property
    def agent_id(self) -> str:
        return self._runner.config.agent_id

    @property
    def name(self) -> str:
        return self._runner.config.name

    @property
    def description(self) -> str:
        return self._runner.config.description

    @property
    def config(self) -> AgentConfig:
        return self._runner.config

    def run(self, initial_input: Any = None) -> AgentRunResult:
        return self._runner.run(initial_input)
