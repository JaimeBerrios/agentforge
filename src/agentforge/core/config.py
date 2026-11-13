"""Cargador y validador de configuración de agentes mediante TOML."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agentforge.core.exceptions import InvalidConfigError

# Claves prohibidas para garantizar que nunca se almacenen secretos en configuración
FORBIDDEN_KEY_SUBSTRINGS = (
    "api_key",
    "secret",
    "token",
    "password",
    "credential",
    "auth_key",
    "private_key",
)


@dataclass(frozen=True, slots=True)
class AgentConfig:
    """Configuración validada e inmutable de un agente en AgentForge."""

    agent_id: str
    name: str
    description: str
    skills: tuple[str, ...]
    execution_order: tuple[str, ...]
    parameters: Mapping[str, Any] = field(default_factory=dict)


def _check_forbidden_keys(data: Any) -> None:
    """Verifica recursivamente que la configuración no contenga credenciales o secretos."""
    if isinstance(data, dict):
        for key, value in data.items():
            key_lower = str(key).lower()
            if any(forbidden in key_lower for forbidden in FORBIDDEN_KEY_SUBSTRINGS):
                raise InvalidConfigError(
                    f"Configuración inválida: Se detectó una clave prohibida ('{key}'). "
                    "No se permite incluir secretos ni credenciales en archivos TOML."
                )
            _check_forbidden_keys(value)
    elif isinstance(data, list):
        for item in data:
            _check_forbidden_keys(item)


def parse_agent_config(toml_content: str) -> AgentConfig:
    """Parsea y valida una cadena TOML retornando un objeto AgentConfig inmutable.

    Lanza:
        InvalidConfigError: Si la estructura, tipos o valores no satisfacen las reglas.
    """
    try:
        data = tomllib.loads(toml_content)
    except tomllib.TOMLDecodeError as err:
        raise InvalidConfigError(f"Error de sintaxis TOML en la configuración: {err}") from err

    if not isinstance(data, dict):
        raise InvalidConfigError("El archivo de configuración debe contener una tabla TOML válida.")

    # 1. Verificación de seguridad (cero secretos)
    _check_forbidden_keys(data)

    # 2. Extracción de sección [agent] o campos de nivel superior
    agent_data = data.get("agent", data)
    if not isinstance(agent_data, dict):
        raise InvalidConfigError("La sección [agent] debe ser una tabla.")

    agent_id = agent_data.get("agent_id") or agent_data.get("id")
    name = agent_data.get("name")
    description = agent_data.get("description")
    skills = agent_data.get("skills")
    execution_order = agent_data.get("execution_order")
    parameters = data.get("parameters", agent_data.get("parameters", {}))

    # 3. Validación de campos obligatorios
    if not isinstance(agent_id, str) or not agent_id.strip():
        raise InvalidConfigError(
            "El campo 'agent_id' es obligatorio y debe ser una cadena no vacía."
        )

    if not isinstance(name, str) or not name.strip():
        raise InvalidConfigError("El campo 'name' es obligatorio y debe ser una cadena no vacía.")

    if not isinstance(description, str) or not description.strip():
        raise InvalidConfigError(
            "El campo 'description' es obligatorio y debe ser una cadena no vacía."
        )

    # 4. Validación de lista de skills autorizadas
    if not isinstance(skills, list) or not skills:
        raise InvalidConfigError(
            "El campo 'skills' debe ser una lista no vacía de nombres de capacidades."
        )

    for skill in skills:
        if not isinstance(skill, str) or not skill.strip():
            raise InvalidConfigError("Todos los elementos de 'skills' deben ser cadenas no vacías.")

    # 5. Validación del orden de ejecución
    if not isinstance(execution_order, list) or not execution_order:
        raise InvalidConfigError(
            "El campo 'execution_order' debe ser una lista no vacía de capacidades a ejecutar."
        )

    skills_set = set(skills)
    for skill_in_order in execution_order:
        if not isinstance(skill_in_order, str) or not skill_in_order.strip():
            raise InvalidConfigError(
                "Todos los elementos de 'execution_order' deben ser cadenas no vacías."
            )
        if skill_in_order not in skills_set:
            raise InvalidConfigError(
                f"La skill '{skill_in_order}' declarada en 'execution_order' "
                f"no está autorizada en la lista de 'skills' ({skills})."
            )

    # 6. Validación de parámetros
    if not isinstance(parameters, dict):
        raise InvalidConfigError("La sección 'parameters' debe ser una tabla clave-valor.")

    return AgentConfig(
        agent_id=agent_id.strip(),
        name=name.strip(),
        description=description.strip(),
        skills=tuple(skills),
        execution_order=tuple(execution_order),
        parameters=parameters,
    )


def load_agent_config(path: str | Path) -> AgentConfig:
    """Carga y valida la configuración de un agente desde un archivo en disco."""
    file_path = Path(path)
    if not file_path.exists():
        raise InvalidConfigError(f"El archivo de configuración no existe: '{file_path}'")

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as err:
        raise InvalidConfigError(
            f"Error de lectura en archivo de configuración '{file_path}': {err}"
        ) from err

    return parse_agent_config(content)
