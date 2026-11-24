"""AIFEC — fábrica de plugins: ayudas de las pruebas de las puertas.

Monta, en una carpeta temporal, plugins hechos con el esqueleto, un «sistema» de mentira cuyo `aifec` es un guion
de Python (para probar cómo se lee el veredicto de `contract:check` e `i18n:check` sin necesitar nada) y —para las
pruebas «con sistema»— un banco real hecho con la fábrica a partir de la instalación que diga `AIFEC_RUTA`. Nada
sale a Internet.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from functools import lru_cache
from pathlib import Path

PROYECTO = Path(__file__).resolve().parent.parent
PUERTAS = PROYECTO / "puertas"
if str(PROYECTO / "skill") not in sys.path:
    sys.path.insert(0, str(PROYECTO / "skill"))
if str(PUERTAS) not in sys.path:
    sys.path.insert(0, str(PUERTAS))

import esqueleto as esqueleto_mod  # noqa: E402  (skill/esqueleto.py)

AIFEC_RUTA = os.environ.get("AIFEC_RUTA", "")


def _borrar(ruta: Path) -> None:
    for _ in range(10):
        shutil.rmtree(str(ruta), ignore_errors=True)
        if not ruta.exists():
            return
        time.sleep(0.2)


# ------------------------------------------------------------------ PHP


def _con_modulos(candidato: str, necesarios=("pdo_sqlite",)) -> bool:
    try:
        salida = subprocess.run([candidato, "-m"], stdin=subprocess.DEVNULL, capture_output=True, timeout=30, text=True).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return all(m in salida.lower() for m in necesarios)


@lru_cache(maxsize=1)
def php_con_sqlite():
    """Un PHP que sirva para el banco real (con `pdo_sqlite`): `AIFEC_PHP`, el del PATH o los de una instalación de
    herramientas conocida. None si no se encuentra ninguno."""
    candidatos = [os.environ.get("AIFEC_PHP", ""), shutil.which("php") or ""]
    for raiz in (os.environ.get("AIFEC_PHP_DIR", ""),):
        carpeta = Path(raiz) if raiz else None
        if carpeta is not None and carpeta.is_dir():
            candidatos += [str(p / "php.exe") for p in sorted(carpeta.glob("php-8.*"), reverse=True)]
    for candidato in candidatos:
        if candidato and Path(candidato).exists() and _con_modulos(candidato):
            return candidato
    return None


@lru_cache(maxsize=1)
def php_cualquiera():
    return shutil.which("php") or php_con_sqlite()


def php_de(version: str):
    """El PHP de esa versión («7.4», «8.4») si se encuentra: `AIFEC_PHP<versión sin punto>`, `php<versión>` en el PATH o la
    carpeta de herramientas conocida. None si no hay."""
    candidatos = [os.environ.get("AIFEC_PHP" + version.replace(".", ""), ""), shutil.which("php" + version) or ""]
    if os.environ.get("AIFEC_PHP_DIR"):
        candidatos.append(os.path.join(os.environ["AIFEC_PHP_DIR"], "php-%s" % version, "php.exe"))
    for candidato in candidatos:
        if candidato and Path(candidato).exists():
            return candidato
    return None


def sistema_disponible() -> bool:
    return bool(AIFEC_RUTA) and (Path(AIFEC_RUTA) / "aifec").is_file() and php_con_sqlite() is not None


# ------------------------------------------------------------------ plugins y puertas


class BasePlugins(unittest.TestCase):
    """Carpeta temporal por prueba, plugins hechos con el esqueleto y una forma de lanzar una puerta."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="puertas-prueba-")).resolve()
        self.addCleanup(_borrar, self.tmp)
        self.banco = self.tmp / "estado" / "banco"
        self.plan = self.tmp / "plan.json"
        self.salida = self.tmp / "salida"

    # ---- plugins ----------------------------------------------------------------------------

    def plugin(self, slug: str = "lista-deseos", nombre: str = "Lista de deseos") -> Path:
        destino = self.salida / slug
        esqueleto_mod.crear(slug, nombre, destino)
        return destino

    def escribir(self, ruta: Path, texto, binario: bool = False) -> Path:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(texto if binario else texto.encode("utf-8"))
        return ruta

    def cambiar(self, plugin: Path, relativa: str, viejo: str, nuevo: str) -> Path:
        """Sustituye un trozo de un fichero del plugin. Si el trozo no está, la prueba falla: una mutación que no se
        aplica no demuestra nada."""
        ruta = plugin / relativa
        texto = ruta.read_text(encoding="utf-8")
        self.assertIn(viejo, texto, "la mutación no se aplica: no encuentro %r en %s" % (viejo, relativa))
        ruta.write_bytes(texto.replace(viejo, nuevo, 1).encode("utf-8"))
        return ruta

    # ---- lanzar una puerta ------------------------------------------------------------------

    def escribir_plan(self, **extra) -> Path:
        datos = {"php": php_cualquiera() or "php", "php_versiones": []}
        datos.update(extra)
        self.plan.write_text(json.dumps(datos), encoding="utf-8")
        return self.plan

    def lanzar(self, puerta: str, plugin: Path, plan: dict = None, slug: str = None, banco: Path = None, plan_ruta: Path = None):
        """Lanza `puertas/<puerta>.py`. Devuelve (código, informe, salida de texto)."""
        slug = slug or plugin.name
        if plan_ruta is None:
            self.escribir_plan(**(plan or {}))
            plan_ruta = self.plan
        informe = self.tmp / ("informe-%s.json" % puerta)
        if informe.exists():
            informe.unlink()
        orden = [sys.executable, str(PUERTAS / (puerta + ".py")), "--slug", slug, "--candidato", str(plugin),
                 "--banco", str(banco or self.banco), "--plan", str(plan_ruta), "--informe", str(informe)]
        proceso = subprocess.run(orden, stdin=subprocess.DEVNULL, capture_output=True, timeout=600, encoding="utf-8", errors="replace")
        datos = {}
        if informe.is_file():
            datos = json.loads(informe.read_text(encoding="utf-8"))
        return proceso.returncode, datos, proceso.stdout + proceso.stderr

    def instantanea(self, carpeta: Path) -> dict:
        return {p.relative_to(carpeta).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns)
                for p in sorted(Path(carpeta).rglob("*")) if p.is_file()}

    def aceptar(self, codigo, informe, texto, esperado=0):
        self.assertEqual(codigo, esperado, "%s\n%s" % (texto, json.dumps(informe, ensure_ascii=False)[:800]))

    def texto_del_informe(self, informe: dict) -> str:
        return informe.get("resumen", "") + "\n" + "\n".join(informe.get("detalles", []))


