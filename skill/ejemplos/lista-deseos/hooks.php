<?php
/**
 * AIFEC — Lista de deseos: el botón de la ficha, el acceso desde Mi cuenta y lo que hace con los datos del cliente.
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   Ver LICENSE.md
 */

declare(strict_types=1);

use Aifec\Kernel\App;
use Plugins\ListaDeseos\Wishlist;

return static function (App $app): void {
    // 1. El botón «guardar» bajo el resumen de la ficha. No lleva nada de quien mira (la página se puede cachear): es un
    //    formulario que, sin sesión, manda a entrar.
    $app->hooks()->slot('product.summary.after', static function ($product) use ($app): string {
        $id = is_array($product) && isset($product['id']) ? (int) $product['id'] : 0;
        if ($id < 1) {
            return '';
        }

        return $app->view()->render('lista-deseos::front/button', ['action' => $app->url()->route('lista_deseos.add', ['id' => $id])]);
    });

    // 2. El acceso desde Mi cuenta, con cuántos productos lleva.
    $app->hooks()->slot('account.dashboard', static function ($customer) use ($app): string {
        $id = is_array($customer) && isset($customer['id']) ? (int) $customer['id'] : 0;
        if ($id < 1) {
            return '';
        }

        return $app->view()->render('lista-deseos::front/account-card', [
            'url' => $app->url()->route('lista_deseos.list'), 'count' => (new Wishlist($app))->count($id),
        ]);
    });

    // 3. Datos personales: la lista se borra con el cliente y viaja en la copia de sus datos.
    $app->hooks()->on('customer.anonymised', static function ($customerId) use ($app): void {
        (new Wishlist($app))->forget((int) $customerId);
    });
    $app->hooks()->filter('customer.export', static function ($data, $customerId) use ($app) {
        if (!is_array($data)) {
            return $data;
        }
        $data['wish_list'] = (new Wishlist($app))->export((int) $customerId);

        return $data;
    });
};
