<?php
/**
 * AIFEC — pruebas de Lista de deseos: se activa, hace lo suyo (guardar, quitar, topes, privacidad, pantallas de la tienda),
 * se desactiva y pasa el contrato (también el ciclo entero de instalar y desinstalar, que el validador hace en su sitio de
 * pruebas).
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   Ver LICENSE.md
 */

declare(strict_types=1);

use Aifec\Kernel\App;
use Plugins\ListaDeseos\Wishlist;

require_once dirname(__DIR__, 3) . '/modules/catalog/tests/helpers.php';
require_once dirname(__DIR__, 3) . '/modules/customers/tests/CustomersKit.php';

/**
 * Sitio de pruebas con el catálogo, los clientes, el gestor de plugins y la lista de deseos activa.
 *
 * @param array<string,mixed> $settings
 */
function listaDeseosSite(array $settings = []): App
{
    $modules = ['plugins', 'catalog', 'customers', 'mail', 'lista-deseos'];
    $app = testApp(['modules' => $modules, 'settings' => $settings + ['modules.active' => $modules, 'mail.mode' => 'live', 'mail.from_email' => 'tienda@tienda.test']]);
    $app->migrate(true);
    $app->boot();

    return $app;
}

/** Un navegador de mentira que ya ha entrado como ese cliente. */
function listaDeseosLogin(App $app, string $email = 'ana@cliente.test'): TestClient
{
    $web = new TestClient($app);
    same(303, $web->post('/mi-cuenta/entrar', ['email' => $email, 'password' => 'clave-larga-1'])->status, 'entrar como ' . $email);

    return $web;
}

test('lista-deseos se activa, se carga y su migración crea la tabla', function (): void {
    $app = listaDeseosSite();
    check($app->modules()->isLoaded('lista-deseos'), 'el plugin está cargado');
    check(!isset($app->modules()->failed()['lista-deseos']), 'no falló al cargar');
    check($app->db()->tableExists('lista_deseos_items'), 'su migración creó la tabla');
});

test('lista-deseos guarda un producto una sola vez, lo quita y no guarda lo que el catálogo no enseña', function (): void {
    $app = listaDeseosSite();
    $customer = customersMakeAccount($app);
    $product = aifecProduct($app, ['name' => 'Silla']);
    $list = new Wishlist($app);
    same('ok', $list->add($customer, $product));
    same('already', $list->add($customer, $product));
    same(1, $list->count($customer));
    same('unknown', $list->add($customer, 987654), 'un producto que no existe');
    same('unknown', $list->add(0, $product), 'sin cliente');
    $list->remove($customer, $product);
    same(0, $list->count($customer));
    $list->remove($customer, $product);
    same(0, $list->count($customer), 'quitar lo que no está no falla');
});

test('lista-deseos respeta el tope del ajuste y lo acota entre 1 y 500', function (): void {
    $app = listaDeseosSite(['lista_deseos.max_items' => 2]);
    $customer = customersMakeAccount($app);
    $list = new Wishlist($app);
    same(2, $list->max());
    same('ok', $list->add($customer, aifecProduct($app, ['name' => 'Uno'])));
    same('ok', $list->add($customer, aifecProduct($app, ['name' => 'Dos'])));
    same('full', $list->add($customer, aifecProduct($app, ['name' => 'Tres'])));
    same(2, $list->count($customer));
    $app->settings()->set('lista_deseos.max_items', 0);
    same(1, $list->max(), 'por debajo de 1 sube a 1');
    $app->settings()->set('lista_deseos.max_items', 100000);
    same(500, $list->max(), 'por encima de 500 baja a 500');
});

test('lista-deseos: cada cliente solo ve su lista', function (): void {
    $app = listaDeseosSite();
    $ana = customersMakeAccount($app, 'ana@cliente.test');
    $luis = customersMakeAccount($app, 'luis@cliente.test');
    $silla = aifecProduct($app, ['name' => 'Silla']);
    $mesa = aifecProduct($app, ['name' => 'Mesa']);
    $list = new Wishlist($app);
    $list->add($ana, $silla);
    $list->add($luis, $mesa);
    same(['Silla'], array_column($list->products($ana), 'name'));
    same(['Mesa'], array_column($list->products($luis), 'name'));
    same([], $list->products(999), 'un cliente sin lista');
});

