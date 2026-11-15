<?php
/**
 * AIFEC — __Nombre__: dónde se guarda la nota de cada producto.
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   Ver LICENSE.md
 */

declare(strict_types=1);

namespace Plugins\__Espacio__;

use Aifec\Kernel\App;

/**
 * La nota de cada producto vive en la tabla propia del plugin (`__id_bajo___notes`), declarada en `plugin.json`. Si un
 * producto no tiene la suya se usa la del ajuste «__id_bajo__.default_note».
 */
final class Notes
{
    /** @var App */
    private $app;

    public function __construct(App $app)
    {
        $this->app = $app;
    }

    /** La nota de un producto, o la del ajuste si no tiene ninguna; «» si no hay ni una ni otra. */
    public function get(int $productId): string
    {
        $default = $this->app->settings()->str('__id_bajo__.default_note');
        if ($productId < 1) {
            return $default;
        }
        $row = $this->app->db()->row('SELECT note FROM {__id_bajo___notes} WHERE product_id = ?', [$productId]);

        return $row !== null && trim((string) $row['note']) !== '' ? (string) $row['note'] : $default;
    }

    /** Guarda la nota de un producto; vacía la quita. */
    public function set(int $productId, string $note): void
    {
        if ($productId < 1) {
            return;
        }
        $db = $this->app->db();
        if ($note === '') {
            $db->delete('__id_bajo___notes', ['product_id' => $productId]);

            return;
        }
        $db->upsert('__id_bajo___notes', ['product_id' => $productId, 'note' => mb_substr($note, 0, 160), 'updated_at' => $this->app->clock()->sql()], ['product_id']);
    }
}