# ------------------------------------------------------------------ un «sistema» de mentira, para contrato y traducciones

AIFEC_MENTIRA = r'''
import os, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
raiz = Path(__file__).resolve().parent
args = [a for a in sys.argv[1:] if not a.startswith("--data=")]
modo = (raiz / "modo.txt").read_text().strip() if (raiz / "modo.txt").exists() else "ok"
orden = args[0] if args else ""
with open(raiz / "llamadas.log", "a", encoding="utf-8") as f:
    f.write(" ".join(args) + "\n")
if modo == "sin_ordenes":
    print("Unknown command: " + orden)
    sys.exit(2)
if orden == "contract:check":
    if modo == "falla":
        print("[ OK ] M1 Manifiesto y declaración")
        print("[FAIL] C5 Usa el dominio «api.ajeno.test», que no está declarado en contract.hosts (hooks.php:21)")
        print("[WARN] C3 Los recursos pesan 70 KB; por encima de 60 KB es pesado")
        print("CONTRACT " + args[1] + ": score 80/100, 1 errors, 1 warnings — FAIL")
        sys.exit(1)
    if modo == "mudo":
        print("el comando no dijo nada útil")
        sys.exit(0)
    print("[ OK ] M1 Manifiesto y declaración")
    print("[WARN] C3 Los recursos pesan 70 KB; por encima de 60 KB es pesado")
    print("CONTRACT " + args[1] + ": score 96/100, 0 errors, 1 warnings — OK")
    sys.exit(0)
if orden == "i18n:check":
    if modo == "falla":
        print("    'Sold out' => '',   // plugins/x/hooks.php")
        print("I18N plugins/x [es]: 6 strings, 2 missing")
        sys.exit(1)
    print("I18N plugins/x [es]: 6 strings, 0 missing")
    sys.exit(0)
print("orden: " + orden)
sys.exit(0)
'''


