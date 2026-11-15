"""AIFEC — fábrica de plugins: prueba de punta a punta, con el sistema real.

Con el motor `simulado` y el esqueleto como origen, `python fabrica.py trabajar --uno` tiene que dejar el encargo en
`hecho`, con su ficha, las siete puertas en el informe (todas «pasa», ninguna «no aplica») y **el banco intacto fuera de
`plugins/<id>`** (y de los datos de su sitio: `sites/` y `public/media/`): la fábrica no ensucia nada más. Y la instalación
de origen **no ha cambiado**: instantánea de fechas y tamaños de toda su carpeta antes y después. También: el plugin de
ejemplo del skill pasa las siete puertas y ninguna puerta lo modifica. Se salta sola si `AIFEC_RUTA` no apunta a una
instalación o no hay un PHP con SQLite.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import ayudas_puertas as ap
from ayudas_puertas import BasePlugins, FabricaReal, PROYECTO, arbol, banco_real, php_de, sistema_disponible

SLUG = "lista-deseos"
PUERTAS = ["sintaxis", "contrato", "pruebas", "traducciones", "ciclo", "humo", "limpieza"]


@unittest.skipUnless(sistema_disponible(), "hace falta AIFEC_RUTA (una instalación de AIFEC) y un PHP con SQLite")
class PruebaDePuntaAPunta(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fab = FabricaReal()
        cls.fab.preparar_banco()
        origen = cls.fab.raiz / "origen" / SLUG
        ap.esqueleto_mod.crear(SLUG, "Lista de deseos", origen)
        versiones = [v for v in (php_de("7.4"), php_de("8.4")) if v]
        cls.fab.escribir_plan({"motor": {"tipo": "simulado", "origen": str(origen)}, "php_versiones": versiones})
        (cls.fab.raiz / "cola.json").write_text(json.dumps([
            {"slug": SLUG, "nombre": "Lista de deseos", "sector": "pruebas", "idea": "idea de prueba",
             "datos": ["customer_id"], "llamadas": "ninguna"}]), encoding="utf-8")
        # instantáneas de antes
        cls.origen_antes = arbol(Path(ap.AIFEC_RUTA))
        cls.ignorar = ("plugins/" + SLUG, "sites", "public/media")
        cls.banco_antes = arbol(cls.fab.banco, ignorar=cls.ignorar)
        cls.codigo, cls.texto = cls.fab.fabrica("trabajar", "--uno")
        cls.origen_despues = arbol(Path(ap.AIFEC_RUTA))
        cls.banco_despues = arbol(cls.fab.banco, ignorar=cls.ignorar)

    @classmethod
    def tearDownClass(cls):
        cls.fab.borrar()

    def estado(self):
        return json.loads((self.fab.raiz / "estado" / "encargos" / (SLUG + ".json")).read_text(encoding="utf-8"))

    def test_el_encargo_queda_hecho(self):
        self.assertEqual(self.codigo, 0, self.texto)
        self.assertEqual(self.estado()["estado"], "hecho", self.texto)
        self.assertIn("HECHO", self.texto.upper())

    def test_deja_su_ficha_en_el_escaparate_con_las_puertas_pasadas(self):
        ficha = json.loads((self.fab.raiz / "escaparate" / SLUG / "ficha.json").read_text(encoding="utf-8"))
        self.assertEqual(ficha["estado"], "hecho")
        self.assertNotEqual(ficha["estado"], "aprobado", "lo que nadie ha mirado no se llama aprobado")
        self.assertEqual(ficha["clase"], "plugins")
        self.assertTrue((self.fab.raiz / "escaparate" / "index.html").is_file())

    def test_el_informe_trae_las_siete_puertas_y_las_siete_pasan_sin_ninguna_no_aplica(self):
        informe = json.loads((self.fab.raiz / "estado" / "encargos" / (SLUG + ".puertas.json")).read_text(encoding="utf-8"))
        estados = {p["nombre"]: p["estado"] for p in informe["puertas"]}
        self.assertEqual(sorted(estados), sorted(PUERTAS))
        for puerta in PUERTAS:
            self.assertEqual(estados[puerta], "pasa", "%s: %s" % (puerta, informe["puertas"]))
        self.assertTrue(informe["pasa"])
        self.assertEqual(informe["linea"], "PUERTAS: 7 de 7 pasan")

    def test_el_plugin_esta_en_salida(self):
        self.assertTrue((self.fab.raiz / "salida" / SLUG / "plugin.json").is_file())

    def test_las_puertas_no_dejan_el_plugin_puesto_en_el_banco(self):
        self.assertFalse((self.fab.banco / "plugins" / SLUG).exists(), "el ciclo y el humo lo quitan al acabar y nadie lo vuelve a poner")

    def test_el_banco_queda_intacto_fuera_de_su_plugin_y_de_sus_datos(self):
        # lo único que se escribe fuera de plugins/<id> son los DATOS del sitio del banco: su base de datos y caché
        # (sites/) y los medios, si se carga una demostración (public/media/)
        diferencias = sorted(k for k in set(self.banco_antes) | set(self.banco_despues) if self.banco_antes.get(k) != self.banco_despues.get(k))
        self.assertEqual(diferencias, [])

    def test_la_instalacion_de_origen_no_ha_cambiado(self):
        diferencias = sorted(k for k in set(self.origen_antes) | set(self.origen_despues) if self.origen_antes.get(k) != self.origen_despues.get(k))
        self.assertEqual(diferencias[:10], [], "%d ficheros distintos en la instalación de origen" % len(diferencias))

    def test_los_otros_plugins_del_banco_no_se_tocan(self):
        self.assertTrue(any(k.startswith("plugins/hello-aifec/") for k in self.banco_despues), "hello-aifec sigue en el banco")


@unittest.skipUnless(sistema_disponible(), "hace falta AIFEC_RUTA (una instalación de AIFEC) y un PHP con SQLite")
class PruebaDelEjemploDelSkill(BasePlugins):
    """El plugin de `skill/ejemplos/lista-deseos/`, hecho siguiendo el skill, pasa las siete puertas con el sistema real."""

    @classmethod
    def setUpClass(cls):
        cls.fab = banco_real()
        versiones = [v for v in (php_de("7.4"), php_de("8.4")) if v]
        cls.fab.escribir_plan({"php_versiones": versiones})

    def test_las_siete_puertas_pasan_y_ninguna_modifica_el_ejemplo(self):
        ejemplo = PROYECTO / "skill" / "ejemplos" / SLUG
        antes = self.instantanea(ejemplo)
        for puerta in PUERTAS:
            with self.subTest(puerta):
                codigo, informe, texto = self.lanzar(puerta, ejemplo, banco=self.fab.banco, plan_ruta=self.fab.plan)
                self.aceptar(codigo, informe, texto, 0)
        self.assertEqual(self.instantanea(ejemplo), antes, "ninguna puerta toca el candidato")

    def test_el_ejemplo_hace_lo_que_dice_en_el_humo_y_el_ciclo(self):
        ejemplo = PROYECTO / "skill" / "ejemplos" / SLUG
        codigo, informe, texto = self.lanzar("ciclo", ejemplo, banco=self.fab.banco, plan_ruta=self.fab.plan)
        self.aceptar(codigo, informe, texto, 0)
        self.assertEqual(informe["medidas"]["tablas_creadas"], 1)
        self.assertEqual(informe["medidas"]["tablas_declaradas"], 1)
        codigo, informe, texto = self.lanzar("pruebas", ejemplo, banco=self.fab.banco, plan_ruta=self.fab.plan)
        self.aceptar(codigo, informe, texto, 0)
        self.assertEqual(informe["medidas"]["ok"], 10)


if __name__ == "__main__":
    unittest.main()
