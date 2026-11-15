<?php
/**
 * AIFEC — Lista de deseos: la lista de cada cliente (guardar, quitar, leer, borrar y exportar).
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   Ver LICENSE.md
 */

declare(strict_types=1);

namespace Plugins\ListaDeseos;

use Aifec\Kernel\App;

/**
 * La lista vive en la tabla propia del plugin (`lista_deseos_items`), declarada en `plugin.json`: un producto por cliente
 * una sola vez. Solo se guardan productos que el catálogo enseña, y no más de «lista_deseos.max_items» por cliente.
 */
final class Wishlist
{
    public const DEFAULT_MAX = 50;

    /** @var App */
    private $app;

    public function __construct(App $app)
    {
        $this->app = $app;
    }

    /** El tope de productos por cliente (entre 1 y 500). */
    public function max(): int
    {
        return max(1, min(500, $this->app->settings()->int('lista_deseos.max_items', self::DEFAULT_MAX)));
    }

    /**
     * Guarda un producto en la lista. Devuelve «ok» (o «already» si ya estaba), «unknown» si el catálogo no lo enseña y
     * «full» si la lista ya tiene el máximo.
     */
    public function add(int $customerId, int $productId): string
    {
        if ($customerId < 1 || $productId < 1) {
            return 'unknown';
        }
        if ($this->app->service('catalog')->product($productId) === null) {
            return 'unknown';
        }
        if ($this->has($customerId, $productId)) {
            return 'already';
        }
        if ($this->count($customerId) >= $this->max()) {
            return 'full';
        }
        $this->app->db()->insert('lista_deseos_items', [
            'customer_id' => $customerId, 'product_id' => $productId, 'created_at' => $this->app->clock()->sql(),
        ]);

        return 'ok';
    }

    public function remove(int $customerId, int $productId): void
    {
        if ($customerId < 1 || $productId < 1) {
            return;
        }
        $this->app->db()->delete('lista_deseos_items', ['customer_id' => $customerId, 'product_id' => $productId]);
    }

    public function has(int $customerId, int $productId): bool
    {
        return (int) $this->app->db()->value('SELECT COUNT(*) FROM {lista_deseos_items} WHERE customer_id = ? AND product_id = ?', [$customerId, $productId]) > 0;
    }

    public function count(int $customerId): int
    {
        return (int) $this->app->db()->value('SELECT COUNT(*) FROM {lista_deseos_items} WHERE customer_id = ?', [$customerId]);
    }

    /**
     * Los productos de un cliente, del último guardado al primero, ya con su ficha del catálogo (los que el catálogo
     * deja de enseñar no salen, aunque sigan guardados).
     *
     * @return array<int,array<string,mixed>>
     */
    public function products(int $customerId): array
    {
        $ids = array_map('intval', $this->app->db()->column(
            'SELECT product_id FROM {lista_deseos_items} WHERE customer_id = ? ORDER BY created_at DESC, product_id DESC',
            [$customerId]
        ));
        if ($ids === []) {
            return [];
        }

        return array_values($this->app->service('catalog')->products($ids));
    }

    /** Borra la lista de un cliente (cuando pide que se le olvide). Devuelve cuántos productos quitó. */
    public function forget(int $customerId): int
    {
        if ($customerId < 1) {
            return 0;
        }
        $count = $this->count($customerId);
        $this->app->db()->delete('lista_deseos_items', ['customer_id' => $customerId]);

        return $count;
    }

    /**
     * Lo que se entrega en la copia de los datos de un cliente.
     *
     * @return array<int,array{product_id:int,saved_at:string}>
     */
    public function export(int $customerId): array
    {
        $rows = [];
        foreach ($this->app->db()->select('SELECT product_id, created_at FROM {lista_deseos_items} WHERE customer_id = ? ORDER BY created_at, product_id', [$customerId]) as $row) {
            $rows[] = ['product_id' => (int) $row['product_id'], 'saved_at' => (string) $row['created_at']];
        }

        return $rows;
    }
}
