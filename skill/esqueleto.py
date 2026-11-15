"""AIFEC — fábrica de plugins: crea un plugin nuevo a partir del esqueleto de `plantillas/esqueleto/`.

    python skill/esqueleto.py <id> "<Nombre del plugin>" [--salida <carpeta>] [--forzar]

Copia el esqueleto (un plugin pequeño y completo que ya pasa `contract:check` y sus propias pruebas) y sustituye
las marcas, tanto en el contenido como en los nombres de fichero:

    __id__        el identificador, con guiones           lista-deseos
    __id_bajo__   el mismo, con guiones bajos             lista_deseos   (tablas, ajustes, funciones)
    __Nombre__    el nombre que verá la persona           Lista de deseos
    __Espacio__   el espacio de nombres, en CamelCase     ListaDeseos

Por defecto escribe en `salida/<id>/` de la fábrica. Sale con 0 si lo ha creado, con 2 si los datos no valen o la
carpeta ya tiene algo.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

RAIZ = Path(__file__).resolve().parent.parent
ESQUELETO = RAIZ / "plantillas" / "esqueleto"
TEXTOS = (".php", ".json", ".md", ".css", ".js", ".txt")
ID = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
PROHIBIDO_EN_NOMBRE = re.compile(r"[\\'\"`$<>{}\n\r\t]|\*/")


def marcas_de(id_: str, nombre: str) -> dict:
    """Las cuatro marcas del esqueleto para un identificador y un nombre. Lanza ValueError si no valen."""
    if not ID.match(id_) or not 2 <= len(id_) <= 40:
        raise ValueError("el identificador va en minúsculas, empieza por una letra y solo lleva cifras y guiones sueltos "
                         "(de 2 a 40 caracteres): %r" % id_)
    nombre = nombre.strip()
    if not nombre or len(nombre) > 60:
        raise ValueError("el nombre no puede estar vacío ni pasar de 60 caracteres")
    if PROHIBIDO_EN_NOMBRE.search(nombre):
        raise ValueError("el nombre no puede llevar comillas, barras invertidas, «$», «<», «>», llaves ni «*/»: %r" % nombre)
    return {
        "__id_bajo__": id_.replace("-", "_"),
        "__id__": id_,
        "__Nombre__": nombre,
        "__Espacio__": "".join(parte[:1].upper() + parte[1:] for parte in id_.split("-")),
    }


def sustituir(texto: str, marcas: dict) -> str:
    for marca in ("__id_bajo__", "__id__", "__Nombre__", "__Espacio__"):
        texto = texto.replace(marca, marcas[marca])
    return texto


def crear(id_: str, nombre: str, destino: Path, forzar: bool = False) -> list:
    """Crea el plugin y devuelve la lista de ficheros escritos. Lanza ValueError si los datos no valen."""
    marcas = marcas_de(id_, nombre)
    if not ESQUELETO.is_dir():
        raise ValueError("no encuentro el esqueleto en %s" % ESQUELETO)
    if destino.exists() and any(destino.iterdir()):
        if not forzar:
            raise ValueError("ya hay algo en %s (usa --forzar para rehacerlo)" % destino)
        shutil.rmtree(str(destino))
    escritos = []
    for origen in sorted(ESQUELETO.rglob("*")):
        if not origen.is_file() or "__pycache__" in origen.parts:
            continue
        relativa = Path(sustituir(origen.relative_to(ESQUELETO).as_posix(), marcas))
        salida = destino / relativa
        salida.parent.mkdir(parents=True, exist_ok=True)
        if origen.suffix.lower() in TEXTOS:
            salida.write_bytes(sustituir(origen.read_text(encoding="utf-8"), marcas).encode("utf-8"))
        else:
            shutil.copy2(str(origen), str(salida))
        escritos.append(relativa.as_posix())
    return escritos


def main() -> int:
    analizador = argparse.ArgumentParser(description="Crea un plugin desde el esqueleto de la fábrica")
    analizador.add_argument("id")
    analizador.add_argument("nombre")
    analizador.add_argument("--salida", default=None, help="carpeta del plugin (por defecto salida/<id>/)")
    analizador.add_argument("--forzar", action="store_true", help="rehace la carpeta si ya existe")
    args = analizador.parse_args()
    destino = Path(args.salida) if args.salida else RAIZ / "salida" / args.id
    try:
        escritos = crear(args.id, args.nombre, destino, args.forzar)
    except ValueError as error:
        print("no se ha creado nada: %s" % error)
        return 2
    print("Plugin «%s» creado en %s (%d ficheros)" % (args.id, destino, len(escritos)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
