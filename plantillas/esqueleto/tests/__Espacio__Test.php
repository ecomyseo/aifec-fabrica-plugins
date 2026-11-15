<?php
/**
 * AIFEC — pruebas de __Nombre__: se activa, hace lo suyo (nota en el producto, hueco, ajuste, campo del panel), se
 * desactiva y pasa el contrato (también el ciclo entero de instalar y desinstalar, que el validador hace en su sitio
 * de pruebas).
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   Ver LICENSE.md
 */

declare(strict_types=1);

use Aifec\Kernel\App;

require_once dirname(__DIR__, 3) . '/modules/catalog/tests/helpers.php';

/**
 * Sitio de pruebas con el catálogo, el gestor de plugins y el plugin activo.
 *
 * @param array<string,mixed> $settings
 */
function __id_bajo__Site(array $settings = []): App
{
    $app = testApp(['modules' => ['plugins', 'catalog', '__id__'], 'settings' => $settings + ['modules.active' => ['plugins', 'catalog', '__id__']]]);
    $app->migrate(true);
    $app->boot();

    return $app;
}

test('__id__ se activa, se carga y su migración crea la tabla', function (): void {
    $app = __id_bajo__Site();
    check($app->modules()->isLoaded('__id__'), 'el plugin está cargado');
    check(!isset($app->modules()->failed()['__id__']), 'no falló al cargar');
    check($app->db()->tableExists('__id_bajo___notes'), 'su migración creó la tabla');
});

test('__id__ guarda la nota de un producto y la quita al vaciarla', function (): void {
    $app = __id_bajo__Site();
    $id = aifecProduct($app, ['name' => 'Silla']);
    $notes = new Plugins\__Espacio__\Notes($app);
    same('', $notes->get($id));
    $notes->set($id, 'Montaje incluido');
    same('Montaje incluido', $notes->get($id));
    $notes->set($id, '');
    same('', $notes->get($id));
});

test('__id__ pinta la nota en el hueco de la ficha y escapa lo que viene de los datos', function (): void {
    $app = __id_bajo__Site();
    $id = aifecProduct($app, ['name' => 'Estantería']);
    (new Plugins\__Espacio__\Notes($app))->set($id, 'Pérez & <Hijos>');
    $html = $app->hooks()->render('product.summary.after', ['id' => $id]);
    contains('Nota: Pérez &amp; &lt;Hijos&gt;', $html);
    notContains('<Hijos>', $html);
    same('', $app->hooks()->render('product.summary.after', ['id' => 0]));
});

test('__id__ usa la nota del ajuste para los productos que no tienen la suya', function (): void {
    $app = __id_bajo__Site(['__id_bajo__.default_note' => 'Envío en 48 horas']);
    $own = aifecProduct($app, ['name' => 'Cama']);
    $other = aifecProduct($app, ['name' => 'Lámpara']);
    $notes = new Plugins\__Espacio__\Notes($app);
    $notes->set($own, 'Colchón aparte');
    same('Colchón aparte', $notes->get($own));
    same('Envío en 48 horas', $notes->get($other));
});

test('__id__ añade su campo al formulario de productos del panel y lo guarda en su tabla', function (): void {
    $app = __id_bajo__Site();
    $con = $app->hooks()->apply('admin.definitions', ['catalog' => ['resources' => ['products' => ['form' => ['fields' => []]]]]], $app);
    $campo = $con['catalog']['resources']['products']['form']['fields']['__id_bajo___note'];
    same('text', $campo['type']);
    same(false, $campo['store']);
    same(['x' => 1], $app->hooks()->apply('admin.definitions', ['x' => 1], $app));

    $id = aifecProduct($app, ['name' => 'Sofá']);
    $app->request()->post = ['f' => ['__id_bajo___note' => ' Entrega gratis ']];
    $app->hooks()->fire('admin.resource.saved', 'products', $id, [], null);
    same('Entrega gratis', (string) $app->db()->value('SELECT note FROM {__id_bajo___notes} WHERE product_id = ?', [$id]));
});

test('__id__ se desactiva y deja de cargarse', function (): void {
    $app = __id_bajo__Site();
    $r = $app->service('plugins')->disable('__id__');
    same(true, $r['ok'], (string) $r['message']);
    check(!in_array('__id__', $app->settings()->arr('modules.active'), true), 'ya no está en modules.active');
    $off = testApp(['modules' => ['plugins', 'catalog', '__id__'], 'settings' => ['modules.active' => $app->settings()->arr('modules.active')]]);
    $off->boot();
    check(!$off->modules()->isLoaded('__id__'), 'no se carga');
});

test('__id__ pasa el contrato AIFEC, también el ciclo entero de instalar y desinstalar', function (): void {
    $app = __id_bajo__Site();
    $plugins = $app->service('plugins');
    $plugins->useTempBase(tmpDir());
    $report = $plugins->validate('__id__');
    $errors = [];
    foreach ($report['checks'] as $check) {
        if (!$check['ok'] && $check['level'] === 'error') {
            $errors[] = $check['rule'] . ': ' . $check['message'] . ' ' . $check['file'] . ':' . $check['line'];
        }
    }
    same([], $errors);
    same(true, $report['ok']);
    same(true, $report['dynamic']);
});
