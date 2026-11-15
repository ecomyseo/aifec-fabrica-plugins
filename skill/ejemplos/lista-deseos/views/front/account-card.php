<?php
/**
 * AIFEC — Lista de deseos: acceso desde Mi cuenta.
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   Ver LICENSE.md
 *
 * @var string $url
 * @var int $count
 */

?>
<section class="af-grid af-cols-2" aria-label="<?= e(t('My wish list')) ?>">
    <a class="af-card" href="<?= e($url) ?>"><strong><?= e(t('My wish list')) ?></strong><br><span class="af-muted af-small"><?= e(tn('{n} product saved|{n} products saved', $count)) ?></span></a>
</section>
