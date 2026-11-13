"""Pruebas de caracterización del proyecto original ai-first-log-analyzer.

Estas pruebas ejecutan el código de la línea base (legacy/ai_first_log_analyzer/log_analyzer.py)
para certificar su comportamiento empírico real sobre los fixtures originales y casos límite.
Garantizan que cualquier futura refactorización en AgentForge preserve la paridad funcional.
"""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

from legacy.ai_first_log_analyzer.log_analyzer import analizar_archivo, extraer_log


class TestExtraerLogCharacterization(unittest.TestCase):
    """Caracterización de la función de extracción y clasificación determinista."""

    def test_linea_valida_estandar(self) -> None:
        linea = "[INFO] 2024-05-10 Conexión exitosa"
        res = extraer_log(linea)
        self.assertEqual(res["estado"], "valida")
        self.assertEqual(res["severidad"], "INFO")
        self.assertEqual(res["fecha"], "2024-05-10")
        self.assertEqual(res["mensaje"], "Conexión exitosa")

    def test_linea_valida_con_prefijo_vineta(self) -> None:
        linea = "· [ERROR] 2025-01-10 Failed to connect to database"
        res = extraer_log(linea)
        self.assertEqual(res["estado"], "valida")
        self.assertEqual(res["severidad"], "ERROR")
        self.assertEqual(res["fecha"], "2025-01-10")
        self.assertEqual(res["mensaje"], "Failed to connect to database")

    def test_incompleta_sin_fecha(self) -> None:
        linea = "· [WARNING] Invalid password attempt"
        res = extraer_log(linea)
        self.assertEqual(res["estado"], "incompleta")
        self.assertEqual(res["severidad"], "WARNING")
        self.assertIsNone(res["fecha"])
        self.assertEqual(res["mensaje"], "Invalid password attempt")

    def test_incompleta_solo_severidad(self) -> None:
        linea = "[INFO]"
        res = extraer_log(linea)
        self.assertEqual(res["estado"], "incompleta")
        self.assertEqual(res["severidad"], "INFO")
        self.assertIsNone(res["fecha"])
        self.assertEqual(res["mensaje"], "")

    def test_incompleta_severidad_y_fecha_sin_mensaje(self) -> None:
        linea = "[ERROR] 2024-05-10"
        res = extraer_log(linea)
        self.assertEqual(res["estado"], "incompleta")
        self.assertEqual(res["severidad"], "ERROR")
        self.assertEqual(res["fecha"], "2024-05-10")
        self.assertEqual(res["mensaje"], "")

    def test_incompleta_con_espacio_al_final_sin_mensaje(self) -> None:
        linea = "[INFO] 2024-05-10 "
        res = extraer_log(linea)
        self.assertEqual(res["estado"], "incompleta")
        self.assertEqual(res["severidad"], "INFO")
        self.assertEqual(res["fecha"], "2024-05-10")
        self.assertEqual(res["mensaje"], "")

    def test_mal_formateada_dia_30_de_febrero(self) -> None:
        linea = "[ERROR] 2024-02-30 Fallo de sincronización con fecha inexistente 30 de febrero"
        res = extraer_log(linea)
        self.assertEqual(res["estado"], "mal_formateada")
        self.assertEqual(res["severidad"], "ERROR")
        self.assertEqual(res["fecha"], "2024-02-30")

    def test_mal_formateada_ano_no_bisiesto_29_febrero(self) -> None:
        linea = "[WARNING] 2023-02-29 Error de año bisiesto inexistente en 2023"
        res = extraer_log(linea)
        self.assertEqual(res["estado"], "mal_formateada")
        self.assertEqual(res["severidad"], "WARNING")
        self.assertEqual(res["fecha"], "2023-02-29")

    def test_mal_formateada_mes_13(self) -> None:
        linea = "[ERROR] 2024-13-01 Mes 13 fuera de rango de calendario"
        res = extraer_log(linea)
        self.assertEqual(res["estado"], "mal_formateada")
        self.assertEqual(res["severidad"], "ERROR")
        self.assertEqual(res["fecha"], "2024-13-01")

    def test_mal_formateada_sin_corchetes(self) -> None:
        linea = "ERROR 2024-05-10 Línea sin corchetes en el nivel de severidad"
        res = extraer_log(linea)
        self.assertEqual(res["estado"], "mal_formateada")
        self.assertIsNone(res["severidad"])

    def test_mal_formateada_parentesis(self) -> None:
        linea = "(INFO) 2024-05-10 Paréntesis utilizados en vez de corchetes"
        res = extraer_log(linea)
        self.assertEqual(res["estado"], "mal_formateada")
        self.assertIsNone(res["severidad"])

    def test_mal_formateada_espacios_dentro_corchetes(self) -> None:
        casos = [
            "[ ERROR  ] 2024-05-10 Espacios irregulares dentro de los corchetes",
            "[  INFO] 2024-05-10 Espacios iniciales dentro de corchetes",
            "[WARNING ] 2024-05-10 Espacios finales dentro de corchetes",
        ]
        for caso in casos:
            with self.subTest(caso=caso):
                res = extraer_log(caso)
                self.assertEqual(res["estado"], "mal_formateada")
                self.assertIsNone(res["severidad"])

    def test_mal_formateada_linea_vacia_y_espacios(self) -> None:
        for caso in ["", "   ", "\t"]:
            with self.subTest(caso=caso):
                res = extraer_log(caso)
                self.assertEqual(res["estado"], "mal_formateada")
                self.assertIsNone(res["severidad"])


