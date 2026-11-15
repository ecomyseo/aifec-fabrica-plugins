<?php
/**
 * AIFEC — Lista de deseos: ajustes. Las claves de pestaña llevan el nombre del plugin y las de ajuste, su zona.
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   Ver LICENSE.md
 */

declare(strict_types=1);

return [
    'title' => 'Wish list',
    'cap' => 'settings.edit',
    'tabs' => [
        'lista_deseos_general' => ['label' => 'General', 'fields' => [
            'lista_deseos.max_items' => [
                'type' => 'number', 'label' => 'Products per customer', 'hint' => 'The most products a customer can save (from 1 to 500)', 'default' => 50, 'rules' => 'int|min:1|max:500', 'width' => 'sm',
            ],
        ]],
    ],
];
