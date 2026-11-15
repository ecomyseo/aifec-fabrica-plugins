"""AIFEC — fábrica de plugins: las siete puertas contra el sistema real.

«Con sistema»: se saltan solas si `AIFEC_RUTA` no apunta a una instalación de AIFEC o no hay un PHP con SQLite.
Cada puerta con el esqueleto da 0 y, con el mismo plugin estropeado **para esa puerta**, da 1 con su motivo. Las
mutaciones comprueban que se aplican (`cambiar` falla si el trozo no está): una mutación que no se aplica no demuestra
nada. Todas comparten un único banco real por proceso; lo que una mutación deja en su base de datos (una tabla que
nadie declara, un ajuste huérfano) se quita al acabar la prueba, para que no cuente en las demás.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path

from ayudas_puertas import BasePlugins, banco_real, php_de, sistema_disponible

CABECERA_PHP = """<?php
/**
 * Migración de prueba.
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   Ver LICENSE.md
 */

declare(strict_types=1);

use Aifec\\Db\\Db;
use Aifec\\Db\\Schema;
use Aifec\\Db\\TableDef;

"""

MIGRACION_TABLA_EXTRA = CABECERA_PHP + """return static function (Schema $schema, Db $db): void {
    $schema->create('lista_deseos_extra', static function (TableDef $t): void {
        $t->bigInteger('product_id');
        $t->primary(['product_id']);
    });
};
"""

MIGRACION_AJUSTE_HUERFANO = CABECERA_PHP + """return static function (Schema $schema, Db $db): void {
    $db->upsert('settings', ['k' => 'otro_plugin.valor', 'v' => '"1"'], ['k']);
};
"""


@unittest.skipUnless(sistema_disponible(), "hace falta AIFEC_RUTA (una instalación de AIFEC) y un PHP con SQLite")
class PuertasConElSistemaReal(BasePlugins):
    @classmethod
    def setUpClass(cls):
        cls.fab = banco_real()
        versiones = [v for v in (php_de("7.4"), php_de("8.4")) if v]
        cls.fab.escribir_plan({"php_versiones": versiones})

    def real(self, puerta, plugin):
        return self.lanzar(puerta, plugin, banco=self.fab.banco, plan_ruta=self.fab.plan)

    def anadir_a_hooks(self, plugin, codigo):
        """Mete código dentro de la función de `hooks.php`, antes de que se cierre."""
        ruta = plugin / "hooks.php"
        texto = ruta.read_text(encoding="utf-8")
        self.assertTrue(texto.endswith("};\n"), "el cierre de hooks.php no es el que espera la prueba")
        ruta.write_bytes((texto[: -len("};\n")] + codigo + "};\n").encode("utf-8"))

    def base_de_datos(self) -> Path:
        encontradas = sorted((self.fab.banco / "sites").glob("*/db.sqlite"))
        self.assertTrue(encontradas, "no encuentro la base de datos del sitio del banco")
        return encontradas[0]

    def limpiar_banco(self, tablas=(), ajustes=()):
        """Quita de la base de datos del banco lo que una mutación dejó (el prefijo del sitio del banco es `af_`)."""
        conexion = sqlite3.connect(str(self.base_de_datos()))
        try:
            for tabla in tablas:
                conexion.execute("DROP TABLE IF EXISTS af_%s" % tabla)
            for ajuste in ajustes:
                conexion.execute("DELETE FROM af_settings WHERE k = ?", (ajuste,))
            conexion.commit()
        finally:
            conexion.close()

    def tablas_del_banco(self) -> set:
        conexion = sqlite3.connect(str(self.base_de_datos()))
        try:
            return {fila[0] for fila in conexion.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        finally:
            conexion.close()

    # ---- el esqueleto pasa las siete -----------------------------------------------------------

    def test_sintaxis_con_el_esqueleto(self):
        self.aceptar(*self.real("sintaxis", self.plugin()), 0)

    def test_contrato_con_el_esqueleto(self):
        codigo, informe, texto = self.real("contrato", self.plugin())
        self.aceptar(codigo, informe, texto, 0)
        self.assertEqual(informe["medidas"]["puntuacion"], 100)
        self.assertEqual(informe["medidas"]["errores"], 0)

    def test_pruebas_con_el_esqueleto(self):
        codigo, informe, texto = self.real("pruebas", self.plugin())
        self.aceptar(codigo, informe, texto, 0)
        self.assertGreaterEqual(informe["medidas"]["ok"], 4)
        self.assertEqual(informe["medidas"]["fallan"], 0)

    def test_traducciones_con_el_esqueleto(self):
        codigo, informe, texto = self.real("traducciones", self.plugin())
        self.aceptar(codigo, informe, texto, 0)
        self.assertEqual(informe["medidas"]["faltan"], 0)

    def test_ciclo_con_el_esqueleto(self):
        codigo, informe, texto = self.real("ciclo", self.plugin())
        self.aceptar(codigo, informe, texto, 0)
        self.assertEqual(informe["medidas"]["pasos"], ["activar: bien", "desactivar: bien", "reactivar: bien", "desinstalar: bien"])
        self.assertEqual(informe["medidas"]["tablas_creadas"], 1)
        self.assertEqual(informe["medidas"]["tablas_antes"], informe["medidas"]["tablas_despues"])

    def test_humo_con_el_esqueleto(self):
        codigo, informe, texto = self.real("humo", self.plugin())
        self.aceptar(codigo, informe, texto, 0)
        for pagina in ("portada", "listado", "ficha", "carrito", "escritorio"):
            self.assertEqual(informe["medidas"]["paginas"][pagina]["con"], 200, pagina)

    def test_limpieza_con_el_esqueleto(self):
        self.aceptar(*self.real("limpieza", self.plugin()), 0)

    def test_el_ciclo_y_el_humo_quitan_el_candidato_del_banco_al_acabar(self):
        plugin = self.plugin()
        for puerta in ("contrato", "traducciones", "pruebas"):
            self.aceptar(*self.real(puerta, plugin), 0)
        self.assertTrue((self.fab.banco / "plugins" / plugin.name).is_dir(), "estas tres lo instalan en el banco para trabajar")
        for puerta in ("ciclo", "humo"):
            self.aceptar(*self.real(puerta, plugin), 0)
            self.assertFalse((self.fab.banco / "plugins" / plugin.name).exists(), "«%s» tiene que dejar el banco sin el candidato" % puerta)
        # y una pasada nueva del ciclo parte de cero y pasa
        self.aceptar(*self.real("ciclo", plugin), 0)

    # ---- el esqueleto estropeado, puerta a puerta ------------------------------------------------

    def test_contrato_caza_una_llamada_a_un_dominio_no_declarado(self):
        plugin = self.plugin()
        self.anadir_a_hooks(plugin, "    $app->hooks()->on('order.paid', static function (array $order) use ($app): void {\n"
                                   "        $app->http()->get('https://api.dominio-ajeno.test/v1/avisar');\n    });\n")
        codigo, informe, texto = self.real("contrato", plugin)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("api.dominio-ajeno.test", self.texto_del_informe(informe))
        self.assertGreaterEqual(informe["medidas"]["errores"], 1)

    def test_contrato_caza_codigo_prohibido(self):
        plugin = self.plugin()
        self.anadir_a_hooks(plugin, "    $app->hooks()->on('order.paid', static function (array $order): void {\n        shell_exec('ls');\n    });\n")
        codigo, informe, texto = self.real("contrato", plugin)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("shell_exec", self.texto_del_informe(informe))

    def test_pruebas_caza_una_prueba_que_falla(self):
        plugin = self.plugin()
        self.cambiar(plugin, "tests/ListaDeseosTest.php", "same('Montaje incluido', $notes->get($id));", "same('otra cosa', $notes->get($id));")
        codigo, informe, texto = self.real("pruebas", plugin)
        self.aceptar(codigo, informe, texto, 1)
        self.assertRegex(informe["resumen"], r"\d+ prueba\(s\) fallan")
        self.assertIn("guarda la nota de un producto", self.texto_del_informe(informe))

    def test_traducciones_caza_una_cadena_sin_traducir(self):
        plugin = self.plugin()
        self.cambiar(plugin, "views/front/note.php", "<?= e(t('Note')) ?>:", "<?= e(t('Note')) ?> <?= e(t('Brand new text')) ?>:")
        codigo, informe, texto = self.real("traducciones", plugin)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("1 cadena(s) sin traducir", informe["resumen"])
        self.assertIn("Brand new text", self.texto_del_informe(informe))

    def test_ciclo_caza_una_tabla_creada_y_no_declarada_y_que_se_queda_tras_desinstalar(self):
        self.addCleanup(self.limpiar_banco, ("lista_deseos_extra",))
        plugin = self.plugin()
        self.escribir(plugin / "migrations" / "0002_extra.php", MIGRACION_TABLA_EXTRA)
        codigo, informe, texto = self.real("ciclo", plugin)
        self.aceptar(codigo, informe, texto, 1)
        detalle = self.texto_del_informe(informe)
        self.assertIn("crea la tabla «lista_deseos_extra» y no la declara", detalle)
        self.assertIn("se queda la tabla «lista_deseos_extra»", detalle)
        self.assertIn("af_lista_deseos_extra", self.tablas_del_banco(), "la tabla de más sigue en el banco: es justo lo que la puerta ha cazado")

    def test_ciclo_caza_una_tabla_declarada_que_no_se_crea(self):
        plugin = self.plugin()
        self.cambiar(plugin, "plugin.json", '"tables": ["lista_deseos_notes"]', '"tables": ["lista_deseos_notes", "lista_deseos_fantasma"]')
        codigo, informe, texto = self.real("ciclo", plugin)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("declara la tabla «lista_deseos_fantasma»", informe["resumen"])

    def test_ciclo_caza_un_ajuste_que_queda_tras_desinstalar(self):
        self.addCleanup(self.limpiar_banco, (), ("otro_plugin.valor",))
        plugin = self.plugin()
        self.escribir(plugin / "migrations" / "0002_ajuste.php", MIGRACION_AJUSTE_HUERFANO)
        codigo, informe, texto = self.real("ciclo", plugin)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("se queda el ajuste «otro_plugin.valor»", self.texto_del_informe(informe))

    def test_el_ciclo_se_recupera_de_una_pasada_anterior_cortada_a_medias(self):
        # Se deja el banco como lo dejaría un corte a mitad del ciclo: plugin instalado, activo y con su tabla.
        plugin = self.plugin()
        self.aceptar(*self.real("contrato", plugin), 0)  # instala el candidato en el banco
        conexion = sqlite3.connect(str(self.base_de_datos()))
        try:
            conexion.execute("CREATE TABLE IF NOT EXISTS af_lista_deseos_notes (product_id INTEGER PRIMARY KEY, note TEXT, updated_at TEXT)")
            conexion.commit()
        finally:
            conexion.close()
        codigo, informe, texto = self.real("ciclo", plugin)
        self.aceptar(codigo, informe, texto, 0)
        self.assertIn("quedaba la tabla «lista_deseos_notes» de una pasada anterior", self.texto_del_informe(informe))

    def test_humo_caza_un_aviso_de_php_en_la_portada(self):
        plugin = self.plugin()
        self.anadir_a_hooks(plugin, "    $app->hooks()->slot('home.top', static function (): string {\n"
                                   "        $vacio = [];\n\n        return (string) $vacio['no-existe'];\n    });\n")
        codigo, informe, texto = self.real("humo", plugin)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("aviso de PHP nuevo con el plugin", informe["resumen"])
        self.assertIn("no-existe", informe["resumen"])

    def test_humo_caza_un_oyente_que_lanza_porque_el_registro_gana_una_linea(self):
        plugin = self.plugin()
        self.anadir_a_hooks(plugin, "    $app->hooks()->slot('home.top', static function (): string {\n"
                                   "        throw new \\RuntimeException('el oyente revienta');\n    });\n")
        codigo, informe, texto = self.real("humo", plugin)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("el registro del sitio gana una línea nueva con el plugin", informe["resumen"])
        self.assertIn("el oyente revienta", informe["resumen"])


if __name__ == "__main__":
    unittest.main()
