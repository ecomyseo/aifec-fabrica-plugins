<?php
/**
 * AIFEC — fábrica de plugins: el humo. Con el plugin activo, ¿sigue en pie la tienda?
 *
 *   php _humo.php --banco <estado/banco> --id <plugin>
 *
 * Pide en el propio proceso, primero SIN el plugin y después CON él (activado con el gestor del sistema), la portada,
 * el listado, una ficha de producto, el carrito y el escritorio del panel (con una persona del equipo creada para la
 * ocasión en el sitio del banco y borrada al acabar). Exige que cada página que respondía 200 sin el plugin siga
 * respondiendo 200 con él, y compara lo que gana el registro del sitio y los avisos de PHP: ni un aviso ni una línea
 * de error o aviso nuevos que no estuvieran ya sin el plugin. Al acabar desactiva y desinstala el plugin del banco.
 *
 * Escribe en su última línea `HUMO {json}`. Sale con 0 si ha llegado hasta el final (haya o no problemas: eso lo
 * dice el JSON), con 2 si falta algo (el banco, su sitio, el gestor de plugins, o la portada ni siquiera responde sin
 * el plugin) y con 1 si revienta por dentro. Solo toca el banco, nunca la instalación de origen.
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   Ver LICENSE.md
 */

if (PHP_SAPI !== 'cli') {
    exit(1);
}

$args = [];
$ultima = '';
foreach (array_slice($argv, 1) as $parte) {
    if (strpos($parte, '--') === 0) {
        $ultima = substr($parte, 2);
        $args[$ultima] = true;
    } elseif ($ultima !== '') {
        $args[$ultima] = $parte;
        $ultima = '';
    }
}
$banco = isset($args['banco']) && is_string($args['banco']) ? rtrim(str_replace('\\', '/', $args['banco']), '/') : '';
$id = isset($args['id']) && is_string($args['id']) ? $args['id'] : '';
// Siempre rutas absolutas: el sitio apunta en su caché a las rutas con las que se arrancó.
$banco = $banco !== '' && realpath($banco) !== false ? rtrim(str_replace('\\', '/', realpath($banco)), '/') : $banco;
if ($banco === '' || preg_match('/^[a-z0-9][a-z0-9-]{1,39}$/', $id) !== 1 || !is_file($banco . '/core/bootstrap.php')) {
    fwrite(STDERR, "uso: php _humo.php --banco <banco> --id <plugin>\n");
    exit(2);
}
if (!is_file($banco . '/plugins/' . $id . '/plugin.json')) {
    fwrite(STDERR, 'el candidato no está instalado en el banco (falta plugins/' . $id . "/plugin.json)\n");
    exit(2);
}

error_reporting(E_ALL);
ini_set('display_errors', '0');

require $banco . '/core/bootstrap.php';

/** @var string[] los avisos de PHP de la pasada en curso: «fichero:línea mensaje» */
$avisosPhp = [];
set_error_handler(static function (int $no, string $texto, string $fichero, int $linea) use (&$avisosPhp): bool {
    if ((error_reporting() & $no) === 0) {
        return false;
    }
    $avisosPhp[] = basename($fichero) . ':' . $linea . ' ' . $texto;

    return true;
});

/**
 * Escribe el resultado y sale.
 *
 * @param array<string,mixed> $resultado
 */
function humo_salir(array $resultado, int $codigo): void
{
    echo 'HUMO ' . json_encode($resultado, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PARTIAL_OUTPUT_ON_ERROR) . "\n";
    exit($codigo);
}

/**
 * Pide una dirección en el propio proceso (siguiendo hasta tres redirecciones) con las cookies del «navegador» dado.
 *
 * @param array<string,string> $cookies
 *
 * @return array{status:int,body:string,url:string,nota:string}
 */
