<?php
/**
 * AIFEC — __Nombre__: tabla de la nota de cada producto.
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
    $schema->create('__id_bajo___notes', static function (TableDef $t): void {
        $t->bigInteger('product_id');
        $t->string('note', 160);
        $t->datetime('updated_at');
        $t->primary(['product_id']);
    });
};
