#!/usr/bin/env python3
"""Log Analyzer - AI-First Log Parsing and Validation Utility.

Este script implementa el analizador principal de logs bajo el enfoque AI-First:
la inteligencia artificial asiste en la extracción inicial, pero el desarrollador humano actúa
como arquitecto de reglas, subsanando las limitaciones de regex puras mediante
validación semántica de calendario (datetime) y estados estructurados de error.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import re
import sys
from typing import Any, Dict, Optional


def extraer_log(linea: str) -> dict[str, str | None]:
    """Extrae el formato '[SEVERIDAD] fecha mensaje' sin efectos secundarios.

    Corrección al sesgo/limitación de regex de IA:
    1. Admite opcionalmente la viñeta '· ' y exige corchetes estrictos.
    2. Conserva eventos incompletos clasificándolos explícitamente como 'incompleta'.
    3. Valida el calendario real (evitando 30 de febrero o 29 en no bisiestos) con datetime.
    """
    patron = (
        r"(?:·[ \t]*)?\[(INFO|WARNING|ERROR)\]"
        r"(?:[ \t]+([0-9]{4}-[0-9]{2}-[0-9]{2})(?=[ \t]|$))?"
        r"(?:[ \t]+([^\r\n]*))?"
    )
    coincidencia = re.fullmatch(patron, linea.rstrip("\r\n"))
    if coincidencia is None:
        return dict(estado="mal_formateada", severidad=None, fecha=None, mensaje=None)

    severidad, fecha, mensaje = coincidencia.groups()
    mensaje = (mensaje or "").strip()
    estado = "valida"
    if fecha is not None:
        try:
            datetime.strptime(fecha, "%Y-%m-%d")
        except ValueError:
            estado = "mal_formateada"
    if estado == "valida" and (fecha is None or not mensaje):
        estado = "incompleta"

    return dict(estado=estado, severidad=severidad, fecha=fecha, mensaje=mensaje)


def analizar_archivo(ruta_archivo: str | Path) -> Optional[Dict[str, Any]]:
    """Orquestador principal que abre y procesa un documento de logs completo.

    Implementa:
    1. Manejo de excepciones defensivo (FileNotFoundError, PermissionError).
    2. Contadores independientes para total de eventos, niveles de severidad,
       fechas válidas/inválidas y líneas anómalas (incompletas vs mal formateadas).
    3. Impresión de un reporte estructurado y comprensivo en consola.
    """
    path = Path(ruta_archivo)

    # 1. Manejo de excepciones al intentar abrir el archivo
    try:
        archivo = path.open("r", encoding="utf-8", errors="replace")
    except FileNotFoundError:
        print(f"\n[ERROR] No se encontró el archivo en la ruta: '{path}'.", file=sys.stderr)
        return None
    except PermissionError:
        print(f"\n[ERROR] Permiso denegado para leer el archivo: '{path}'.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"\n[ERROR] Error inesperado al abrir '{path}': {e}", file=sys.stderr)
        return None

    # 2. Inicialización de contadores independientes
    total_eventos = 0
    total_validas = 0
    total_con_fecha_valida = 0
    total_sin_fecha_valida = 0

    desglose_severidad = {
        "INFO": 0,
        "WARNING": 0,
        "ERROR": 0,
    }
    total_anomalas = 0
    desglose_anomalias = {
        "incompleta": 0,
        "mal_formateada": 0,
    }

    # 3. Iteración y procesamiento línea por línea
    with archivo:
        for linea in archivo:
            total_eventos += 1
            resultado = extraer_log(linea)
            estado = resultado.get("estado")
            severidad = resultado.get("severidad")
            fecha = resultado.get("fecha")

            # Conteo de severidad identificada
            if severidad in desglose_severidad:
                desglose_severidad[severidad] += 1

            # Validación de presencia y validez de fecha
            if fecha is not None and estado != "mal_formateada":
                total_con_fecha_valida += 1
            else:
                total_sin_fecha_valida += 1

            # Conteo de validez general
            if estado == "valida":
                total_validas += 1
            elif estado in ("incompleta", "mal_formateada"):
                total_anomalas += 1
                desglose_anomalias[estado] += 1

    # 4. Generación y presentación del reporte en consola
    porcentaje_validas = (total_validas / total_eventos * 100) if total_eventos > 0 else 0.0
    porcentaje_anomalas = (total_anomalas / total_eventos * 100) if total_eventos > 0 else 0.0

    print("=" * 68)
    print(f"  RESUMEN DE ANÁLISIS DE LOGS: {path.name}")
    print(f"  Ruta: {path.resolve()}")
    print("=" * 68)
    print(f"Total de eventos analizados        : {total_eventos}")
    print(f"  - Eventos válidos y completos    : {total_validas} ({porcentaje_validas:.1f}%)")
    print(f"  - Eventos anómalos               : {total_anomalas} ({porcentaje_anomalas:.1f}%)")
    print("-" * 68)
    print("VALIDACIÓN DE FECHAS:")
    print(f"  - Con fecha válida en calendario : {total_con_fecha_valida}")
    print(f"  - Sin fecha o con fecha inválida : {total_sin_fecha_valida}")
    print("-" * 68)
    print("CANTIDAD DE EVENTOS POR TIPO DE SEVERIDAD:")
    for nivel, cantidad in desglose_severidad.items():
        print(f"  [{nivel:<7}] : {cantidad}")
    print("-" * 68)
    print("DESGLOSE DE LÍNEAS ANÓMALAS:")
    print(f"  - Incompletas (faltan campos)       : {desglose_anomalias['incompleta']}")
    print(f"  - Mal formateadas (sintaxis/fechas) : {desglose_anomalias['mal_formateada']}")
    print("=" * 68)
    print()

    return {
        "ruta_archivo": str(path),
        "total_eventos": total_eventos,
        "total_validas": total_validas,
        "total_con_fecha_valida": total_con_fecha_valida,
        "total_sin_fecha_valida": total_sin_fecha_valida,
        "desglose_severidad": desglose_severidad,
        "total_anomalas": total_anomalas,
        "desglose_anomalias": desglose_anomalias,
    }


def menu_interactivo() -> None:
    """Permite al usuario seleccionar el archivo a analizar interactivamente."""
    base_dir = Path(__file__).resolve().parent
    ruta_validos = base_dir / "tests" / "logs_validos.txt"
    ruta_invalidos = base_dir / "tests" / "logs_invalidos.txt"

    print("\n" + "=" * 68)
    print("      SISTEMA DE ANÁLISIS DE LOGS (ENFOQUE AI-FIRST)")
    print("=" * 68)
    print("Seleccione una opción para analizar:")
    print(f"1. Archivo de logs válidos ({ruta_validos.name})")
    print(f"2. Archivo de logs anómalos / casos borde ({ruta_invalidos.name})")
    print("3. Analizar ambos archivos de prueba (Suite completa)")
    print("4. Ingresar ruta de un archivo personalizado")
    print("0. Salir")
    print("-" * 68)

    try:
        opcion = input("Ingrese una opción (0-4): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nOperación cancelada por el usuario.")
        return

    if opcion == "1":
        analizar_archivo(ruta_validos)
    elif opcion == "2":
        analizar_archivo(ruta_invalidos)
    elif opcion == "3":
        analizar_archivo(ruta_validos)
        analizar_archivo(ruta_invalidos)
    elif opcion == "4":
        try:
            ruta_custom = input("Ingrese la ruta del archivo de texto: ").strip()
            if ruta_custom:
                analizar_archivo(ruta_custom)
            else:
                print("No se especificó ninguna ruta.")
        except (EOFError, KeyboardInterrupt):
            print("\nOperación cancelada.")
    elif opcion == "0":
        print("Saliendo del analizador.")
    else:
        print("Opción no válida. Ejecutando análisis por defecto de archivos de prueba:")
        analizar_archivo(ruta_validos)
        analizar_archivo(ruta_invalidos)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analizador de logs de aplicaciones (AI-First Log Analyzer)."
    )
    parser.add_argument(
        "archivos",
        nargs="*",
        help="Rutas opcionales de archivos de log a procesar. Si no se especifican, se inicia el menú de selección.",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Ejecuta automáticamente la suite de pruebas sin abrir el menú interactivo.",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    ruta_validos = base_dir / "tests" / "logs_validos.txt"
    ruta_invalidos = base_dir / "tests" / "logs_invalidos.txt"

    # Si se pasaron archivos por línea de comandos
    if args.archivos:
        hubo_error = False
        for ruta_str in args.archivos:
            if analizar_archivo(ruta_str) is None:
                hubo_error = True
        return 1 if hubo_error else 0

    # Si se solicitó ejecución automática o no es terminal interactiva
    if args.auto or not sys.stdin.isatty():
        resultados = [analizar_archivo(ruta_validos), analizar_archivo(ruta_invalidos)]
        return 1 if any(resultado is None for resultado in resultados) else 0

    # Modo interactivo
    menu_interactivo()
    return 0


if __name__ == "__main__":
    sys.exit(main())
