# AgentForge — Informe Académico y Técnico de Refactorización Agéntica

**Programa**: AI for Developers Jr. — KODIGO Academy  
**Autor**: Jaime Berríos  
**Proyecto**: AgentForge (`agentforge`)  
**Proyecto Base de Referencia**: `ai-first-log-analyzer` (Commit `ebeb2845dcdbb779fa2be92bcc5057a64b75c6f3`)  
**Fecha de Publicación**: Noviembre 2026  

---

## 1. El Proyecto Original y sus Limitaciones

El proyecto original [`ai-first-log-analyzer`](https://github.com/JaimeBerrios/ai-first-log-analyzer) consistía en un script monolítico de Python (`log_analyzer.py`) diseñado para analizar registros estructurados en formato `[SEVERIDAD] AAAA-MM-DD Mensaje`.

### Limitaciones Identificadas:
1. **Ausencia de capacidades agénticas o de IA**: Pese a su nombre, el proyecto original no contenía ningún agente, ninguna llamada a modelos de lenguaje ni arquitectura modular; era un script puramente procedimental.
2. **Monolitismo y acoplamiento severo**:
   - Mezclaba la lectura física de archivos desde disco (`open()`), el parsing por expresiones regulares, la validación de fechas, el cálculo de métricas acumuladas y la impresión directa en consola con `print()`.
   - Era imposible consumir el análisis en memoria (por ejemplo, a partir de flujos de red o colas de eventos) sin modificar el código fuente.
3. **Manejo de tipos primitivo**:
   - Los registros analizados se modelaban como diccionarios planos `dict[str, Any]` sin tipado estático ni inmutabilidad, facilitando errores por mutaciones accidentales.
4. **Discrepancias en la documentación histórica**:
   - La documentación previa afirmaba que `logs_invalidos.txt` contenía 1 registro válido y 1 incompleto, cuando la ejecución real demostró que contenía **0 válidos, 4 incompletos y 12 mal formateados** (16 anomalías en total).

---

## 2. Refactorización Realizada

La refactorización se ejecutó en fases estrictamente justificadas y verificadas contra la línea base inmutable preservada en `legacy/`:

### 2.1 Fase 0: Caracterización y Preservación de Línea Base
- Se importó una copia inmutable del proyecto original en `legacy/ai_first_log_analyzer/` y se calcularon sus sumas de verificación criptográficas SHA-256.
- Se implementaron 16 pruebas de caracterización ([`tests/test_characterization.py`](file:///home/jaimeberrios/Proyectos/Kodigo/agentforge/tests/test_characterization.py)) que capturaron el comportamiento observable exacto del código legado antes de cualquier modificación.

### 2.2 Fase 1: Extracción del Motor Determinista
- Separación de responsabilidades en módulos puros e independientes de I/O de disco y consola:
  - `src/agentforge/core/types.py`: Dataclasses inmutables (`ParsedLogEntry`, `LogMetrics`, `LogStatus`, `SeverityLevel`).
  - `src/agentforge/logs/parser.py`: Extracción sintáctica sin validación de negocio.
  - `src/agentforge/logs/validator.py`: Validación de calendario gregoriano completo (incluyendo la regla centenaria de años bisiestos: divisibles por 4 y no por 100, excepto divisibles por 400).
  - `src/agentforge/logs/metrics.py`: Acumulador de contadores.
  - `src/agentforge/logs/service.py`: Fachada `LogEngineService` con interfaz dual (`analizar_lineas` en memoria y `analizar_archivo` para compatibilidad histórica).
- **Paridad 100%**: Comprobada mediante pruebas de paridad línea por línea contra la implementación original.

### 2.3 Fase 2: Núcleo Agéntico y Contratos
- Definición de protocolos runtime-checkable estándar (`SkillProtocol`, `AgentProtocol`, `LLMProviderProtocol`).
- Registro dinámico `SkillRegistry` con resolución autorizada de capacidades.
- Ejecutor secuencial determinista `SequentialAgentRunner` con inmutabilidad de contexto.

---

## 3. Skills Propias Documentadas mediante `SKILL.md`

Se crearon tres capacidades modulares autónomas bajo el estándar `SKILL.md`:

1. **`log-parser`** ([`skills/log-parser/SKILL.md`](file:///home/jaimeberrios/Proyectos/Kodigo/agentforge/skills/log-parser/SKILL.md)):
   - Convierte cadenas de logs crudos en registros tipados y métricas acumuladas mediante `LogEngineService`.
   - Código: [`src/agentforge/skills/log_parser.py`](file:///home/jaimeberrios/Proyectos/Kodigo/agentforge/src/agentforge/skills/log_parser.py).
2. **`anomaly-detector`** ([`skills/anomaly-detector/SKILL.md`](file:///home/jaimeberrios/Proyectos/Kodigo/agentforge/skills/anomaly-detector/SKILL.md)):
   - Clasifica registros anómalos (`incompleta` vs `mal_formateada`).
   - Distingue rigurosamente entre **severidad operacional válida** (`[ERROR]` funcional de base de datos) y **anomalías estructurales** (corchetes rotos o fechas imposibles como 30 de febrero).
   - Código: [`src/agentforge/skills/anomaly_detector.py`](file:///home/jaimeberrios/Proyectos/Kodigo/agentforge/src/agentforge/skills/anomaly_detector.py).
3. **`incident-reporter`** ([`skills/incident-reporter/SKILL.md`](file:///home/jaimeberrios/Proyectos/Kodigo/agentforge/skills/incident-reporter/SKILL.md)):
   - Genera reportes estructurados consolidados con observaciones objetivas basadas en hechos observables.
   - Código: [`src/agentforge/skills/incident_reporter.py`](file:///home/jaimeberrios/Proyectos/Kodigo/agentforge/src/agentforge/skills/incident_reporter.py).

---

## 4. Personalización del Sistema Agéntico

En lugar de construir agentes genéricos, se desarrollaron roles altamente especializados:

### 4.1 `LogAnalysisAgent`
Agente especializado que orquesta internamente el pipeline de las tres skills en estricto orden secuencial (`log-parser` $\to$ `anomaly-detector` $\to$ `incident-reporter`) reutilizando el motor determinista sin duplicar lógica.

### 4.2 `IncidentTriageAgent`
Agente de toma de decisiones operativas basado en reglas deterministas cuantitativas. Asigna niveles de prioridad (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`):
- `CRITICAL`: $\ge 5$ errores operacionales o tasa de anomalías $\ge 50\%$.
- `HIGH`: $\ge 1$ error operacional o tasa de anomalías $\ge 20\%$.
- `MEDIUM`: Tasa de anomalías $\ge 5\%$, advertencias $\ge 1$ o registros incompletos.
- `LOW`: Lote nominal limpio.

**Garantía**: Sus metadatos declaran formalmente que la prioridad es una propuesta basada en reglas operativas, no un diagnóstico causal médico ni de certeza absoluta.

### 4.3 `AgentCoordinator`
Orquestador secuencial desacoplado que transfiere de forma inmutable los resultados entre agentes sin variables globales ni efectos secundarios.

---

## 5. El Uso del LLM y sus Límites

La integración de modelos de lenguaje en la **Fase 5** y su estabilización en la **Fase 6** se rigieron bajo una estricta política de seguridad:

### 5.1 Confinamiento y Frontera de Datos
- El LLM **nunca es la fuente de verdad** para métricas, conteos, estados ni prioridades.
- Su función se limita a formular hipótesis preliminares sobre posibles causas raíz y recomendaciones técnicas adicionales.
- Todas las hipótesis son etiquetadas con el prefijo obligatorio: `[Hipótesis no confirmada]`.

### 5.2 Mitigaciones de Seguridad Implementadas
1. **Delimitación de Datos**: Las muestras de logs se aíslan dentro de `<untrusted_log_data>`. Se neutralizan intentos de cierre de etiquetas (`</untrusted_log_data>`).
2. **Preservación de Instrucciones Críticas**: Si el tamaño del prompt excede el presupuesto (`max_prompt_chars=4000`), el agente reduce o descarta progresivamente las muestras de logs no confiables, asegurando que las reglas de seguridad y la tarea nunca sean recortadas.
3. **Prevención de SSRF**: `OllamaProvider` restringe destinos exclusivamente a hosts locales autorizados (`localhost`, `127.0.0.1`, `::1`), rechazando intentos de redirección hacia IPs internas o de metadatos de nube.
4. **Protección de Memoria**: Límite de 2 MB en respuestas HTTP contra Ollama para evitar ataques de denegación de servicio por agotamiento de memoria.
5. **Degradación Graciosa**: Si el servidor Ollama no está disponible, cae por timeout o el modelo no existe, el pipeline determinista culmina con éxito total, informando la indisponibilidad del LLM en advertencias.

---

## 6. Decisiones Tomadas Durante el Desarrollo Asistido por IA

Durante las sesiones de diseño asistido por IA, se tomaron decisiones arquitectónicas deliberadas:
1. **Uso de Python estándar (`urllib.request`) para el adaptador Ollama**: Evitó introducir dependencias pesadas de terceros en el paquete base de desarrollo, asegurando que las pruebas corran en entornos aislados sin conexión.
2. **Inmutabilidad Profunda (`dataclasses(frozen=True, slots=True)`)**: Todos los modelos de intercambio entre skills y agentes son inmutables, protegiendo contra mutaciones accidentales concurrentes o en cascada.
3. **Diseño Hermético de Pruebas**: Se diseñó `FakeLLMProvider` para que el 100% de la suite de pruebas unitarias y de integración se ejecute en milisegundos sin requerir servicios externos activos.

---

## 7. Problemas Detectados y Soluciones Verificadas

| # | Problema Detectado | Causa Raíz | Solución Aplicada y Verificada |
| :--- | :--- | :--- | :--- |
| 1 | Discrepancia histórica en `logs_invalidos.txt` | El README original asumía 1 registro válido y 1 incompleto. | La caracterización demostró 0 válidos y 16 anomalías (12 mal formateadas, 4 incompletas). Se documentó en `docs/baseline.md`. |
| 2 | Fecha 29 de febrero en años no bisiestos | Validación de expresiones regulares no puede verificar calendarios. | Implementación de `validar_fecha()` con lógica gregoriana completa de bisiestos en `src/agentforge/logs/validator.py`. |
| 3 | Severidad no nula en corchetes rotos | Registros como `(INFO)` o `[ INFO]` no deben extraer severidad válida. | Extracción condicional estricta donde solo corchetes exactos `[INFO]`, `[WARNING]`, `[ERROR]` pueblan `severidad`. |
| 4 | Riesgo SSRF en adaptador Ollama | Conexión a IPs arbitrarias configurables externamente. | Validación estricta de `allowed_hosts` en `OllamaConfig`, limitando por defecto a interfaces de loopback local. |
| 5 | Truncamiento de instrucciones de seguridad | Truncar el prompt consolidado al final eliminaba las directivas del sistema. | Presupuestación adaptativa: se descartan muestras de logs antes que recortar el prompt del sistema. |
| 6 | Aceptación de métricas corruptas (NaN/Inf) | Ausencia de validación en diccionarios externos pasados al triaje. | Validación estricta con `_validate_numeric_fact()` y `_get_validated_int/float()`, rechazando NaN, Inf y valores negativos. |

---

## 8. Evidencias Reproducibles de Pruebas

- **Total de pruebas automatizadas**: **140 pruebas y 53 subpruebas**, ejecutadas en 0.22 segundos con `pytest`.
- **Comprobación de calidad y formato**: `ruff check .` (0 errores) y `ruff format --check .` (100% conforme en 63 archivos).
- **Integridad del proyecto original**: La carpeta `legacy/` mantiene intactos sus archivos y sumas SHA-256 originales.
- **Workflow de Integración Continua**: Configurado en `.github/workflows/ci.yml` ejecutando linting, formateo y pruebas automatizadas en Python 3.12.
