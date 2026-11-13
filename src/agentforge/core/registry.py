"""Registro explícito y seguro de capacidades (skills) para AgentForge."""

from __future__ import annotations

from collections.abc import Iterable

from agentforge.core.contracts import SkillProtocol
from agentforge.core.exceptions import DuplicateSkillError, SkillNotFoundError


class SkillRegistry:
    """Registro determinista y seguro de skills en memoria.

    Garantías de seguridad:
    1. No evalúa archivos Markdown (SKILL.md) como código ejecutable.
    2. No realiza importación dinámica arbitraria de módulos desde configuración externa.
    3. Exige registro programático explícito de instancias que cumplan SkillProtocol.
    """

    def __init__(self) -> None:
        self._skills: dict[str, SkillProtocol] = {}

    def register(self, skill: SkillProtocol) -> None:
        """Registra una nueva capacidad en el framework.

        Lanza:
            DuplicateSkillError: Si el identificador ya existe en el registro.
            TypeError: Si el objeto no satisface el contrato SkillProtocol.
        """
        if not isinstance(skill, SkillProtocol):
            # Verificación estructural en caso de mocks o subclases duck-typed
            if not (hasattr(skill, "name") and hasattr(skill, "execute")):
                raise TypeError(f"El objeto {skill!r} no implementa el contrato SkillProtocol.")

        name = skill.name
        if not isinstance(name, str) or not name.strip():
            raise ValueError("El identificador de la skill debe ser una cadena no vacía.")

        if name in self._skills:
            raise DuplicateSkillError(
                f"La skill '{name}' ya está registrada en el framework. "
                "No se permiten identificadores duplicados."
            )

        self._skills[name] = skill

    def get(self, name: str) -> SkillProtocol:
        """Recupera una skill por su identificador único.

        Lanza:
            SkillNotFoundError: Si la skill no existe en el registro.
        """
        if name not in self._skills:
            raise SkillNotFoundError(f"Skill '{name}' no encontrada en el registro de AgentForge.")
        return self._skills[name]

    def has(self, name: str) -> bool:
        """Verifica si una skill está registrada."""
        return name in self._skills

    def list_skills(self) -> list[str]:
        """Retorna una lista ordenada de los identificadores de skills registradas."""
        return sorted(self._skills.keys())

    def resolve_authorized(self, authorized_names: Iterable[str]) -> list[SkillProtocol]:
        """Resuelve una lista de nombres autorizados asegurando su existencia previa.

        Lanza:
            SkillNotFoundError: Si alguna de las skills autorizadas no está registrada.
        """
        resolved: list[SkillProtocol] = []
        for name in authorized_names:
            resolved.append(self.get(name))
        return resolved

    def unregister(self, name: str) -> None:
        """Elimina una skill del registro si existe."""
        self._skills.pop(name, None)

    def clear(self) -> None:
        """Limpia todas las skills registradas."""
        self._skills.clear()