test('lista-deseos pinta el botón en el hueco de la ficha, sin nada de quien mira, y no pinta sin producto', function (): void {
    $app = listaDeseosSite();
    $id = aifecProduct($app, ['name' => 'Estantería']);
    $html = $app->hooks()->render('product.summary.after', ['id' => $id]);
    contains('action="', $html);
    contains('/mi-cuenta/lista-deseos/anadir/' . $id, $html);
    contains('Guardar en mi lista de deseos', $html);
    same($html, $app->hooks()->render('product.summary.after', ['id' => $id]), 'siempre lo mismo: la página se puede cachear');
    same('', $app->hooks()->render('product.summary.after', ['id' => 0]));
});

test('lista-deseos: la tienda guarda, enseña (escapado) y quita desde las pantallas de un cliente con sesión', function (): void {
    $app = listaDeseosSite();
    customersMakeAccount($app);
    $id = aifecProduct($app, ['name' => 'Pérez & <Hijos> "Silla"']);
    $web = listaDeseosLogin($app);

    $r = $web->post('/mi-cuenta/lista-deseos/anadir/' . $id);
    same(303, $r->status);
    same('/mi-cuenta/lista-deseos', $r->headers['Location']);
    $r = $web->follow();
    same(200, $r->status);
    contains('Guardado en tu lista de deseos', $r->body);
    contains('Pérez &amp; &lt;Hijos&gt; &quot;Silla&quot;', $r->body);
    notContains('<Hijos>', $r->body);
    contains('no-store', $r->headers['Cache-Control']);

    $r = $web->post('/mi-cuenta/lista-deseos/quitar/' . $id);
    same(303, $r->status);
    $r = $web->follow();
    contains('Tu lista de deseos está vacía.', $r->body);
    contains('Quitado de tu lista de deseos', $r->body);
});

test('lista-deseos: sin sesión manda a entrar y no guarda nada, un envío de otra web se rechaza y un producto que no existe es un 404', function (): void {
    $app = listaDeseosSite();
    $customer = customersMakeAccount($app);
    $id = aifecProduct($app, ['name' => 'Silla']);

    $anon = new TestClient($app);
    $r = $anon->post('/mi-cuenta/lista-deseos/anadir/' . $id);
    check(in_array($r->status, [302, 303], true), 'sin sesión se redirige');
    contains('/entrar', $r->headers['Location']);
    same(0, (int) $app->db()->value('SELECT COUNT(*) FROM {lista_deseos_items}'));

    $web = listaDeseosLogin($app);
    same(403, $web->post('/mi-cuenta/lista-deseos/anadir/' . $id, [], ['sec-fetch-site' => 'cross-site'])->status, 'otra web no puede hacer guardar');
    same(0, (new Wishlist($app))->count($customer));
    same(404, $web->post('/mi-cuenta/lista-deseos/anadir/987654')->status);
});

test('lista-deseos: la lista se borra al anonimizar al cliente y viaja en la copia de sus datos', function (): void {
    $app = listaDeseosSite();
    $customer = customersMakeAccount($app);
    $other = customersMakeAccount($app, 'luis@cliente.test');
    $id = aifecProduct($app, ['name' => 'Silla']);
    $list = new Wishlist($app);
    $list->add($customer, $id);
    $list->add($other, $id);

    $export = $app->service('customers')->exportData($customer);
    same([$id], array_column($export['wish_list'], 'product_id'));
    check(is_array($export['customer']), 'el resto de la copia sigue ahí');

    $app->service('customers')->anonymise($customer);
    same(0, $list->count($customer), 'la lista del cliente anonimizado se va');
    same(1, $list->count($other), 'la de otro cliente no se toca');
});

test('lista-deseos se desactiva y deja de cargarse', function (): void {
    $app = listaDeseosSite();
    $r = $app->service('plugins')->disable('lista-deseos');
    same(true, $r['ok'], (string) $r['message']);
    check(!in_array('lista-deseos', $app->settings()->arr('modules.active'), true), 'ya no está en modules.active');
    $off = testApp(['modules' => ['plugins', 'catalog', 'customers', 'mail', 'lista-deseos'], 'settings' => ['modules.active' => $app->settings()->arr('modules.active')]]);
    $off->boot();
    check(!$off->modules()->isLoaded('lista-deseos'), 'no se carga');
});

test('lista-deseos pasa el contrato AIFEC, también el ciclo entero de instalar y desinstalar', function (): void {
    $app = listaDeseosSite();
    $plugins = $app->service('plugins');
    $plugins->useTempBase(tmpDir());
    $report = $plugins->validate('lista-deseos');
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
