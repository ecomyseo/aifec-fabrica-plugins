"""AIFEC — fábrica de plugins: pruebas de higiene del código.

El motor y `fabrica.py` son idénticos en la fábrica de temas y en la de plugins (byte a byte, cuando la otra carpeta
está al lado), así que no pueden saber qué fabrican, ni llevar rutas de esta máquina, ni usar programas que no existan
en los tres sistemas operativos. Las puertas, sus guiones de PHP y el esqueleto tienen sus propias reglas: cabecera,
biblioteca estándar, nada de rutas de esta máquina y PHP que compila en 7.4 y en 8.4.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

from ayudas import PROYECTO
from ayudas_puertas import php_de
from motor import plan as plan_mod

FICHEROS = sorted((PROYECTO / "motor").glob("*.py")) + [PROYECTO / "fabrica.py"]
PUERTAS = sorted((PROYECTO / "puertas").glob("*.py"))
HERMANA = PROYECTO.parent / "aifec-fabrica-temas"
RUTAS_DE_ESTA_MAQUINA = r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]|/Users/|/home/|Usuario|dev-tools|modulos IA"


def _lineas_con(patron, ficheros=FICHEROS):
    encontradas = []
    expresion = re.compile(patron)
    for ruta in ficheros:
        for numero, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
            if expresion.search(linea):
                encontradas.append("%s:%d: %s" % (ruta.name, numero, linea.strip()))
    return encontradas


class PruebasHigieneDelMotor(unittest.TestCase):
    def test_hay_motor_y_fabrica(self):
        self.assertGreaterEqual(len(FICHEROS), 10)

    @unittest.skipUnless(HERMANA.is_dir(), "la fábrica de temas no está al lado")
    def test_el_motor_y_fabrica_py_son_los_mismos_ficheros_que_en_la_fabrica_de_temas(self):
        for nombre in sorted(p.name for p in (HERMANA / "motor").glob("*.py")) + ["../fabrica.py"]:
            if nombre == "../fabrica.py":
                propio, ajeno = PROYECTO / "fabrica.py", HERMANA / "fabrica.py"
            else:
                propio, ajeno = PROYECTO / "motor" / nombre, HERMANA / "motor" / nombre
            self.assertTrue(propio.is_file(), "falta %s en esta fábrica" % nombre)
            self.assertEqual(propio.read_bytes(), ajeno.read_bytes(), "%s no es idéntico al de la fábrica de temas" % nombre)
        propios = sorted(p.name for p in (PROYECTO / "motor").glob("*.py"))
        ajenos = sorted(p.name for p in (HERMANA / "motor").glob("*.py"))
        self.assertEqual(propios, ajenos, "los dos motores tienen que tener los mismos ficheros")

    def test_el_motor_no_sabe_si_fabrica_temas_o_plugins(self):
        self.assertEqual(_lineas_con(r"(?i)tema|plugin|theme"), [])

    def test_ningun_programa_que_no_exista_en_los_tres_sistemas(self):
        self.assertEqual(_lineas_con(r"(?i)wmic|tasklist|taskkill"), [])
        self.assertEqual(_lineas_con(r"(?i)wmic|tasklist|taskkill", PUERTAS), [])

    def test_ninguna_ruta_absoluta_de_esta_maquina_ni_nombre_de_usuario(self):
        self.assertEqual(_lineas_con(RUTAS_DE_ESTA_MAQUINA), [])
        # en las puertas: una ruta de esta máquina solo en los comentarios de ejemplo no cabe; ninguna
        self.assertEqual(_lineas_con(RUTAS_DE_ESTA_MAQUINA, PUERTAS), [])

    def test_todo_subprocess_lleva_la_entrada_vacia(self):
        # El único sitio donde se lanzan procesos es procesos.lanzar (también en las puertas).
        fuentes = _lineas_con(r"subprocess\.(Popen|run|call|check_output)")
        self.assertTrue(all(l.startswith("procesos.py:") for l in fuentes), fuentes)
        self.assertEqual(_lineas_con(r"subprocess\.", PUERTAS), [], "las puertas lanzan por procesos.lanzar")
        self.assertIn("stdin", (PROYECTO / "motor" / "procesos.py").read_text(encoding="utf-8"))

    def test_ninguna_dependencia_de_fuera_de_la_biblioteca_estandar(self):
        permitidos = set(sys.stdlib_module_names) | {"motor", "ctypes", "_comun", "esqueleto"}
        for ruta in FICHEROS + PUERTAS + [PROYECTO / "skill" / "esqueleto.py", PROYECTO / "skill" / "informe.py"]:
            arbol = ast.parse(ruta.read_text(encoding="utf-8"))
            for nodo in ast.walk(arbol):
                if isinstance(nodo, ast.Import):
                    modulos = [a.name.split(".")[0] for a in nodo.names]
                elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
                    modulos = [nodo.module.split(".")[0]]
                else:
                    continue
                for modulo in modulos:
                    self.assertIn(modulo, permitidos, "%s importa %s" % (ruta.name, modulo))

    def test_cada_fichero_de_python_empieza_por_su_cabecera(self):
        for ruta in FICHEROS:
            texto = ruta.read_text(encoding="utf-8")
            self.assertTrue(texto.startswith('"""AIFEC — '), ruta.name)
            self.assertIn("@author  Ecom Experts <ecomyseo@gmail.com>", texto, ruta.name)
            self.assertIn("@license Ver LICENSE.md", texto, ruta.name)
        for ruta in PUERTAS + [PROYECTO / "skill" / "esqueleto.py", PROYECTO / "skill" / "informe.py"]:
            texto = ruta.read_text(encoding="utf-8")
            self.assertTrue(texto.startswith('"""AIFEC — fábrica de plugins'), ruta.name)
            self.assertIn("@author  Ecom Experts <ecomyseo@gmail.com>", texto, ruta.name)
            self.assertIn("@license Ver LICENSE.md", texto, ruta.name)

    def test_los_ficheros_son_utf8_sin_bom_y_con_saltos_lf(self):
        for ruta in FICHEROS + PUERTAS + sorted((PROYECTO / "puertas").glob("*.php")):
            crudo = ruta.read_bytes()
            self.assertFalse(crudo.startswith(b"\xef\xbb\xbf"), ruta.name)
            self.assertNotIn(b"\r\n", crudo, ruta.name)


