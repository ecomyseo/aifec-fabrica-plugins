# El Contrato AIFEC, regla a regla

Lo comprueba el propio sistema (`php aifec contract:check <id>`, y la pantalla de Plugins al activar). La puerta `contrato` solo lee su veredicto: aquí se explica **qué mira cada regla** y se enseña un ejemplo que cumple y otro que no. Las dos reglas previas, **M1** (el manifiesto: nombre, versión `1.0.0`, `namespace` propio sin empezar por `Aifec\`, y las cuatro claves de `contract`) y **P1** (nada de `eval`, `shell_exec`, `exec`, `system`, `proc_open`, `popen`, backticks, escribir fuera de la carpeta de datos del sitio, ni `base64_decode` seguido de ejecutar), bloquean todo lo demás: con una de ellas en rojo no se llega a ejecutar el plugin.

| Regla | Qué exige | Cómo se mira |
|---|---|---|
| C1 | Precio, existencias, impuestos y plazos, solo por los cauces del sistema | estático y dinámico |
| C2 | Lo que se añade al producto se declara como dato tipado | estático |
| C3 | Salida ligera y cacheable | estático y dinámico |
| C4 | Todo escapado y por plantilla | estático |
| C5 | Servicios externos y datos personales declarados | estático |
| C6 | IA, correo, tareas y caché por los cauces comunes | estático |
| C7 | Datos estructurados (JSON-LD) intactos | dinámico |
| C8 | Textos traducidos | estático |
| C9 | Se desinstala limpio | estático y dinámico |
| C10 | No tumba la tienda | dinámico |

## C1 — No escribir precio, existencias, impuestos ni plazos por fuera

Cumple: una tabla propia, declarada, y la capacidad `pricing` solo si de verdad se toca un gancho sellado.

```php
$app->db()->insert('lista_deseos_items', ['customer_id' => $id, 'product_id' => $p, 'created_at' => $now]);
```

No cumple: escribir en una tabla que no es del plugin, o enganchar un filtro sellado (`product.price`, `product.availability`, `shipping.options`, `tax.rate`, `cart.adjustments`) sin `"capabilities": ["pricing"]`.

```php
$app->db()->update('products', ['price' => 100], ['id' => $p]);               // C1: tabla del catálogo
$app->hooks()->filter('product.price', static function ($price) { return 0; }); // C1: gancho sellado sin capacidad
```

## C2 — Lo que se añade al producto se declara con su etiqueta, su tipo y si es público

Cumple (`plugins/hello-aifec`): `['label' => t('Made in'), 'value' => $country, 'type' => 'text', 'public' => true]`. No cumple: añadir `'value'` suelto sin `label`, `type` y `public`.

## C3 — Salida ligera y cacheable

Cumple: hojas y guiones propios en `assets/`, juntos por debajo de 60 KB, y HTML que **no depende de quien mira** (la página se cachea). No cumple: `<script src="https://…">` o `<link href="https://…">` en una vista, `@import` o `url(https://…)` en una hoja, recursos por encima de 200 KB, o un hueco que pinta algo distinto para cada visitante (se cachearía el de otro).

## C4 — Todo escapado y por plantilla

Cumple: el HTML solo en `views/`, y en ellas `<?= e($dato) ?>`. No cumple: `echo`, `print`, `printf`, `var_dump`, `header()`, `setcookie()`, `exit` o `die` fuera de las vistas, HTML suelto dentro de una clase, o un valor impreso en una vista sin `e()` (aviso). Un controlador devuelve un `Response`; no imprime.

## C5 — Servicios externos y datos personales declarados

Cumple: llamar solo con `$app->http()` a un dominio que está en `contract.hosts`, y declarar en `contract.personal_data` lo que se lee de clientes o pedidos.

```json
"contract": { "hosts": ["api.ejemplo.test"], "personal_data": ["email"], "tables": [], "capabilities": [] }
```

No cumple: `curl_*`, `fsockopen`, `file_get_contents('https://…')` (usa `$app->http()`), un dominio en el código que no está en `hosts`, o leer `customers`/`orders`/`addresses` (por SQL o con `$app->service('customers')`) con `personal_data` vacío.

## C6 — IA, correo, tareas y caché por los cauces comunes

Cumple: `$app->service('mail')` para correo, `$app->service('ai')` para IA y `jobs.php` para trabajos. No cumple: `mail()`, PHPMailer o un transporte propio; llamar directamente a una API de IA; `sleep()`/`usleep()`; `set_time_limit(0)`; un trabajo que lee **todo** el historial de pedidos o clientes sin límite de fecha ni de id (aviso, y en este proyecto es un fallo de diseño: 24 horas como mucho y una marca de enviado).

## C7 — Datos estructurados intactos

Dinámico: con el plugin activo, el JSON-LD de la ficha sigue siendo válido y coincide con `ProductData`. Cumple: añadir datos por `product.extra`. No cumple: pintar un `<script type="application/ld+json">` propio roto o duplicado.

## C8 — Textos traducidos

Cumple: cada cadena de `t('…')`, de las etiquetas de `settings.php` y `admin.php` y del manifiesto, con su entrada en `lang/es.php` (clave inglesa tal cual, valor en castellano). No cumple: una cadena nueva sin traducción. Se comprueba con `php aifec i18n:check plugins/<id> es`.

## C9 — Se desinstala limpio

Estático: toda tabla que crea una migración está en `contract.tables`. Dinámico: se instala, se desinstala sin conservar datos y se compara el esquema y los ajustes. Los ajustes se borran por su prefijo (`<id>.` o `<id_con_guiones_bajos>.`); lo que se guarde con otra clave se queda. La puerta `ciclo` lo mide también de otra forma: las tablas que aparecen al activar son **exactamente** las declaradas.

## C10 — No tumba la tienda

Dinámico: con el plugin lanzando una excepción en cada gancho, portada, ficha, carrito y listado siguen respondiendo 200. Un oyente que lanza se anota y la página sigue; pero **la puerta `humo` lo cuenta como fallo**, porque el registro del sitio gana una línea de error que sin el plugin no tenía.
