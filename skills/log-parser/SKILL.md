# Skill: log-parser

## 1. Identificador y Descripción
- **Identificador único:** `log-parser`
- **Descripción:** Procesa colecciones de registros de log en memoria extrayendo tokens y aplicando validación semántica de fechas y completitud mediante `LogEngineService`.

## 2. Propósito y Casos de Uso
- **Propósito:** Actuar como la primera etapa de ingestión determinista en un pipeline agéntico, transformando texto crudo en entidades tipadas `ParsedLogEntry` y calculando métricas iniciales `LogMetrics`.
- **Casos de uso:**
  - Análisis de flujos de texto procedentes de archivos, sockets o APIs.
  - Validación sintáctica y semántica previa a la detección de anomalías.
  - Generación de estadísticas base de severidad y calendario gregoriano.

## 3. Entradas y Salidas
- **Entrada esperada (`ExecutionContext.get_latest_output()` o `context.initial_input`):**
  - Cadena de texto multilínea (`str`).
  - Colección de cadenas (`list[str]`, `tuple[str, ...]`).
  - Diccionario estructurado con la clave `'lines'` o `'logs'` conteniendo secuencias de cadenas.
- **Salida estructurada (`SkillResult.output`):**
  - Objeto `LogParserOutput`:
    - `entries`: Tupla de objetos inmutables `ParsedLogEntry`.
    - `metrics`: Objeto `LogMetrics` con contadores agregados.
    - `total_lines`: Entero con la cantidad de registros procesados.

## 4. Procedimiento de Ejecución
1. Extrae y valida que la entrada recibida sea iterable y esté compuesta por cadenas de texto.
2. Si la entrada está vacía, genera una salida con 0 eventos y métricas en cero con `success=True`.
3. Itera secuencialmente sobre cada línea aplicando `LogEngineService.process_line(line)`.
4. Acumula contadores independientes en `LogMetricsAccumulator`.
5. Empaqueta el resultado en un `LogParserOutput` inmutable y lo retorna dentro de un `SkillResult` exitoso.

## 5. Restricciones
- No realiza lecturas directas del sistema de archivos (`open`, `Path.read_text`).
- No altera el texto original ni descarta líneas no reconocidas; todas son catalogadas en uno de los 3 estados: `valida`, `incompleta` o `mal_formateada`.
- No requiere ni invoca modelos de lenguaje (LLM).

## 6. Ejemplo Funcional
```python
from agentforge.core.contracts import ExecutionContext
from agentforge.skills.log_parser import LogParserSkill

skill = LogParserSkill()
context = ExecutionContext(
    agent_id="test_agent",
    initial_input=[
        "[INFO] 2024-05-10 Conexión establecida",
        "[ERROR] 2024-02-30 Fecha imposible",
    ],
)
result = skill.execute(context)
assert result.success is True
assert len(result.output.entries) == 2
assert result.output.entries[0].estado == "valida"
assert result.output.entries[1].estado == "mal_formateada"
```

## 7. Errores Esperados
- **Error de validación de entrada:** Si la entrada contiene tipos no soportados (ej. enteros, bytes, booleanos), la skill retorna `SkillResult(success=False, error="Error de validación de entrada en log-parser: ...")` sin abortar el proceso del agente.

## 8. Dependencias
- `agentforge.core.contracts` (`ExecutionContext`, `SkillProtocol`, `SkillResult`).
- `agentforge.core.types` (`LogMetrics`, `ParsedLogEntry`).
- `agentforge.logs.service` (`LogEngineService`).
- `agentforge.logs.metrics` (`LogMetricsAccumulator`).

## 9. Relación con Otras Skills
- **Predecesoras:** Ninguna (usualmente es la primera capacidad en la cadena).
- **Sucesoras:** Entrega su salida directamente a `anomaly-detector`.
