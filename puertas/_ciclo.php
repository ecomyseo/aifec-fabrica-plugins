<?php
/**
 * AIFEC — fábrica de plugins: el ciclo de vida de un plugin en el banco.
 *
 *   php _ciclo.php --banco <estado/banco> --id <plugin>
 *
 * Con el gestor de plugins del propio sistema activa el candidato (que ya está en `<banco>/plugins/<id>`; sin pasar
 * otra vez el validador, que es de la puerta «contrato»), lo desactiva, lo vuelve a activar y lo desinstala sin
 * conservar datos. Apunta las tablas y los ajustes del sitio del
 * banco antes de empezar, con el plugin activo y después de desinstalar, y comprueba: que las tablas que aparecen al
 * activar son exactamente las que declara `contract.tables`; que desactivar no pierde datos y reactivar no cambia el
 * esquema; y que tras desinstalar el sitio queda como estaba (ni una tabla ni un ajuste de más).
 *
 * Escribe en su última línea `CICLO {json}` con `ok`, `problemas`, `pasos` y las listas de tablas. Sale con 0 si ha
 * llegado hasta el final (haya o no problemas: eso lo dice el JSON), con 2 si falta algo (el banco, su sitio o el
 * gestor de plugins) y con 1 si revienta por dentro.
 *
 * Solo toca el banco (una copia de trabajo), nunca la instalación de origen. Si una pasada anterior se cortó a medias,
 * lo primero que hace es dejar el banco como si el plugin no se hubiera instalado nunca.
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
    fwrite(STDERR, "uso: php _ciclo.php --banco <banco> --id <plugin>\n");
    exit(2);
}
if (!is_file($banco . '/plugins/' . $id . '/plugin.json')) {
    fwrite(STDERR, 'el candidato no está instalado en el banco (falta plugins/' . $id . "/plugin.json)\n");
    exit(2);
}

error_reporting(E_ALL);
ini_set('display_errors', '0');

require $banco . '/core/bootstrap.php';

/** Los avisos de PHP que salen de ficheros del plugin mientras se hace el ciclo: «fichero:línea mensaje». */
$avisosDelPlugin = [];
set_error_handler(static function (int $no, string $texto, string $fichero, int $linea) use (&$avisosDelPlugin, $id): bool {
    if ((error_reporting() & $no) === 0) {
        return false;
    }
    if (strpos(str_replace('\\', '/', $fichero), '/plugins/' . $id . '/') !== false) {
        $avisosDelPlugin[] = basename($fichero) . ':' . $linea . ' ' . $texto;
    }

    return true;
});

/**
 * Escribe el resultado y sale.
 *
 * @param array<string,mixed> $resultado
 */
function ciclo_salir(array $resultado, int $codigo): void
{
    echo 'CICLO ' . json_encode($resultado, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PARTIAL_OUTPUT_ON_ERROR) . "\n";
    exit($codigo);
}

/**
 * Las tablas (sin el prefijo del sitio) y los ajustes del sitio, sin lo que el propio gestor cambia al activar.
 *
 * @return array{tables:string[],settings:array<string,string>}
 */
function ciclo_foto(\Aifec\Kernel\App $app): array
{
    $db = $app->db();
    $prefijo = $db->prefix();
    $nombres = $db->driver() === 'sqlite'
        ? $db->column("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite%'")
        : $db->column('SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE()');
    $tablas = [];
    foreach ($nombres as $real) {
        $real = (string) $real;
        if ($prefijo !== '' && strpos($real, $prefijo) !== 0) {
            continue;
        }
        $tablas[] = substr($real, strlen($prefijo));
    }
    sort($tablas);
    $ajustes = [];
    foreach ($db->select('SELECT k, v FROM {settings}') as $fila) {
        $clave = (string) $fila['k'];
        if (!in_array($clave, ['modules.active', 'plugins.reports', 'plugins.granted'], true)) {
            $ajustes[$clave] = (string) $fila['v'];
        }
    }
    ksort($ajustes);

    return ['tables' => $tablas, 'settings' => $ajustes];
}

