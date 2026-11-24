# Fallos frecuentes al construir un plugin

Lo que ya ha hecho tropezar a alguien, con lo que pasó y cómo se evita. Se lee **antes** de la fase 3 del skill. Cada tropiezo nuevo se apunta aquí en cuanto se arregla. Los cuatro primeros salieron de **seguir este skill de principio a fin** con el encargo «lista de deseos» (`skill/ejemplos/lista-deseos/`, 2026-11-13); el resto, de medir las puertas con el esqueleto estropeado.

## Los nombres de los servicios y de sus métodos se leen, no se adivinan

La prueba de privacidad llamó a `$app->service('customers')->export($id)` y dio «Call to undefined method Customers::export()»: el método es `exportData()`. Lo mismo pasa con ganchos (`customer.anonymised`, no `customer.deleted`) y con rutas con nombre (`account.login`). **Se busca en el código del sistema** (`estado/banco/modules/<módulo>/src/`) o en la lista generada (`docs/07-referencia/_generado/`: `ganchos.md`, `rutas.md`, `ajustes.md`, `tablas.md`, `permisos.md`). Un nombre inventado en `hooks.php` ni siquiera falla: el oyente se engancha a un gancho que nadie dispara.

## Un hueco de una página cacheable no pinta nada de quien mira

`product.summary.after` está en la ficha, que se cachea y se sirve a todos. Un botón «en tu lista» o «ya guardado» pintado según la sesión enseñaría al siguiente visitante el estado del anterior, y **ninguna puerta lo caza** (el humo mira que responda 200, no de quién es el HTML). La ficha pinta siempre lo mismo (un formulario que, sin sesión, manda a entrar) y lo que cambia por persona va en una ruta con `middleware => ['customer']`, que sale con `Cache-Control: no-store, private`. Una prueba lo fija: el hueco devuelve el mismo HTML dos veces.

## `Db::value()` devuelve el valor tal como lo da el motor

Con SQLite puede ser un entero y con MySQL, una cadena: `->value('SELECT COUNT(*) …') > 0` compara según el motor. Se escribe `(int) $db->value(…) > 0`. Una prueba en SQLite no lo ve.

## Si guarda algo de un cliente, hay que oír dos ganchos

`customer.anonymised` (borrar lo suyo cuando el cliente pide que se le olvide) y `customer.export` (añadir lo suyo a la copia de sus datos). Sin ellos, el plugin guarda datos que el sistema no sabe borrar ni entregar. Y los dos se prueban: anonimizar a un cliente quita su lista y deja la de otro.

## Una tabla que se crea y no se declara (o se declara y no se crea)

`contract.tables` y las migraciones tienen que coincidir. La puerta `ciclo` mide lo que aparece de verdad al activar: «crea la tabla X y no la declara» y, tras desinstalar, «se queda la tabla X» (el gestor solo borra las declaradas). Al revés: «declara la tabla X pero no la crea». Se arregla en las dos direcciones a la vez: la migración y la declaración.

## Un ajuste con un prefijo que no es el del plugin se queda al desinstalar

El gestor borra los ajustes que empiezan por `<id>.` o por `<id_con_guiones_bajos>.`. Un `$app->settings()->set('otra_cosa.valor', …)` se queda y la puerta `ciclo` dice «se queda el ajuste». Todo ajuste propio lleva su prefijo.

## Un nullable implícito avisa en PHP 8.4 aunque `php -l` salga con 0

`function f(int $x = null)` sale con «Deprecated: Implicitly marking parameter $x as nullable» y código de salida 0. La puerta `sintaxis` lo cuenta como fallo: se escribe `?int $x = null`. Y un `match`, una propiedad `readonly` o un tipo unión no compilan en PHP 7.4: por eso el plan lleva `php_versiones` con el 7.4 y el 8.4.

## La clave de una pestaña de ajustes lleva el nombre del plugin

`'general' => …` acaba como `id` del DOM del panel y puede chocar con uno que ya existe. Se escribe `lista_deseos_general`. Lo mismo con las claves de los ajustes: `lista_deseos.max_items`.

## Las cadenas con número: la clave lleva la barra y se escribe con `tn()`

`tn('{n} product saved|{n} products saved', $count)` y, en `lang/es.php`, la misma clave inglesa con la barra: `'{n} product saved|{n} products saved' => '{n} producto guardado|{n} productos guardados'`. Una cadena con valores variables: `t('You can save up to {n} products.', ['n' => $max])`, con la clave inglesa tal cual (con `{n}`).

## El nombre de una cadena se traduce una vez y es la clave inglesa

El `name` del manifiesto, su `description`, los `title`, `label` y `hint` de `settings.php` y de `admin.php` cuentan como cadenas del plugin. El `name` también: `'Lista de deseos' => 'Lista de deseos'`. Si falta, `i18n:check` da «missing» sin decir que es del manifiesto.

## `php tests/run.php plugins/hola` también ejecuta `plugins/hola-mundo`

El filtro del corredor es «la ruta contiene». La puerta lanza `plugins/<id>/` con la barra final; a mano, igual.

## Las pruebas no desinstalan el plugin de verdad

`Plugins::uninstall()` **borra la carpeta del plugin**. En una prueba corre sobre la instalación real y se llevaría el plugin. El ciclo de instalar y desinstalar se prueba con `$plugins->validate('<id>')` (lo hace en un sitio de pruebas) y lo mide la puerta `ciclo` en el banco.

## Una prueba de una ruta de la tienda: entrar como un cliente y mandar el origen

`customersMakeAccount($app)` crea la cuenta (de `modules/customers/tests/CustomersKit.php`), `$web->post('/mi-cuenta/entrar', ['email' => …, 'password' => 'clave-larga-1'])` entra, y `TestClient::post($url, $datos, ['sec-fetch-site' => 'cross-site'])` prueba el rechazo de un envío desde otra web (403). Sin sesión, el intermediario `customer` redirige a la entrada (302 o 303).

## Cabecera exacta y `declare(strict_types=1)`

`<?php`, **salto de línea y el bloque `/**` enseguida** (sin línea en blanco), con `@author` y `@license`; después `declare(strict_types=1);` en todo lo que no sea una vista. Sin marca BOM (escupe tres bytes) y con saltos de línea LF. La puerta de limpieza lo comprueba fichero a fichero.

## Una clave o un correo «de mentira» tiene que parecerlo

una línea `'api_key' => '<32 caracteres seguidos de letras y cifras>'` es una clave con pinta de real para la puerta de limpieza. Los ejemplos: `clave-de-mentira`, `ana@cliente.test`, `x@example.com`. Un correo de verdad solo vale en las líneas `@author` y `@copyright` de una cabecera.

## Nada en la raíz que no sea una pieza por convenio

Un `composer.json`, un `package.json`, un `.env`, una captura o un ZIP dentro del plugin llegan al cliente. La limpieza rechaza todo lo que no sea `plugin.json`, las piezas por convenio (`hooks.php`, `routes.php`, `admin.php`, `settings.php`, `jobs.php`, `cli.php`, `blocks.php`), sus carpetas (`migrations/`, `views/`, `lang/`, `assets/`, `mail/`, `src/`, `tests/`, `docs/`) y la documentación.

## El marcado del esqueleto no admite comillas ni barras en el nombre

`python skill/esqueleto.py <id> "<Nombre>"`: el nombre se escribe en PHP, JSON y Markdown a la vez; con comillas, barras invertidas, `$`, `<`, `>`, llaves o `*/` se rechaza, para que ningún fichero salga roto.
