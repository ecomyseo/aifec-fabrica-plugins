---
name: fabrica-plugins-aifec
description: "Cómo construir un plugin de AIFEC (el sistema de comercio electrónico en PHP) que pase las siete puertas de la fábrica de plugins a la primera: declarar primero el contrato (dominios, datos personales, tablas, capacidades), partir del esqueleto, datos y migraciones, ganchos y rutas, panel, tienda, traducción, pruebas, y pasar `python fabrica.py puertas <id>` hasta que salga limpio. Usar siempre que se vaya a crear o a rehacer un plugin dentro de `salida/<id>/`."
---

# Construir un plugin de AIFEC que pase las puertas

Este skill lo sigue **cualquier IA de programación** (o una persona) que reciba un encargo de la fábrica de plugins. Se trabaja solo en `salida/<id>/`; la fábrica comprueba el resultado con siete puertas y no da nada por hecho hasta que todas pasan.

## Lo que hay que saber antes de empezar

- Un plugin es una carpeta con **piezas por convenio, todas opcionales** menos `plugin.json`: `hooks.php`, `routes.php`, `admin.php` (menú, recursos declarativos, permisos), `settings.php` (ajustes con pestañas), `jobs.php`, `cli.php`, `blocks.php`, `migrations/`, `views/`, `lang/`, `assets/`, `mail/`, `src/` y `tests/`. Nada más en la raíz: la puerta de limpieza rechaza el resto.
- El **Contrato AIFEC** (C1 a C10, en `skill/referencias/contrato.md`) lo comprueba el propio sistema con `php aifec contract:check <id>`. Aquí no se repite: se cumple.
- Lo que el plugin **declara** en `plugin.json` tiene que ser verdad: la puerta de ciclo mide las tablas que crea de verdad y la de contrato mira los dominios y los datos personales que usa de verdad.
- No se toca el sistema ni el banco (`estado/banco/`), no se sale a Internet y no se escribe fuera de `salida/<id>/`.
- Las convenciones de código del sistema valen aquí: PHP 7.4 a 8.4 sin avisos, cabecera exacta, `declare(strict_types=1)`, identificadores en inglés, comentarios en castellano, textos visibles en inglés dentro de `t('…')` con su traducción en `lang/es.php`. Las dudas, en `skill/referencias/fallos-frecuentes.md` (**léelo antes de la fase 3**).

## Fases (en este orden; no se salta ninguna)

### 1. Qué hace y qué toca

`python fabrica.py encargo <id>` escribe el encargo entero. Antes de una sola línea de código, **rellena la declaración del contrato en `plugin.json`** (el esqueleto trae `plugin.json` con la forma; si todavía no hay carpeta, apúntala en un borrador y pégala en la fase 2):

| Clave | Qué se declara | Se comprueba |
|---|---|---|
| `contract.hosts` | cada dominio al que llamará (`api.ejemplo.test`) | `contrato`: cualquier dominio que aparezca en el código y no esté aquí es un error |
| `contract.personal_data` | los datos de personas que lee o guarda (`email`, `name`, `address`, `phone`, `customer_id`…) | `contrato`: leer clientes o pedidos con la lista vacía es un error |
| `contract.tables` | **todas** sus tablas propias, sin prefijo | `ciclo`: las que aparecen al activar son exactamente estas, y las borra al desinstalar |
| `contract.capabilities` | `pricing` solo si toca precios, impuestos, plazos o disponibilidad a la vista | `contrato`: usar un gancho sellado sin la capacidad es un error |

Y responde por escrito (en el `LEEME.md`): qué hace, qué datos toca y a qué llama. Si hay duda sobre si algo cuenta como dato personal, **cuenta**.

### 2. Esqueleto

```
python skill/esqueleto.py <id> "<Nombre del plugin>"        crea salida/<id>/ desde plantillas/esqueleto/
```

