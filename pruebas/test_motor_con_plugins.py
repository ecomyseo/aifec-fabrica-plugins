"""AIFEC — fábrica de plugins: el motor copiado de la fábrica de temas, funcionando con la configuración de ESTA fábrica.

Con un «sistema» de mentira y puertas de mentira (nada de PHP, nada de IA): el ciclo de un encargo con el `fabrica.json`
real de la fábrica de plugins (el esqueleto sale de `plugin:create`, el manifiesto es `plugin.json`, se instala en
`plugins/`), y el encargo que recibe el motor, escrito con la plantilla real de esta fábrica. Las pruebas del motor en sí
(estado, plan, cola, procesos, reintentos) son las de la fábrica de temas: es el mismo código byte a byte.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import json
import shutil
import unittest

from ayudas import Base, PROYECTO
from motor import nucleo, plan as plan_mod


class PruebasDelCicloConPlugins(Base):
    def montar_de_plugins(self, **kwargs):
        config = {clave: valor for clave, valor in plan_mod.cargar_config(PROYECTO).items()}
        return self.montar(clase="plugins", config=config, **kwargs)

    def test_un_encargo_feliz_queda_hecho_con_su_ficha_y_sus_puertas(self):
        self.montar_de_plugins()
        ctx = self.abrir()
        codigo, linea = nucleo.trabajar(ctx)
        self.assertEqual(codigo, 0, linea)
        self.assertEqual(ctx.cola.estado("uno")["estado"], "hecho")
        self.assertTrue((self.raiz / "salida" / "uno" / "plugin.json").is_file())
        ficha = json.loads((self.raiz / "escaparate" / "uno" / "ficha.json").read_text(encoding="utf-8"))
        self.assertEqual(ficha["clase"], "plugins")
        self.assertEqual(ficha["estado"], "hecho")
        self.assertNotEqual(ficha["estado"], "aprobado", "lo que nadie ha mirado no se llama aprobado")
        ficha_md = (self.raiz / "escaparate" / "uno" / "ficha.md").read_text(encoding="utf-8")
        self.assertIn("Qué hace: pruebas", ficha_md)
        self.assertIn("(plugins)", ficha_md)

    def test_el_esqueleto_se_pide_a_plugin_create_con_el_slug_y_el_nombre_del_encargo(self):
        self.montar_de_plugins(motor="manual")
        ctx = self.abrir()
        nucleo.ciclo(ctx, "uno")
        self.assertTrue((self.raiz / "salida" / "uno" / "plugin.json").is_file())
        llamadas = (self.raiz / "estado" / "banco" / "argv.log").read_text(encoding="utf-8")
        self.assertIn('"plugin:create", "uno", "--name=Encargo uno"', llamadas)

    def test_un_candidato_sin_plugin_json_se_rechaza_y_dice_cual_falta(self):
        self.montar_de_plugins(plan={"intentos": 1})
        for fichero in (self.tmp / "origen").glob("plugin.json"):
            fichero.unlink()
        self.modo("aifec", "sin_esqueleto")
        ctx = self.abrir()
        resultado, mensaje = nucleo.ciclo(ctx, "uno")
        self.assertEqual(resultado, "atascado")
        self.assertIn("falta plugin.json", mensaje)

    def test_el_encargo_que_recibe_el_motor_pide_la_declaracion_del_contrato_primero(self):
        self.montar_de_plugins(encargos=("uno",))
        (self.raiz / "skill").mkdir()
        shutil.copy2(str(PROYECTO / "skill" / "SKILL.md"), str(self.raiz / "skill" / "SKILL.md"))
        codigo, texto = self.cli("encargo", "uno")
        self.assertEqual(codigo, 0, texto)
        for trozo in ("Fábrica de plugins de AIFEC", "fabricas plugins de AIFEC", "salida/uno/", "plugin.json", "`plugins/`",
                      "estado/banco/", "python fabrica.py puertas uno", "`contract.personal_data`", "`contract.hosts`",
                      "`contract.tables`", "antes de escribir una línea de código", "Lo que ya existe", "Lo que falló la vez anterior",
                      "recorrer históricos", "skill/SKILL.md"):
            self.assertIn(trozo, texto)
        self.assertNotIn("{{", texto, "no se queda ninguna marca sin rellenar")

    def test_instalar_copia_el_plugin_a_plugins_de_una_instalacion_y_no_pisa_sin_forzar(self):
        self.montar_de_plugins()
        destino = self.tmp / "instalacion"
        (destino / "core").mkdir(parents=True)
        (destino / "core" / "bootstrap.php").write_text("<?php")
        (destino / "aifec").write_text("<?php")
        codigo, salida = self.cli("instalar", "uno", "--en", str(destino))
        self.assertEqual(codigo, 1)
        self.assertIn("solo se instala lo que está hecho o aprobado", salida)
        self.cli("trabajar")
        codigo, salida = self.cli("instalar", "uno", "--en", str(destino))
        self.assertEqual(codigo, 0, salida)
        self.assertTrue((destino / "plugins" / "uno" / "plugin.json").is_file())
        self.assertFalse((destino / "themes").exists(), "un plugin no va a themes/")
        codigo, _ = self.cli("instalar", "uno", "--en", str(destino))
        self.assertEqual(codigo, 1, "no pisa lo que ya hay sin --forzar")


if __name__ == "__main__":
    unittest.main()
