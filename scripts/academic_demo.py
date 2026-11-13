# ruff: noqa: E402
"""Demostración académica reproducible para AgentForge (KODIGO Academy).

Ejecuta los 7 escenarios arquitectónicos clave del framework:
1. Análisis de logs válidos.
2. Identificación y clasificación de registros mal formateados / incompletos.
3. Priorización operativa determinista cuantitativa.
4. Ejecución del pipeline completo de tres agentes.
5. Análisis asistido por IA mediante FakeLLMProvider (hermético, 0 llamadas a red).
6. Ejecución opcional con Ollama local real (qwen2.5-coder:3b).
7. Simulación de fallo de Ollama con degradación graciosa y conservación de la verdad determinista.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Configurar path raíz
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from agentforge.adapters.exceptions import LLMConnectionError
from agentforge.adapters.fake_llm import FakeLLMProvider
from agentforge.adapters.ollama import OllamaConfig, OllamaProvider
from agentforge.agents.analysis_agent import LogAnalysisAgent
from agentforge.agents.coordinator import AgentCoordinator
from agentforge.agents.llm_agent import LLMAnalysisAgent
from agentforge.agents.triage_agent import IncidentTriageAgent


def print_banner(title: str, step: int) -> None:
    print("\n" + "=" * 70)
    print(f" ESCENARIO {step}: {title.upper()}")
    print("=" * 70)


def run_demo(run_live_ollama: bool = False) -> None:
    fixtures_dir = REPO_ROOT / "tests" / "fixtures"
    valid_lines = (fixtures_dir / "logs_validos.txt").read_text(encoding="utf-8").splitlines()
    invalid_lines = (fixtures_dir / "logs_invalidos.txt").read_text(encoding="utf-8").splitlines()

    # ---------------------------------------------------------
    # Escenario 1: Análisis determinista de logs válidos
    # ---------------------------------------------------------
    print_banner("Análisis determinista de registros válidos", 1)
    analysis_agent = LogAnalysisAgent()
    valid_res = analysis_agent.run(valid_lines)
    print(f"Estado de ejecución: {'ÉXITO' if valid_res.success else 'FALLO'}")
    facts = valid_res.final_output.facts
    print(f"Total registros analizados : {facts['total_events']}")
    print(f"Registros válidos          : {facts['valid_events']}")
    print(f"Eventos ERROR operacionales: {facts['operational_errors']}")
    print(f"Tasa de anomalías          : {facts['anomalous_percentage']}%")

    # ---------------------------------------------------------
    # Escenario 2: Identificación de anomalías estructurales
    # ---------------------------------------------------------
    print_banner("Identificación y taxonomía de registros anómalos", 2)
    invalid_res = analysis_agent.run(invalid_lines)
    inv_facts = invalid_res.final_output.facts
    print(f"Total procesados           : {inv_facts['total_events']}")
    print(f"Registros mal formateados  : {inv_facts['malformed_records']} (sintaxis inválida)")
    print(f"Registros incompletos      : {inv_facts['incomplete_records']} (truncados/sin fecha)")
    print(f"Tasa de anomalías          : {inv_facts['anomalous_percentage']}%")

    # ---------------------------------------------------------
    # Escenario 3: Priorización operativa determinista
    # ---------------------------------------------------------
    print_banner("Triaje y priorización operativa cuantitativa", 3)
    triage_agent = IncidentTriageAgent()
    triage_valid = triage_agent.run(valid_res).final_output
    triage_invalid = triage_agent.run(invalid_res).final_output
    print(f"Prioridad asignada a logs_validos.txt   : [{triage_valid.priority.value}]")
    print(f"  ➜ Razón: {triage_valid.reasons[0]}")
    print(f"Prioridad asignada a logs_invalidos.txt : [{triage_invalid.priority.value}]")
    print(f"  ➜ Razón: {triage_invalid.reasons[0]}")

    # ---------------------------------------------------------
    # Escenario 4: Pipeline coordinado de tres agentes
    # ---------------------------------------------------------
    print_banner("Pipeline coordinado secuencial desacoplado", 4)
    fake_llm = FakeLLMProvider(
        default_response=(
            "Hipótesis: Posible cuello de botella en transacciones SQL concurrentes.\n"
            "Recomendación: Auditar tiempos de respuesta del pool de conexiones."
        )
    )
    llm_agent = LLMAnalysisAgent(llm_provider=fake_llm)
    coordinator = AgentCoordinator(
        analysis_agent=analysis_agent,
        triage_agent=triage_agent,
        llm_agent=llm_agent,
    )
    coord_result = coordinator.coordinate(valid_lines)
    print(f"Éxito coordinado           : {coord_result.success}")
    print(f"Orden de ejecución auditado: {' -> '.join(coord_result.execution_order)}")
    print(f"Prioridad determinista     : {coord_result.triage_result.priority.value}")

    # ---------------------------------------------------------
    # Escenario 5: Asistencia analítica con FakeLLMProvider
    # ---------------------------------------------------------
    print_banner("Generación asistida con FakeLLMProvider (Hermético)", 5)
    llm_out = coord_result.llm_result
    print(f"Proveedor configurado      : {llm_out.provider} (Modelo: {llm_out.model})")
    print(f"Prioridad conservada       : {llm_out.triage_priority.value} (Inmutable)")
    print("Hipótesis generadas (etiquetadas como no confirmadas):")
    for h in llm_out.hypotheses:
        print(f"  ? {h}")
    print("Recomendaciones generadas:")
    for r in llm_out.recommendations:
        print(f"  ➜ {r}")

    # ---------------------------------------------------------
    # Escenario 6: Ejecución con Ollama local real (opcional)
    # ---------------------------------------------------------
    print_banner("Ejecución con Ollama local (qwen2.5-coder:3b)", 6)
    if run_live_ollama:
        ollama_config = OllamaConfig(
            host="http://127.0.0.1:11434", model="qwen2.5-coder:3b", timeout=120.0
        )
        ollama_prov = OllamaProvider(ollama_config)
        if ollama_prov.is_available():
            real_coordinator = AgentCoordinator(
                analysis_agent=analysis_agent,
                triage_agent=triage_agent,
                llm_agent=LLMAnalysisAgent(llm_provider=ollama_prov),
            )
            real_res = real_coordinator.coordinate(valid_lines)
            print(f"Ollama local conectado     : SÍ ({ollama_config.host})")
            print(f"Prioridad determinista     : {real_res.triage_result.priority.value}")
            print(f"Éxito inferencia LLM       : {real_res.llm_result.success}")
            for h in real_res.llm_result.hypotheses:
                print(f"  ? {h}")
        else:
            print("Servidor Ollama no disponible en 127.0.0.1:11434 (demostración offline).")
    else:
        print("Demostración offline (use --with-ollama para invocar el servidor local en Fedora).")

    # ---------------------------------------------------------
    # Escenario 7: Simulación de fallo y degradación graciosa
    # ---------------------------------------------------------
    print_banner("Degradación graciosa ante caída de servicio LLM", 7)
    failing_fake = FakeLLMProvider()
    failing_fake.set_raise_error(LLMConnectionError("Servidor Ollama 127.0.0.1:11434 inalcanzable"))
    failing_coordinator = AgentCoordinator(
        analysis_agent=analysis_agent,
        triage_agent=triage_agent,
        llm_agent=LLMAnalysisAgent(llm_provider=failing_fake),
    )
    fail_result = failing_coordinator.coordinate(valid_lines)
    print(f"Éxito global del pipeline  : {fail_result.success} (¡Análisis no interrumpido!)")
    print(f"Prioridad determinista     : {fail_result.triage_result.priority.value}")
    llm_ok = "EXITOSA" if fail_result.llm_result.success else "FALLIDA"
    print(f"Estado de inferencia LLM   : {llm_ok}")
    print(f"Aviso capturado en warnings: {fail_result.llm_result.warnings[0]}")
    print("\n" + "=" * 70)
    print(" DEMOSTRACIÓN COMPLETADA EXITOSAMENTE")
    print("=" * 70)


if __name__ == "__main__":
    with_ollama = "--with-ollama" in sys.argv
    run_demo(run_live_ollama=with_ollama)
