# Ganchos: los más usados y dónde está la lista completa

**La lista completa y al día** sale del propio sistema: `docs/07-referencia/_generado/ganchos.md` de la instalación (se genera con `php aifec docs:reference`). Dice, de cada gancho, de qué tipo es, dónde se dispara, quién lo escucha y con qué capacidad está sellado. En el banco está en `estado/banco/docs/07-referencia/_generado/ganchos.md`. **Los nombres no se adivinan: se buscan ahí.**

Tres tipos, tres formas de engancharse (en `hooks.php`, dentro de `return static function (App $app): void { … };`):

| Tipo | Para qué | Cómo |
|---|---|---|
| Acción | avisarse de algo que ha pasado (`order.paid`) | `$app->hooks()->on('order.paid', static function (array $order) use ($app): void { … });` |
| Filtro | cambiar un valor que pasa por el gancho (`product.extra`, `admin.definitions`) | `$app->hooks()->filter('product.extra', static function ($extra, $product): array { …; return $extra; });` |
| Hueco | pintar un trozo de HTML donde el tema lo ofrece (`product.summary.after`) | `$app->hooks()->slot('product.summary.after', static function ($product) use ($app): string { return $app->view()->render('<id>::front/x', $datos); });` |

Cada oyente se atribuye al plugin y se mide. **Si lanza, se anota y la página sigue**, pero la puerta `humo` lo cuenta como fallo y, en las pruebas, un oyente que lanza hace fallar la prueba (salvo `expectHookErrors()`).

## Los más usados

| Gancho | Tipo | Cuándo | Argumentos |
|---|---|---|---|
| `app.boot` | acción | al arrancar la aplicación | `$app` |
| `product.summary.after` | hueco | bajo el resumen de la ficha | `$product` (ProductData) |
| `product.buy.after`, `product.bottom` | hueco | tras el botón de compra, al pie de la ficha | `$product` |
| `product.extra` | filtro | datos tipados del producto (`label`, `type`, `public`) | `$extra, $product` |
| `account.dashboard` | hueco | inicio de Mi cuenta | `$customer` |
| `cart.after`, `checkout.before`, `checkout.after`, `order.thanks` | hueco | carrito, caja, gracias | `$cart` / `$summary` / `$order` |
| `home.top`, `home.bottom`, `header.actions`, `footer.columns`, `body.end` | hueco | portada y envoltorio del tema | — |
| `order.placed`, `order.paid`, `order.status`, `order.refunded`, `order.cancelled` | acción | ciclo del pedido | `$order` (array) |
| `stock.changed` | acción | cambia la existencia | `$productId, $variantId, $after` |
| `customer.registered`, `customer.login` | acción | alta e inicio de sesión | `$customer` |
| `customer.anonymised` | acción | un cliente pide que se le olvide | `$customerId, $email` |
| `customer.export` | filtro | copia de los datos de un cliente | `$data, $customerId` |
| `admin.definitions` | filtro | recursos del panel (añadir un campo al formulario de productos) | `$definitions, $app` |
| `admin.resource.saved`, `admin.resource.deleted` | acción | se guarda o se borra algo desde el panel | `$resource, $id, …` |
| `settings.saved` | acción | se guardan ajustes de un módulo | `$module, $keys, $app` |
| `page.meta`, `menu.items`, `home.sections`, `listing.query` | filtro | metadatos, menús, portada, consulta del listado | según el gancho |

## Sellados: solo con la capacidad `pricing`

`product.price`, `product.availability`, `shipping.options`, `tax.rate` y `cart.adjustments` cambian lo que el cliente paga o lo que ve disponible. Enganchar uno sin `"capabilities": ["pricing"]` en `plugin.json` es un error de C1, y con ella el plugin **declara** que lo hace. El usuario concede la capacidad en el panel (`php aifec plugin:grant <id> pricing`). Un descuento visible se hace con `cart.adjustments` (aparece como línea del desglose), no cambiando el precio por debajo.

## Datos personales: dos ganchos que hay que oír

Si el plugin guarda algo de un cliente, escucha `customer.anonymised` (borra lo suyo) y `customer.export` (añade lo suyo a la copia de datos). Y lo declara en `contract.personal_data`. Modelo: `skill/ejemplos/lista-deseos/hooks.php`.

## Servicios que se registran por gancho

Un transporte: `$app->service('shipping')->registerHandler(new MiTransporte())` (`Aifec\Commerce\ShippingHandler`: `code()`, `needsAddress()`, `quote()` con el precio en céntimos). Una tarea periódica: `jobs.php` con `'cron' => ['<id>.diaria' => ['every' => 'daily@04:10', 'run' => [Tareas::class, 'diaria']]]`. Un bloque del editor: `blocks.php`. Una orden de consola: `cli.php`. `php aifec plugin:create <id> --features=carrier,job,block,command,payment,screen,listener,slot,setting` genera ejemplos de cada uno.
