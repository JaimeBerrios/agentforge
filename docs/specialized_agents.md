# Agentes Especializados y Coordinación — Fase 4

**Proyecto:** AgentForge  
**Rama:** `feat/specialized-agents`  
**Fase:** Fase 4 — Agentes especializados y orquestación  
**Fecha:** Noviembre 2026  

---

## 1. Arquitectura General y Reutilización de Capacidades

La Fase 4 introduce agentes de dominio especializados y un mecanismo de coordinación determinista, reutilizando de forma transparente el núcleo agéntico de la Fase 2 y las skills modulares desarrolladas en la Fase 3:

```
src/agentforge/agents/
├── __init__.py           # Exportaciones públicas de agentes y tipos
├── types.py              # Modelos de triaje: TriagePriority, TriageThresholds, TriageResult, CoordinatedExecutionResult
├── analysis_agent.py     # LogAnalysisAgent: Orquesta el pipeline de skills sin duplicar lógica
├── triage_agent.py       # IncidentTriageAgent: Evalúa reportes y asigna prioridades operativas
└── coordinator.py        # AgentCoordinator: Coordina la transferencia inmutable entre ambos agentes
```

### Reutilización de Componentes Previos
- **`LogAnalysisAgent`** no reimplementa parsing, ni validación de calendario, ni agregación estadística. Instancia un `SequentialAgentRunner` con la configuración declarativa y ejecuta en secuencia las tres skills de la Fase 3:
  1. `log-parser` (Ingestión y extracción determinista).
  2. `anomaly-detector` (Separación de severidad de negocio vs. formato).
  3. `incident-reporter` (Generación de `IncidentReport` factual).
- **`IncidentTriageAgent`** consume directamente el `IncidentReport` estructurado y emite un `TriageResult`.
- **`AgentCoordinator`** orquesta ambos agentes transmitiendo los datos mediante argumentos inmutables, **sin variables globales ni concurrencia no controlada**.

---

## 2. Responsabilidades por Agente

| Agente / Componente | Rol en el Framework | Entrada | Salida |
| :--- | :--- | :--- | :--- |
| **`LogAnalysisAgent`** | Extracción, validación determinista, detección de anomalías y reporte fáctico. | `list[str]`, `str`, o `dict` con líneas de log | `AgentRunResult` con trazabilidad de 3 pasos y `IncidentReport` final. |
| **`IncidentTriageAgent`** | Triaje operativo, cálculo de prioridades cuantitativas y recomendaciones. | `IncidentReport` (o `AgentRunResult`) | `AgentRunResult` con `TriageResult` estructurado. |
| **`AgentCoordinator`** | Orquestación secuencial defensiva de extremo a extremo. | Flujo de logs crudos (`Any`) | `CoordinatedExecutionResult` consolidado con ambos resultados. |

---

## 3. Reglas Cuantitativas de Priorización

El agente `IncidentTriageAgent` aplica reglas explícitas sobre umbrales configurables (`TriageThresholds`):

| Prioridad | Condición Cuantitativa Determinista | Justificación Factual |
| :---: | :--- | :--- |
| **`CRITICAL`** | `operational_errors >= 5` **o** `anomaly_rate >= 50.0%` | Fallo operativo masivo o corrupción estructural crítica del lote de logs. |
| **`HIGH`** | `operational_errors >= 1` **o** `anomaly_rate >= 20.0%` | Detección de fallos operacionales `ERROR` en logs válidos o degradación notable de formato. |
| **`MEDIUM`** | `anomaly_rate >= 5.0%` **o** `operational_warnings >= 1` **o** `incomplete_records > 0` | Presencia de advertencias `WARNING`, eventos truncados o anomalías moderadas. |
| **`LOW`** | Lote nominal (0 errores operacionales y anomalías < 5.0%) | Sistema en estado saludable sin eventos críticos. |

> [!IMPORTANT]
> **Declaración Metodológica y Disclaimer Operativo:**  
> Las prioridades (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) y las recomendaciones generadas representan **propuestas operativas basadas en reglas deterministas**, **no diagnósticos causales confirmados**. Su propósito es asistir al equipo de operaciones en la clasificación ágil de incidentes sin inventar causas no comprobadas.

---

## 4. Ejemplos Reproducibles de Ejecución

### 4.1 Lote con Errores Operacionales (`tests/fixtures/logs_validos.txt`)
- **Datos:** 10 eventos bien formateados, incluyendo 3 con severidad `ERROR` (fallo de base de datos, timeout de consulta, fallo de pasarela de pagos).
- **Resultado del Análisis:** 10 válidos (100%), 0 anomalías.
- **Resultado del Triaje:**
  - **Prioridad:** `HIGH` (3 errores operacionales $\ge$ umbral alto de 1).
  - **Justificación:** *"Se detectaron 3 eventos operacionales ERROR en registros válidos (umbral alto: 1)."*
  - **Recomendación:** *"Auditar los componentes que emitieron los 3 eventos ERROR válidos para identificar fallos en servicios o dependencias."*

### 4.2 Lote con Anomalías Estructurales (`tests/fixtures/logs_invalidos.txt`)
- **Datos:** 16 registros anómalos (4 incompletos y 12 mal formateados por corchetes espurios, fechas inexistentes como 30 de febrero, etc.).
- **Resultado del Análisis:** 0 válidos, 16 anomalías (tasa de anomalía: 100.0%).
- **Resultado del Triaje:**
  - **Prioridad:** `CRITICAL` (tasa del 100.0% $\ge$ umbral crítico del 50.0%).
  - **Justificación:** *"La tasa de anomalías estructurales (100.0%) supera o iguala el umbral crítico (50.0%)."*
  - **Recomendación:** *"Revisar los emisores de logs que produjeron 12 registros mal formateados por corchetes rotos o fechas inexistentes."* e *"Inspeccionar el mecanismo de recolección para evitar truncamiento de 4 eventos."*

---

## 5. Configuración Declarativa Externa

Se diseñaron dos archivos de configuración TOML:
1. [`configs/triage_rules_example.toml`](../configs/triage_rules_example.toml): Parametriza umbrales de triaje de forma segura sin código ejecutable.
2. [`configs/coordinated_pipeline_example.toml`](../configs/coordinated_pipeline_example.toml): Define el pipeline de los dos agentes especializados y sus parámetros operativos.

---

## 6. Limitaciones del Sistema

1. **Determinismo Heurístico:** La asignación de prioridades depende estrictamente de umbrales cuantitativos numéricos; no evalúa semántica contextual libre ni correlaciones de red complejas (reservado para fases con LLM).
2. **Recomendaciones Basadas en Hechos:** Las recomendaciones son plantillas accionables estructuradas; el sistema deliberadamente no infiere causas raíz hipotéticas para evitar alucinaciones.
3. **Flujo Unidireccional:** El coordinador opera de forma lineal (`LogAnalysisAgent` $\to$ `IncidentTriageAgent`); no implementa ciclos de retroalimentación ni reintentos automáticos.