function humo_pedir(\Aifec\Kernel\App $app, array &$cookies, string $metodo, string $ruta, array $post = []): array
{
    for ($salto = 0; $salto < 4; $salto++) {
        try {
            $peticion = \Aifec\Kernel\Request::create($metodo, $ruta, $post, $cookies, ['sec-fetch-site' => 'same-origin', 'user-agent' => 'AifecFabrica/1.0']);
            $peticion->host = 'banco.test';
            $peticion->secure = true;
            $respuesta = $app->handle($peticion);
        } catch (\Throwable $e) {
            return ['status' => 500, 'body' => '', 'url' => $ruta, 'nota' => get_class($e) . ': ' . $e->getMessage()];
        }
        foreach ($respuesta->cookies as $nombre => $cookie) {
            if ($cookie['value'] === '' || ((int) $cookie['options']['expires'] !== 0 && (int) $cookie['options']['expires'] < $app->clock()->now())) {
                unset($cookies[$nombre]);
            } else {
                $cookies[$nombre] = $cookie['value'];
            }
        }
        $respuesta->drain();
        if ($respuesta->isRedirect() && isset($respuesta->headers['Location'])) {
            $ruta = (string) preg_replace('#^https?://[^/]+#', '', (string) $respuesta->headers['Location']);
            $ruta = $ruta === '' ? '/' : $ruta;
            $metodo = 'GET';
            $post = [];
            continue;
        }

        return ['status' => (int) $respuesta->status, 'body' => (string) $respuesta->body, 'url' => $ruta, 'nota' => ''];
    }

    return ['status' => 508, 'body' => '', 'url' => $ruta, 'nota' => 'demasiadas redirecciones'];
}

/** Las líneas de registro del sitio por fichero: nombre => bytes que tiene ahora. */
function humo_tamanos(string $carpeta): array
{
    $tamanos = [];
    $ficheros = glob(rtrim($carpeta, '/') . '/*.log');
    foreach (is_array($ficheros) ? $ficheros : [] as $fichero) {
        $tamanos[basename($fichero)] = (int) filesize($fichero);
    }

    return $tamanos;
}

/**
 * Lo que han añadido los ficheros de registro desde las medidas dadas: líneas «nivel|mensaje» de error o aviso.
 *
 * @param array<string,int> $desde
 *
 * @return string[]
 */
function humo_registro_nuevo(string $carpeta, array $desde): array
{
    $nuevas = [];
    $ficheros = glob(rtrim($carpeta, '/') . '/*.log');
    foreach (is_array($ficheros) ? $ficheros : [] as $fichero) {
        $antes = isset($desde[basename($fichero)]) ? $desde[basename($fichero)] : 0;
        $texto = (string) file_get_contents($fichero);
        foreach (explode("\n", (string) substr($texto, $antes)) as $linea) {
            if (trim($linea) === '') {
                continue;
            }
            $dato = json_decode($linea, true);
            if (!is_array($dato)) {
                $nuevas[] = 'texto|' . substr($linea, 0, 160);
                continue;
            }
            $nivel = isset($dato['level']) ? (string) $dato['level'] : '';
            if (in_array($nivel, ['error', 'warning', 'critical', 'alert', 'emergency'], true)) {
                $nuevas[] = $nivel . '|' . substr(isset($dato['message']) ? (string) $dato['message'] : '', 0, 160);
            }
        }
    }

    return $nuevas;
}

/**
 * Un sitio nuevo del banco con el registro en ficheros (así se ve lo que lanzan los oyentes de los ganchos) y sin
 * caché de páginas (así se ejecuta el código del plugin en cada petición).
 */
function humo_app(string $banco, string $datos, string $sitioId): ?\Aifec\Kernel\App
{
    \Aifec\Kernel\SiteResolver::forget();
    $sitio = \Aifec\Kernel\SiteResolver::load($datos, $sitioId);
    if ($sitio === null) {
        return null;
    }
    $sitio->host = 'banco.test';
    $app = new \Aifec\Kernel\App($sitio, $banco, ['public_dir' => $banco . '/public', 'log_files' => true]);
    $app->settings()->override(['cache.pages' => false]);
    $app->makeCurrent();

    return $app;
}

/**
 * Pide las cinco páginas y devuelve nombre => [url, status, bytes, nota].
 *
 * @param array<string,string> $rutas
 *
 * @return array<string,array<string,mixed>>
 */
function humo_paginas(\Aifec\Kernel\App $app, array $rutas, string $correo, string $clave): array
{
    $resultado = [];
    $anonimo = [];
    foreach (['portada', 'listado', 'ficha', 'carrito'] as $nombre) {
        if (!isset($rutas[$nombre])) {
            continue;
        }
        $p = humo_pedir($app, $anonimo, 'GET', $rutas[$nombre]);
        $resultado[$nombre] = ['url' => $rutas[$nombre], 'status' => $p['status'], 'bytes' => strlen($p['body']), 'nota' => $p['nota']];
    }
    $equipo = [];
    $entrada = humo_pedir($app, $equipo, 'POST', '/admin/login', ['email' => $correo, 'password' => $clave]);
    $p = humo_pedir($app, $equipo, 'GET', '/admin');
    $resultado['escritorio'] = ['url' => '/admin', 'status' => $p['status'], 'bytes' => strlen($p['body']),
        'nota' => $p['nota'] !== '' ? $p['nota'] : ($entrada['status'] >= 400 ? 'la entrada al panel respondió ' . $entrada['status'] : '')];

    return $resultado;
}