Deja un plugin pequeño y completo que **ya pasa las siete puertas** (una nota por producto: hueco en la ficha, campo en el panel, ajuste, tabla, traducción y siete pruebas). Es un punto de partida: se sustituye por lo que haga el plugin y **se borra lo que no se use** (y se quita de `plugin.json` lo que ya no declare). Si el sistema trae `plugin:create`, también vale (`php aifec plugin:create <id> --name=… --features=…` en el banco), con otros ejemplos (carrier, tarea, bloque, pantalla). Y hay un plugin **completo y real hecho siguiendo este skill**, con rutas, páginas de la tienda, privacidad y diez pruebas, que pasa las siete puertas: `skill/ejemplos/lista-deseos/`. Se mira antes de escribir el propio.

### 3. Datos y migraciones

- Una migración por cambio en `migrations/NNNN_nombre.php` (se aplican en orden al activar y **no se editan una vez publicadas**: el cambio va en otra).
- Tablas con el prefijo del plugin (`lista_deseos_items`), declaradas en `contract.tables`. Nunca se toca una tabla del sistema ni de otro módulo.
- **Dinero, siempre en enteros de céntimos.** Nunca `float` para un importe.
- Lo que el plugin guarda en ajustes lleva su prefijo (`<id_con_guiones_bajos>.clave`): al desinstalar se borran por ese prefijo.
- Consultas con parámetros (`?`) y por la capa de datos del núcleo. Nunca se concatena un valor.

### 4. Ganchos y rutas

- Ganchos en `hooks.php`; cada oyente se atribuye al plugin y, si lanza, se anota y la página sigue (pero la puerta de humo lo cuenta como fallo). Lista en `skill/referencias/ganchos.md`.
- Rutas en `routes.php`; todo envío de un formulario por el intermediario `csrf`; lo que pide haber entrado, por `customer`.
- **Nada de recorrer históricos para mandar correos o llamar a terceros.** Un trabajo que avisa mira como mucho las últimas 24 horas y apunta una marca de enviado por registro; nunca «todos los pedidos» ni «todos los clientes».
- **Correo solo por el servicio común** (`mail`), nunca `mail()` ni un transporte propio. **IA solo por el servicio `ai`.**
- **Llamadas externas solo con `$app->http()`**, a dominios declarados y con tiempo límite.
- Fechas: se recibe el instante o se pide al reloj de la aplicación (`$app->clock()`), nunca `time()` ni `date()` sueltos en la lógica.

### 5. Panel

Recursos declarativos en `admin.php` (tabla, columnas, formulario, permisos propios `<id>.view` y `<id>.edit`), ajustes en `settings.php` con **pestañas cuyas claves llevan el nombre del plugin** (`lista_deseos_general`, nunca `general`) y ajustes con la clave `<id_bajo>.nombre`. Referencia en `skill/referencias/panel.md`.

### 6. Tienda

Se pinta en los **huecos** que el tema ofrece (`product.summary.after`, `cart.after`, `account.dashboard`…), con vistas del propio plugin (`views/front/…`, y `$app->view()->render('<id>::front/x', $datos)`). **Nunca se sustituye una plantilla del núcleo ni de un tema.** Todo dato impreso, por `e()`; nunca se imprime sin escapar. Sin recursos de otro dominio; los guiones y hojas propios, en `assets/` y ligeros (por encima de 60 KB es aviso; de 200 KB, error).

### 7. Traducción

Cada cadena visible, en inglés dentro de `t('…')` (y las etiquetas de `settings.php`, `admin.php` y del manifiesto), con su traducción en `lang/es.php`, en castellano con tildes y eñes. La clave es la inglesa tal cual. `python fabrica.py puertas <id> --solo traducciones` enseña las que faltan.

### 8. Pruebas

`tests/<Espacio>Test.php`, con las funciones del sistema (`test`, `check`, `same`, `contains`, `testApp`). **Las cuatro mínimas**: se activa y se carga, hace lo suyo, se desactiva, y pasa el contrato (también el ciclo de instalar y desinstalar). Más las de lo que hace: casos vacíos, `null`, texto con «&», comillas y emojis, y un oyente que lanza. Una prueba que no falla cuando el código está mal no vale: rompe a propósito una línea, comprueba que salta y deshazla.

