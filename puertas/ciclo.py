"""AIFEC — fábrica de plugins: puerta «ciclo» (entra y sale limpio).

Instala el candidato en el banco y lanza `_ciclo.php`, que con el gestor de plugins del sistema lo activa, lo
desactiva, lo vuelve a activar y lo desinstala sin conservar datos, apuntando las tablas y los ajustes del sitio
antes, durante y después. Pasa si las tablas que aparecen al activar son exactamente las que declara
`contract.tables`, si desactivar conserva los datos, si reactivar no cambia el esquema y si, tras desinstalar,
el sitio queda como estaba. Al acabar quita el candidato del banco: no deja un plugin puesto para las siguientes.

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
        codigo, texto = _comun.lanzar_php(ctx, "_ciclo.php", ["--banco", ctx.banco, "--id", ctx.slug], 10, "ciclo")
    finally:
        _comun.retirar_del_banco(ctx)
    if codigo == _comun.procesos.TIEMPO_AGOTADO:
        raise _comun.NoPasa("el ciclo se pasó del tiempo y se cortó")
    ultima = (texto.strip().splitlines() or ["sin mensaje"])[-1][:200]
    if codigo == 2:
        raise _comun.NoAplica("no se puede hacer el ciclo con el banco: %s" % ultima)
    datos = _comun.resultado_de(texto, "CICLO")
    if datos is None:
        raise _comun.NoPasa("el guion del ciclo no dio su resultado (código %s): %s" % (codigo, ultima))
    problemas = [str(p) for p in datos.get("problemas", [])] if isinstance(datos.get("problemas"), list) else []
    pasos = datos.get("pasos") if isinstance(datos.get("pasos"), list) else []
    creadas = datos.get("creadas") if isinstance(datos.get("creadas"), list) else []
    declaradas = datos.get("declaradas") if isinstance(datos.get("declaradas"), list) else []
    medidas = {"pasos": pasos, "tablas_declaradas": len(declaradas), "tablas_creadas": len(creadas),
               "tablas_antes": datos.get("antes"), "tablas_despues": datos.get("despues"), "problemas": len(problemas)}
    notas = [str(n) for n in datos.get("notas", [])] if isinstance(datos.get("notas"), list) else []
    if problemas:
        return ctx.terminar(_comun.NO_PASA, problemas[0], problemas + ["nota: " + n for n in notas], medidas)
    return ctx.terminar(_comun.PASA, "activa, desactiva, reactiva y desinstala limpio; %d tabla(s) creada(s), las %d declarada(s)" % (
        len(creadas), len(declaradas)), ["nota: " + n for n in notas], medidas)


if __name__ == "__main__":
    sys.exit(_comun.ejecutar("ciclo", puerta))
