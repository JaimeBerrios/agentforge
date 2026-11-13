"""Pruebas unitarias para contratos y protocolos del núcleo agéntico."""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

from agentforge.core.contracts import (
    AgentProtocol,
    AgentRunResult,
    ExecutionContext,
    LLMProviderProtocol,
    LLMResponse,
    SkillProtocol,
    SkillResult,
)


class DummySkill:
    """Implementación dummy de prueba para SkillProtocol."""

    @property
    def name(self) -> str:
        return "dummy_skill"

    @property
    def description(self) -> str:
        return "Skill dummy para pruebas"

    def execute(self, context: ExecutionContext) -> SkillResult:
        return SkillResult(skill_name=self.name, success=True, output="dummy_output")


class DummyLLM:
    """Implementación dummy para LLMProviderProtocol."""

    @property
    def name(self) -> str:
        return "mock_llm"

    def generate(self, prompt: str, **kwargs: object) -> LLMResponse:
        return LLMResponse(content=f"Echo: {prompt}", model="mock-model")


class DummyAgent:
    """Implementación dummy para AgentProtocol."""

    @property
    def agent_id(self) -> str:
        return "dummy_agent"

    @property
    def name(self) -> str:
        return "Dummy Agent"

    @property
    def description(self) -> str:
        return "Agente dummy para pruebas"

    def run(self, initial_input: object = None) -> AgentRunResult:
        return AgentRunResult(
            agent_id=self.agent_id,
            success=True,
            step_results=(),
            final_output=initial_input,
        )


class TestContracts(unittest.TestCase):
    """Verificación de contratos, protocolos e inmutabilidad de tipos."""

    def test_skill_protocol_runtime_check(self) -> None:
        skill = DummySkill()
        self.assertIsInstance(skill, SkillProtocol)

    def test_llm_provider_protocol_runtime_check(self) -> None:
        llm = DummyLLM()
        self.assertIsInstance(llm, LLMProviderProtocol)

    def test_agent_protocol_runtime_check(self) -> None:
        agent = DummyAgent()
        self.assertIsInstance(agent, AgentProtocol)

    def test_execution_context_immutability(self) -> None:
        context = ExecutionContext(
            agent_id="test_agent",
            initial_input="test_data",
            parameters={"threshold": 0.8},
        )
        with self.assertRaises(FrozenInstanceError):
            context.agent_id = "altered"  # type: ignore[misc]

    def test_execution_context_helpers(self) -> None:
        r1 = SkillResult(skill_name="step1", success=True, output="output1")
        r2 = SkillResult(skill_name="step2", success=True, output="output2")
        context = ExecutionContext(
            agent_id="test_agent",
            initial_input="base",
            previous_results=(r1, r2),
        )
        self.assertEqual(context.get_latest_output(), "output2")
        self.assertEqual(context.get_result("step1"), r1)
        self.assertIsNone(context.get_result("non_existent"))

    def test_skill_result_immutability(self) -> None:
        res = SkillResult(skill_name="s1", success=True, output=42)
        with self.assertRaises(FrozenInstanceError):
            res.success = False  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
