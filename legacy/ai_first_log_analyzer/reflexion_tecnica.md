# Documento de Reflexión Técnica: IA como Herramienta, no como Autor

**Programa:** KODIGO - Innovación y Criterio Técnico  
**Módulo:** Semana 3 – IA-First Mindset  
**Actividad:** IA como Herramienta, no como Autor: Desarrollo Guiado y Validado de un Script en Python  
**Estudiante / Rol:** Jaime Berrios — Arquitecto de Reglas y Software  

---

## 1. Delimitación de Responsabilidades: IA vs. Estudiante

En el desarrollo de software bajo el paradigma **AI-First**, la inteligencia artificial actúa como un acelerador de código y asistente exploratorio, mientras que el desarrollador humano asume de forma indelegable el rol de **arquitecto de reglas, auditor de calidad y garante de la integridad del software**.

### A. Partes del código apoyadas o sugeridas por la IA
* **Estructura sintáctica preliminar de expresiones regulares:** La IA propuso el andamiaje inicial con grupos de captura morfológicos (`r"\[([A-Z]+)\]\s+([0-9-]+)\s+(.*)"`).
* **Esqueleto boilerplate de entrada/salida:** Propuesta inicial para abrir archivos de texto e iterar sobre líneas mediante bloques básicos en Python.
* **Sugerencia de formateo de reporte:** Ideas para alinear texto en consola usando f-strings formateados.

### B. Partes que fueron decisión exclusiva del estudiante (Arquitecto de Reglas)
* **Arquitectura de dos fases (Sintaxis vs. Semántica):** Decisión consciente de no delegar la lógica de negocio a una sola expresión regular, reconociendo las limitaciones de los autómatas finitos.
* **Definición de la taxonomía de tres estados:** En lugar de una salida booleana (`True / False`), se diseñó un modelo de estados explícito:
  1. `valida`: Cumple severidad, estructura, mensaje y fecha existente en el calendario gregoriano.
  2. `incompleta`: Registros auténticos que carecen de fecha (ej. `· [WARNING] Invalid password attempt`) o sin mensaje. Se tomó la decisión de negocio de **no descartarlos**, sino conservarlos, contabilizar su severidad y catalogarlos para auditoría.
  3. `mal_formateada`: Violaciones de delimitadores (sin corchetes, paréntesis, espacios espurios como `[ ERROR  ]`), fechas imposibles o líneas vacías.
* **Integración determinista de `datetime`:** Incorporación de `datetime.strptime(fecha, "%Y-%m-%d")` para validar el calendario real y resolver años bisiestos.
* **Manejo defensivo de excepciones:** Implementación de `try/except` específico para `FileNotFoundError`, `PermissionError` y errores de I/O, evitando interrupciones catastróficas.
* **Interfaz de usuario dual (CLI + Menú interactivo):** Soporte tanto para ejecución automática por parámetros como para un menú interactivo en terminal para seleccionar el archivo.

---

## 2. Caso Concreto de Detección y Corrección de Error de la IA

### i. Sugerencia incorrecta / incompleta de la IA (El sesgo del "Vibecoding")
Al pedirle a la IA que validara la fecha y estructura del log, sugirió validar todo mediante una única expresión regular:
```regex
^(INFO|WARNING|ERROR)\s+(\d{4}-\d{2}-\d{2})\s+(.*)$
```
**Fallo detectado:**  
La IA asumió que cualquier combinación de dígitos con formato `AAAA-MM-DD` era una fecha válida. Bajo este patrón, líneas con **30 de febrero** (`[ERROR] 2024-02-30 ...`) o el **29 de febrero de un año no bisiesto** (`[WARNING] 2023-02-29 ...`) eran marcadas como válidas. Además, el patrón no contemplaba los corchetes de `[INFO]`, y la ausencia de fecha simplemente retornaba `None`, perdiendo la traza de eventos incompletos.

### ii. Detección y corrección implementada por el estudiante
Se refactorizó la función `extraer_log` desacoplando la expresión regular (para captura morfológica con límites estrictos) de la validación cronológica con el módulo estándar `datetime`:

