"""Pruebas unitarias para el cargador y validador de configuración TOML."""

from __future__ import annotations

import unittest
from pathlib import Path

from agentforge.core.config import load_agent_config, parse_agent_config
from agentforge.core.exceptions import InvalidConfigError


class TestAgentConfig(unittest.TestCase):
    """Verificación de la carga, validación y seguridad de archivos TOML."""

    def setUp(self) -> None:
        self.configs_dir = Path(__file__).resolve().parent.parent.parent / "configs"

    def test_parse_config_valida_completa(self) -> None:
        toml_content = """
        [agent]
        agent_id = "test_agent"
        name = "Test Agent"
        description = "Agente de prueba"
        skills = ["skill_a", "skill_b"]
        execution_order = ["skill_a", "skill_b"]

        [parameters]
        threshold = 0.9
        enabled = true
        """
        config = parse_agent_config(toml_content)
        self.assertEqual(config.agent_id, "test_agent")
        self.assertEqual(config.name, "Test Agent")
        self.assertEqual(config.description, "Agente de prueba")
        self.assertEqual(config.skills, ("skill_a", "skill_b"))
        self.assertEqual(config.execution_order, ("skill_a", "skill_b"))
        self.assertEqual(config.parameters.get("threshold"), 0.9)
        self.assertTrue(config.parameters.get("enabled"))

    def test_cargar_ejemplos_reales_de_disco(self) -> None:
        cfg1 = load_agent_config(self.configs_dir / "agent_analyzer_example.toml")
        self.assertEqual(cfg1.agent_id, "log_analyzer_agent")
        self.assertEqual(len(cfg1.skills), 3)

        cfg2 = load_agent_config(self.configs_dir / "agent_minimal_example.toml")
        self.assertEqual(cfg2.agent_id, "minimal_agent")
        self.assertEqual(cfg2.skills, ("echo_skill",))

    def test_rechazo_de_skill_no_autorizada_en_execution_order(self) -> None:
        toml_content = """
        [agent]
        agent_id = "agent_x"
        name = "Agent X"
        description = "Test"
        skills = ["skill_a"]
        execution_order = ["skill_a", "unauthorized_skill"]
        """
        with self.assertRaises(InvalidConfigError) as cm:
            parse_agent_config(toml_content)
        self.assertIn("no está autorizada", str(cm.exception))

    def test_rechazo_de_claves_prohibidas_con_secretos(self) -> None:
        casos_secretos = [
            'api_key = "secret_12345"',
            'openai_token = "token_xyz"',
            'db_password = "supersecret"',
            'auth_credentials = "creds"',
        ]
        base_toml = """
        [agent]
        agent_id = "agent_sec"
        name = "Sec Agent"
        description = "Test security"
        skills = ["s1"]
        execution_order = ["s1"]
        """
        for caso in casos_secretos:
            with self.subTest(caso=caso):
                with self.assertRaises(InvalidConfigError) as cm:
                    parse_agent_config(f"{base_toml}\n{caso}")
                self.assertIn("clave prohibida", str(cm.exception))

    def test_rechazo_de_campos_obligatorios_ausentes(self) -> None:
        campos = [
            (
                "agent_id",
                'name = "A"\ndescription = "B"\nskills = ["s1"]\nexecution_order = ["s1"]',
            ),
            (
                "name",
                'agent_id = "A"\ndescription = "B"\nskills = ["s1"]\nexecution_order = ["s1"]',
            ),
            (
                "description",
                'agent_id = "A"\nname = "B"\nskills = ["s1"]\nexecution_order = ["s1"]',
            ),
            (
                "skills",
                'agent_id = "A"\nname = "B"\ndescription = "C"\nexecution_order = ["s1"]',
            ),
            (
                "execution_order",
                'agent_id = "A"\nname = "B"\ndescription = "C"\nskills = ["s1"]',
            ),
        ]
        for campo, contenido in campos:
            with self.subTest(campo=campo):
                with self.assertRaises(InvalidConfigError):
                    parse_agent_config(contenido)

    def test_archivo_no_existente(self) -> None:
        with self.assertRaises(InvalidConfigError):
            load_agent_config("ruta/falsa/que_no_existe.toml")

    def test_sintaxis_toml_invalida(self) -> None:
        with self.assertRaises(InvalidConfigError):
            parse_agent_config("clave_sin_cerrar = [1, 2,")


if __name__ == "__main__":
    unittest.main()