/** El texto de un resultado del gestor (`ok`, `message`, `errors`), para contarlo en un problema. */
function ciclo_motivo(array $r): string
{
    $texto = isset($r['message']) ? (string) $r['message'] : 'sin mensaje';
    if (isset($r['errors']) && is_array($r['errors']) && $r['errors'] !== []) {
        $texto .= ' — ' . implode(' | ', array_slice(array_map('strval', $r['errors']), 0, 3));
    }

    return $texto;
}

$resultado = ['ok' => false, 'id' => $id, 'problemas' => [], 'pasos' => [], 'declaradas' => [], 'creadas' => [], 'antes' => 0, 'activo' => 0, 'despues' => 0, 'notas' => []];

$datos = $banco . '/sites';
$sitios = \Aifec\Kernel\SiteResolver::all($datos);
$sitio = isset($sitios[0]) ? \Aifec\Kernel\SiteResolver::load($datos, $sitios[0]['id']) : null;
if ($sitio === null) {
    fwrite(STDERR, "el banco no tiene ningún sitio\n");
    exit(2);
}
$sitio->host = 'banco.test';
$app = new \Aifec\Kernel\App($sitio, $banco, ['public_dir' => $banco . '/public', 'log_files' => false]);
$app->makeCurrent();

try {
    $app->boot();
    $plugins = $app->service('plugins');
} catch (\Throwable $e) {
    fwrite(STDERR, 'el banco no tiene el gestor de plugins: ' . get_class($e) . ': ' . $e->getMessage() . "\n");
    exit(2);
}

$manifiesto = json_decode((string) file_get_contents($banco . '/plugins/' . $id . '/plugin.json'), true);
$declaradas = [];
if (is_array($manifiesto) && isset($manifiesto['contract']['tables']) && is_array($manifiesto['contract']['tables'])) {
    foreach ($manifiesto['contract']['tables'] as $tabla) {
        if (is_string($tabla)) {
            $declaradas[] = $tabla;
        }
    }
}
sort($declaradas);
$resultado['declaradas'] = $declaradas;
$problemas = [];

