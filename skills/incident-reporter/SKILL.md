# Skill: incident-reporter

## 1. Identificador y Descripción
- **Identificador único:** `incident-reporter`
- **Descripción:** Genera reportes estructurados y resúmenes objetivos basados estrictamente en hechos observados y métricas cuantitativas, sin realizar suposiciones ni inventar causas.

## 2. Propósito y Casos de Uso
- **Propósito:** Consolidar el resultado del análisis de logs en un artefacto estructurado que distingue métricas cuantitativas de hechos observables, facilitando auditorías técnicas y operativas.
- **Casos de uso:**
  - Emisión de reportes de guardia técnica post-análisis.
  - Generación de resúmenes consolidados para bitácoras de incidentes.
  - Auditoría forense de calidad de logs de aplicaciones.

## 3. Entradas y Salidas
- **Entrada esperada (`ExecutionContext.get_latest_output()`):**
  - Objeto `AnomalyDetectorOutput` generado por la skill `anomaly-detector`.
- **Salida estructurada (`SkillResult.output`):**
  - Objeto `IncidentReport`:
    - `report_id`: Identificador único del reporte (ej. `REP-agent_id-total_eventos`).
    - `facts`: Diccionario con métricas cuantitativas verificables (totales, porcentajes, desglose de severidad, validación de fechas).
    - `observations`: Tupla de afirmaciones estrictamente factuales (sin hipótesis no fundamentadas).
    - `summary_text`: Representación en texto plano/Markdown estructurado del reporte.
    - `metadata`: Metadatos contextuales (identificador del agente, parámetros).

## 4. Procedimiento de Ejecución
1. Valida que la entrada del contexto corresponda a un `AnomalyDetectorOutput`.
2. Extrae hechos y contadores objetivos del objeto de métricas.
3. Evalúa reglas factuales para generar la lista de observaciones verificables.
4. Ensambla el texto estructurado del reporte.
5. Retorna un `IncidentReport` inmutable dentro de un `SkillResult` exitoso.

## 5. Restricciones
- No debe conjeturar ni alucinar causas raíz no presentes en los datos de entrada (ej. no inventar fallos de red o base de datos salvo que se desprendan de los hechos).
- Opera de forma 100% determinista sin modelos LLM.
- No almacena estado en variables globales.

## 6. Ejemplo Funcional
```python
from agentforge.core.contracts import ExecutionContext
from agentforge.skills.anomaly_detector import AnomalyDetectorSkill
from agentforge.skills.incident_reporter import IncidentReporterSkill
from agentforge.skills.log_parser import LogParserSkill

parser = LogParserSkill()
detector = AnomalyDetectorSkill()
reporter = IncidentReporterSkill()

# Cadena de ejecución
ctx1 = ExecutionContext("demo_agent", initial_input=["[INFO] 2024-05-10 Inicio"])
res1 = parser.execute(ctx1)

ctx2 = ExecutionContext("demo_agent", previous_results=(res1,))
res2 = detector.execute(ctx2)

ctx3 = ExecutionContext("demo_agent", previous_results=(res1, res2))
res3 = reporter.execute(ctx3)

assert res3.success is True
report = res3.output
assert report.facts["total_events"] == 1
assert report.facts["valid_percentage"] == 100.0
assert "Integridad estructural del 100%" in report.observations[0]
```

## 7. Errores Esperados
- **Error de entrada incompatible:** Si la entrada no es un `AnomalyDetectorOutput`, retorna `SkillResult(success=False, error="Error de entrada en incident-reporter: ...")`.

## 8. Dependencias
- `agentforge.core.contracts` (`ExecutionContext`, `SkillProtocol`, `SkillResult`).
- `agentforge.skills.types` (`AnomalyDetectorOutput`, `IncidentReport`).

## 9. Relación con Otras Skills
- **Predecesoras:** `anomaly-detector` (y transitivamente `log-parser`).
- **Sucesoras:** Ninguna (etapa final de síntesis determinista).
