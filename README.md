# AgentForge 🛠️

**AgentForge** es un framework agéntico modular y extensible en Python (3.12+) diseñado para el análisis determinista de telemetría y logs, triaje operativo cuantitativo y asistencia analítica basada en modelos de lenguaje locales (LLMs) ejecutados mediante Ollama.

Desarrollado como proyecto de refactorización y extensión académica en el bootcamp **AI for Developers Jr.** de **KODIGO Academy**.

---

## 🎯 Problema que Resuelve

Los sistemas tradicionales de análisis de registros suelen oscilar entre dos extremos perjudiciales:
1. **Scripts rígidos monolíticos**: Acoplan estrechamente lectura de archivos, expresiones regulares y presentación en consola, impidiendo su reutilización en pipelines automatizados.
2. **Uso ingenuo de LLMs**: Pasar volcados masivos de logs a modelos generativos produce alucinaciones de cifras, riesgos severos de *prompt injection* y costos desmedidos de cómputo.

**AgentForge** resuelve esta disyuntiva mediante una **arquitectura híbrida**:
- **Motor determinista inmutable**: Parser, validador de fechas gregorianas y agregador de métricas actúan como única fuente de verdad matemática.
- **Triaje cuantitativo basado en reglas**: Asigna prioridades operativas (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) basadas en hechos empíricos.
- **Asistencia analítica LLM aislada**: La inteligencia artificial se confina a proponer hipótesis no verificadas y recomendaciones complementarias sobre datos acotados y saneados, sin poder alterar jamás las métricas ni las prioridades.

---

## 🏗️ Arquitectura del Sistema

```
                            [Fuente de Logs Crudos]
                                       │
                                       ▼
                     ┌───────────────────────────────────┐
                     │         LogAnalysisAgent          │
                     │  (Skills: parser, anomaly, report)│
                     └─────────────────┬─────────────────┘
                                       │ Hechos y Métricas Validadas
                                       ▼
                     ┌───────────────────────────────────┐
                     │        IncidentTriageAgent        │
                     │   (Prioridad y Triaje Operativo)  │
                     └─────────────────┬─────────────────┘
                                       │ TriageResult: [LOW / MED / HIGH / CRIT]
                                       ▼
                       ═════════════════════════════════
                         Frontera de Seguridad y Datos
                       ═════════════════════════════════
                                       │ Datos delimitados en <untrusted_log_data>
                                       ▼
                     ┌───────────────────────────────────┐
                     │         LLMAnalysisAgent          │
                     │  (Hipótesis y Recomendaciones IA) │
                     └─────────────────┬─────────────────┘
                                       ├── OllamaProvider (Local)
                                       └── FakeLLMProvider (Pruebas)
```

### Capas del Proyecto (`src/agentforge/`)
- `core/`: Contratos e interfaces (`SkillProtocol`, `AgentProtocol`, `LLMProviderProtocol`, `AgentRunResult`).
- `logs/`: Motor determinista refactorizado (parser sintáctico, validador de calendario, métricas agregadas).
- `skills/`: Capacidades modulares desacopladas (`log-parser`, `anomaly-detector`, `incident-reporter`).
- `agents/`: Agentes especializados (`LogAnalysisAgent`, `IncidentTriageAgent`, `LLMAnalysisAgent`) y `AgentCoordinator`.
- `adapters/`: Adaptadores de proveedores (`OllamaProvider`, `FakeLLMProvider`) con validaciones de seguridad.
- `cli/`: Interfaz de línea de comandos robusta.

---

## 📋 Requisitos del Entorno

- **Sistema Operativo**: Fedora Linux / Linux x86_64 / macOS.
- **Python**: 3.12 o superior (compatible con 3.13+).
- **Ollama** (opcional): Únicamente requerido si se desea ejecutar inferencia LLM local real.

---

## 🚀 Instalación en Fedora / Linux

