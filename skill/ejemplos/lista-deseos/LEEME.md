# Lista de deseos

Plugin de AIFEC: los clientes con cuenta guardan productos desde la ficha y los ven y los quitan desde Mi cuenta. Viene **desactivado**. Es el plugin de ejemplo de la fábrica de plugins: se hizo siguiendo su skill de principio a fin y pasa las siete puertas.

## Qué hace

| Pieza | Dónde | Qué hace |
|---|---|---|
| Botón «Guardar en mi lista de deseos» | hueco `product.summary.after`, `views/front/button.php` | Un formulario que no lleva nada de quien mira (la ficha se cachea); sin sesión, manda a entrar. |
| Página de la lista | `routes.php`, `src/WishlistController.php`, `views/front/list.php` | `/mi-cuenta/lista-deseos`: los productos guardados (escapados), con «Quitar». Sin caché. |
| Acceso desde Mi cuenta | hueco `account.dashboard`, `views/front/account-card.php` | Una tarjeta con cuántos productos lleva. |
| Privacidad | ganchos `customer.anonymised` y `customer.export` | La lista se borra con el cliente y viaja en la copia de sus datos. |
| Ajuste «Productos por cliente» | `settings.php` | Tope de la lista, de 1 a 500 (50 por defecto). |

Su tabla, `lista_deseos_items` (un producto por cliente, una sola vez), está declarada en `plugin.json` y la crea `migrations/0001_items.php`. Al desinstalar sin conservar los datos se borran la tabla y el ajuste.

## Cómo se usa

1. Panel, «Módulos y plugins», pestaña «Plugins»: pulsa «Activar». Necesita los módulos de catálogo y de clientes.
2. Por consola: `php aifec plugin:enable lista-deseos` y `php aifec contract:check lista-deseos`.
3. Pruebas: `php tests/run.php plugins/lista-deseos/`.
4. Traducciones: `php aifec i18n:check plugins/lista-deseos es`.

## Qué declara en el contrato

Ningún servicio externo; un dato personal (`customer_id`, el cliente al que pertenece cada lista); una tabla propia (`lista_deseos_items`); ninguna capacidad: no toca precios, impuestos ni plazos. No manda correos ni recorre clientes ni pedidos.
