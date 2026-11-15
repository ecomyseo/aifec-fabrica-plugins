"""AIFEC — fábrica de plugins: puerta «pruebas» (trae pruebas y pasan).

Instala el candidato en el banco y lanza `php tests/run.php plugins/<id>/`, el corredor del propio sistema.
Pasa si el corredor sale con 0 y su última línea dice «PRUEBAS: n OK, 0 FALLAN» con **al menos cuatro**
pruebas: las mínimas de un plugin (se activa, hace lo suyo, se desactiva, se desinstala). Sin pruebas, o con
menos de cuatro, no pasa: «cero pruebas» no es un verde. Antes de lanzar nada se cuenta en el candidato
cuántas declara, para dar un motivo claro cuando no hay ninguna.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _comun  # noqa: E402

MINIMO = 4
RESULTADO = re.compile(r"PRUEBAS:\s*(\d+)\s+OK,\s*(\d+)\s+FALLAN", re.I)
DECLARADA = re.compile(r"^\s*test\s*\(", re.M)


def pruebas_declaradas(carpeta: Path) -> tuple:
    """(ficheros de prueba, pruebas declaradas con `test(`) del candidato."""
    ficheros = [f for f in _comun.ficheros(carpeta, (".php",)) if f.startswith("tests/") and f.endswith("Test.php")]
    total = sum(len(DECLARADA.findall(_comun.leer_texto(carpeta / f))) for f in ficheros)
    return ficheros, total


def puerta(ctx) -> int:
    _comun.exigir_manifiesto(ctx)
    ficheros, declaradas = pruebas_declaradas(ctx.candidato)
    if not ficheros:
        raise _comun.NoPasa("el plugin no trae pruebas: falta tests/<Nombre>Test.php (las cuatro mínimas: se activa, hace lo suyo, se desactiva, se desinstala)")
    if declaradas < MINIMO:
        raise _comun.NoPasa("el plugin declara %d prueba(s) y hacen falta al menos %d (se activa, hace lo suyo, se desactiva, se desinstala)" % (declaradas, MINIMO))
    _comun.instalar_candidato(ctx)  # sin banco preparado, aquí sale con 2
    # La barra final: «plugins/hola» también coge «plugins/hola-mundo»; «plugins/hola/» solo el suyo.
    codigo, texto = _comun.php_en_banco(ctx,["tests/run.php", "plugins/%s/" % ctx.slug], minutos=10, nombre="tests")
    if codigo == _comun.procesos.TIEMPO_AGOTADO:
        raise _comun.NoPasa("las pruebas se pasaron del tiempo y se cortaron")
    final = None
    for linea in texto.splitlines():
        encontrado = RESULTADO.search(linea)
        if encontrado:
            final = encontrado
    if final is None:
        ultimas = [l.strip() for l in texto.strip().splitlines()[-5:]]
        return ctx.terminar(_comun.NO_PASA, "el corredor de pruebas no dio su línea final (código %s)" % codigo, ultimas,
                            {"declaradas": declaradas, "codigo": codigo if isinstance(codigo, int) else -1})
    buenas, malas = int(final.group(1)), int(final.group(2))
    medidas = {"ok": buenas, "fallan": malas, "declaradas": declaradas, "ficheros": len(ficheros),
               "codigo": codigo if isinstance(codigo, int) else -1}
    if malas > 0 or codigo != 0:
        detalles = [l.rstrip() for l in texto.splitlines() if l.strip() and not RESULTADO.search(l)][:30]
        return ctx.terminar(_comun.NO_PASA, "%d prueba(s) fallan de %d" % (malas, buenas + malas), detalles, medidas)
    if buenas < MINIMO:
        return ctx.terminar(_comun.NO_PASA, "solo se ejecutan %d prueba(s) y hacen falta al menos %d" % (buenas, MINIMO), [], medidas)
    return ctx.terminar(_comun.PASA, "%d pruebas, todas pasan" % buenas, [], medidas)


if __name__ == "__main__":
    sys.exit(_comun.ejecutar("pruebas", puerta))
