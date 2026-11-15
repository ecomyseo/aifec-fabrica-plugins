"""AIFEC — fábrica de plugins: puerta «humo» (no rompe nada).

Instala el candidato en el banco y lanza `_humo.php`, que pide en el propio proceso la portada, el listado, una
ficha, el carrito y el escritorio del panel (con una persona del equipo creada para la ocasión), primero sin el
plugin y después con él activo. Pasa si cada página que respondía 200 sin el plugin sigue respondiendo 200 con él
y si el registro del sitio y los avisos de PHP no ganan ni una línea nueva. Al acabar quita el candidato del banco.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _comun  # noqa: E402


def puerta(ctx) -> int:
    _comun.exigir_banco(ctx)
    _comun.exigir_manifiesto(ctx)
    _comun.php_principal(ctx)
    _comun.instalar_candidato(ctx)
    try:
        codigo, texto = _comun.lanzar_php(ctx, "_humo.php", ["--banco", ctx.banco, "--id", ctx.slug], 10, "humo")
    finally:
        _comun.retirar_del_banco(ctx)
    if codigo == _comun.procesos.TIEMPO_AGOTADO:
        raise _comun.NoPasa("el humo se pasó del tiempo y se cortó")
    ultima = (texto.strip().splitlines() or ["sin mensaje"])[-1][:200]
    datos = _comun.resultado_de(texto, "HUMO")
    if codigo == 2:
        notas = [str(n) for n in datos.get("notas", [])] if isinstance(datos, dict) and isinstance(datos.get("notas"), list) else []
        raise _comun.NoAplica("no se puede hacer el humo con el banco: %s" % (notas[-1] if notas else ultima))
    if datos is None:
        raise _comun.NoPasa("el guion del humo no dio su resultado (código %s): %s" % (codigo, ultima))
    problemas = [str(p) for p in datos.get("problemas", [])] if isinstance(datos.get("problemas"), list) else []
    paginas = datos.get("paginas") if isinstance(datos.get("paginas"), dict) else {}
    notas = [str(n) for n in datos.get("notas", [])] if isinstance(datos.get("notas"), list) else []
    medidas = {"paginas": paginas, "avisos_php": len(datos.get("avisos_php") or []),
               "registro": len(datos.get("registro") or []), "problemas": len(problemas)}
    if problemas:
        return ctx.terminar(_comun.NO_PASA, problemas[0], problemas + ["nota: " + n for n in notas], medidas)
    con_200 = sorted(n for n, p in paginas.items() if isinstance(p, dict) and p.get("con") == 200)
    return ctx.terminar(_comun.PASA, "%d página(s) responden 200 con el plugin activo (%s) y el registro no gana nada" % (
        len(con_200), ", ".join(con_200)), ["nota: " + n for n in notas], medidas)


if __name__ == "__main__":
    sys.exit(_comun.ejecutar("humo", puerta))