### 9. Puertas

```
python fabrica.py puertas <id>
python skill/informe.py <id>          el detalle completo de cada puerta
```

Sale con 0 si ninguna puerta da 1. Léelo y arregla **la causa**, no el síntoma. Una puerta que sale «no aplica» no bloquea, pero tampoco demuestra nada: dilo en la entrega. Repite hasta `PUERTAS: n de n pasan`.

### 10. Entrega

El plugin está en `salida/<id>/` con su `LEEME.md` de una página (qué hace, cómo se configura, qué declara en el contrato). Se dice la última línea de las puertas tal cual y lo que no se pudo comprobar. **No** se dice «terminado» ni «aprobado»: eso lo decide una persona que lo mire.

## Lista de comprobación: las puertas y su medida

| Puerta | Pasa si… | Medida |
|---|---|---|
| `sintaxis` | `php -l` de cada fichero con `php` y cada `php_versiones` (7.4 y 8.4) | cero errores **y cero avisos**: un nullable implícito avisa en 8.4 aunque `php -l` salga con 0 |
| `contrato` | `php aifec contract:check <id>` sale sin errores | errores = 0, puntuación 100 |
| `pruebas` | `php tests/run.php plugins/<id>/` | al menos 4 pruebas y 0 fallan |
| `traducciones` | `php aifec i18n:check plugins/<id> es` | `0 missing` |
| `ciclo` | activar, desactivar, reactivar y desinstalar sin conservar datos | tablas creadas = `contract.tables`; tras desinstalar, ni una tabla ni un ajuste de más |
| `humo` | con el plugin activo, portada, listado, ficha, carrito y escritorio del panel | 200 donde ya lo daban sin él; ni un aviso de PHP ni una línea de error nuevos en el registro |
| `limpieza` | nada de sobra | sin paquetes, `vendor`, `composer.json`, capturas ni cosas fuera de las piezas por convenio; cabeceras exactas; sin credenciales con pinta de real; sin correos que no sean de ejemplo |

## Lo prohibido

- **Declarar menos de lo que hace**, o más de lo que hace: las dos cosas se miden.
- **Escribir precio, existencias, impuestos o plazos por fuera** de los cauces del sistema (C1).
- **Recorrer históricos** para disparar correos, WhatsApp, llamadas a terceros o sincronizaciones.
- `mail()`, `curl_*`, `file_get_contents('https://…')`, `exec`, `shell_exec`, `eval`, `extract`, `sleep`, `header()`, `exit` y `echo` en librerías.
- `(array) $x` como «un array o vacío» (se escribe `is_array($x) ? $x : []`); `match`, `readonly`, tipos unión, `?->` y argumentos con nombre (no valen en PHP 7.4); `Tipo $x = null` (se escribe `?Tipo $x = null`).
- Tocar el sistema (`core/`, `modules/`, otros plugins, temas) o el banco, o escribir fuera de `salida/<id>/`.
- Datos de ejemplo con pinta de reales: correos (`ana@cliente.test`), teléfonos (`600000001`), claves (`clave-de-mentira`). Nunca un caso real.
- Dar por bueno lo que no se ha comprobado.

## Referencias

- `skill/referencias/contrato.md` — C1 a C10, cada una con un ejemplo que cumple y otro que no.
- `skill/referencias/ganchos.md` — los ganchos más usados y dónde está la lista completa.
- `skill/referencias/panel.md` — `admin.php` y `settings.php`.
- `skill/referencias/fallos-frecuentes.md` — lo que ya ha hecho tropezar a alguien. **Léelo antes de la fase 3.**
- `skill/ejemplos/lista-deseos/` — un plugin de verdad hecho con este skill (encargo «lista de deseos» de `cola.ejemplo.json`).
- `docs/puertas.md` y `docs/primer-plugin.md` — qué mira cada puerta y el recorrido completo de un plugin.
