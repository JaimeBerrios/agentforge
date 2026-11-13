# Núcleo Agéntico, Contratos y Configuración — Fase 2

**Proyecto:** AgentForge  
**Rama:** `feat/agent-core`  
**Fase:** Fase 2 — Núcleo agéntico, contratos y configuración  
**Fecha:** Noviembre 2026  

---

## 1. Arquitectura General del Núcleo

La Fase 2 dota a **AgentForge** de la infraestructura agéntica base, permitiendo registrar capacidades modulares (*skills*), cargar configuraciones externas declarativas en formato TOML y orquestar la ejecución secuencial de agentes mediante contratos estrictos y tipos inmutables.

```
src/agentforge/core/
├── __init__.py           # Exportaciones públicas unificadas del núcleo
├── contracts.py          # Protocolos estructurales (SkillProtocol, AgentProtocol, LLMProviderProtocol)
├── types.py              # Modelos de dominio inmutables y estados
├── exceptions.py         # Jerarquía de excepciones de dominio de AgentForge
├── registry.py           # Registro explícito y seguro de capacidades (SkillRegistry)
├── config.py             # Cargador y validador de configuración TOML (tomllib)
└── runner.py             # Orquestador secuencial determinista (SequentialAgentRunner)
```

---

## 2. Contratos y Protocolos

Se implementaron contratos formales mediante `typing.Protocol` con el decorador `@runtime_checkable`:

### 2.1 `SkillProtocol`
Define el contrato para cualquier capacidad modular:
- Propiedad `name`: Identificador único de la skill.
- Propiedad `description`: Resumen del propósito y rol técnico de la capacidad.
- Método `execute(context: ExecutionContext) -> SkillResult`: Ejecución pura sobre un contexto inmutable.

### 2.2 `AgentProtocol`
Define el contrato estándar para cualquier agente en el framework:
- Propiedades: `agent_id`, `name`, `description`.
- Método `run(initial_input: Any = None) -> AgentRunResult`: Ejecución completa del ciclo de vida del agente.

### 2.3 `LLMProviderProtocol`
Define la abstracción para futuros proveedores de modelos de lenguaje (Ollama / Gemini):
- Propiedad: `name`.
- Método `generate(prompt: str, **kwargs: Any) -> LLMResponse`.
- **Nota de Fase 2:** El contrato está definido pero **no** se conecta a ningún servicio externo ni realiza inferencias en esta fase.

---

## 3. Inmutabilidad y Protección de Contexto (`ExecutionContext`)

Para evitar que una skill modifique silenciosamente resultados anteriores o corrompa el estado del agente:
1. `ExecutionContext` es una `dataclass(frozen=True, slots=True)`.
2. El historial `previous_results` se expone como una tupla inmutable de `SkillResult`.
3. Cualquier intento de mutación directa sobre `context` o sobre los objetos `SkillResult` arroja inmediatamente `dataclasses.FrozenInstanceError`.
4. Métodos de conveniencia:
   - `get_latest_output()`: Retorna la salida del paso anterior exitoso, o la entrada inicial.
   - `get_result(skill_name)`: Permite inspeccionar resultados previos por nombre de skill sin alterar su contenido.

---

## 4. Registro de Capacidades (`SkillRegistry`)

El registro en memoria (`SkillRegistry`) administra el ciclo de vida de las skills con estrictas garantías de seguridad:

1. **Unicidad Obligatoria:** Si se intenta registrar una skill cuyo `name` ya existe, se lanza `DuplicateSkillError`.
2. **Rechazo de Skills Desconocidas:** Toda solicitud o resolución de una skill inexistente lanza `SkillNotFoundError`.
3. **Resolución de Autorización:** Valida que la lista de skills solicitadas por un agente exista previamente en el registro.
4. **Prevención de Importación Dinámica No Confiable:** El registro no permite cargar cadenas arbitrarias de módulos externos (`importlib`) a partir de configuración. Las skills deben registrarse programáticamente.
5. **No Interpretación de Markdown:** Los archivos `SKILL.md` se consideran documentación técnica descriptiva; en ningún momento son evaluados como código ejecutable por el motor.

---

## 5. Configuración Declarativa mediante TOML

Se implementó el cargador y validador de configuración externa apoyándose en `tomllib` (biblioteca estándar de Python):

### 5.1 Estructura Soportada
```toml
[agent]
id = "log_analyzer_agent"
name = "Log Analyzer Agent"
description = "Agente determinista para parsing, validación y métricas de registros de log."
skills = [
    "log_parser",
    "log_validator",
    "log_metrics",
]
execution_order = [
    "log_parser",
    "log_validator",
    "log_metrics",
]

[parameters]
max_events = 10000
strict_mode = true
date_format = "%Y-%m-%d"
```

### 5.2 Reglas de Validación
1. **Campos Requeridos:** `agent_id`, `name`, `description`, `skills` y `execution_order` deben ser válidos y no vacíos.
2. **Coherencia de Ejecución:** Toda skill declarada en `execution_order` debe estar explícitamente listada en `skills` (habilidades autorizadas). En caso contrario, se rechaza con `InvalidConfigError`.
3. **Protección Cero Secretos:** Se inspecciona recursivamente la configuración; cualquier clave que contenga términos como `api_key`, `secret`, `token`, `password`, `credential` es rechazada inmediatamente con `InvalidConfigError`.

---

## 6. Orquestador Secuencial (`SequentialAgentRunner`)

El orquestador coordina la ejecución de capacidades:
1. **Verificación Inicial:** Valida que todas las skills autorizadas y las que componen `execution_order` existan en el `SkillRegistry`.
2. **Ejecución en Orden Estricto:** Ejecuta las skills en el orden exacto definido por `config.execution_order`.
3. **Aislamiento de Excepciones:** Si una skill lanza un error imprevisto o retorna `success=False`, el runner captura el mensaje de error en el `SkillResult`, detiene la cadena para evitar propagación de estado inconsistente y genera un `AgentRunResult(success=False)` detallado.
4. **Operatividad 100% Determinista:** Funciona de forma autónoma sin depender de modelos LLM ni de conectividad de red.

---

## 7. Pruebas y Evidencia de Calidad

Se incorporaron 26 nuevas pruebas unitarias especializadas en el núcleo:
- [`tests/unit/test_contracts.py`](../tests/unit/test_contracts.py): Verificación de protocolos en runtime e inmutabilidad de tipos.
- [`tests/unit/test_registry.py`](../tests/unit/test_registry.py): Registro, unicidad, rechazo de duplicados y resolución autorizada.
- [`tests/unit/test_config.py`](../tests/unit/test_config.py): Carga de TOML, rechazo de sintaxis inválida, rechazo de credenciales y archivos no encontrados.
- [`tests/unit/test_runner.py`](../tests/unit/test_runner.py): Ejecución secuencial en orden declarado, verificación activa de inmutabilidad y captura defensiva de fallos.

### Resumen de la Suite Completa
- **Total de pruebas ejecutadas:** **66 pruebas** (40 heredadas de Fase 0 y 1 + 26 nuevas del núcleo).
- **Subtests evaluados:** 49 subtests adicionales.
- **Resultado:** **100% exitosas (66 passed en 0.15s)**.
- **Linter Ruff:** `All checks passed!`.
- **Formato Ruff:** `28 files already formatted`.
