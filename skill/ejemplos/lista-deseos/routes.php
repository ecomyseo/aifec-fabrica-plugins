<?php
/**
 * AIFEC — Lista de deseos: rutas de la tienda. Solo para clientes con sesión y los envíos solo desde la propia web.
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   Ver LICENSE.md
 */

declare(strict_types=1);

use Aifec\Kernel\App;
use Aifec\Kernel\Router;
use Plugins\ListaDeseos\WishlistController;

return static function (Router $r, App $app): void {
    $account = trim($app->settings()->str('urls.account', 'mi-cuenta'), '/');
    $account = '/' . ($account !== '' ? $account : 'mi-cuenta');

    $r->group(['prefix' => $account . '/lista-deseos', 'middleware' => ['customer', 'csrf']], static function (Router $r): void {
        $r->get('', [WishlistController::class, 'index'])->name('lista_deseos.list');
        $r->post('/anadir/{id:\d+}', [WishlistController::class, 'add'])->name('lista_deseos.add');
        $r->post('/quitar/{id:\d+}', [WishlistController::class, 'remove'])->name('lista_deseos.remove');
    });
};
