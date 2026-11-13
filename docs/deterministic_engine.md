# Refactorización del Motor Determinista de Logs — Fase 1

**Proyecto:** AgentForge  
**Rama:** `feat/deterministic-log-engine`  
**Fase:** Fase 1 — Refactorización del motor determinista de logs  
**Fecha:** Noviembre 2026  

---

## 1. Objetivos y Alcance de la Refactorización

La Fase 1 descompone el script monolítico heredado ([`legacy/ai_first_log_analyzer/log_analyzer.py`](../legacy/ai_first_log_analyzer/log_analyzer.py)) en componentes de dominio modulares, desacoplados, altamente testeables y estrictamente tipados.

Se mantuvieron intactas todas las reglas de negocio originales (taxonomía de estados, validación astronómica con `datetime`, y agregación estadística), pero separando responsabilidades y eliminando el acoplamiento con la consola y el sistema de archivos.

---

## 2. Nueva Arquitectura Modular

```
src/agentforge/
├── core/
│   ├── __init__.py           # Exportación de tipos y contratos base
│   └── types.py              # Modelos de dominio inmutables con dataclasses y StrEnum
└── logs/
    ├── __init__.py           # Exportación del motor de logs
    ├── parser.py             # Extracción sintáctica pura mediante expresiones regulares
    ├── validator.py          # Validación semántica, calendario gregoriano y completitud
    ├── metrics.py            # Acumulador determinista de contadores estadísticos
    └── service.py            # Servicio orquestador desacoplado de I/O
```

### 2.1 Responsabilidades por Componente

| Módulo | Clase / Función | Responsabilidad Técnica |
| :--- | :--- | :--- |
| [`core/types.py`](../src/agentforge/core/types.py) | `SeverityLevel`<br>`LogStatus`<br>`RawLogMatch`<br>`ParsedLogEntry`<br>`LogMetrics` | Define las entidades de dominio y tipos enumerados. `ParsedLogEntry` y `RawLogMatch` son inmutables (`frozen=True, slots=True`). Incluyen métodos `.to_dict()` para garantizar paridad con el código legado. |
| [`logs/parser.py`](../src/agentforge/logs/parser.py) | `LogParser`<br>`parse_line()` | Ejecuta exclusivamente la extracción morfológica de la línea sin validar fechas ni reglas de completitud. Retorna un `RawLogMatch`. |
| [`logs/validator.py`](../src/agentforge/logs/validator.py) | `LogValidator`<br>`validate_match()` | Aplica las reglas de negocio sobre el `RawLogMatch`: verificación de calendario real gregoriano (`datetime.strptime`) y categorización en `valida`, `incompleta` o `mal_formateada`. Retorna un `ParsedLogEntry`. |
| [`logs/metrics.py`](../src/agentforge/logs/metrics.py) | `LogMetricsAccumulator` | Acumulador de estado en memoria. Incrementa contadores independientes por severidad, fecha válida/inválida y tipos de anomalías. |
| [`logs/service.py`](../src/agentforge/logs/service.py) | `LogEngineService`<br>`extraer_log()`<br>`analizar_lineas()` | Orquesta el pipeline parsing → validación → métricas sobre iterables genéricos en memoria (`Iterable[str]`). Proporciona funciones con compatibilidad drop-in para el código heredado. |

---

## 3. Decisiones Técnicas y Comportamientos Heredados

1. **Independencia Total de E/S y Presentación:**
   - En el proyecto original, `analizar_archivo` leía directamente de disco (`path.open()`) y llamaba a `print()` en la terminal.
   - En `AgentForge`, `LogEngineService.analyze_stream` opera sobre cualquier `Iterable[str]`. Esto permite analizar listas en memoria, streams de red o archivos leídos por adaptadores sin mezclar I/O con lógica de dominio.
2. **Ambivalencia Heredada de Fechas en Registros Incompletos:**
   - Si una línea presenta una fecha válida en calendario pero carece de mensaje (ej. `[ERROR] 2024-05-10`), su estado se cataloga como `incompleta`, pero su fecha es considerada válida en el contador `total_con_fecha_valida`.
   - Se preservó idéntica esta regla en `LogValidator` y `LogMetricsAccumulator` para garantizar 100% de paridad con los fixtures originales.
3. **Manejo de Espacios y Trailing Whitespace:**
   - La regla original aplica `.rstrip("\r\n")` al inicio y `.strip()` sobre el mensaje capturado. Si el mensaje queda vacío (`""`), el registro es clasificado como `incompleta`.
   - Esto se desacopló formalmente: `LogParser` conserva el texto crudo y `LogValidator` ejecuta la regla de completitud.
4. **Modelado con `dataclasses`:**
   - Sin dependencias de bibliotecas externas pesadas como Pydantic para el motor base. Se utilizaron `slots=True` para optimizar el consumo de memoria y la velocidad de instanciación.
5. **Distinción entre Interfaces Públicas:**
   - `analizar_archivo(ruta_archivo)`: Pertenece exclusivamente al proyecto original (`legacy/ai_first_log_analyzer/log_analyzer.py`). Depende fuertemente de acceso a disco (`path.open()`) y de emisión visual por terminal (`print()`).
   - `analizar_lineas(lineas: Iterable[str]) -> dict[str, Any]`: Es la nueva interfaz pública introducida por `AgentForge` (`agentforge.logs.service`). Opera sobre cualquier generador, lista o flujo en memoria, retornando el resultado estructurado sin efectos secundarios.
   - `extraer_log(linea: str) -> dict[str, str | None]`: Se mantiene en ambos entornos con idéntica firma y resultado para garantizar compatibilidad drop-in.

---

## 4. Evidencia de Validación y Suite de Pruebas

Se añadieron pruebas unitarias y de integración que ejecutan ambos motores simultáneamente sobre los mismos datos:

- [`tests/unit/test_parser.py`](../tests/unit/test_parser.py): 7 pruebas unitarias de extracción sintáctica aislada.
- [`tests/unit/test_validator.py`](../tests/unit/test_validator.py): 7 pruebas unitarias de reglas de fecha, bisiestos y completitud.
- [`tests/unit/test_metrics.py`](../tests/unit/test_metrics.py): 3 pruebas unitarias de acumulación y porcentajes.
- [`tests/integration/test_engine_parity.py`](../tests/integration/test_engine_parity.py):
  - Paridad línea por línea sobre `tests/fixtures/logs_validos.txt` (10 líneas).
  - Paridad línea por línea sobre `tests/fixtures/logs_invalidos.txt` (16 líneas).
  - Paridad de métricas agregadas completas en ambos fixtures.
  - Casos límite adicionales: Regla gregoriana completa (siglos divisibles por 400 como el 2000 vs no divisibles como 1900/2100), meses de 30 vs 31 días (31 de abril inexistente vs 31 de mayo válido) y caracteres especiales/Unicode en mensajes.
- [`tests/test_characterization.py`](../tests/test_characterization.py): 16 pruebas originales de caracterización de la línea base (conservadas y pasando al 100%).

### Resumen de Ejecución
- **Total de pruebas:** **40 pruebas unitarias e integración (+ 40 subtests parametrados)**.
- **Resultado:** **40 pasadas (100%), 0 fallos, 0 errores en 0.08s**.
- **Linter Ruff:** `All checks passed!`.
- **Formateador Ruff:** `18 files already formatted`.
