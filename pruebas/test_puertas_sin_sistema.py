"""AIFEC — fábrica de plugins: pruebas de las puertas que no necesitan el sistema.

`sintaxis`, `limpieza` y la parte de `pruebas` que mira el candidato trabajan solo con PHP y los ficheros del plugin.
`contrato` y `traducciones` se prueban con un «sistema» de mentira (un `aifec` escrito en Python que contesta lo que
la prueba diga): aquí se comprueba **cómo se lee su veredicto**. Cada puerta se prueba con el esqueleto (sale con 0) y
con el esqueleto estropeado para esa puerta (sale con 1 y dice por qué). Las puertas no modifican el candidato.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import sys
import unittest

import ayudas_puertas as ap
from ayudas_puertas import BasePlugins, montar_sistema_de_mentira, php_cualquiera, php_de

import _comun  # noqa: E402  (puertas/_comun.py)


@unittest.skipUnless(php_cualquiera(), "hace falta un PHP")
class PruebasDeSintaxis(BasePlugins):
    def test_el_esqueleto_pasa_con_el_php_del_plan(self):
        codigo, informe, texto = self.lanzar("sintaxis", self.plugin())
        self.aceptar(codigo, informe, texto, 0)
        self.assertEqual(informe["medidas"]["ficheros"], 7)
        self.assertEqual(informe["medidas"]["problemas"], 0)

    @unittest.skipUnless(php_de("7.4"), "hace falta PHP 7.4")
    def test_un_match_de_php8_no_compila_en_php74(self):
        plugin = self.plugin()
        self.cambiar(plugin, "src/Notes.php", "return $row !== null && trim((string) $row['note']) !== ''",
                     "return match (true) { $row !== null && trim((string) $row['note']) !== '' => (string) $row['note'], default => $default };\n        return $row !== null && trim((string) $row['note']) !== ''")
        codigo, informe, texto = self.lanzar("sintaxis", plugin, plan={"php_versiones": [php_de("7.4")]})
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("src/Notes.php", informe["resumen"])
        self.assertIn("php-7.4", informe["resumen"])
        self.assertIn("Parse error", informe["resumen"])

    @unittest.skipUnless(php_de("8.4"), "hace falta PHP 8.4")
    def test_el_nullable_implicito_avisa_en_php84_aunque_php_l_salga_con_cero(self):
        plugin = self.plugin()
        self.cambiar(plugin, "src/Notes.php", "public function get(int $productId): string", "public function get(int $productId, string $extra = null): string")
        codigo, informe, texto = self.lanzar("sintaxis", plugin, plan={"php_versiones": [php_de("8.4")]})
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("Deprecated", informe["resumen"])
        self.assertIn("php-8.4", informe["resumen"])

    def test_un_php_del_plan_que_no_existe_se_dice_y_no_pasa(self):
        codigo, informe, texto = self.lanzar("sintaxis", self.plugin(), plan={"php_versiones": ["php-que-no-existe-9.9"]})
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("no encuentro el PHP «php-que-no-existe-9.9»", informe["resumen"])

    def test_sin_php_en_el_plan_la_puerta_no_aplica(self):
        codigo, informe, texto = self.lanzar("sintaxis", self.plugin(), plan={"php": "php-que-no-existe-9.9"})
        self.aceptar(codigo, informe, texto, 2)
        self.assertTrue(informe["ok"], "un «no aplica» no es un fallo")


class PruebasDeLimpieza(BasePlugins):
    def test_el_esqueleto_esta_limpio(self):
        codigo, informe, texto = self.lanzar("limpieza", self.plugin())
        self.aceptar(codigo, informe, texto, 0)
        self.assertEqual(informe["medidas"]["ficheros"], 9)

    def test_una_clave_con_pinta_de_real_no_pasa(self):
        casos = (
            ("hex en un array", "'api_secret' => 'a1b2c3d4e5f60718293a4b5c6d7e8f90',"),
            ("base64 en una asignación", "$token = 'Zm9vYmFyMTIzNDU2Nzg5MGFiY2RlZg==';"),
            ("clave de GitHub", "// ghp_" + "a" * 4 + "B1c2D3e4F5g6H7i8J9k0L1m2N3o4P5q6R7s8"),
        )
        for numero, (nombre, linea) in enumerate(casos):
            with self.subTest(nombre):
                plugin = self.plugin(slug="plugin-%d" % numero)
                texto = (plugin / "hooks.php").read_text(encoding="utf-8")
                (plugin / "hooks.php").write_bytes((texto + "\n" + linea + "\n").encode("utf-8"))
                codigo, informe, salida = self.lanzar("limpieza", plugin)
                self.aceptar(codigo, informe, salida, 1)
                self.assertIn("hooks.php", informe["resumen"])
                self.assertRegex(informe["resumen"], r"clave|token|«ghp_")

    def test_lo_que_se_parece_a_una_clave_pero_no_lo_es_pasa(self):
        plugin = self.plugin()
        extra = ("$ejemplos = ['password' => 'clave-de-mentira', 'token_label' => 'Etiqueta del token',\n"
                 "    'api_key' => 'tu-clave-aqui-de-ejemplo-123456', 'secret_name' => 'solo_letras_minusculas_y_guiones'];\n")
        texto = (plugin / "hooks.php").read_text(encoding="utf-8")
        (plugin / "hooks.php").write_bytes((texto + extra).encode("utf-8"))
        codigo, informe, salida = self.lanzar("limpieza", plugin)
        self.aceptar(codigo, informe, salida, 0)

    def test_un_correo_que_no_es_de_ejemplo_no_pasa_y_los_de_ejemplo_si(self):
        plugin = self.plugin()
        (plugin / "LEEME.md").write_bytes((plugin / "LEEME.md").read_bytes() + b"\nEscribe a ana@cliente.test, a x@example.com o a juan@tienda.invalid.\n")
        codigo, informe, salida = self.lanzar("limpieza", plugin)
        self.aceptar(codigo, informe, salida, 0)
        (plugin / "LEEME.md").write_bytes((plugin / "LEEME.md").read_bytes() + b"Soporte: soporte@empresa-de-verdad.com\n")
        codigo, informe, salida = self.lanzar("limpieza", plugin)
        self.aceptar(codigo, informe, salida, 1)
        self.assertIn("soporte@empresa-de-verdad.com", informe["resumen"])
        self.assertIn("LEEME.md", informe["resumen"])

    def test_el_correo_de_la_linea_author_de_una_cabecera_no_cuenta(self):
        codigo, informe, salida = self.lanzar("limpieza", self.plugin())
        self.aceptar(codigo, informe, salida, 0)
        self.assertIn("ecomyseo@gmail.com", (self.salida / "lista-deseos" / "hooks.php").read_text(encoding="utf-8"))

    def test_los_ficheros_de_sobra_no_pasan(self):
        casos = (
            ("paquete comprimido", "src/paquete.zip", "un paquete comprimido"),
            ("dependencias", "vendor/autoload.php", "carpeta que no es de un plugin"),
            ("composer", "src/composer.json", "un fichero de otra cosa"),
            ("captura", "assets/../captura.png", "no es una pieza de un plugin"),
            ("mapa de código", "assets/app.js.map", "un fichero de trabajo"),
            ("registro", "src/error.log", "un fichero de trabajo"),
        )
        for numero, (nombre, ruta, motivo) in enumerate(casos):
            with self.subTest(nombre):
                plugin = self.plugin(slug="sobra-%d" % numero)
                destino = plugin / ruta.replace("assets/../", "")
                self.escribir(destino, "x")
                codigo, informe, salida = self.lanzar("limpieza", plugin)
                self.aceptar(codigo, informe, salida, 1)
                self.assertIn(motivo, self.texto_del_informe(informe))

    def test_las_cabeceras_mal_puestas_no_pasan(self):
        casos = (
            ("línea en blanco tras <?php", "src/Notes.php", "<?php\n/**", "<?php\n\n/**", "tiene que ir enseguida el bloque"),
            ("sin license", "src/Notes.php", " * @license   Ver LICENSE.md\n", "", "@author» y «@license"),
            ("sin strict_types", "src/Notes.php", "declare(strict_types=1);\n", "", "declare(strict_types=1)"),
        )
        for numero, (nombre, relativa, viejo, nuevo, motivo) in enumerate(casos):
            with self.subTest(nombre):
                plugin = self.plugin(slug="cabecera-%d" % numero)
                self.cambiar(plugin, relativa, viejo, nuevo)
                codigo, informe, salida = self.lanzar("limpieza", plugin)
                self.aceptar(codigo, informe, salida, 1)
                self.assertIn(motivo, self.texto_del_informe(informe))

    def test_una_marca_bom_delante_de_php_no_pasa(self):
        plugin = self.plugin()
        ruta = plugin / "src" / "Notes.php"
        ruta.write_bytes(b"\xef\xbb\xbf" + ruta.read_bytes())
        codigo, informe, salida = self.lanzar("limpieza", plugin)
        self.aceptar(codigo, informe, salida, 1)
        self.assertIn("BOM", informe["resumen"])


class PruebasDeLaPuertaPruebas(BasePlugins):
    """La puerta `pruebas` decide sobre el candidato antes de necesitar el banco: sin pruebas o con pocas, no pasa."""

    def test_un_plugin_sin_pruebas_no_pasa(self):
        plugin = self.plugin()
        _comun.borrar(plugin / "tests")
        codigo, informe, salida = self.lanzar("pruebas", plugin)
        self.aceptar(codigo, informe, salida, 1)
        self.assertIn("no trae pruebas", informe["resumen"])

    def test_un_plugin_con_menos_de_cuatro_pruebas_no_pasa(self):
        plugin = self.plugin()
        ruta = plugin / "tests" / "ListaDeseosTest.php"
        texto = ruta.read_text(encoding="utf-8")
        corte = texto.index("test('lista-deseos usa la nota del ajuste")
        ruta.write_bytes(texto[:corte].encode("utf-8"))
        codigo, informe, salida = self.lanzar("pruebas", plugin)
        self.aceptar(codigo, informe, salida, 1)
        self.assertRegex(informe["resumen"], r"declara 3 prueba\(s\) y hacen falta al menos 4")

    def test_con_pruebas_suficientes_pero_sin_banco_la_puerta_no_aplica(self):
        codigo, informe, salida = self.lanzar("pruebas", self.plugin())
        self.aceptar(codigo, informe, salida, 2)
        self.assertIn("banco de pruebas no está preparado", informe["resumen"])


class PruebasConUnSistemaDeMentira(BasePlugins):
    def lanzar(self, puerta, plugin, **kwargs):
        # el `aifec` de mentira es un guion de Python: se lanza con el Python de la prueba en vez de con PHP
        kwargs["plan"] = dict(kwargs.get("plan") or {}, php=sys.executable)
        return super().lanzar(puerta, plugin, **kwargs)

    def _montar(self, modo="ok"):
        montar_sistema_de_mentira(self.banco, modo)
        return self.plugin()

    def test_el_contrato_pasa_cuando_contract_check_sale_sin_errores(self):
        plugin = self._montar("ok")
        codigo, informe, texto = self.lanzar("contrato", plugin)
        self.aceptar(codigo, informe, texto, 0)
        self.assertIn("puntuación 96", informe["resumen"])
        self.assertTrue((self.banco / "plugins" / plugin.name / "plugin.json").is_file(), "el candidato se instala en el banco")
        self.assertIn("contract:check %s" % plugin.name, (self.banco / "llamadas.log").read_text(encoding="utf-8"))

    def test_el_contrato_no_pasa_y_cuenta_el_error_con_su_motivo(self):
        plugin = self._montar("falla")
        codigo, informe, texto = self.lanzar("contrato", plugin)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("api.ajeno.test", informe["resumen"])
        self.assertFalse(informe["ok"])
        self.assertEqual(informe["medidas"]["errores"], 1)
        self.assertEqual(informe["medidas"]["puntuacion"], 80)

    def test_un_contract_check_que_no_da_veredicto_no_pasa(self):
        plugin = self._montar("mudo")
        codigo, informe, texto = self.lanzar("contrato", plugin)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("sin dar su veredicto", informe["resumen"])

    def test_si_el_sistema_no_trae_la_orden_la_puerta_sale_con_dos_y_no_la_imita(self):
        plugin = self._montar("sin_ordenes")
        for puerta in ("contrato", "traducciones"):
            codigo, informe, texto = self.lanzar(puerta, plugin)
            self.aceptar(codigo, informe, texto, 2)
            self.assertIn("no se imita su comprobación", informe["resumen"])
            self.assertTrue(informe["ok"], "un «no aplica» no es un fallo")

    def test_sin_banco_preparado_las_puertas_que_lo_necesitan_salen_con_dos(self):
        plugin = self.plugin()
        for puerta in ("contrato", "traducciones", "ciclo", "humo"):
            codigo, informe, texto = self.lanzar(puerta, plugin)
            self.aceptar(codigo, informe, texto, 2)
            self.assertIn("banco de pruebas no está preparado", informe["resumen"])

    def test_las_traducciones_pasan_con_cero_cadenas_sin_traducir(self):
        plugin = self._montar("ok")
        codigo, informe, texto = self.lanzar("traducciones", plugin)
        self.aceptar(codigo, informe, texto, 0)
        self.assertEqual(informe["medidas"]["faltan"], 0)
        self.assertEqual(informe["medidas"]["cadenas"], 6)
        self.assertIn("i18n:check plugins/%s es" % plugin.name, (self.banco / "llamadas.log").read_text(encoding="utf-8"))

    def test_las_traducciones_enseñan_las_cadenas_que_faltan(self):
        plugin = self._montar("falla")
        codigo, informe, texto = self.lanzar("traducciones", plugin)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("2 cadena(s) sin traducir de 6", informe["resumen"])
        self.assertIn("Sold out", self.texto_del_informe(informe))

    def test_las_puertas_no_modifican_el_candidato(self):
        plugin = self._montar("ok")
        antes = self.instantanea(plugin)
        for puerta in ("sintaxis", "limpieza", "contrato", "traducciones", "pruebas", "ciclo", "humo"):
            self.lanzar(puerta, plugin)
            self.assertEqual(self.instantanea(plugin), antes, "la puerta «%s» ha tocado el candidato" % puerta)


class PruebasDeLosApoyos(unittest.TestCase):
    def test_la_declaracion_del_contrato_se_lee_aunque_este_mal_formada(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta)
            (ruta / "plugin.json").write_text('{"contract": {"hosts": ["api.ejemplo.test"], "tables": "no-es-lista", "personal_data": [1, "email"]}}', encoding="utf-8")
            declaracion = _comun.declaracion(ruta)
            self.assertEqual(declaracion["hosts"], ["api.ejemplo.test"])
            self.assertEqual(declaracion["tables"], [])
            self.assertEqual(declaracion["personal_data"], ["email"])
            self.assertEqual(declaracion["capabilities"], [])
            (ruta / "plugin.json").write_text("esto no es JSON", encoding="utf-8")
            self.assertEqual(_comun.declaracion(ruta), {"hosts": [], "personal_data": [], "tables": [], "capabilities": []})

    def test_el_resultado_de_un_guion_de_php_sale_de_su_ultima_linea_con_marca(self):
        texto = 'ruido\nCICLO {"ok": false}\nmas ruido\nCICLO {"ok": true, "pasos": ["a"]}\nfin\n'
        self.assertEqual(_comun.resultado_de(texto, "CICLO"), {"ok": True, "pasos": ["a"]})
        self.assertIsNone(_comun.resultado_de("sin marca\n", "CICLO"))
        self.assertIsNone(_comun.resultado_de("CICLO {esto no es json}\n", "CICLO"))
        self.assertIsNone(_comun.resultado_de('HUMO {"ok": true}\n', "CICLO"))


if __name__ == "__main__":
    unittest.main()