$resultado = ['ok' => false, 'id' => $id, 'problemas' => [], 'paginas' => [], 'notas' => [], 'avisos_php' => [], 'registro' => []];

$datos = $banco . '/sites';
$sitios = \Aifec\Kernel\SiteResolver::all($datos);
if (!isset($sitios[0])) {
    fwrite(STDERR, "el banco no tiene ningún sitio\n");
    exit(2);
}
$sitioId = (string) $sitios[0]['id'];
$app = humo_app($banco, $datos, $sitioId);
if ($app === null) {
    fwrite(STDERR, "el banco no tiene ningún sitio\n");
    exit(2);
}
try {
    $app->boot();
    $plugins = $app->service('plugins');
} catch (\Throwable $e) {
    fwrite(STDERR, 'el banco no tiene el gestor de plugins: ' . get_class($e) . ': ' . $e->getMessage() . "\n");
    exit(2);
}

$correo = 'humo-fabrica@ejemplo.test';
$clave = 'clave-de-mentira-1234';
$problemas = [];
$creadoUsuario = false;

try {
    // 0. El banco como si el plugin no se hubiera instalado nunca (por si una pasada anterior se cortó a medias).
    if (in_array($id, $plugins->activeIds(), true)) {
        $plugins->disable($id);
        $resultado['notas'][] = 'estaba activo de una pasada anterior: se desactiva';
    }
    $manifiesto = json_decode((string) file_get_contents($banco . '/plugins/' . $id . '/plugin.json'), true);
    $protegidas = $plugins->protectedTables($id);
    $esquema = new \Aifec\Db\Schema($app->db());
    if (is_array($manifiesto) && isset($manifiesto['contract']['tables']) && is_array($manifiesto['contract']['tables'])) {
        foreach ($manifiesto['contract']['tables'] as $tabla) {
            if (is_string($tabla) && preg_match('/^[a-z][a-z0-9_]*$/', $tabla) === 1 && !isset($protegidas[$tabla]) && $app->db()->tableExists($tabla)) {
                $esquema->drop($tabla);
                $resultado['notas'][] = 'quedaba la tabla «' . $tabla . '» de una pasada anterior: se borra';
            }
        }
    }
    (new \Aifec\Db\Migrator($app->db()))->forget($id);

    // Una persona del equipo para abrir el escritorio del panel; se borra al acabar.
    $ahora = $app->clock()->sql();
    $app->db()->delete('users', ['email' => $correo]);
    $app->db()->insert('users', [
        'email' => $correo, 'name' => 'Humo', 'password' => \Aifec\Security\Passwords::hash($clave), 'role' => 'admin',
        'locale' => 'es', 'active' => 1, 'created_at' => $ahora, 'updated_at' => $ahora,
    ]);
    $creadoUsuario = true;

    // Las direcciones de las cinco páginas. La ficha es la de un producto del banco; si no hay ninguno se crea uno.
    $buscar = $app->router()->has('search') ? route('search') : '/buscar';
    $rutas = ['portada' => '/', 'listado' => (string) preg_replace('#^https?://[^/]+#', '', (string) $buscar)];
    if ($app->modules()->isLoaded('catalog')) {
        // El listado es el de una categoría si el banco tiene alguna; si no, el del buscador de la tienda.
        $categoria = $app->db()->value('SELECT id FROM {categories} ORDER BY id');
        if ($categoria !== null && $categoria !== false) {
            $rutaCategoria = parse_url($app->url()->entity('category', (int) $categoria), PHP_URL_PATH);
            if (is_string($rutaCategoria) && $rutaCategoria !== '') {
                $rutas['listado'] = $rutaCategoria;
            }
        }
        $producto = $app->db()->value("SELECT id FROM {products} WHERE status = 'published' ORDER BY id");
        if ($producto === null || $producto === false) {
            $lang = $app->defaultLang();
            $producto = $app->db()->insert('products', [
                'kind' => 'physical', 'has_variants' => 0, 'price' => 1000, 'manage_stock' => 1, 'stock' => 10, 'status' => 'published',
                'visibility' => 'everywhere', 'published_at' => $ahora, 'created_at' => $ahora, 'updated_at' => $ahora,
            ]);
            $app->db()->insert('product_i18n', ['product_id' => $producto, 'lang' => $lang, 'name' => 'Reference product', 'summary' => '', 'description' => '']);
            $app->slugs()->set('product', (int) $producto, $lang, 'producto/reference-product');
            $resultado['notas'][] = 'el banco no tenía productos: se creó uno de referencia';
        }
        $ruta = parse_url($app->url()->entity('product', (int) $producto), PHP_URL_PATH);
        if (is_string($ruta) && $ruta !== '') {
            $rutas['ficha'] = $ruta;
        }
    }
    $carrito = $app->router()->has('cart') ? route('cart') : '/carrito';
    $rutas['carrito'] = (string) preg_replace('#^https?://[^/]+#', '', (string) $carrito);

    // 1. Sin el plugin: la línea de base.
    $avisosPhp = [];
    $base = humo_paginas($app, $rutas, $correo, $clave);
    $avisosBase = $avisosPhp;
    if (!isset($base['portada']) || $base['portada']['status'] !== 200) {
        $resultado['notas'][] = 'la portada del banco no responde 200 ni siquiera sin el plugin (' . (isset($base['portada']) ? $base['portada']['status'] : '?') . ')';
        $resultado['problemas'] = [];
        humo_salir($resultado, 2);
    }

    // 2. Con el plugin: se activa con el gestor (sin pasar otra vez el validador, que es de la puerta «contrato»).
    $r = $plugins->activate($id);
    if (!$r['ok']) {
        $problemas[] = 'no se puede activar: ' . (isset($r['message']) ? (string) $r['message'] : 'sin mensaje');
    } else {
        $logs = $app->site()->path('logs');
        $medidas = humo_tamanos($logs);
        $app2 = humo_app($banco, $datos, $sitioId);
        if ($app2 === null) {
            $problemas[] = 'no se pudo volver a abrir el sitio del banco con el plugin activo';
        } else {
            $avisosPhp = [];
            $con = humo_paginas($app2, $rutas, $correo, $clave);
            $avisosCon = $avisosPhp;
            foreach ($con as $nombre => $pagina) {
                $sin = isset($base[$nombre]) ? $base[$nombre] : null;
                $resultado['paginas'][$nombre] = ['url' => $pagina['url'], 'sin' => $sin !== null ? $sin['status'] : null, 'con' => $pagina['status']];
                if ($sin === null || $sin['status'] !== 200) {
                    $resultado['notas'][] = 'la página «' . $nombre . '» no responde 200 ni sin el plugin (' . ($sin !== null ? $sin['status'] : '?') . '): no se puede culpar al plugin';
                    continue;
                }
                if ($pagina['status'] !== 200) {
                    $problemas[] = 'la página «' . $nombre . '» (' . $pagina['url'] . ') responde ' . $pagina['status'] . ' con el plugin y 200 sin él'
                        . ($pagina['nota'] !== '' ? ' — ' . $pagina['nota'] : '');
                }
            }
            $nuevosAvisos = array_values(array_diff(array_unique($avisosCon), array_unique($avisosBase)));
            foreach (array_slice($nuevosAvisos, 0, 8) as $aviso) {
                $problemas[] = 'aviso de PHP nuevo con el plugin: ' . $aviso;
            }
            $resultado['avisos_php'] = $nuevosAvisos;
            $registro = humo_registro_nuevo($logs, $medidas);
            $resultado['registro'] = $registro;
            foreach (array_slice(array_values(array_unique($registro)), 0, 8) as $linea) {
                $problemas[] = 'el registro del sitio gana una línea nueva con el plugin: ' . str_replace('|', ' — ', $linea);
            }
            $plugins = $app2->service('plugins');
        }
    }
} catch (\Throwable $e) {
    $problemas[] = 'el humo se corta con una excepción: ' . get_class($e) . ': ' . $e->getMessage() . ' (' . basename($e->getFile()) . ':' . $e->getLine() . ')';
}

// Al acabar, el banco como estaba: sin el plugin, sin sus tablas y sin la persona de pega.
try {
    if (in_array($id, $plugins->activeIds(), true)) {
        $plugins->disable($id);
    }
    if (is_dir($banco . '/plugins/' . $id)) {
        $plugins->uninstall($id, false);
    }
    if ($creadoUsuario) {
        $app->db()->delete('users', ['email' => $correo]);
    }
} catch (\Throwable $e) {
    $resultado['notas'][] = 'no se pudo dejar el banco limpio: ' . $e->getMessage();
}

$resultado['problemas'] = $problemas;
$resultado['ok'] = $problemas === [];
humo_salir($resultado, 0);
