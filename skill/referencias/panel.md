# El panel: `admin.php` y `settings.php`

## Ajustes (`settings.php`)

Un solo fichero que devuelve un array con `title`, el permiso (`cap`) y las **pestañas**. Cada pestaña es una clave y lleva sus campos; cada campo es una clave de ajuste `<id_con_guiones_bajos>.nombre`.

```php
return [
    'title' => 'Wish list',
    'cap' => 'settings.edit',
    'tabs' => [
        'lista_deseos_general' => ['label' => 'General', 'fields' => [
            'lista_deseos.max_items' => [
                'type' => 'number', 'label' => 'Products per customer', 'hint' => 'The most products a customer can save (from 1 to 500)',
                'default' => 50, 'rules' => 'int|min:1|max:500', 'width' => 'sm',
            ],
        ]],
    ],
];
```

- **La clave de la pestaña lleva el nombre del plugin** (`lista_deseos_general`), nunca `general`, `content` o `main`: acaba como `id` del DOM del panel y puede chocar con uno que ya existe.
- **La clave del ajuste empieza por `<id_bajo>.`**: así el gestor la borra al desinstalar. Con otro prefijo se queda huérfana y la puerta `ciclo` la caza.
- Tipos habituales: `text`, `textarea`, `number`, `toggle`, `select`, `checks`. Reglas de validación en `rules` (`required|max:120`, `int|min:0|max:365`, `nullable`). `default` es el valor de fábrica y se lee con `$app->settings()->int('<clave>', <por defecto>)`, `->str()`, `->bool()`, `->arr()`.
- `label`, `hint` y `title` van **en inglés** y tienen su traducción en `lang/es.php`.
- Un ajuste que mueve algo de la tienda **no se lee dos veces con valores distintos**: léelo una vez y acótalo (`max(1, min(500, …))`).

## Recursos declarativos (`admin.php`)

Un listado y un formulario sin escribir un controlador:

```php
return [
    'caps' => ['punto_recogida.view' => 'See the pickup points', 'punto_recogida.edit' => 'Change the pickup points'],
    'menu' => [['group' => 'plugins', 'items' => [['label' => 'Pickup points', 'resource' => 'punto_recogida_points', 'cap' => 'punto_recogida.view', 'order' => 50]]]],
    'resources' => [
        'punto_recogida_points' => [
            'table' => 'punto_recogida_points', 'title' => 'Pickup points', 'singular' => 'Pickup point', 'label_field' => 'name', 'cap' => 'punto_recogida',
            'list' => ['columns' => ['name' => ['label' => 'Name', 'link' => true, 'sort' => true]], 'search' => ['name'], 'sort' => ['id', 'desc']],
            'form' => ['fields' => ['name' => ['label' => 'Name', 'rules' => 'required|max:120']]],
        ],
    ],
];
```

- Los permisos son del plugin (`<id_bajo>.view`, `<id_bajo>.edit`) y se declaran en `caps`; el recurso los usa con `'cap' => '<id_bajo>'`.
- La tabla del recurso es una tabla **propia** y declarada en `contract.tables`.
- **Dinero en el formulario: céntimos.** Un campo de precio guarda un entero; el listado lo enseña con `money()`.
- Para añadir **un campo al formulario de otro recurso** (productos), no se toca su definición: se usa el filtro `admin.definitions` y se guarda aparte al oír `admin.resource.saved` (modelo: `plantillas/esqueleto/hooks.php`).

## Pantallas propias

Si un recurso declarativo no basta, `routes.php` con un grupo `prefix => '/admin/<id>'` y `middleware => ['admin']`, un controlador en `src/` y vistas en `views/admin/`. Los envíos del panel llevan su ficha de formulario (`tokenField()` en la vista). Menú y permisos, igual que arriba.
