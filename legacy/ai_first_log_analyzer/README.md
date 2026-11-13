# AI-First Log Analyzer

Analizador y validador de logs estructurados desarrollado bajo el paradigma **AI-First**: la inteligencia artificial asiste en la formulación inicial de expresiones regulares y patrones de extracción, mientras que el desarrollador humano asume el rol crítico de **arquitecto de reglas**, superando las limitaciones inherentes de los modelos de lenguaje mediante validación semántica determinista y catalogación explícita de estados.

---

## 1. Evidencia de Refactorización Crítica (AI-First)

### El Fallo de la Expresión Regular Generada por IA
Durante la generación inicial, los modelos de lenguaje tienden a proponer expresiones regulares como:
```regex
^(INFO|WARNING|ERROR)\s+(\d{4}-\d{2}-\d{2})\s+(.*)$
```
**Limitaciones técnicas detectadas por el criterio humano:**
1. **Incapacidad de validar calendario real:** Una expresión regular sintáctica considera válido `2024-02-30` (30 de febrero) o `2023-02-29` (año no bisiesto), ya que coinciden con el patrón `\d{4}-\d{2}-\d{2}`.
2. **Fragilidad ante eventos incompletos:** Si un evento carece de mensaje o de fecha (ej. `· [WARNING] Invalid password attempt`), la regex simplemente falla sin discriminar si fue un error de sintaxis o un registro truncado.
3. **Corchetes ausentes en el patrón:** La propuesta inicial esperaba `INFO`, aunque los ejemplos usan `[INFO]`. La corrección exige corchetes y rechaza espacios internos como `[ ERROR  ]`.

### La Intervención del Arquitecto Humano (`datetime` + Estados)
Para solucionar esta limitación técnica, se diseñó la función `extraer_log(linea)` que desacopla la extracción sintáctica de la verificación semántica:
- **Catálogo explícito de estados:** `valida`, `incompleta` y `mal_formateada`.
- **Validación con `datetime.strptime`:** Intercepta fechas imposibles en el calendario y verifica años bisiestos con precisión.
- **Trazabilidad limpia:** Permite al orquestador contabilizar de manera independiente las anomalías estructurales frente a las incompletas y conservar la severidad detectada.

```python
# Validación semántica que supera la limitación de la regex pura
if fecha is not None:
    try:
        datetime.strptime(fecha, "%Y-%m-%d")
    except ValueError:
        estado = "mal_formateada"

if estado == "valida" and (fecha is None or not mensaje):
    estado = "incompleta"
```

---

## 2. Arquitectura del Orquestador (`analizar_archivo`)

La función [`analizar_archivo(ruta_archivo)`](log_analyzer.py):
1. **Manejo robusto de excepciones:** Captura `FileNotFoundError`, `PermissionError` y errores de E/S.
2. **Contadores independientes:**
   - Total de eventos / líneas procesadas.
   - Total de líneas válidas.
   - Conteo de eventos con fecha válida vs sin fecha válida.
   - Desglose por severidad (`INFO`, `WARNING`, `ERROR`).
   - Total de líneas anómalas y su categorización (`incompleta` vs `mal_formateada`).
3. **Reporte legible por consola:** Emite un resumen formateado de métricas clave.

---

## 3. Archivos de Prueba

Ubicados en la carpeta [`tests/`](tests/):

* **[`tests/logs_validos.txt`](tests/logs_validos.txt):** Contiene 10 eventos válidos con severidades `INFO`, `WARNING` y `ERROR`, incluyendo prefijos con viñetas `· ` y directos.
* **[`tests/logs_invalidos.txt`](tests/logs_invalidos.txt):** Contiene 16 casos límite estructurados:
  - Evento sin fecha `· [WARNING] Invalid password attempt`.
  - 30 de febrero (`2024-02-30`) y año no bisiesto (`2023-02-29`).
  - Líneas sin corchetes de severidad (`ERROR 2024-05-10 ...`).
  - Paréntesis en lugar de corchetes (`(INFO)`).
  - Espacios irregulares dentro de corchetes (`[ ERROR  ]`, `[  INFO]`, `[WARNING ]`).
  - Líneas incompletas (`[INFO]`, `[ERROR] 2024-05-10`, `[INFO] 2024-05-10 `).
  - Saltos de línea vacíos y con espacios en blanco.
  - Formatos no estándar (mes 13, texto plano).

---

## 4. Ejecución del Ciclo Completo

### Modo Interactivo (Menú de Selección)
Permite al usuario seleccionar el archivo a analizar:
```bash
python3 log_analyzer.py
```

### Modo Automático o por Archivo Específico
```bash
# Ejecutar suite completa de pruebas
python3 log_analyzer.py --auto

# Analizar un archivo específico directamente
python3 log_analyzer.py tests/logs_validos.txt
```