class TestAnalizarArchivoCharacterization(unittest.TestCase):
    """Caracterización del orquestador y resolución empírica de discrepancias."""

    def setUp(self) -> None:
        self.base_dir = Path(__file__).resolve().parent
        self.ruta_validos = self.base_dir / "fixtures" / "logs_validos.txt"
        self.ruta_invalidos = self.base_dir / "fixtures" / "logs_invalidos.txt"

    def test_orquestador_logs_validos(self) -> None:
        # Silenciamos stdout temporalmente durante la ejecución del orquestador
        stdout_trap = io.StringIO()
        original_stdout = sys.stdout
        try:
            sys.stdout = stdout_trap
            resultado = analizar_archivo(self.ruta_validos)
        finally:
            sys.stdout = original_stdout

        self.assertIsNotNone(resultado)
        assert resultado is not None  # type narrowing
        self.assertEqual(resultado["total_eventos"], 10)
        self.assertEqual(resultado["total_validas"], 10)
        self.assertEqual(resultado["total_anomalas"], 0)
        self.assertEqual(resultado["total_con_fecha_valida"], 10)
        self.assertEqual(resultado["total_sin_fecha_valida"], 0)
        self.assertEqual(
            resultado["desglose_severidad"],
            {"INFO": 5, "WARNING": 2, "ERROR": 3},
        )
        self.assertEqual(
            resultado["desglose_anomalias"],
            {"incompleta": 0, "mal_formateada": 0},
        )

    def test_orquestador_logs_invalidos_resolucion_discrepancia(self) -> None:
        """Verifica los resultados reales observados en logs_invalidos.txt.

        Resolución de discrepancia:
        El diagnóstico inicial asumió erróneamente 1 sola línea incompleta y 1 válida.
        La ejecución real demuestra:
        - 0 líneas válidas.
        - 16 líneas anómalas (100%).
        - 4 incompletas:
            1. '· [WARNING] Invalid password attempt' (sin fecha)
            2. '[INFO]' (sin fecha ni mensaje)
            3. '[ERROR] 2024-05-10' (sin mensaje)
            4. '[INFO] 2024-05-10 ' (sin mensaje)
        - 12 mal formateadas:
            - Fechas no astronómicas: 2024-02-30, 2023-02-29, 2024-13-01 (3)
            - Delimitadores incorrectos: ERROR sin corchetes, (INFO), [ ERROR  ],
              [  INFO], [WARNING ] (5)
            - Líneas vacías / espacios en blanco / texto plano (4)
        - 2 eventos con fecha válida en calendario:
            Las líneas 3 y 4 de incompletas poseen '2024-05-10', válida en calendario.
        - Desglose de severidad: INFO=2, WARNING=2, ERROR=3 (total 7 identificadas).
        """
        stdout_trap = io.StringIO()
        original_stdout = sys.stdout
        try:
            sys.stdout = stdout_trap
            resultado = analizar_archivo(self.ruta_invalidos)
        finally:
            sys.stdout = original_stdout

        self.assertIsNotNone(resultado)
        assert resultado is not None  # type narrowing
        self.assertEqual(resultado["total_eventos"], 16)
        self.assertEqual(resultado["total_validas"], 0)
        self.assertEqual(resultado["total_anomalas"], 16)
        self.assertEqual(resultado["total_con_fecha_valida"], 2)
        self.assertEqual(resultado["total_sin_fecha_valida"], 14)
        self.assertEqual(
            resultado["desglose_severidad"],
            {"INFO": 2, "WARNING": 2, "ERROR": 3},
        )
        self.assertEqual(
            resultado["desglose_anomalias"],
            {"incompleta": 4, "mal_formateada": 12},
        )

    def test_archivo_inexistente(self) -> None:
        stderr_trap = io.StringIO()
        original_stderr = sys.stderr
        try:
            sys.stderr = stderr_trap
            resultado = analizar_archivo("ruta_falsa_que_no_existe_12345.txt")
        finally:
            sys.stderr = original_stderr
        self.assertIsNone(resultado)


if __name__ == "__main__":
    unittest.main()
