"""AIFEC — fábrica de plugins: apoyos comunes de las puertas.

Leer los argumentos del contrato (`--slug --candidato --banco --plan --informe`), escribir el informe y salir
con 0, 1 o 2, localizar PHP, instalar el candidato en el banco, lanzar las órdenes de AIFEC y los guiones de PHP
de esta carpeta (`_ciclo.php`, `_humo.php`) y leer la declaración del contrato de un `plugin.json`.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import stat
import sys
from pathlib import Path

# En Windows la consola habla en la página de códigos de la máquina: el informe saldría con «?» donde van las tildes.
for _salida in (sys.stdout, sys.stderr):
    try:
        _salida.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

CARPETA = Path(__file__).resolve().parent
RAIZ = CARPETA.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from motor import estado as estado_mod, procesos  # noqa: E402

PASA = "pasa"
NO_PASA = "no_pasa"
NO_APLICA = "no_aplica"
CODIGOS = {PASA: 0, NO_PASA: 1, NO_APLICA: 2}

IGNORAR = ("__pycache__", ".git", "node_modules")


class NoAplica(Exception):
    """Falta algo opcional (PHP, el banco, una orden de AIFEC): la puerta sale con 2 y lo dice."""


class NoPasa(Exception):
    """Lo fabricado impide seguir (por ejemplo, un plugin sin manifiesto): la puerta sale con 1 y lo dice."""


# ------------------------------------------------------------------ contexto e informe


class Contexto:
    """Lo que recibe una puerta y cómo termina."""

    def __init__(self, nombre: str, args):
        self.nombre = nombre
        self.slug = args.slug
        self.candidato = Path(args.candidato)
        self.banco = Path(args.banco)
        self.plan_ruta = Path(args.plan)
        self.informe_ruta = Path(args.informe)
        self.plan = leer_json(self.plan_ruta, {})
        if not isinstance(self.plan, dict):
            self.plan = {}
        self.args = args

    # donde viven las cosas de la fábrica, contando desde el banco (`<fábrica>/estado/banco`)
    @property
    def estado(self) -> Path:
        return self.banco.parent

    @property
    def fabrica(self) -> Path:
        return self.estado.parent

    @property
    def sesiones(self) -> Path:
        return self.estado / "sesiones"

    def opcion(self, clave: str, defecto=None):
        valor = self.plan.get(clave, defecto)
        return defecto if valor is None else valor

    def terminar(self, veredicto: str, resumen: str, detalles=None, medidas=None) -> int:
        """Escribe el informe, enseña el resumen y devuelve el código de salida."""
        informe = {"puerta": self.nombre, "ok": veredicto != NO_PASA, "resumen": resumen,
                   "detalles": [str(d) for d in (detalles or [])], "medidas": medidas or {}}
        self.informe_ruta.parent.mkdir(parents=True, exist_ok=True)
        estado_mod.escribir(self.informe_ruta, informe)
        etiqueta = {PASA: "PASA", NO_PASA: "NO PASA", NO_APLICA: "NO APLICA"}[veredicto]
        print("%s %s: %s" % (self.nombre, etiqueta, resumen))
        for detalle in informe["detalles"][:40]:
            print("  - " + detalle)
        return CODIGOS[veredicto]


def leer_json(ruta, defecto=None):
    try:
        return json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defecto


def contexto(nombre: str, argv=None, extra=None) -> Contexto:
    """Lee la línea de órdenes de una puerta. `extra(parser)` añade argumentos propios."""
    analizador = argparse.ArgumentParser(prog=nombre, description="Puerta «%s» de la fábrica de plugins de AIFEC" % nombre)
    analizador.add_argument("--slug", required=True)
    analizador.add_argument("--candidato", required=True)
    analizador.add_argument("--banco", required=True)
    analizador.add_argument("--plan", required=True)
    analizador.add_argument("--informe", required=True)
    if extra:
        extra(analizador)
    return Contexto(nombre, analizador.parse_args(argv))


def ejecutar(nombre: str, funcion, argv=None, extra=None) -> int:
    """Ciclo común: lee argumentos, llama a `funcion(ctx)` (que devuelve el código de `ctx.terminar`) y
    convierte `NoAplica`, `NoPasa` y cualquier excepción inesperada en un informe con su código."""
    ctx = contexto(nombre, argv, extra)
    try:
        return funcion(ctx)
    except NoAplica as error:
        return ctx.terminar(NO_APLICA, str(error))
    except NoPasa as error:
        return ctx.terminar(NO_PASA, str(error))
    except Exception as error:  # una puerta que revienta tiene que decirlo en su informe, no solo en el registro
        return ctx.terminar(NO_PASA, "la puerta falló por dentro: %s: %s" % (type(error).__name__, error))


# ------------------------------------------------------------------ ficheros del plugin


def firma_arbol(carpeta) -> str:
    """Una huella del contenido de una carpeta: cambia si cambia un nombre, un fichero o un byte."""
    carpeta = Path(carpeta)
    resumen = hashlib.sha1()
    if not carpeta.is_dir():
        return ""
    for ruta in sorted(carpeta.rglob("*")):
        relativa = ruta.relative_to(carpeta).as_posix()
        if any(parte in IGNORAR for parte in ruta.relative_to(carpeta).parts) or not ruta.is_file():
            continue
        resumen.update(relativa.encode("utf-8"))
        try:
            resumen.update(ruta.read_bytes())
        except OSError:
            resumen.update(b"?")
    return resumen.hexdigest()


def ficheros(carpeta, extensiones=None):
    """Ficheros de una carpeta (rutas relativas con `/`), sin carpetas de trabajo."""
    carpeta = Path(carpeta)
    if not carpeta.is_dir():
        return []
    salida = []
    for ruta in sorted(carpeta.rglob("*")):
        partes = ruta.relative_to(carpeta).parts
        if not ruta.is_file() or any(p in IGNORAR for p in partes):
            continue
        if extensiones is None or ruta.suffix.lower() in extensiones:
            salida.append(ruta.relative_to(carpeta).as_posix())
    return salida


def leer_texto(ruta) -> str:
    try:
        return Path(ruta).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def manifiesto(carpeta) -> dict:
    datos = leer_json(Path(carpeta) / "plugin.json", {})
    return datos if isinstance(datos, dict) else {}


def declaracion(carpeta) -> dict:
    """La declaración del contrato de un plugin: `hosts`, `personal_data`, `tables` y `capabilities` (listas de
    textos; lo que falte o no sea una lista sale vacío)."""
    contrato = manifiesto(carpeta).get("contract")
    contrato = contrato if isinstance(contrato, dict) else {}
    salida = {}
    for clave in ("hosts", "personal_data", "tables", "capabilities"):
        valor = contrato.get(clave)
        salida[clave] = [v for v in valor if isinstance(v, str)] if isinstance(valor, list) else []
    return salida


def exigir_manifiesto(ctx: Contexto) -> None:
    if not (ctx.candidato / "plugin.json").is_file():
        raise NoPasa("el candidato no trae plugin.json")


# ------------------------------------------------------------------ PHP y el banco


def ejecutable(texto):
    """La ruta de un programa si existe (ruta o nombre en el PATH); si no, None."""
    if not isinstance(texto, str) or not texto.strip():
        return None
    if Path(texto).is_file():
        return str(Path(texto))
    return shutil.which(texto)


def php_principal(ctx: Contexto) -> str:
    php = ejecutable(ctx.opcion("php", "php"))
    if php is None:
        raise NoAplica("no encuentro PHP (plan.json → «php»: %s)" % ctx.opcion("php", "php"))
    return php


def programas_php(ctx: Contexto) -> list:
    """Los PHP con los que hay que comprobar la sintaxis: el principal y los de `php_versiones` (sin repetir)."""
    programas = []
    for texto in [ctx.opcion("php", "php")] + [v for v in ctx.opcion("php_versiones", []) if isinstance(v, str)]:
        if texto not in programas:
            programas.append(texto)
    return programas


def banco_listo(ctx: Contexto) -> bool:
    return (ctx.banco / "aifec").is_file() and (ctx.banco / "core" / "bootstrap.php").is_file()


def exigir_banco(ctx: Contexto) -> None:
    if not banco_listo(ctx):
        raise NoAplica("el banco de pruebas no está preparado (ejecuta `python fabrica.py banco`)")


def _forzar_borrado(funcion, camino, _info):
    try:
        Path(camino).chmod(stat.S_IWRITE)
        funcion(camino)
    except OSError:
        pass


def borrar(ruta: Path) -> None:
    if ruta.exists():
        shutil.rmtree(str(ruta), onerror=_forzar_borrado)


def sincronizar(origen: Path, destino: Path) -> bool:
    """Deja `destino` igual que `origen`. Devuelve True si hubo que copiar."""
    if firma_arbol(origen) == firma_arbol(destino) and destino.is_dir():
        return False
    borrar(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(origen), str(destino), ignore=shutil.ignore_patterns(*IGNORAR))
    return True


def carpeta_en_banco(ctx: Contexto) -> Path:
    return ctx.banco / "plugins" / ctx.slug


def instalar_candidato(ctx: Contexto) -> None:
    """El candidato, en `plugins/` del banco (si ya está igual, no se toca)."""
    exigir_banco(ctx)
    sincronizar(ctx.candidato, carpeta_en_banco(ctx))


def retirar_del_banco(ctx: Contexto) -> None:
    """Quita el candidato del banco: ninguna puerta deja un plugin instalado para las siguientes."""
    borrar(carpeta_en_banco(ctx))


def orden_aifec(ctx: Contexto, args: list, minutos: float = 5, nombre: str = "orden"):
    """Lanza `php aifec <args>` en el banco con los datos forzados a `banco/sites`. Devuelve (código, texto)."""
    exigir_banco(ctx)
    registro = ctx.sesiones / ("%s.%s.%s.log" % (ctx.slug, ctx.nombre, nombre))
    if registro.exists():
        registro.unlink()
    orden = [php_principal(ctx), "aifec"] + [str(a) for a in args] + ["--data=" + str(ctx.banco / "sites")]
    codigo = procesos.lanzar(orden, ctx.banco, registro, minutos)
    return codigo, leer_texto(registro)


def php_en_banco(ctx: Contexto, args: list, minutos: float = 5, nombre: str = "php"):
    """Lanza `php <args>` con el directorio de trabajo en el banco (por ejemplo, `tests/run.php`). Devuelve (código, texto)."""
    exigir_banco(ctx)
    registro = ctx.sesiones / ("%s.%s.%s.log" % (ctx.slug, ctx.nombre, nombre))
    if registro.exists():
        registro.unlink()
    codigo = procesos.lanzar([php_principal(ctx)] + [str(a) for a in args], ctx.banco, registro, minutos)
    return codigo, leer_texto(registro)


def lanzar_php(ctx: Contexto, guion: str, args: list, minutos: float, nombre: str):
    """Lanza un guion de PHP de `puertas/` (`_ciclo.php`, `_humo.php`). Devuelve (código, texto de la salida)."""
    registro = ctx.sesiones / ("%s.%s.%s.log" % (ctx.slug, ctx.nombre, nombre))
    if registro.exists():
        registro.unlink()
    orden = [php_principal(ctx), str(CARPETA / guion)] + [str(a) for a in args]
    codigo = procesos.lanzar(orden, ctx.banco, registro, minutos)
    return codigo, leer_texto(registro)


def resultado_de(texto: str, marca: str):
    """El JSON que un guion de PHP escribe en su última línea con esa marca (`CICLO {...}`); None si no está."""
    for linea in reversed(texto.splitlines()):
        if linea.startswith(marca + " "):
            try:
                datos = json.loads(linea[len(marca) + 1:])
            except ValueError:
                return None
            return datos if isinstance(datos, dict) else None
    return None


def kb(bytes_: int) -> str:
    return ("%.1f" % (bytes_ / 1000.0)).replace(".", ",") + " KB"
