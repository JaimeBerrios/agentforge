"""Tipos y modelos de dominio para agentes especializados y coordinación."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from agentforge.core.contracts import AgentRunResult


class TriagePriority(StrEnum):
    """Niveles de prioridad para el triaje operativo de incidentes."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class TriageThresholds:
    """Umbrales cuantitativos configurables para la asignación de prioridades."""

    critical_operational_errors: int = 5
    high_operational_errors: int = 1
    critical_anomaly_rate: float = 50.0
    high_anomaly_rate: float = 20.0
    medium_anomaly_rate: float = 5.0
    medium_warnings_count: int = 1

    def __post_init__(self) -> None:
        """Valida que los umbrales sean lógicos, positivos y ordenados."""
        if self.critical_operational_errors <= self.high_operational_errors:
            raise ValueError(
                "critical_operational_errors debe ser mayor que high_operational_errors."
            )
        valid_rates = (
            self.critical_anomaly_rate > self.high_anomaly_rate > self.medium_anomaly_rate >= 0
        )
        if not valid_rates:
            raise ValueError(
                "Los umbrales de tasa de anomalías deben cumplir: critical > high > medium >= 0."
            )
        if self.critical_operational_errors < 0 or self.high_operational_errors < 0:
            raise ValueError("Los umbrales de conteo de errores deben ser no negativos.")


@dataclass(frozen=True, slots=True)
class TriageResult:
    """Resultado estructurado del análisis de triaje y priorización operativa."""

    priority: TriagePriority
    reasons: tuple[str, ...]
    operational_error_count: int
    format_anomaly_count: int
    recommendations: tuple[str, ...]
    metadata: dict[str, Any] = field(
        default_factory=lambda: {
            "disclaimer": (
                "La prioridad y recomendaciones representan una propuesta operativa "
                "basada en reglas deterministas, no un diagnóstico causal confirmado."
            )
        }
    )

    def to_dict(self) -> dict[str, Any]:
        """Convierte el resultado de triaje a un diccionario serializable."""
        return {
            "priority": str(self.priority.value),
            "reasons": list(self.reasons),
            "operational_error_count": self.operational_error_count,
            "format_anomaly_count": self.format_anomaly_count,
            "recommendations": list(self.recommendations),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class LLMAnalysisResult:
    """Resultado estructurado del análisis asistido por modelo de lenguaje."""

    success: bool
    provider: str
    model: str
    triage_priority: TriagePriority | None
    confirmed_facts: dict[str, Any]
    hypotheses: tuple[str, ...]
    recommendations: tuple[str, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)
    raw_response: str | None = None
    metadata: dict[str, Any] = field(
        default_factory=lambda: {
            "disclaimer": (
                "Las hipótesis generadas por el modelo de lenguaje son sugerencias no "
                "verificadas y no sustituyen las métricas ni la validación determinista."
            ),
            "nature": "unverified_ai_hypotheses",
        }
    )

    def to_dict(self) -> dict[str, Any]:
        """Convierte el resultado del análisis LLM a un diccionario serializable."""
        return {
            "success": self.success,
            "provider": self.provider,
            "model": self.model,
            "triage_priority": self.triage_priority.value if self.triage_priority else None,
            "confirmed_facts": dict(self.confirmed_facts),
            "hypotheses": list(self.hypotheses),
            "recommendations": list(self.recommendations),
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class CoordinatedExecutionResult:
    """Resultado consolidado de la ejecución coordinada entre agentes."""

    success: bool
    analysis_result: AgentRunResult
    triage_result: TriageResult | None = None
    llm_result: LLMAnalysisResult | None = None
    execution_order: tuple[str, ...] = ("log_analysis_agent", "incident_triage_agent")
    errors: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """Convierte el resultado coordinado a diccionario."""
        return {
            "success": self.success,
            "analysis_success": self.analysis_result.success,
            "triage_priority": self.triage_result.priority.value if self.triage_result else None,
            "has_llm_analysis": self.llm_result is not None,
            "execution_order": list(self.execution_order),
            "errors": list(self.errors),
        }
