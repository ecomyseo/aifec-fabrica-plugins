# Las puertas

Una puerta es un programa de `puertas/` con esta interfaz:

```
python puertas/<nombre>.py --slug <id> --candidato <salida/id> --banco <estado/banco> --plan <plan.json> --informe <fichero.json>
```

Sale con **0** (pasa), **1** (no pasa) o **2** (no aplica: falta algo opcional) y escribe en `--informe`:

```json
{"puerta": "ciclo", "ok": true, "resumen": "activa, desactiva, reactiva y desinstala limpio; 1 tabla(s) creada(s), las 1 declarada(s)", "detalles": ["…"], "medidas": {"tablas_creadas": 1}}
```

**No modifica el candidato** (una prueba lo comprueba con cada puerta). `motor/puertas.py` las lanza en el orden del plan, junta los informes en `estado/encargos/<id>.puertas.json` y decide: pasa si ninguna da 1. Una puerta que no existe, que revienta o que no deja informe **cuenta como que no pasa**.

`python fabrica.py puertas <id> [--solo ciclo,humo]` las lanza a mano; `python skill/informe.py <id> [--puerta ciclo]` enseña el detalle completo.

## Cómo se reparte el trabajo con el sistema

La fábrica **no repite** ninguna comprobación que ya sepa hacer AIFEC: `contrato` y `traducciones` solo leen el veredicto de `php aifec contract:check` y `php aifec i18n:check`, y `pruebas` lanza el corredor del sistema. Si el sistema no trae la orden, la puerta sale con 2 («no se imita su comprobación por otro lado»). Lo que añade la fábrica es lo que el sistema no mide de la misma manera: la sintaxis en todas las versiones, el ciclo de vida con el gestor real, la tienda en pie con el plugin activo y la limpieza del paquete.

| Puerta | Qué comprueba | Cómo | Pasa si |
|---|---|---|---|
| `sintaxis` | que el código vale en todas las versiones | `php -l` de cada `.php` con `php` y con cada ejecutable de `php_versiones` | cero errores **y cero avisos** (8.4 avisa de un nullable implícito y sale con 0) |
| `contrato` | el Contrato AIFEC | instala el candidato en el banco y lanza `php aifec contract:check <id>` | sale con 0 y su línea final dice `0 errors` |
| `pruebas` | que trae pruebas y pasan | `php tests/run.php plugins/<id>/` en el banco | al menos 4 pruebas declaradas y ejecutadas, `0 FALLAN` |
| `traducciones` | nada sin traducir | `php aifec i18n:check plugins/<id> es` | `0 missing` |
| `ciclo` | que entra y sale limpio | en el banco, con el gestor de plugins: activar, desactivar, reactivar y desinstalar sin conservar datos | ver abajo |
| `humo` | que no rompe nada | con el plugin activo, portada, listado, ficha, carrito y escritorio del panel | ver abajo |
| `limpieza` | nada de sobra | ficheros que no son del plugin, cabeceras, credenciales y correos | ver abajo |

## `sintaxis`

Para cada fichero y cada PHP: `php -d display_errors=1 -d error_reporting=-1 -l <fichero>`. No pasa si sale con código distinto de 0 **o si escribe cualquier línea `Parse error`, `Fatal error`, `Deprecated`, `Warning` o `Notice`**. Con PHP 7.4 caza lo que PHP 8 permite (`match`, `readonly`, tipos unión, `?->`); con 8.4, lo que ya está obsoleto. Un ejecutable del plan que no existe es un fallo (sin él no se comprueba esa versión); si falta `php`, la puerta sale con 2.

## `contrato`

Instala `salida/<id>/` en `estado/banco/plugins/<id>/` y lanza `php aifec contract:check <id>`. Lee las líneas `[ OK ]`, `[WARN]` y `[FAIL]` y la final `CONTRACT <id>: score N/100, E errors, W warnings`. Los avisos se enseñan pero no bloquean. Qué mide cada regla (C1 a C10): `skill/referencias/contrato.md`.

## `pruebas`

