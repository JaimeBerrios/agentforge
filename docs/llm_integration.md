# AgentForge — Fase 5: Integración LLM Local con Ollama

## 1. Visión General y Arquitectura

La **Fase 5** introduce asistencia analítica basada en modelos de lenguaje de gran escala (LLM) ejecutados de forma local mediante [Ollama](https://ollama.ai/), preservando de manera estricta la arquitectura determinista desarrollada en las Fases 1 a 4.

### Principio Fundamental: Separación entre Hechos e Hipótesis

```
                                  [Entrada de Logs Crudos]
                                             │
                                             ▼
                                  ┌───────────────────────┐
                                  │   LogAnalysisAgent    │ (Fase 4 / Skills Fase 3)
                                  └──────────┬────────────┘
                                             │ [Métricas + Registros validados]
                                             ▼
                                  ┌───────────────────────┐
                                  │  IncidentTriageAgent  │ (Fase 4 - Prioridad determinista)
                                  └──────────┬────────────┘
                                             │ [TriageResult: Prioridad LOW/MED/HIGH/CRITICAL]
                                             ▼
                              ═══════════════════════════════
                                Frontera de Aislamiento LLM
                              ═══════════════════════════════
                                             │ [Prompt saneado y delimitado]
                                             ▼
                                  ┌───────────────────────┐
                                  │   LLMAnalysisAgent    │ (Fase 5 - Asistido por LLM)
                                  └──────────┬────────────┘
                                             │
                     ┌───────────────────────┴───────────────────────┐
                     ▼                                               ▼
       [OllamaProvider (Local)]                            [FakeLLMProvider (Mock)]
       - http://127.0.0.1:11434                             - Pruebas deterministas
       - Endpoint HTTP /api/generate                        - 0 llamadas de red
       - Detección de fallos y timeouts                     - Simulación de errores
```

### Reglas de Integridad
1. **La IA no altera métricas**: Conteos de eventos, registros válidos, anomalías estructurales y conteos de severidad son calculados exclusivamente por el motor determinista.
2. **La IA no altera la prioridad de triaje**: `TriagePriority` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) asignada por `IncidentTriageAgent` prevalece en todo momento.
3. **Etiquetado transparente de no confirmación**: Cualquier sugerencia o explicación generada por el LLM se almacena con el prefijo explícito `[Hipótesis no confirmada]`.
4. **Degradación graciosa**: Si el servidor Ollama está apagado, timeout o el modelo no existe, el pipeline determinista sigue operando con 100% de éxito, registrando advertencias sin abortar.

---

## 2. Contratos y Adaptadores

### `LLMProviderProtocol` y Adaptadores
Ubicados en `src/agentforge/adapters/`:

- **`OllamaProvider`** (`src/agentforge/adapters/ollama.py`):
  - Conexión vía HTTP estándar (`urllib.request`) a la API de Ollama (`/api/generate`).
  - No realiza conexiones de red durante la inicialización de la clase.
  - No requiere librerías de terceros obligatorias para su funcionamiento básico.
  - Manejo de excepciones tipadas:
    - `LLMConnectionError`: Servidor apagado o rechazo de conexión.
    - `LLMTimeoutError`: Solicitud excede el tiempo límite configurado.
    - `LLMModelNotFoundError`: Modelo solicitado no existe en Ollama (HTTP 404).
    - `LLMResponseError`: Respuestas corruptas o códigos HTTP 5xx.
  - Método `is_available(timeout=2.0) -> bool`: Verificación no invasiva contra `/api/tags`.
  - **Privacidad**: Nunca registra en logs el prompt completo, datos sensibles ni tokens.

- **`FakeLLMProvider`** (`src/agentforge/adapters/fake_llm.py`):
  - Adaptador simulado para pruebas unitarias e integración herméticas.
  - Permite encolar respuestas, registrar prompts recibidos e inducir fallos controlados.

---

## 3. Seguridad y Mitigación de Prompt Injection

Los logs son considerados **datos no confiables (untrusted data)** emitidos por aplicaciones externas.

### Medidas Implementadas
1. **Delimitación Estricta**:
   Las muestras de logs se aíslan dentro de etiquetas `<untrusted_log_data>...</untrusted_log_data>`.
2. **Neutralización de Escape**:
   Cualquier intento de cerrar la etiqueta (`</untrusted_log_data>`) dentro del cuerpo de un log se sustituye por `[TAG_CERRADA_NEUTRALIZADA]`.
3. **Instrucciones del Sistema Prioritarias**:
   El prompt instruye de forma imperativa al LLM a tratar el bloque delimitado como texto pasivo de telemetría y a ignorar cualquier comando embebido.
4. **Límites Estrictos de Entrada**:
   - `max_sample_messages = 5`: Solo se transmiten hasta 5 mensajes de muestra.
   - `max_message_chars = 200`: Cada mensaje es truncado para evitar desbordes de contexto.
   - `max_prompt_chars = 4000`: Límite superior sobre el prompt consolidado.
5. **No Ejecución**:
   Las respuestas del modelo son procesadas como cadenas de texto pasivas; en ningún caso se evalúan con `eval()`, `exec()` ni se ejecutan en consola.

> [!WARNING]
> **Limitación de seguridad**: Las mitigaciones reducen drásticamente el riesgo de inyección de prompt pero, dada la naturaleza probabilística de los modelos de lenguaje, no garantizan inmunidad matemática total frente a ataques de ingeniería de prompts adversariales avanzados. La verdadera garantía de seguridad radica en que el sistema de toma de decisiones no depende del texto del LLM, sino de las reglas deterministas inmutables.

---

## 4. Configuración TOML

