<?php
/**
 * AIFEC — Lista de deseos: la página con los productos guardados.
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   Ver LICENSE.md
 *
 * @var array<string,mixed> $page
 * @var array<int,array<string,mixed>> $products fichas del catálogo
 * @var string $message
 * @var int $max
 */

declare(strict_types=1);

$this->layout('layout', ['page' => $page]);
?>
<div class="af-container af-section">
    <h1 class="af-title"><?= e(t('My wish list')) ?></h1>
<?php if ($message !== '') : ?>
    <p class="af-card" role="status"><?= e($message) ?></p>
<?php endif; ?>
<?php if ($products === []) : ?>
    <div class="af-card af-empty">
        <p class="af-empty-title"><?= e(t('Your wish list is empty.')) ?></p>
    </div>
<?php else : ?>
    <ul class="af-stack">
<?php foreach ($products as $af_product) : ?>
        <li class="af-card af-row">
            <a href="<?= e((string) $af_product['url']) ?>"><strong><?= e((string) $af_product['name']) ?></strong></a>
<?php if (isset($af_product['price']['amount'])) : ?>
            <span class="af-muted"><?= e(money((int) $af_product['price']['amount'])) ?></span>
<?php endif; ?>
            <form method="post" action="<?= e(route('lista_deseos.remove', ['id' => (int) $af_product['id']])) ?>">
                <button type="submit" class="af-btn af-btn-sm af-btn-ghost"><?= e(t('Remove')) ?></button>
            </form>
        </li>
<?php endforeach; ?>
    </ul>
<?php endif; ?>
    <p class="af-muted af-small"><?= e(t('You can save up to {n} products.', ['n' => $max])) ?></p>
</div>
