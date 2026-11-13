"""Pruebas unitarias para el registro de skills (SkillRegistry)."""

from __future__ import annotations

import unittest

from agentforge.core.contracts import ExecutionContext, SkillResult
from agentforge.core.exceptions import DuplicateSkillError, SkillNotFoundError
from agentforge.core.registry import SkillRegistry


class MockSkill:
    """Mock skill para probar el registro."""

    def __init__(self, name: str, description: str = "Mock skill") -> None:
        self._name = name
        self._description = description

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def execute(self, context: ExecutionContext) -> SkillResult:
        return SkillResult(skill_name=self.name, success=True, output=f"executed_{self.name}")


class TestSkillRegistry(unittest.TestCase):
    """Verificación de registro, prevención de duplicados y resolución segura."""

    def setUp(self) -> None:
        self.registry = SkillRegistry()

    def test_registro_exitoso_y_recuperacion(self) -> None:
        skill = MockSkill("parser_skill")
        self.registry.register(skill)

        self.assertTrue(self.registry.has("parser_skill"))
        self.assertEqual(self.registry.get("parser_skill"), skill)
        self.assertEqual(self.registry.list_skills(), ["parser_skill"])

    def test_rechazo_de_identificador_duplicado(self) -> None:
        s1 = MockSkill("validator_skill")
        s2 = MockSkill("validator_skill", description="Duplicada")

        self.registry.register(s1)
        with self.assertRaises(DuplicateSkillError) as cm:
            self.registry.register(s2)
        self.assertIn("ya está registrada", str(cm.exception))

    def test_error_al_solicitar_skill_no_registrada(self) -> None:
        with self.assertRaises(SkillNotFoundError) as cm:
            self.registry.get("unknown_skill")
        self.assertIn("no encontrada", str(cm.exception))

    def test_rechazo_de_objeto_invalido(self) -> None:
        class IncompleteSkill:
            pass

        with self.assertRaises(TypeError):
            self.registry.register(IncompleteSkill())  # type: ignore[arg-type]

    def test_resolve_authorized_exitoso(self) -> None:
        s1 = MockSkill("s1")
        s2 = MockSkill("s2")
        self.registry.register(s1)
        self.registry.register(s2)

        resolved = self.registry.resolve_authorized(["s2", "s1"])
        self.assertEqual(resolved, [s2, s1])

    def test_resolve_authorized_con_skill_desconocida(self) -> None:
        s1 = MockSkill("s1")
        self.registry.register(s1)

        with self.assertRaises(SkillNotFoundError):
            self.registry.resolve_authorized(["s1", "missing_skill"])

    def test_unregister_y_clear(self) -> None:
        s1 = MockSkill("s1")
        s2 = MockSkill("s2")
        self.registry.register(s1)
        self.registry.register(s2)

        self.registry.unregister("s1")
        self.assertFalse(self.registry.has("s1"))
        self.assertTrue(self.registry.has("s2"))

        self.registry.clear()
        self.assertEqual(self.registry.list_skills(), [])


if __name__ == "__main__":
    unittest.main()
