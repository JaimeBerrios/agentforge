# Línea Base Técnica y Decisiones de Arquitectura — AgentForge

**Proyecto:** AgentForge  
**Programa Académico:** Bootcamp AI for Developers Jr. — KODIGO Academy  
**Fase Actual:** Fase 0 — Preparación del entorno y línea base del proyecto original  
**Fecha de Establecimiento:** Noviembre 2026  

---

## 1. Procedencia y Trazabilidad del Proyecto Original

El proyecto base para la refactorización es **ai-first-log-analyzer**, desarrollado bajo el paradigma *AI-First: IA como herramienta, no como autor*.

- **Repositorio de origen:** [https://github.com/JaimeBerrios/ai-first-log-analyzer](https://github.com/JaimeBerrios/ai-first-log-analyzer)
- **Commit exacto de referencia:** `ebeb2845dcdbb779fa2be92bcc5057a64b75c6f3`
- **Mensaje de commit:** `feat: agregar analizador de logs con validacion de calendario`
- **Fecha:** `2026-10-25T16:52:05Z`
- **Autor:** Jaime Berrios (`bo0310042024@unab.edu.sv`)
- **Ubicación de la copia inalterada:** [`legacy/ai_first_log_analyzer/`](../legacy/ai_first_log_analyzer/)

Sumas de verificación criptográfica (SHA-256):
- `log_analyzer.py`: `352965e4f1d4833732bb57d115ded48987baa8205017bb8ba1ab147c220f8909`
- `tests/logs_validos.txt`: `ca15a34c1cc1d1bca57a3a59f160af6e4313f5670ef02b5bec32dc26d7c74acd`
- `tests/logs_invalidos.txt`: `99756d4fa950da098d9f080b72e65cf8823b06da70f2ce1e198cd66927576cf3`

---

## 2. Decisiones Técnicas Aprobadas

| Componente / Aspecto | Decisión Aprobada | Justificación Técnica |
| :--- | :--- | :--- |
| **Versión de Python** | Python >= 3.12 (Ejecución actual: 3.15.2) | Aprovechamiento de mejoras de rendimiento, tipado estricto nativo (`X \| Y`, `type`, `typing.override`) y `tomllib` en biblioteca estándar. |
| **Modelos de Dominio** | `dataclasses` (Biblioteca Estándar) | Cero dependencias externas para el núcleo del framework, inmutabilidad opcional (`frozen=True`), alto rendimiento y claridad semántica. |
| **Gestión de Configuración** | TOML con `tomllib` | Formato legible, estándar moderno de Python (PEP 680), nativo sin requerir `pyyaml`. |
| **Gestor de Entorno** | `venv` + `pip` | Estándar de la industria, portable y sin herramientas propietarias adicionales. |
| **Testing** | `pytest` | Pruebas concisas, fixtures parametrizadas y reporte detallado de aserciones. Los tests de caracterización se diseñaron compatibles con `unittest` nativo. |
| **Calidad de Código** | `ruff` | Linter y formateador ultrarrápido compatible con PEP 8, isort y pyupgrade. |
| **Proveedores LLM** | Ollama (Principal) / Gemini (Secundario) | Inferencia local privada sin costo de tokens como proveedor primario, y Gemini vía `google-genai` como proveedor secundario en la nube. |
| **Estructura de Paquete** | `src/agentforge/` (src-layout) | Previene importaciones accidentales del código fuente en desarrollo y asegura que las pruebas corran contra el paquete instalado. |

---

## 3. Resolución Empírica de la Discrepancia en `logs_invalidos.txt`

### 3.1 Planteamiento del Problema
En el diagnóstico preliminar se produjo una discrepancia en el conteo de eventos anómalos: se estimó informalmente 1 sola línea incompleta y 1 válida, mientras que en otros resúmenes se mencionaban valores dispares.

### 3.2 Evidencia Experimental
Se implementó una suite de pruebas de caracterización ([`tests/test_characterization.py`](../tests/test_characterization.py)) que ejecutó de manera controlada la función `analizar_archivo` de la línea base sobre el fixture exacto [`tests/fixtures/logs_invalidos.txt`](../tests/fixtures/logs_invalidos.txt).

### 3.3 Resultados Observados y Certificados

```
Total de eventos analizados        : 16
  - Eventos válidos y completos    : 0 (0.0%)
  - Eventos anómalos               : 16 (100.0%)
VALIDACIÓN DE FECHAS:
  - Con fecha válida en calendario : 2
  - Sin fecha o con fecha inválida : 14
CANTIDAD DE EVENTOS POR TIPO DE SEVERIDAD:
  [INFO   ] : 2
  [WARNING] : 2
  [ERROR  ] : 3
DESGLOSE DE LÍNEAS ANÓMALAS:
  - Incompletas (faltan campos)       : 4
  - Mal formateadas (sintaxis/fechas) : 12
```

### 3.4 Desglose Línea por Línea

| Línea | Contenido Exacto | Estado Resultante | Severidad | Fecha | Explicación Determinista |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **1** | `· [WARNING] Invalid password attempt` | `incompleta` | `WARNING` | `None` | Severidad y mensaje presentes; fecha ausente. |
| **2** | `[ERROR] 2024-02-30 Fallo de sincronización...` | `mal_formateada` | `ERROR` | `2024-02-30` | Fecha astronómicamente imposible (30 de feb). |
| **3** | `[WARNING] 2023-02-29 Error de año bisiesto...` | `mal_formateada` | `WARNING` | `2023-02-29` | 2023 no fue bisiesto (29 de feb inválido). |
| **4** | ` ` *(línea vacía)* | `mal_formateada` | `None` | `None` | No coincide con el patrón regex. |
| **5** | `ERROR 2024-05-10 Línea sin corchetes...` | `mal_formateada` | `None` | `None` | Carece de corchetes obligatorios. |
| **6** | `(INFO) 2024-05-10 Paréntesis utilizados...` | `mal_formateada` | `None` | `None` | Paréntesis en lugar de corchetes. |
| **7** | `[ ERROR  ] 2024-05-10 Espacios irregulares...` | `mal_formateada` | `None` | `None` | Espacios internos en corchetes. |
| **8** | `[  INFO] 2024-05-10 Espacios iniciales...` | `mal_formateada` | `None` | `None` | Espacios internos al inicio. |
| **9** | `[WARNING ] 2024-05-10 Espacios finales...` | `mal_formateada` | `None` | `None` | Espacios internos al final. |
| **10** | ` ` *(línea vacía)* | `mal_formateada` | `None` | `None` | No coincide con el patrón regex. |
| **11** | `[INFO]` | `incompleta` | `INFO` | `None` | Falta fecha y mensaje. |
| **12** | `[ERROR] 2024-05-10` | `incompleta` | `ERROR` | `2024-05-10` | Fecha válida, pero mensaje vacío (`strip() == ""`). |
| **13** | `[INFO] 2024-05-10 ` | `incompleta` | `INFO` | `2024-05-10` | Fecha válida, mensaje con solo espacios en blanco. |
| **14** | `[ERROR] 2024-13-01 Mes 13 fuera de rango...` | `mal_formateada` | `ERROR` | `2024-13-01` | Mes fuera de rango gregoriano. |
| **15** | `Esta línea no cumple con ningún formato...` | `mal_formateada` | `None` | `None` | Texto plano sin estructura. |
| **16** | `   ` *(espacios en blanco)* | `mal_formateada` | `None` | `None` | Espacios sin estructura. |

**Conclusiones Clave:**
1. Las líneas 12 y 13 poseen una fecha que **sí existe** en el calendario gregoriano (`2024-05-10`), por lo que el contador `total_con_fecha_valida` marca exactamente **2**.
2. Las líneas con severidad válida identificada son **7** (`INFO`: 2, `WARNING`: 2, `ERROR`: 3). Las otras 9 líneas no reconocen severidad al no coincidir la regex.
3. Las líneas incompletas son **4** (líneas 1, 11, 12 y 13).
4. Las líneas mal formateadas son **12** (líneas 2, 3, 4, 5, 6, 7, 8, 9, 10, 14, 15, 16).

---

## 4. Estado de Validación y Herramientas en Fase 0

### 4.1 Entorno Virtual y Versiones de Herramientas
- **Intérprete Python:** Python 3.15.2 (Fedora Linux)
- **Entorno Virtual:** `.venv/` (creado mediante `python3 -m venv .venv`)
- **Gestor de paquetes:** `pip 26.1.2`
- **Herramientas de testing:** `pytest 9.2.0`, `pluggy 1.7.0`, `iniconfig 2.3.1`, `packaging 26.3`
- **Herramientas de calidad:** `ruff 0.17.5`

### 4.2 Instalación de Dependencias de Desarrollo
Comando ejecutado:
```bash
.venv/bin/python -m pip install -e ".[dev]"
```
Resultado: Paquete `agentforge` (0.1.0) instalado en modo editable junto con `pytest` y `ruff`.

### 4.3 Ejecución de Pruebas Automatizadas
1. **Unittest nativo:**
   ```bash
   .venv/bin/python -m unittest discover -s tests -p "test_*.py" -v
   ```
   *Resultado:* 16 pruebas ejecutadas, 16 exitosas (0 fallos, 0 errores) en 0.009s.

2. **Pytest:**
   ```bash
   .venv/bin/pytest
   ```
   *Resultado:* 16 passed, 6 subtests passed en 0.05s.

### 4.4 Verificación de Calidad y Formato con Ruff
1. **Linter en modo comprobación:**
   ```bash
   .venv/bin/ruff check .
   ```
   *Resultado:* `All checks passed!` (excluyendo el código histórico en `legacy/`).

2. **Formateo en modo comprobación:**
   ```bash
   .venv/bin/ruff format --check .
   ```
   *Resultado:* `5 files already formatted`.

### 4.5 Verificación de Integridad de la Línea Base
Comando ejecutado:
```bash
sha256sum legacy/ai_first_log_analyzer/log_analyzer.py \
          legacy/ai_first_log_analyzer/README.md \
          legacy/ai_first_log_analyzer/reflexion_tecnica.md \
          legacy/ai_first_log_analyzer/tests/logs_validos.txt \
          legacy/ai_first_log_analyzer/tests/logs_invalidos.txt
```
*Resultado:* Coincidencia exacta al 100% con los hashes registrados en `PROVENANCE.md`.

### 4.6 Verificación de Seguridad y Ausencia de Secretos
Comando ejecutado:
```bash
find . -name "*.env*" -o -name "*secret*" -o -name "*key*" -not -path "./.git/*" -not -path "./.venv/*"
```
*Resultado:* Cero credenciales, claves o variables de entorno detectadas. Exclusiones en `.gitignore` validadas para `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, y `*.egg-info/`.
