# Skill: anomaly-detector

## 1. Identificador y Descripción
- **Identificador único:** `anomaly-detector`
- **Descripción:** Analiza los registros procesados por `log-parser` para clasificar anomalías estructurales y de completitud, separando estrictamente la severidad del evento frente a la validez de formato.

## 2. Propósito y Casos de Uso
- **Propósito:** Discriminar con precisión determinista las líneas que sufren de fallos de formato o falta de campos, de aquellas que son estructuralmente válidas pero reportan un fallo operativo (severidad `ERROR`).
- **Casos de uso:**
  - Detección de fallos en emisores de logs (corchetes faltantes, fechas erróneas).
  - Auditoría de completitud (eventos truncados sin fecha o sin mensaje).
  - Aislamiento de eventos de error de negocio para reportes de incidentes.

## 3. Entradas y Salidas
- **Entrada esperada (`ExecutionContext.get_latest_output()`):**
  - Objeto `LogParserOutput` o diccionario que contenga la clave `'entries'` con objetos `ParsedLogEntry`.
- **Salida estructurada (`SkillResult.output`):**
  - Objeto `AnomalyDetectorOutput`:
    - `total_analyzed`: Total de registros analizados.
    - `total_valid`: Registros completos y válidos.
    - `total_anomalies`: Suma de registros incompletos y mal formateados.
    - `anomaly_rate`: Porcentaje de anomalías sobre el total.
    - `incomplete_entries`: Tupla de entradas con estado `incompleta`.
    - `malformed_entries`: Tupla de entradas con estado `mal_formateada`.
    - `valid_error_events`: Tupla de entradas con estado `valida` y severidad `ERROR`.
    - `valid_warning_events`: Tupla de entradas con estado `valida` y severidad `WARNING`.
    - `valid_info_events`: Tupla de entradas con estado `valida` y severidad `INFO`.
    - `metrics`: Objeto `LogMetrics` preservado.

## 4. Procedimiento de Ejecución
1. Extrae de forma segura `entries` y `metrics` del contexto previo.
2. Itera sobre las entradas clasificándolas por su estado determinista (`valida`, `incompleta`, `mal_formateada`).
3. Para los registros con estado `valida`, clasifica su severidad operativa (`ERROR`, `WARNING`, `INFO`).
4. Calcula métricas derivadas de tasa de anomalías.
5. Retorna un objeto `AnomalyDetectorOutput` inmutable dentro de un `SkillResult` exitoso.

## 5. Restricciones
- No debe clasificar un evento `[ERROR]` válido (ej. fallo de base de datos bien formateado) como una anomalía de formato.
- No muta las entidades `ParsedLogEntry` originales.
- No invoca modelos LLM.

## 6. Ejemplo Funcional
```python
from agentforge.core.contracts import ExecutionContext
from agentforge.skills.anomaly_detector import AnomalyDetectorSkill
from agentforge.skills.log_parser import LogParserSkill

parser = LogParserSkill()
detector = AnomalyDetectorSkill()

# Paso 1: Parseo
ctx1 = ExecutionContext(
    agent_id="agent_1",
    initial_input=[
        "[ERROR] 2024-05-10 Fallo en la pasarela de pagos",
        "[ERROR] 2024-02-30 Fecha no existente",
    ],
)
res1 = parser.execute(ctx1)

# Paso 2: Detección
ctx2 = ExecutionContext(
    agent_id="agent_1",
    previous_results=(res1,),
)
res2 = detector.execute(ctx2)
assert res2.success is True
assert len(res2.output.valid_error_events) == 1  # Pasarela de pagos (válido)
assert len(res2.output.malformed_entries) == 1  # 30 de febrero (anómalo)
```

## 7. Errores Esperados
- **Error de tipo de entrada:** Si el contexto no contiene un `LogParserOutput` o un diccionario con `'entries'`, retorna `SkillResult(success=False, error="Error de entrada en anomaly-detector: ...")`.

## 8. Dependencias
- `agentforge.core.contracts` (`ExecutionContext`, `SkillProtocol`, `SkillResult`).
- `agentforge.core.types` (`LogMetrics`, `LogStatus`, `ParsedLogEntry`, `SeverityLevel`).
- `agentforge.skills.types` (`AnomalyDetectorOutput`, `LogParserOutput`).

## 9. Relación con Otras Skills
- **Predecesoras:** `log-parser`.
- **Sucesoras:** `incident-reporter`.
