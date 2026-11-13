"""Excepciones de dominio para el núcleo agéntico de AgentForge."""

from __future__ import annotations


class AgentForgeError(Exception):
    """Excepción base para todos los errores del framework AgentForge."""


class SkillRegistryError(AgentForgeError):
    """Excepción base para errores relacionados con el registro de skills."""


class DuplicateSkillError(SkillRegistryError):
    """Lanzada al intentar registrar una skill con un identificador ya existente."""


class SkillNotFoundError(SkillRegistryError):
    """Lanzada cuando se solicita una skill no registrada en el framework."""


class UnauthorizedSkillError(AgentForgeError):
    """Lanzada cuando un agente intenta ejecutar una skill no autorizada en su configuración."""


class ConfigError(AgentForgeError):
    """Excepción base para errores de configuración."""


class InvalidConfigError(ConfigError):
    """Lanzada cuando una configuración externa TOML es sintáctica o semánticamente inválida."""


class ExecutionError(AgentForgeError):
    """Lanzada cuando ocurre un error irrecuperable durante la ejecución del pipeline agéntico."""