Antes de lanzar nada mira el candidato: sin `tests/*Test.php`, o con menos de cuatro llamadas a `test(`, no pasa («las cuatro mínimas: se activa, hace lo suyo, se desactiva, se desinstala»). Después lanza el corredor con la barra final (`plugins/<id>/`, para no coger `plugins/<id>-otro`). «Cero pruebas» no es un verde.

## `ciclo`

Lanza `puertas/_ciclo.php` dentro del banco. Con el gestor real (`Aifec\Modules\Plugins\Plugins`): activa el plugin (sin repetir el validador), lo desactiva, lo reactiva y lo desinstala sin conservar datos, apuntando antes, durante y después las tablas y los ajustes del sitio del banco. No pasa si:

- las tablas que aparecen al activar **no son exactamente** las de `contract.tables` (una de más: «crea la tabla X y no la declara»; una de menos: «declara la tabla X pero no la crea»);
- desactivar **pierde** una tabla (los datos se conservan hasta desinstalar) o reactivar **cambia** el esquema;
- tras desinstalar sin conservar datos se queda **una tabla o un ajuste** que antes no estaba, o desaparece uno que no era suyo;
- el código del plugin lanza un aviso de PHP durante el ciclo.

Si una pasada anterior se cortó a medias, lo primero que hace es dejar el banco como si el plugin no se hubiera instalado nunca y lo dice en una nota. Al acabar quita el candidato del banco.

## `humo`

Lanza `puertas/_humo.php`: crea en el sitio del banco una persona del equipo para la ocasión (y la borra), pide en el propio proceso la portada, el listado (una categoría si hay, o el buscador), una ficha de producto (si el banco no tiene ninguno, crea uno), el carrito y el escritorio del panel **sin el plugin** y después **con él activo**, y compara:

- cada página que respondía 200 sin el plugin tiene que seguir en 200 con él (una página que ya fallaba sin el plugin no se le achaca: se dice en una nota);
- **ni un aviso de PHP nuevo** (un manejador de errores recoge los avisos, las notas y lo obsoleto de cada pasada);
- **ni una línea de error o aviso nueva en el registro del sitio**: un oyente que lanza no tira la página, pero deja su línea, y es justo lo que esta puerta caza.

Al acabar desactiva y desinstala el plugin del banco.

## `limpieza`

1. **Ficheros de sobra:** ZIP y demás paquetes, `vendor`, `node_modules`, `composer.json`, `.env`, mapas de código, registros, capturas y programas; y nada en la raíz que no sea `plugin.json`, una pieza por convenio (`hooks.php`, `routes.php`, `admin.php`, `settings.php`, `jobs.php`, `cli.php`, `blocks.php`), una de sus carpetas (`migrations/`, `views/`, `lang/`, `assets/`, `mail/`, `src/`, `tests/`, `docs/`) o la documentación.
2. **Cabeceras:** cada `.php` empieza por `<?php`, salto de línea y el bloque `/**` enseguida, con `@author` y `@license`; fuera de las vistas, también `declare(strict_types=1);`; sin BOM y con saltos LF.
3. **Credenciales con pinta de real:** una cadena larga (24 o más caracteres de hexadecimal o base64, con letras y cifras) asignada a algo que se llame `key`, `secret`, `token` o `password`, y los formatos conocidos (`sk-…`, `ghp_…`, `AKIA…`, `AIza…`, `xox…`, una clave privada). Lo que diga «mentira», «ejemplo», «test»… no cuenta.
4. **Correos que no son de ejemplo:** solo valen `.test`, `.example`, `.invalid`, `.localhost`, `example.com/org/net`. Las líneas `@author` y `@copyright` de una cabecera no cuentan.

## Lo que ninguna puerta ve

Una puerta que pasa no demuestra que el plugin haga lo que el encargo pide. Hay cosas que solo mira una persona: que el texto tenga sentido, que la pantalla se vea bien en un navegador, que un hueco de una página cacheable no pinte nada de quien mira (`skill/referencias/fallos-frecuentes.md`). Por eso `hecho` y `aprobado` van separados.
