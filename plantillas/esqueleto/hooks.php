<?php
/**
 * AIFEC — __Nombre__: la nota del producto, su campo en el panel y su hueco en la ficha.
 *
 * Es el esqueleto de la fábrica de plugins: pequeño, completo y con su prueba. Se sustituye por lo que haga
 * el plugin de verdad; lo que no se use se borra (y se quita de `plugin.json` lo que ya no declare).
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   Ver LICENSE.md
 */

declare(strict_types=1);

use Aifec\Kernel\App;
use Plugins\__Espacio__\Notes;

return static function (App $app): void {
    // 1. Un hueco en la ficha: el tema decide dónde pone «product.summary.after». Lo que viene de un dato se escapa en la vista.
    $app->hooks()->slot('product.summary.after', static function ($product) use ($app): string {
        $note = (new Notes($app))->get(is_array($product) && isset($product['id']) ? (int) $product['id'] : 0);

        return $note === '' ? '' : $app->view()->render('__id__::front/note', ['note' => $note]);
    });

    // 2. Su campo en el formulario del producto del panel (filtro «admin.definitions»). No se guarda en la tabla de
    //    productos: lo guarda este plugin en la suya cuando el panel avisa de que se ha guardado un producto.
    $app->hooks()->filter('admin.definitions', static function ($definitions): array {
        $definitions = is_array($definitions) ? $definitions : [];
        $form = isset($definitions['catalog']['resources']['products']['form']) ? $definitions['catalog']['resources']['products']['form'] : null;
        if (is_array($form) && isset($form['fields']) && is_array($form['fields'])) {
            $definitions['catalog']['resources']['products']['form']['fields']['__id_bajo___note'] = [
                'type' => 'text', 'label' => 'Note', 'hint' => 'Short note shown under the product summary', 'store' => false,
            ];
        }

        return $definitions;
    });
    $app->hooks()->on('admin.resource.saved', static function ($resource, $id) use ($app): void {
        if ($resource !== 'products' || !is_numeric($id)) {
            return;
        }
        $form = $app->request()->arr('f');
        if (array_key_exists('__id_bajo___note', $form) && is_string($form['__id_bajo___note'])) {
            (new Notes($app))->set((int) $id, trim($form['__id_bajo___note']));
        }
    });
};