def montar_sistema_de_mentira(banco: Path, modo: str = "ok") -> None:
    (banco / "core").mkdir(parents=True, exist_ok=True)
    (banco / "core" / "bootstrap.php").write_text("<?php\n", encoding="utf-8")
    (banco / "plugins").mkdir(exist_ok=True)
    (banco / "aifec").write_text(AIFEC_MENTIRA, encoding="utf-8")
    (banco / "modo.txt").write_text(modo, encoding="utf-8")


# ------------------------------------------------------------------ el banco real, para las pruebas «con sistema»


class FabricaReal:
    """Una copia de la fábrica en una carpeta temporal con su plan apuntando a la instalación real y su banco ya
    hecho. Se monta una vez (`banco_real()`) y se borra al acabar el proceso."""

    def __init__(self):
        self.raiz = Path(tempfile.mkdtemp(prefix="fabrica-real-")).resolve()
        for nombre in ("motor", "puertas", "plantillas", "skill"):
            shutil.copytree(str(PROYECTO / nombre), str(self.raiz / nombre), ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy2(str(PROYECTO / "fabrica.py"), str(self.raiz / "fabrica.py"))
        shutil.copy2(str(PROYECTO / "fabrica.json"), str(self.raiz / "fabrica.json"))
        self.php = php_con_sqlite()
        self.escribir_plan({})
        self.banco = self.raiz / "estado" / "banco"
        self.plan = self.raiz / "plan.json"

    def escribir_plan(self, extra: dict) -> None:
        plan = {"aifec": AIFEC_RUTA, "php": self.php, "php_versiones": [], "puertas_minutos": 10}
        plan.update(extra)
        (self.raiz / "plan.json").write_text(json.dumps(plan), encoding="utf-8")

    def fabrica(self, *args, entorno=None, tiempo=900):
        env = dict(os.environ)
        env.update(entorno or {})
        proceso = subprocess.run([sys.executable, str(self.raiz / "fabrica.py")] + [str(a) for a in args], cwd=str(self.raiz),
                                 stdin=subprocess.DEVNULL, capture_output=True, timeout=tiempo, env=env, encoding="utf-8", errors="replace")
        return proceso.returncode, proceso.stdout + proceso.stderr

    def preparar_banco(self) -> None:
        codigo, texto = self.fabrica("banco")
        if codigo != 0 or not (self.banco / "aifec").is_file():
            raise RuntimeError("no se pudo preparar el banco real: %s" % texto[-300:])

    def borrar(self) -> None:
        _borrar(self.raiz)


_COMPARTIDA = []


def banco_real() -> FabricaReal:
    """Un banco real compartido por todas las pruebas «con sistema» del proceso (preparar uno cuesta unos segundos)."""
    if not _COMPARTIDA:
        fabrica = FabricaReal()
        fabrica.preparar_banco()
        _COMPARTIDA.append(fabrica)
        atexit.register(fabrica.borrar)
    return _COMPARTIDA[0]


def arbol(carpeta: Path, ignorar=()) -> dict:
    """Instantánea (tamaño y fecha de cada fichero) de una carpeta, sin las subcarpetas de `ignorar`."""
    carpeta = Path(carpeta)
    resultado = {}
    for ruta, subcarpetas, nombres in os.walk(str(carpeta)):
        relativa = os.path.relpath(ruta, str(carpeta)).replace("\\", "/")
        subcarpetas[:] = [s for s in subcarpetas if (s if relativa == "." else relativa + "/" + s) not in ignorar and s != "__pycache__"]
        for nombre in nombres:
            ficha = os.stat(os.path.join(ruta, nombre))
            clave = nombre if relativa == "." else relativa + "/" + nombre
            resultado[clave] = (ficha.st_size, ficha.st_mtime_ns)
    return resultado
