"""AIFEC — fábrica de plugins: puerta «sintaxis» (el código vale en todas las versiones de PHP).

Pasa `php -l` a cada fichero `.php` del candidato con cada ejecutable del plan (`php` y `php_versiones`: el más
bajo y el más alto que se admiten). No basta con que `php -l` salga con 0: PHP 8.4 avisa de lo obsoleto
(«Implicitly marking parameter as nullable») y sigue saliendo con 0, así que cualquier línea de aviso cuenta
como fallo. Un `match` o una propiedad `readonly` no se compilan en PHP 7.4: es justo lo que esta puerta caza.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _comun  # noqa: E402

BIEN = re.compile(r"No syntax errors detected", re.I)
AVISO = re.compile(r"^(?:PHP\s+)?(Parse error|Fatal error|Deprecated|Warning|Notice)\s*:\s*(.*)$", re.I)


def version_de(ejecutable: str) -> str:
    """Un nombre corto para decir con qué PHP se comprobó: la carpeta del programa (`php-7.4`) o el programa."""
    ruta = Path(ejecutable)
    return ruta.parent.name if ruta.parent.name not in ("", ".", "bin") else ruta.name


def lintar(ctx, ejecutable: str, carpeta: Path, relativa: str):
    """Devuelve el primer problema de ese fichero con ese PHP, o None si está limpio."""
    registro = ctx.sesiones / ("%s.sintaxis.lint.log" % ctx.slug)
    if registro.exists():
        registro.unlink()
    codigo = _comun.procesos.lanzar(
        [ejecutable, "-d", "display_errors=1", "-d", "error_reporting=-1", "-l", str(carpeta / relativa)],
        carpeta, registro, 2)
    texto = _comun.leer_texto(registro)
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    for linea in lineas:
        encontrada = AVISO.match(linea)
        if encontrada:
            return "%s: %s" % (encontrada.group(1), re.sub(r"\s+in\s+\S+\s+on line\s+(\d+)$", r" (línea \1)", encontrada.group(2))[:150])
    if codigo != 0 or not BIEN.search(texto):
        return (lineas or ["sin mensaje (código %s)" % codigo])[0][:150]
    return None


def puerta(ctx) -> int:
    carpeta = ctx.candidato
    if not carpeta.is_dir():
        raise _comun.NoPasa("no hay candidato en %s" % carpeta)
    _comun.php_principal(ctx)  # sin PHP no hay nada que comprobar: sale con 2
    php = _comun.ficheros(carpeta, (".php",))
    if not php:
        raise _comun.NoPasa("el candidato no trae ningún fichero PHP")
    problemas = []
    hechas = 0
    usadas = []
    for texto in _comun.programas_php(ctx):
        ejecutable = _comun.ejecutable(texto)
        if ejecutable is None:
            problemas.append("no encuentro el PHP «%s» del plan: sin él no se comprueba la sintaxis en esa versión" % texto)
            continue
        usadas.append(version_de(ejecutable))
        for relativa in php:
            hechas += 1
            fallo = lintar(ctx, ejecutable, carpeta, relativa)
            if fallo:
                problemas.append("%s con %s — %s" % (relativa, version_de(ejecutable), fallo))
    medidas = {"ficheros": len(php), "versiones": usadas, "comprobaciones": hechas, "problemas": len(problemas)}
    if problemas:
        return ctx.terminar(_comun.NO_PASA, problemas[0], problemas, medidas)
    return ctx.terminar(_comun.PASA, "%d ficheros, sintaxis correcta y sin avisos con %d versión(es) de PHP (%s)" % (
        len(php), len(usadas), ", ".join(usadas)), [], medidas)


if __name__ == "__main__":
    sys.exit(_comun.ejecutar("sintaxis", puerta))