```python
# Corrección del estudiante: Autómata de reglas + Validación Semántica
severidad, fecha, mensaje = coincidencia.groups()
mensaje = (mensaje or "").strip()
estado = "valida"

if fecha is not None:
    try:
        # Validación astronómica y de calendario real (bisiestos, días del mes)
        datetime.strptime(fecha, "%Y-%m-%d")
    except ValueError:
        estado = "mal_formateada"

# Regla de completitud: si no tiene fecha o mensaje, es incompleta
if estado == "valida" and (fecha is None or not mensaje):
    estado = "incompleta"
```

Con esta corrección, los casos borde imposibles son interceptados inmediatamente como anomalías de formato sin riesgo de corrupción de datos.

---

## 3. Aprendizaje sobre el uso de la IA como Herramienta y no como Reemplazo

1. **La IA ignora el contexto de negocio y las leyes del dominio:** La IA genera código probabilísticamente verosímil pero no necesariamente correcto en el mundo real. Comprender las limitaciones matemáticas de herramientas como Regex frente a cálculos astronómicos o calendáricos es responsabilidad 100% humana.
2. **El peligro del "Vibecoding":** Aceptar ciegamente el código generado por IA sin diseñar casos borde estructurados crea software frágil que fallará en producción bajo condiciones operativas reales.
3. **El Ingeniero como Arquitecto y Auditor:** El verdadero valor del programador actual no reside en memorizar sintaxis, sino en definir las **reglas de validación, la arquitectura de control de flujo, el diseño de casos de prueba y la mitigación de riesgos**.

---

## 4. Evidencia de Pruebas y Resultados

Para certificar el comportamiento del script, se diseñaron dos conjuntos de pruebas independientes en la carpeta `/tests`:

### A. Archivo Bien Formado (`tests/logs_validos.txt`)
Contiene 10 eventos que cubren todas las severidades permitidas (`INFO`, `WARNING`, `ERROR`), tanto con prefijo de viñeta (`· `) como directo:
* **Resultado Esperado:** 10 eventos procesados, 10 válidos (100%), 0 anómalos, 10 fechas válidas.
* **Resultado Obtenido:**
  ```text
  Total de eventos analizados        : 10
    - Eventos válidos y completos    : 10 (100.0%)
    - Eventos anómalos               : 0 (0.0%)
  VALIDACIÓN DE FECHAS:
    - Con fecha válida en calendario : 10
    - Sin fecha o con fecha inválida : 0
  CANTIDAD DE EVENTOS POR TIPO DE SEVERIDAD:
    [INFO   ] : 5 | [WARNING] : 2 | [ERROR  ] : 3
  ```

### B. Archivo con Errores e Inconsistencias (`tests/logs_invalidos.txt`)
Contiene 16 casos límite estructurados para validar cada regla del sistema:
1. `· [WARNING] Invalid password attempt`: Incompleto (sin fecha, pero con severidad).
2. `[ERROR] 2024-02-30 ...`: Mal formateado (30 de febrero no existe).
3. `[WARNING] 2023-02-29 ...`: Mal formateado (2023 no fue bisiesto).
4. `ERROR 2024-05-10 ...`: Mal formateado (sin corchetes).
5. `(INFO) 2024-05-10 ...`: Mal formateado (paréntesis en vez de corchetes).
6. `[ ERROR  ] ...`, `[  INFO] ...`, `[WARNING ] ...`: Mal formateados (espacios irregulares).
7. `[INFO]`, `[ERROR] 2024-05-10`, `[INFO] 2024-05-10 `: Incompletos (faltan campos obligatorios).
8. `[ERROR] 2024-13-01 ...`: Mal formateado (mes 13 fuera de rango).
9. Líneas vacías y texto plano no estructurado: Mal formateados.

* **Resultado Esperado:** 16 eventos analizados, 0 válidos (0.0%), 16 anómalos (4 incompletos y 12 mal formateados).
* **Resultado Obtenido:**
  ```text
  Total de eventos analizados        : 16
    - Eventos válidos y completos    : 0 (0.0%)
    - Eventos anómalos               : 16 (100.0%)
  VALIDACIÓN DE FECHAS:
    - Con fecha válida en calendario : 2
    - Sin fecha o con fecha inválida : 14
  DESGLOSE DE LÍNEAS ANÓMALAS:
    - Incompletas (faltan campos)       : 4
    - Mal formateadas (sintaxis/fechas) : 12
  ```

Los resultados coinciden con lo esperado para estos 26 ejemplos; esta comprobación no garantiza el comportamiento ante todas las entradas posibles.