```bash
# 1. Clonar el repositorio
git clone https://github.com/JaimeBerrios/agentforge.git
cd agentforge

# 2. Crear y activar el entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# 3. Instalar en modo editable con herramientas de desarrollo
pip install -e ".[dev]"
```

---

## 💻 Uso de la Interfaz de Línea de Comandos (CLI)

AgentForge provee el ejecutable `agentforge` (o invocable mediante `python -m agentforge`):

### 1. Análisis Determinista Estándar (Modo por Defecto)
```bash
agentforge analyze --file tests/fixtures/logs_validos.txt
```

### 2. Análisis con Salida JSON Estructurada
```bash
agentforge analyze --file tests/fixtures/logs_invalidos.txt --format json
```

### 3. Análisis con Asistencia Simulada (Fake LLM, sin red)
```bash
agentforge analyze --file tests/fixtures/logs_validos.txt --llm fake
```

### 4. Análisis Asistido por LLM Local Real (Ollama)
```bash
agentforge analyze --file tests/fixtures/logs_validos.txt --llm ollama --model qwen2.5-coder:3b
```

---

## 🤖 Configuración de Ollama Local

AgentForge incluye plantillas TOML de ejemplo en `configs/`:
- [`configs/ollama_provider_example.toml`](file:///home/jaimeberrios/Proyectos/Kodigo/agentforge/configs/ollama_provider_example.toml): Parámetros del servidor local (`http://127.0.0.1:11434`, modelo, temperatura).
- [`configs/llm_pipeline_example.toml`](file:///home/jaimeberrios/Proyectos/Kodigo/agentforge/configs/llm_pipeline_example.toml): Definición de pipeline coordinado con agentes.

```bash
# Iniciar servidor Ollama (en otra terminal o como servicio)
ollama serve

# Descargar modelo ligero recomendado (3B)
ollama pull qwen2.5-coder:3b
```

---

## 🧪 Ejecución de Pruebas y Linters

La suite completa es **100% hermética** y no requiere Ollama ni conexión a red para ejecutarse:

```bash
# Ejecutar todas las 140 pruebas automatizadas
.venv/bin/python -m pytest

# Comprobación de tipos y calidad de código con Ruff
.venv/bin/ruff check .

# Verificación de formato
.venv/bin/ruff format --check .

# Demostración académica interactiva de 7 escenarios
.venv/bin/python scripts/academic_demo.py
```

---

## 🔒 Mitigaciones y Límites de Seguridad

1. **Prevención de SSRF**: `OllamaProvider` restringe destinos a `localhost`, `127.0.0.1`, `::1` por defecto, rechazando IPs arbitrarias y credenciales incrustadas en URL.
2. **Protección de Memoria**: Límite estricto de 2 MB en lectura de respuestas HTTP para evitar agotamiento de memoria.
3. **Mitigación de Prompt Injection**: Delimitación explícita mediante `<untrusted_log_data>` y neutralización de etiquetas de escape.
4. **Preservación del Presupuesto de Seguridad**: Ante desbordes de longitud, se descartan muestras de logs no confiables antes de recortar directivas de seguridad.
5. **Validación de Métricas**: Rechazo sistemático de NaN, Infinito y conteos negativos.

---

## 📚 Enlaces a Documentación Técnica y Académica

- [Reporte Académico Integral (KODIGO Academy)](file:///home/jaimeberrios/Proyectos/Kodigo/agentforge/docs/academic_report.md)
- [Línea Base y Caracterización Histórica (Fase 0)](file:///home/jaimeberrios/Proyectos/Kodigo/agentforge/docs/baseline.md)
- [Especificación de Skills Propias (Fase 3)](file:///home/jaimeberrios/Proyectos/Kodigo/agentforge/skills/)
- [Agentes Especializados y Coordinación (Fase 4)](file:///home/jaimeberrios/Proyectos/Kodigo/agentforge/docs/specialized_agents.md)
- [Integración con LLM Local Ollama (Fase 5)](file:///home/jaimeberrios/Proyectos/Kodigo/agentforge/docs/llm_integration.md)
