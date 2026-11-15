# __Nombre__

Plugin de AIFEC hecho desde el esqueleto de la fábrica de plugins. Viene **desactivado**.

## Qué hace

Añade a cada producto una nota corta y la enseña bajo el resumen de la ficha.

| Punto de extensión | Dónde está | Qué hace |
|---|---|---|
| Hueco de plantilla (`product.summary.after`) | `hooks.php`, `views/front/note.php` | Pinta «Nota: …» bajo el resumen, ya escapado. |
| Campo en el panel (`admin.definitions`) | `hooks.php` | Añade el campo al formulario de productos. Lo guarda el propio plugin en su tabla. |
| Ajuste | `settings.php` | «Nota por defecto», para los productos que no tienen la suya. |

Su tabla, `__id_bajo___notes`, está declarada en `plugin.json` y la crea `migrations/0001_notes.php`. Al desinstalar sin conservar los datos se borran la tabla y el ajuste.

## Cómo se usa

1. Panel, «Módulos y plugins», pestaña «Plugins»: pulsa «Activar». Antes pasa el validador del Contrato AIFEC.
2. Por consola: `php aifec plugin:enable __id__` y `php aifec contract:check __id__`.
3. Pruebas: `php tests/run.php plugins/__id__/`.
4. Traducciones: `php aifec i18n:check plugins/__id__ es`.

## Qué declara en el contrato

Ningún servicio externo, ningún dato personal, una tabla propia y ninguna capacidad: no toca precios, impuestos ni plazos.
