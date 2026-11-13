"""Interfaz de línea de comandos (CLI) para AgentForge."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from agentforge.adapters.fake_llm import FakeLLMProvider
from agentforge.adapters.ollama import OllamaConfig, OllamaProvider
from agentforge.agents.analysis_agent import LogAnalysisAgent
from agentforge.agents.coordinator import AgentCoordinator
from agentforge.agents.llm_agent import LLMAnalysisAgent
from agentforge.agents.triage_agent import IncidentTriageAgent
from agentforge.agents.types import CoordinatedExecutionResult

MAX_CLI_FILE_BYTES = 10 * 1024 * 1024  # 10 MB límite para archivos en CLI


def build_parser() -> argparse.ArgumentParser:
    """Construye y configura el parser de argumentos de la CLI."""
    parser = argparse.ArgumentParser(
        prog="agentforge",
        description="AgentForge: Framework modular agéntico para análisis determinista de logs.",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version="AgentForge 0.1.0",
        help="Muestra la versión de AgentForge y finaliza.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Ejecuta el análisis coordinado sobre un archivo de logs.",
    )
    analyze_parser.add_argument(
        "--file",
        "-f",
        required=True,
        type=str,
        help="Ruta al archivo de logs a procesar.",
    )
    analyze_parser.add_argument(
        "--llm",
        choices=["none", "fake", "ollama"],
        default="none",
        help="Proveedor LLM opcional para asistencia analítica (default: none).",
    )
    analyze_parser.add_argument(
        "--model",
        type=str,
        default="qwen2.5-coder:3b",
        help="Nombre del modelo Ollama a utilizar (default: qwen2.5-coder:3b).",
    )
    analyze_parser.add_argument(
        "--host",
        type=str,
        default="http://127.0.0.1:11434",
        help="Host del servidor Ollama (default: http://127.0.0.1:11434).",
    )
    analyze_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Formato de salida de resultados (default: text).",
    )

    return parser


def format_text_output(result: CoordinatedExecutionResult, file_path: Path) -> str:
    """Genera una salida en texto plano estructurada y legible para terminal."""
    lines: list[str] = [
        "=" * 60,
        "          AGENTFORGE - REPORTE DE ANÁLISIS DE INCIDENTES",
        "=" * 60,
        f"Archivo analizado : {file_path}",
        f"Éxito del pipeline: {'SÍ' if result.success else 'NO'}",
    ]

    triage = result.triage_result
    if triage:
        lines.extend(
            [
                "-" * 60,
                f"PRIORIDAD DETERMINISTA ASIGNADA: [{triage.priority.value}]",
                f"- Errores operacionales en logs válidos: {triage.operational_error_count}",
                f"- Anomalías estructurales de formato   : {triage.format_anomaly_count}",
                "",
                "Razones de asignación:",
            ]
        )
        for r in triage.reasons:
            lines.append(f"  • {r}")

        lines.append("\nRecomendaciones operativas deterministas:")
        for rec in triage.recommendations:
            lines.append(f"  ➜ {rec}")

    llm = result.llm_result
    if llm:
        lines.extend(
            [
                "-" * 60,
                f"ASISTENCIA ANALÍTICA LLM (Proveedor: {llm.provider}, Modelo: {llm.model})",
            ]
        )
        if llm.success:
            if llm.hypotheses:
                lines.append("\nHipótesis preliminares generadas por IA (No verificadas):")
                for h in llm.hypotheses:
                    lines.append(f"  ? {h}")
            if llm.recommendations:
                lines.append("\nRecomendaciones sugeridas por IA:")
                for r in llm.recommendations:
                    lines.append(f"  • {r}")
        else:
            lines.append("\nAviso: La inferencia LLM no estuvo disponible o falló.")
            for w in llm.warnings:
                lines.append(f"  ! {w}")
            lines.append("  (Los resultados del análisis determinista permanecen intactos)")

    lines.append("=" * 60)
    return "\n".join(lines)


def format_json_output(result: CoordinatedExecutionResult, file_path: Path) -> str:
    """Genera una salida en JSON serializable y validado."""
    data: dict[str, Any] = {
        "file": str(file_path),
        "coordinated_result": result.to_dict(),
        "triage": result.triage_result.to_dict() if result.triage_result else None,
        "llm_analysis": result.llm_result.to_dict() if result.llm_result else None,
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def run_cli(args_list: list[str] | None = None) -> int:
    """Punto de entrada lógico para la ejecución de la CLI."""
    parser = build_parser()
    args = parser.parse_args(args_list)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "analyze":
        target_path = Path(args.file).resolve()

        if not target_path.exists():
            sys.stderr.write(f"Error: El archivo '{target_path}' no existe.\n")
            return 1

        if not target_path.is_file():
            sys.stderr.write(f"Error: La ruta '{target_path}' no es un archivo regular.\n")
            return 1

        try:
            file_size = target_path.stat().st_size
            if file_size > MAX_CLI_FILE_BYTES:
                msg = f"Error: Archivo supera límite permitido ({MAX_CLI_FILE_BYTES} bytes).\n"
                sys.stderr.write(msg)
                return 1

            lines = target_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception as err:
            sys.stderr.write(f"Error al leer el archivo '{target_path}': {err}\n")
            return 1

        # Configuración de agentes
        llm_agent: LLMAnalysisAgent | None = None
        if args.llm == "fake":
            llm_agent = LLMAnalysisAgent(llm_provider=FakeLLMProvider())
        elif args.llm == "ollama":
            try:
                config = OllamaConfig(host=args.host, model=args.model)
                provider = OllamaProvider(config)
                llm_agent = LLMAnalysisAgent(llm_provider=provider)
            except Exception as err:
                sys.stderr.write(f"Error al configurar Ollama: {err}\n")
                return 1

        coordinator = AgentCoordinator(
            analysis_agent=LogAnalysisAgent(),
            triage_agent=IncidentTriageAgent(),
            llm_agent=llm_agent,
        )

        result = coordinator.coordinate(lines)

        if args.format == "json":
            sys.stdout.write(format_json_output(result, target_path) + "\n")
        else:
            sys.stdout.write(format_text_output(result, target_path) + "\n")

        return 0 if result.success else 1

    return 0


def main() -> None:
    """Función de entrada para el script de consola."""
    sys.exit(run_cli())


if __name__ == "__main__":
    main()
