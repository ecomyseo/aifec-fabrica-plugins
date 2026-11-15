<?php
/**
 * AIFEC — Lista de deseos: tabla de los productos guardados por cada cliente.
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   Ver LICENSE.md
 */

declare(strict_types=1);

use Aifec\Db\Db;
use Aifec\Db\Schema;
use Aifec\Db\TableDef;

return static function (Schema $schema, Db $db): void {
    $schema->create('lista_deseos_items', static function (TableDef $t): void {
        $t->bigInteger('customer_id');
        $t->bigInteger('product_id');
        $t->datetime('created_at');
        $t->primary(['customer_id', 'product_id']);
        $t->index(['product_id']);
    });
};
