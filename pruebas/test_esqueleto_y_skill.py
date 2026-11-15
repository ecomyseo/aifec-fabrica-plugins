"""AIFEC — fábrica de plugins: pruebas del esqueleto, del skill y de los ejemplos que lo acompañan.

El esqueleto se convierte en un plugin con sus marcas sustituidas (en el contenido y en los nombres de fichero); el skill
tiene menos de 250 líneas, sus diez fases en orden, las puertas bloqueantes y todos los ficheros que nombra; la cola de
ejemplo trae tres encargos completos; y el plugin de ejemplo (`skill/ejemplos/lista-deseos/`) declara y trae lo que dice.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest

import ayudas_puertas as ap
from ayudas_puertas import BasePlugins, PROYECTO

SKILL = PROYECTO / "skill"
EJEMPLO = SKILL / "ejemplos" / "lista-deseos"


class PruebasEsqueleto(BasePlugins):
    def test_las_marcas_se_sustituyen_en_el_contenido_y_en_los_nombres_y_no_queda_ninguna(self):
        plugin = self.plugin("lista-deseos", "Lista de deseos")
        nombres = sorted(p.relative_to(plugin).as_posix() for p in plugin.rglob("*") if p.is_file())
        self.assertEqual(nombres, ["LEEME.md", "hooks.php", "lang/es.php", "migrations/0001_notes.php", "plugin.json",
                                   "settings.php", "src/Notes.php", "tests/ListaDeseosTest.php", "views/front/note.php"])
        for ruta in plugin.rglob("*"):
            if ruta.is_file():
                texto = ruta.read_text(encoding="utf-8")
                for marca in ("__id__", "__id_bajo__", "__Nombre__", "__Espacio__", "{{"):
                    self.assertNotIn(marca, texto, "%s lleva la marca %s" % (ruta.name, marca))

    def test_el_manifiesto_sale_con_el_nombre_el_espacio_y_la_tabla_del_identificador(self):
        plugin = self.plugin("lista-deseos", "Lista de deseos")
        manifiesto = json.loads((plugin / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifiesto["name"], "Lista de deseos")
        self.assertEqual(manifiesto["namespace"], "Plugins\\ListaDeseos")
        self.assertEqual(manifiesto["contract"]["tables"], ["lista_deseos_notes"])
        self.assertEqual(manifiesto["contract"]["hosts"], [])
        self.assertEqual(manifiesto["contract"]["capabilities"], [])
        self.assertRegex(manifiesto["version"], r"^\d+\.\d+\.\d+$")
        self.assertIn("namespace Plugins\\ListaDeseos;", (plugin / "src" / "Notes.php").read_text(encoding="utf-8"))
        self.assertIn("'lista-deseos::front/note'", (plugin / "hooks.php").read_text(encoding="utf-8"))
        self.assertIn("lista_deseos_general", (plugin / "settings.php").read_text(encoding="utf-8"))

    def test_un_identificador_de_una_sola_palabra_y_otro_con_cifras_dan_su_espacio_de_nombres(self):
        self.assertEqual(ap.esqueleto_mod.marcas_de("recogida", "Recogida")["__Espacio__"], "Recogida")
        marcas = ap.esqueleto_mod.marcas_de("aviso-stock-24h", "Aviso")
        self.assertEqual(marcas["__Espacio__"], "AvisoStock24h")
        self.assertEqual(marcas["__id_bajo__"], "aviso_stock_24h")

    def test_los_identificadores_y_nombres_que_no_valen_se_rechazan(self):
        for mal in ("Lista", "lista_deseos", "1lista", "-lista", "lista-", "lista--deseos", "a", "x" * 41, "lista deseos"):
            with self.assertRaises(ValueError, msg=mal):
                ap.esqueleto_mod.marcas_de(mal, "Nombre")
        for mal in ("", "   ", "N" * 61, "Pérez's", 'Dice "hola"', "Ruta\\mala", "Precio $5", "<b>", "Cierra */ ya", "Llave {x}"):
            with self.assertRaises(ValueError, msg=mal):
                ap.esqueleto_mod.marcas_de("lista-deseos", mal)

    def test_un_nombre_con_tildes_eñes_y_ampersand_deja_un_json_valido_y_php_correcto(self):
        plugin = self.plugin("pedidos-nandu", "Pérez & Hijos: añadir")
        manifiesto = json.loads((plugin / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifiesto["name"], "Pérez & Hijos: añadir")
        self.assertIn("'Pérez & Hijos: añadir' => 'Pérez & Hijos: añadir'", (plugin / "lang" / "es.php").read_text(encoding="utf-8"))

    def test_una_carpeta_con_algo_dentro_pide_forzar(self):
        plugin = self.plugin("lista-deseos")
        with self.assertRaises(ValueError):
            ap.esqueleto_mod.crear("lista-deseos", "Lista de deseos", plugin)
        (plugin / "propio.txt").write_text("x")
        ap.esqueleto_mod.crear("lista-deseos", "Lista de deseos", plugin, forzar=True)
        self.assertFalse((plugin / "propio.txt").exists(), "forzar rehace la carpeta entera")

    def test_la_orden_de_consola_crea_el_plugin_y_dice_donde(self):
        destino = self.tmp / "hecho" / "lista-deseos"
        proceso = subprocess.run([sys.executable, str(SKILL / "esqueleto.py"), "lista-deseos", "Lista de deseos", "--salida", str(destino)],
                                 stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(proceso.returncode, 0, proceso.stdout + proceso.stderr)
        self.assertIn("(9 ficheros)", proceso.stdout)
        self.assertTrue((destino / "plugin.json").is_file())
        proceso = subprocess.run([sys.executable, str(SKILL / "esqueleto.py"), "Mal-Id", "Nombre", "--salida", str(self.tmp / "x")],
                                 stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(proceso.returncode, 2)
        self.assertIn("no se ha creado nada", proceso.stdout)

    def test_el_esqueleto_declara_una_tabla_y_la_crea_su_migracion(self):
        plugin = self.plugin("lista-deseos")
        declaradas = json.loads((plugin / "plugin.json").read_text(encoding="utf-8"))["contract"]["tables"]
        creadas = re.findall(r"->create\('([a-z_0-9]+)'", (plugin / "migrations" / "0001_notes.php").read_text(encoding="utf-8"))
        self.assertEqual(declaradas, creadas)

    def test_el_esqueleto_trae_las_cuatro_pruebas_minimas_y_las_de_lo_que_hace(self):
        texto = (self.plugin("lista-deseos") / "tests" / "ListaDeseosTest.php").read_text(encoding="utf-8")
        nombres = re.findall(r"^test\('([^']+)'", texto, re.M)
        self.assertGreaterEqual(len(nombres), 6)
        for fragmento in ("se activa", "se desactiva", "pasa el contrato"):
            self.assertTrue(any(fragmento in n for n in nombres), fragmento)
        self.assertTrue(any("nota" in n for n in nombres), "hace lo suyo")


class PruebasDelSkill(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")

    def test_tiene_menos_de_250_lineas(self):
        self.assertLess(len(self.texto.splitlines()), 250)

    def test_lleva_su_frontmatter(self):
        self.assertTrue(self.texto.startswith("---\nname: fabrica-plugins-aifec\ndescription: "))

    def test_las_diez_fases_estan_en_orden(self):
        titulos = re.findall(r"^### (\d+)\. (.+)$", self.texto, re.M)
        self.assertEqual([int(n) for n, _ in titulos], list(range(1, 11)))
        esperados = ["Qué hace y qué toca", "Esqueleto", "Datos y migraciones", "Ganchos y rutas", "Panel", "Tienda",
                     "Traducción", "Pruebas", "Puertas", "Entrega"]
        self.assertEqual([t for _, t in titulos], esperados)

    def test_la_declaracion_del_contrato_va_antes_que_el_esqueleto_y_que_el_codigo(self):
        fase1 = self.texto.index("### 1. Qué hace y qué toca")
        fase2 = self.texto.index("### 2. Esqueleto")
        cuerpo = self.texto[fase1:fase2]
        self.assertIn("antes de una sola línea de código", cuerpo.lower())
        for clave in ("contract.hosts", "contract.personal_data", "contract.tables", "contract.capabilities"):
            self.assertIn(clave, cuerpo)

    def test_nombra_las_siete_puertas_y_el_comando_para_pasarlas(self):
        for puerta in ("sintaxis", "contrato", "pruebas", "traducciones", "ciclo", "humo", "limpieza"):
            self.assertIn("`%s`" % puerta, self.texto, puerta)
        self.assertIn("python fabrica.py puertas <id>", self.texto)
        self.assertIn("python skill/esqueleto.py <id>", self.texto)

    def test_las_puertas_bloqueantes_estan_como_lista_de_comprobacion(self):
        for frase in ("Declarar menos de lo que hace", "Recorrer históricos", "Correo solo por el servicio común", "Llamadas externas solo con",
                      "céntimos", "PHP 7.4", "e()", "con parámetros", "24 horas", "marca de enviado", "tiempo límite"):
            self.assertIn(frase, self.texto, frase)

    def test_todos_los_ficheros_que_nombra_existen(self):
        nombrados = set(re.findall(r"`((?:skill|plantillas|docs)/[A-Za-z0-9_./\-]+)`", self.texto))
        self.assertGreaterEqual(len(nombrados), 7)
        for ruta in sorted(nombrados):
            if ruta.endswith("/"):
                self.assertTrue((PROYECTO / ruta).is_dir(), ruta)
            elif "<" not in ruta:
                self.assertTrue((PROYECTO / ruta).exists(), ruta)

    def test_las_referencias_existen_y_no_estan_vacias(self):
        for nombre in ("ganchos", "panel", "contrato", "fallos-frecuentes"):
            ruta = SKILL / "referencias" / (nombre + ".md")
            self.assertTrue(ruta.is_file(), nombre)
            self.assertGreater(len(ruta.read_text(encoding="utf-8")), 1500, nombre)

    def test_la_referencia_del_contrato_trae_de_c1_a_c10_cada_una_con_su_encabezado(self):
        texto = (SKILL / "referencias" / "contrato.md").read_text(encoding="utf-8")
        encabezados = re.findall(r"^## (C\d+) — ", texto, re.M)
        self.assertEqual(encabezados, ["C%d" % n for n in range(1, 11)])
        self.assertIn("**M1**", texto)
        self.assertIn("**P1**", texto)

    def test_los_fallos_frecuentes_cuentan_lo_que_paso_y_como_se_evita_y_traen_los_de_seguir_el_skill(self):
        texto = (SKILL / "referencias" / "fallos-frecuentes.md").read_text(encoding="utf-8")
        self.assertGreaterEqual(len(re.findall(r"^## ", texto, re.M)), 12)
        self.assertIn("exportData()", texto, "el tropiezo real de seguir el skill con la lista de deseos")
        self.assertIn("cacheable", texto)

    def test_la_plantilla_del_encargo_pide_la_declaracion_y_las_marcas_de_la_fabrica_estan_todas(self):
        texto = (PROYECTO / "plantillas" / "encargo.md").read_text(encoding="utf-8")
        for marca in ("titulo", "clase", "slug", "nombre", "encargo", "trabajo", "manifiesto", "carpeta_destino", "skill", "banco",
                      "existentes", "comprobar", "anterior"):
            self.assertIn("{{%s}}" % marca, texto, marca)
        for campo in ("`sector`", "`datos`", "`llamadas`", "`contract.personal_data`", "`contract.hosts`"):
            self.assertIn(campo, texto, campo)
        ficha = (PROYECTO / "plantillas" / "ficha.md").read_text(encoding="utf-8")
        for marca in ("nombre", "slug", "estado", "sector", "idea", "puertas", "resumen_puertas"):
            self.assertIn("{{%s}}" % marca, ficha, marca)

    def test_la_cola_de_ejemplo_trae_tres_encargos_completos_para_plugins(self):
        cola = json.loads((PROYECTO / "cola.ejemplo.json").read_text(encoding="utf-8"))
        self.assertEqual([e["slug"] for e in cola], ["lista-deseos", "aviso-existencias", "punto-recogida"])
        for encargo in cola:
            for campo in ("slug", "nombre", "sector", "idea", "datos", "llamadas", "no_hacer"):
                self.assertIn(campo, encargo, "%s: falta %s" % (encargo["slug"], campo))
            self.assertIsInstance(encargo["datos"], list)
            self.assertRegex(encargo["slug"], r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
        self.assertEqual(cola[1]["datos"], ["email"], "el aviso guarda un correo: lo declara")
        self.assertIn("servicio de correo", cola[1]["llamadas"])


class PruebasDelEjemploDelSkill(unittest.TestCase):
    """`skill/ejemplos/lista-deseos/` es el encargo «lista de deseos» hecho siguiendo el skill: declara y trae lo que dice."""

    def test_trae_las_piezas_que_dice_su_leeme(self):
        for ruta in ("plugin.json", "LEEME.md", "hooks.php", "routes.php", "settings.php", "lang/es.php", "migrations/0001_items.php",
                     "src/Wishlist.php", "src/WishlistController.php", "views/front/list.php", "views/front/button.php",
                     "views/front/account-card.php", "tests/ListaDeseosTest.php"):
            self.assertTrue((EJEMPLO / ruta).is_file(), ruta)

    def test_declara_primero_lo_que_hace_el_encargo(self):
        manifiesto = json.loads((EJEMPLO / "plugin.json").read_text(encoding="utf-8"))
        cola = {e["slug"]: e for e in json.loads((PROYECTO / "cola.ejemplo.json").read_text(encoding="utf-8"))}
        encargo = cola["lista-deseos"]
        self.assertEqual(manifiesto["contract"]["personal_data"], encargo["datos"])
        self.assertEqual(manifiesto["contract"]["hosts"], [], "el encargo dice «ninguna» llamada")
        self.assertEqual(manifiesto["contract"]["capabilities"], encargo["capacidades"])
        self.assertEqual(manifiesto["contract"]["tables"], ["lista_deseos_items"])
        self.assertEqual(manifiesto["requires"]["modules"], ["catalog", "customers"])

    def test_las_tablas_declaradas_son_las_que_crea_su_migracion(self):
        declaradas = json.loads((EJEMPLO / "plugin.json").read_text(encoding="utf-8"))["contract"]["tables"]
        creadas = re.findall(r"->create\('([a-z_0-9]+)'", (EJEMPLO / "migrations" / "0001_items.php").read_text(encoding="utf-8"))
        self.assertEqual(declaradas, creadas)

    def test_oye_los_dos_ganchos_de_privacidad_y_no_manda_correos_ni_llama_a_nadie(self):
        codigo = "".join(p.read_text(encoding="utf-8") for p in EJEMPLO.rglob("*.php") if "tests" not in p.parts)
        self.assertIn("'customer.anonymised'", codigo)
        self.assertIn("'customer.export'", codigo)
        for prohibido in (r"(?<![A-Za-z_])mail\(", r"->http\(", r"curl_", r"file_get_contents", r"(?<![A-Za-z_>])time\(\)", r"(?<![A-Za-z_>])date\("):
            self.assertIsNone(re.search(prohibido, codigo), prohibido)

    def test_el_encargo_de_la_cola_menciona_lo_que_el_ejemplo_hace(self):
        cola = {e["slug"]: e for e in json.loads((PROYECTO / "cola.ejemplo.json").read_text(encoding="utf-8"))}
        for hueco in cola["lista-deseos"]["huecos"]:
            self.assertIn("'%s'" % hueco, (EJEMPLO / "hooks.php").read_text(encoding="utf-8"), hueco)
        for ajuste in cola["lista-deseos"]["ajustes"]:
            self.assertIn("'%s'" % ajuste, (EJEMPLO / "settings.php").read_text(encoding="utf-8"), ajuste)


if __name__ == "__main__":
    unittest.main()