try {
    // 0. El banco como si el plugin no se hubiera instalado nunca (por si una pasada anterior se cortó a medias).
    if (in_array($id, $plugins->activeIds(), true)) {
        $plugins->disable($id);
        $resultado['notas'][] = 'estaba activo de una pasada anterior: se desactiva';
    }
    $protegidas = $plugins->protectedTables($id);
    $esquema = new \Aifec\Db\Schema($app->db());
    foreach ($declaradas as $tabla) {
        if (preg_match('/^[a-z][a-z0-9_]*$/', $tabla) === 1 && !isset($protegidas[$tabla]) && $app->db()->tableExists($tabla)) {
            $esquema->drop($tabla);
            $resultado['notas'][] = 'quedaba la tabla «' . $tabla . '» de una pasada anterior: se borra';
        }
    }
    (new \Aifec\Db\Migrator($app->db()))->forget($id);
    $antes = ciclo_foto($app);
    $resultado['antes'] = count($antes['tables']);

    // 1. Activar con el gestor, sin repetir el validador del contrato (eso es de la puerta «contrato»): así el ciclo
    //    mide lo que hace el plugin aunque su contrato esté mal, y dice las tablas de más o de menos.
    $r = $plugins->activate($id);
    $resultado['pasos'][] = 'activar: ' . ($r['ok'] ? 'bien' : 'falla');
    if (!$r['ok']) {
        $problemas[] = 'no se puede activar: ' . ciclo_motivo($r);
    } else {
        $activo = ciclo_foto($app);
        $resultado['activo'] = count($activo['tables']);
        $creadas = array_values(array_diff($activo['tables'], $antes['tables']));
        $resultado['creadas'] = $creadas;
        foreach ($creadas as $tabla) {
            if (!in_array($tabla, $declaradas, true)) {
                $problemas[] = 'al activarse crea la tabla «' . $tabla . '» y no la declara en contract.tables';
            }
        }
        foreach ($declaradas as $tabla) {
            if (!in_array($tabla, $creadas, true)) {
                $problemas[] = 'declara la tabla «' . $tabla . '» en contract.tables pero no la crea al activarse';
            }
        }
        if (!in_array($id, $plugins->activeIds(), true)) {
            $problemas[] = 'tras activarlo no aparece entre los plugins activos';
        }

        // 2. Desactivar: los datos se conservan.
        $r = $plugins->disable($id);
        $resultado['pasos'][] = 'desactivar: ' . ($r['ok'] ? 'bien' : 'falla');
        if (!$r['ok']) {
            $problemas[] = 'no se puede desactivar: ' . ciclo_motivo($r);
        } else {
            if (in_array($id, $plugins->activeIds(), true)) {
                $problemas[] = 'tras desactivarlo sigue entre los plugins activos';
            }
            $desactivado = ciclo_foto($app);
            foreach (array_diff($activo['tables'], $desactivado['tables']) as $tabla) {
                $problemas[] = 'al desactivarse pierde la tabla «' . $tabla . '»: los datos se conservan hasta desinstalar';
            }
        }

        // 3. Volver a activar: nada nuevo en el esquema.
        $r = $plugins->activate($id);
        $resultado['pasos'][] = 'reactivar: ' . ($r['ok'] ? 'bien' : 'falla');
        if (!$r['ok']) {
            $problemas[] = 'no se puede volver a activar: ' . ciclo_motivo($r);
        } else {
            $reactivado = ciclo_foto($app);
            if ($reactivado['tables'] !== $activo['tables']) {
                $problemas[] = 'al volver a activarse cambia el esquema: ' . implode(', ', array_merge(
                    array_map(static function ($t) {
                        return '+' . $t;
                    }, array_diff($reactivado['tables'], $activo['tables'])),
                    array_map(static function ($t) {
                        return '-' . $t;
                    }, array_diff($activo['tables'], $reactivado['tables']))
                ));
            }
        }
    }

    // 4. Desactivar y desinstalar sin conservar datos.
    if (in_array($id, $plugins->activeIds(), true)) {
        $plugins->disable($id);
    }
    $r = $plugins->uninstall($id, false);
    $resultado['pasos'][] = 'desinstalar: ' . ($r['ok'] ? 'bien' : 'falla');
    if (!$r['ok']) {
        $problemas[] = 'no se puede desinstalar: ' . ciclo_motivo($r);
    }
    $despues = ciclo_foto($app);
    $resultado['despues'] = count($despues['tables']);
    foreach (array_diff($despues['tables'], $antes['tables']) as $tabla) {
        $problemas[] = 'tras desinstalar sin conservar datos se queda la tabla «' . $tabla . '»';
    }
    foreach (array_diff($antes['tables'], $despues['tables']) as $tabla) {
        $problemas[] = 'al desinstalar desaparece la tabla «' . $tabla . '», que no era suya';
    }
    foreach ($despues['settings'] as $clave => $valor) {
        if (!array_key_exists($clave, $antes['settings'])) {
            $problemas[] = 'tras desinstalar sin conservar datos se queda el ajuste «' . $clave . '»';
        } elseif ($antes['settings'][$clave] !== $valor) {
            $problemas[] = 'al desinstalar cambia el ajuste «' . $clave . '», que no era suyo';
        }
    }
    foreach (array_keys($antes['settings']) as $clave) {
        if (!array_key_exists($clave, $despues['settings'])) {
            $problemas[] = 'al desinstalar desaparece el ajuste «' . $clave . '», que no era suyo';
        }
    }
} catch (\Throwable $e) {
    $problemas[] = 'el ciclo se corta con una excepción: ' . get_class($e) . ': ' . $e->getMessage() . ' (' . basename($e->getFile()) . ':' . $e->getLine() . ')';
    // Que el banco no se quede con el plugin puesto para las puertas siguientes.
    try {
        if (in_array($id, $plugins->activeIds(), true)) {
            $plugins->disable($id);
        }
        if (is_dir($banco . '/plugins/' . $id)) {
            $plugins->uninstall($id, false);
        }
    } catch (\Throwable $ignorada) {
        $resultado['notas'][] = 'no se pudo dejar el banco limpio: ' . $ignorada->getMessage();
    }
}

foreach (array_slice(array_values(array_unique($avisosDelPlugin)), 0, 5) as $aviso) {
    $problemas[] = 'el código del plugin lanza un aviso de PHP durante el ciclo: ' . $aviso;
}
$resultado['problemas'] = $problemas;
$resultado['ok'] = $problemas === [];
ciclo_salir($resultado, 0);
