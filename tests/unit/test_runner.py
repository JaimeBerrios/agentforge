"""Pruebas unitarias para el orquestador secuencial (SequentialAgentRunner)."""

from __future__ import annotations

import unittest

from agentforge.core.config import AgentConfig
from agentforge.core.contracts import ExecutionContext, SkillResult
from agentforge.core.exceptions import SkillNotFoundError, UnauthorizedSkillError
from agentforge.core.registry import SkillRegistry
from agentforge.core.runner import ConfigurableAgent, SequentialAgentRunner


class TrackingSkill:
    """Skill de prueba que registra el orden de ejecución y genera transformaciones."""

    def __init__(self, name: str, execution_log: list[str]) -> None:
        self._name = name
        self._execution_log = execution_log

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return f"Tracking skill {self._name}"

    def execute(self, context: ExecutionContext) -> SkillResult:
        self._execution_log.append(self.name)
        prev_data = context.get_latest_output() or ""
        output = f"{prev_data}->{self.name}" if prev_data else self.name
        return SkillResult(skill_name=self.name, success=True, output=output)


class FaultySkill:
    """Skill de prueba que lanza una excepción deliberada."""

    @property
    def name(self) -> str:
        return "faulty_skill"

    @property
    def description(self) -> str:
        return "Skill que falla para probar tolerancia a fallos"

    def execute(self, context: ExecutionContext) -> SkillResult:
        raise RuntimeError("Fallo deliberado en skill")


class MutatorAttemptSkill:
    """Skill maliciosa que intenta modificar el historial de resultados previos."""

    @property
    def name(self) -> str:
        return "mutator_skill"

    @property
    def description(self) -> str:
        return "Intenta modificar resultados previos"

    def execute(self, context: ExecutionContext) -> SkillResult:
        # Intenta mutar la tupla o asignar atributos en los resultados previos
        try:
            context.previous_results[0].success = False  # type: ignore[misc]
        except Exception as e:
            # Captura el error de inmutabilidad y lo reporta
            return SkillResult(
                skill_name=self.name,
                success=True,
                output=f"inmutability_enforced:{type(e).__name__}",
            )
        return SkillResult(skill_name=self.name, success=False, error="Mutación permitida")


class TestSequentialAgentRunner(unittest.TestCase):
    """Verificación de orquestación, orden, inmutabilidad y tolerancia a fallos."""

    def setUp(self) -> None:
        self.registry = SkillRegistry()
        self.execution_log: list[str] = []

        self.s1 = TrackingSkill("step1", self.execution_log)
        self.s2 = TrackingSkill("step2", self.execution_log)
        self.s3 = TrackingSkill("step3", self.execution_log)
        self.faulty = FaultySkill()
        self.mutator = MutatorAttemptSkill()

        self.registry.register(self.s1)
        self.registry.register(self.s2)
        self.registry.register(self.s3)
        self.registry.register(self.faulty)
        self.registry.register(self.mutator)

    def test_ejecucion_secuencial_en_orden_declarado(self) -> None:
        # Declaramos orden inverso al registro para confirmar estricto seguimiento
        config = AgentConfig(
            agent_id="test_agent",
            name="Sequential Test",
            description="Test orden",
            skills=("step3", "step1", "step2"),
            execution_order=("step3", "step1", "step2"),
        )
        runner = SequentialAgentRunner(config, self.registry)
        result = runner.run(initial_input="start")

        self.assertTrue(result.success)
        self.assertEqual(self.execution_log, ["step3", "step1", "step2"])
        self.assertEqual(result.final_output, "start->step3->step1->step2")
        self.assertEqual(len(result.step_results), 3)

    def test_inmutabilidad_de_resultados_previos(self) -> None:
        config = AgentConfig(
            agent_id="security_agent",
            name="Security Agent",
            description="Verifica inmutabilidad",
            skills=("step1", "mutator_skill"),
            execution_order=("step1", "mutator_skill"),
        )
        runner = SequentialAgentRunner(config, self.registry)
        result = runner.run()

        self.assertTrue(result.success)
        self.assertEqual(
            result.final_output,
            "inmutability_enforced:FrozenInstanceError",
        )
        # El resultado del paso 1 sigue intacto con success=True
        self.assertTrue(result.step_results[0].success)

    def test_tolerancia_a_fallos_y_captura_de_excepciones(self) -> None:
        config = AgentConfig(
            agent_id="error_agent",
            name="Error Agent",
            description="Prueba fallos",
            skills=("step1", "faulty_skill", "step3"),
            execution_order=("step1", "faulty_skill", "step3"),
        )
        runner = SequentialAgentRunner(config, self.registry)
        result = runner.run()

        self.assertFalse(result.success)
        self.assertEqual(len(result.step_results), 2)  # step3 no debe ejecutarse
        self.assertTrue(result.step_results[0].success)
        self.assertFalse(result.step_results[1].success)
        self.assertIn("Fallo deliberado en skill", result.step_results[1].error or "")
        self.assertEqual(self.execution_log, ["step1"])  # step3 no fue llamado

    def test_rechazo_de_skill_no_registrada(self) -> None:
        config = AgentConfig(
            agent_id="missing_agent",
            name="Missing Agent",
            description="Skill inexistente",
            skills=("step1", "unregistered_skill"),
            execution_order=("step1", "unregistered_skill"),
        )
        with self.assertRaises(SkillNotFoundError):
            SequentialAgentRunner(config, self.registry)

    def test_rechazo_en_runtime_de_skill_no_autorizada(self) -> None:
        # Manipulamos una configuración anómala donde execution_order no esté en skills
        config = AgentConfig(
            agent_id="unauth_agent",
            name="Unauth Agent",
            description="Skill no autorizada",
            skills=("step1",),
            execution_order=("step1", "step2"),  # step2 no autorizada
        )
        with self.assertRaises(UnauthorizedSkillError):
            SequentialAgentRunner(config, self.registry)

    def test_configurable_agent_wrapper(self) -> None:
        config = AgentConfig(
            agent_id="wrapper_agent",
            name="Wrapper Agent",
            description="Prueba interfaz AgentProtocol",
            skills=("step1",),
            execution_order=("step1",),
        )
        agent = ConfigurableAgent(config, self.registry)
        self.assertEqual(agent.agent_id, "wrapper_agent")
        self.assertEqual(agent.name, "Wrapper Agent")

        result = agent.run("hello")
        self.assertTrue(result.success)
        self.assertEqual(result.final_output, "hello->step1")


if __name__ == "__main__":
    unittest.main()
