"""Módulo de skills modulares de AgentForge."""

from __future__ import annotations

from agentforge.skills.anomaly_detector import AnomalyDetectorSkill
from agentforge.skills.incident_reporter import IncidentReporterSkill
from agentforge.skills.log_parser import LogParserSkill
from agentforge.skills.types import (
    AnomalyDetectorOutput,
    IncidentReport,
    LogParserOutput,
)

__all__ = [
    "AnomalyDetectorOutput",
    "AnomalyDetectorSkill",
    "IncidentReport",
    "IncidentReporterSkill",
    "LogParserOutput",
    "LogParserSkill",
]