class PruebasDeLaConfiguracion(unittest.TestCase):
    def test_la_fabrica_de_plugins_trae_su_configuracion_completa(self):
        config = plan_mod.cargar_config(PROYECTO)
        self.assertEqual(config["clase"], "plugins")
        self.assertEqual(config["titulo"], "Fábrica de plugins de AIFEC")
        self.assertEqual(config["carpeta_destino"], "plugins")
        self.assertEqual(config["manifiesto"], "plugin.json")
        self.assertEqual(config["orden_esqueleto"], ["plugin:create", "{slug}", "--name={nombre}"])
        self.assertEqual(config["puertas"], ["sintaxis", "contrato", "pruebas", "traducciones", "ciclo", "humo", "limpieza"])

    def test_cada_puerta_del_contrato_existe_y_ninguna_sobra(self):
        config = plan_mod.cargar_config(PROYECTO)
        publicas = sorted(p.stem for p in (PROYECTO / "puertas").glob("*.py") if not p.name.startswith("_"))
        self.assertEqual(publicas, sorted(config["puertas"]))
        for apoyo in ("_ciclo.php", "_humo.php", "_comun.py"):
            self.assertTrue((PROYECTO / "puertas" / apoyo).is_file(), apoyo)

    def test_los_ejemplos_son_json_validos_y_el_plan_de_ejemplo_no_lleva_rutas_de_esta_maquina(self):
        for nombre in ("plan.ejemplo.json", "cola.ejemplo.json", "fabrica.json"):
            json.loads((PROYECTO / nombre).read_text(encoding="utf-8"))
        ejemplo = (PROYECTO / "plan.ejemplo.json").read_text(encoding="utf-8")
        self.assertNotRegex(ejemplo, r"[A-Za-z]:[\\/]")
        cola = json.loads((PROYECTO / "cola.ejemplo.json").read_text(encoding="utf-8"))
        self.assertEqual(len(cola), 3)

    def test_gitignore_deja_fuera_lo_que_no_se_publica(self):
        lineas = (PROYECTO / ".gitignore").read_text(encoding="utf-8").split()
        for esperado in ("plan.json", "cola.json", "estado/", "salida/", "escaparate/", "__pycache__/"):
            self.assertIn(esperado, lineas)


class PruebasDelPhpDeLaFabrica(unittest.TestCase):
    """Lo que corre dentro del banco con el PHP del plan tiene que compilar en 7.4 y en 8.4 y no avisar."""

    def _lintar(self, version, ficheros):
        php = php_de(version)
        if php is None:
            self.skipTest("hace falta PHP %s" % version)
        for fichero in ficheros:
            proceso = subprocess.run([php, "-d", "display_errors=1", "-d", "error_reporting=-1", "-l", str(fichero)],
                                     stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
            salida = proceso.stdout + proceso.stderr
            self.assertEqual(proceso.returncode, 0, "%s con PHP %s: %s" % (fichero.name, version, salida))
            self.assertNotRegex(salida, r"Deprecated|Warning|Notice", "%s con PHP %s: %s" % (fichero.name, version, salida))

    def test_los_guiones_de_php_de_las_puertas_compilan_en_74_y_en_84(self):
        guiones = sorted((PROYECTO / "puertas").glob("*.php"))
        self.assertEqual([g.name for g in guiones], ["_ciclo.php", "_humo.php"])
        self._lintar("7.4", guiones)
        self._lintar("8.4", guiones)

    def test_el_php_del_esqueleto_y_del_ejemplo_compila_en_74_y_en_84(self):
        from ayudas_puertas import esqueleto_mod
        import tempfile
        with tempfile.TemporaryDirectory() as carpeta:
            destino = Path(carpeta) / "lista-deseos"
            esqueleto_mod.crear("lista-deseos", "Lista de deseos", destino)
            php = sorted(destino.rglob("*.php")) + sorted((PROYECTO / "skill" / "ejemplos").rglob("*.php"))
            self.assertGreaterEqual(len(php), 15)
            self._lintar("7.4", php)
            self._lintar("8.4", php)


if __name__ == "__main__":
    unittest.main()
