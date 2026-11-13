"""Excepciones especializadas para adaptadores de proveedores LLM."""

from __future__ import annotations


class LLMProviderError(Exception):
    """Excepción base para errores originados en adaptadores LLM."""


class LLMConnectionError(LLMProviderError):
    """El servidor del proveedor LLM es inaccesible o rechazó la conexión."""


class LLMTimeoutError(LLMProviderError):
    """La solicitud al proveedor LLM excedió el tiempo máximo de espera."""


class LLMModelNotFoundError(LLMProviderError):
    """El modelo solicitado no está instalado o disponible en el proveedor."""


class LLMResponseError(LLMProviderError):
    """La respuesta del proveedor LLM fue inválida, corrupta o devolvió error HTTP."""