### Ejemplo de Proveedor Ollama (`configs/ollama_provider_example.toml`)
```toml
[provider.ollama]
name = "ollama"
host = "http://127.0.0.1:11434"
model = "qwen2.5-coder:3b"
timeout = 30.0
max_retries = 0
temperature = 0.2

[provider.ollama.options]
num_predict = 512
top_p = 0.9
```

### Ejemplo de Pipeline Coordinado (`configs/llm_pipeline_example.toml`)
```toml
[pipeline]
name = "Full Coordinated Pipeline with Local LLM"
description = "Pipeline que combina análisis determinista, triaje e hipótesis no verificadas con LLM."
agents = [
    "log_analysis_agent",
    "incident_triage_agent",
    "llm_analysis_agent",
]

[log_analysis_agent]
id = "log_analysis_agent"
skills = ["log-parser", "anomaly-detector", "incident-reporter"]

[incident_triage_agent.thresholds]
critical_operational_errors = 5
high_operational_errors = 1
critical_anomaly_rate = 50.0
high_anomaly_rate = 20.0
medium_anomaly_rate = 5.0
medium_warnings_count = 1

[llm_analysis_agent]
id = "llm_analysis_agent"
provider = "ollama"
max_sample_messages = 5
max_message_chars = 200
max_prompt_chars = 4000

[llm_analysis_agent.provider_config]
host = "http://127.0.0.1:11434"
model = "qwen2.5-coder:3b"
timeout = 30.0
```

---

## 5. Instrucciones de Uso y Demostración

### Uso Programático con Proveedor Simulado (Sin Dependencias)
```python
from agentforge.adapters.fake_llm import FakeLLMProvider
from agentforge.agents.analysis_agent import LogAnalysisAgent
from agentforge.agents.coordinator import AgentCoordinator
from agentforge.agents.llm_agent import LLMAnalysisAgent
from agentforge.agents.triage_agent import IncidentTriageAgent

# Instanciación
fake_llm = FakeLLMProvider(
    default_response=(
        "Hipótesis: Sobrecarga en la base de datos por conexiones no liberadas.\n"
        "Recomendación: Auditar el middleware de transacciones."
    )
)
llm_agent = LLMAnalysisAgent(llm_provider=fake_llm)
coordinator = AgentCoordinator(
    analysis_agent=LogAnalysisAgent(),
    triage_agent=IncidentTriageAgent(),
    llm_agent=llm_agent,
)

# Ejecución
lines = ["[ERROR] 2024-05-10 Fallo al conectar a PostgreSQL"]
result = coordinator.coordinate(lines)

print(result.triage_result.priority)  # TriagePriority.HIGH (determinista)
print(result.llm_result.hypotheses)  # ('[Hipótesis no confirmada] Sobrecarga...')
```

### Demostración con Ollama Local Real
Si dispones del servicio Ollama activo (`systemctl status ollama` o `ollama serve`) y un modelo instalado (ej. `qwen2.5-coder:3b` o `llama3.2`):

```python
from agentforge.adapters.ollama import OllamaConfig, OllamaProvider
from agentforge.agents.llm_agent import LLMAnalysisAgent

config = OllamaConfig(host="http://127.0.0.1:11434", model="qwen2.5-coder:3b")
provider = OllamaProvider(config)

if provider.is_available():
    llm_agent = LLMAnalysisAgent(llm_provider=provider)
    # Ejecutar pipeline con llm_agent...
```

---

## 6. Evidencia de Verificación y Pruebas

### 6.1 Suite Automatizada Hermética (Sin llamadas externas)
Ejecución de la suite completa de pruebas:
- **121 pruebas pasadas, 53 subpruebas pasadas** en 0.22s.
- Cobertura completa de adaptadores (`OllamaProvider` y `FakeLLMProvider`), mitigación de prompt injection, límites de longitud y degradación ante caídas de servidor y timeouts.
- **Ruff**: 0 errores de comprobación (`All checks passed!`) y 100% de archivos formateados.

### 6.2 Prueba Controlada en Vivo con Ollama Local (`qwen2.5-coder:3b`)
Ejecutada sobre Fedora Linux contra el servicio local `http://127.0.0.1:11434` procesando el fixture `logs_validos.txt`:

```text
Ollama disponible: True
Ejecutando pipeline coordinado de 3 agentes con logs_validos.txt...
Éxito global: True
Prioridad determinista: HIGH
Errores operacionales observados: 3
Éxito inferencia LLM: True
Proveedor: ollama
Modelo: qwen2.5-coder:3b
Prioridad en LLMResult (invariable): HIGH

Hipótesis generadas (marcadas como no confirmadas):
 - [Hipótesis no confirmada] Los errores operacionales pueden estar relacionados con problemas
   de rendimiento del sistema, posiblemente debido a un aumento en el número de operaciones
   concurrentes o a un problema en el rendimiento del hardware.

Recomendaciones generadas:
 - Realizar una auditoría del rendimiento del sistema para identificar cualquier problema
   potencial en el rendimiento y tomar medidas para mejorarla.
 - Implementar un sistema de monitoreo más avanzado para detectar problemas de rendimiento
   antes de que afecten a la operación del sistema.

Advertencias registradas: ()
```

### 6.3 Verificación de Degradación Graciosa
Cuando el servicio de Ollama excede el timeout configurado o se encuentra inaccesible, el sistema no aborta:
- `Éxito global: True`
- `Prioridad determinista: HIGH` (conservada intacta)
- `Éxito inferencia LLM: False`
- `Advertencias registradas`: `("Proveedor LLM 'ollama' no disponible o falló: LLMTimeoutError: ...",)`
- Hipótesis y recomendaciones vacías sin contaminar los hechos confirmados.

