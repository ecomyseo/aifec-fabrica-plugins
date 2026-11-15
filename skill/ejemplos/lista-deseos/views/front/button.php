<?php
/**
 * AIFEC — Lista de deseos: botón «guardar» de la ficha del producto.
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   Ver LICENSE.md
 *
 * @var string $action
 */

?>
<form class="lista-deseos-button" method="post" action="<?= e($action) ?>">
    <button type="submit" class="af-btn af-btn-ghost"><?= e(t('Save in my wish list')) ?></button>
</form>
