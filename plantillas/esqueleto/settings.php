<?php
/**
 * AIFEC — __Nombre__: ajustes. Las claves de pestaña llevan el nombre del plugin y las de ajuste, su zona.
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   Ver LICENSE.md
 */

declare(strict_types=1);

return [
    'title' => '__Nombre__',
    'cap' => 'settings.edit',
    'tabs' => [
        '__id_bajo___general' => ['label' => 'General', 'fields' => [
            '__id_bajo__.default_note' => [
                'type' => 'text', 'label' => 'Default note', 'hint' => 'Shown on the products that do not have their own note', 'default' => '', 'rules' => 'max:160',
            ],
        ]],
    ],
];
