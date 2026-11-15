# Fábrica de plugins de AIFEC

Toma encargos de una cola y los lleva, uno a uno y sin perder el hilo aunque se apague el equipo, hasta «hecho» o «atascado». Cada encargo es un plugin de AIFEC: la fábrica prepara el esqueleto, entrega el trabajo a un **motor** (una IA de programación o una persona) y no da nada por hecho hasta que pasa todas las **puertas**, incluida la que activa, desactiva y desinstala el plugin en un sitio de pruebas y la que comprueba que la tienda sigue en pie con él puesto.

Es un proyecto independiente del sistema: **no lleva AIFEC dentro**. Lo localiza por `plan.json` y **solo lo lee**; para validar trabaja sobre un banco de pruebas, una copia de trabajo en `estado/banco/`.

## Requisitos

- Python 3.10 o posterior. Solo biblioteca estándar: nada que instalar.
- Windows, Linux o macOS.
- Una instalación de AIFEC cercana (la que se pone en `plan.json`) y PHP con `pdo_sqlite` para el banco. Para la puerta de sintaxis, además, el PHP más bajo y el más alto que se admiten (7.4 y 8.4).

## Primeros pasos

```
copy plan.ejemplo.json plan.json        (o cp en Linux y macOS) y edita "aifec" con la ruta de tu instalación
copy cola.ejemplo.json cola.json        los encargos de ejemplo, o los tuyos
python fabrica.py estado                comprueba que el plan vale y mira el día, el cupo y lo que toca
python fabrica.py trabajar --uno        el primer encargo, con el motor manual: deja el encargo escrito
python fabrica.py puertas <id>          cuando el plugin esté en salida/<id>/, pásale las puertas
```

Con el motor `manual` (el de por defecto) la fábrica escribe el encargo completo en `estado/encargos/<id>.encargo.md` y espera. Para que trabaje sola, se configura un motor `orden` (ver `docs/motores.md`). El recorrido entero está en `docs/primer-plugin.md`.

## Las siete puertas

| Puerta | Qué comprueba |
|---|---|
| `sintaxis` | `php -l` con cada versión del plan, sin errores **ni avisos** |
| `contrato` | `php aifec contract:check <id>` (Contrato AIFEC, C1 a C10) |
| `pruebas` | `php tests/run.php plugins/<id>/`, con al menos cuatro pruebas |
| `traducciones` | `php aifec i18n:check plugins/<id> es` |
| `ciclo` | activar, desactivar, reactivar y desinstalar: las tablas que crea son las que declara y no deja nada |
| `humo` | con el plugin activo, portada, listado, ficha, carrito y escritorio del panel en 200 y el registro sin líneas nuevas |
| `limpieza` | nada de sobra, cabeceras exactas, ninguna credencial con pinta de real, ningún correo que no sea de ejemplo |

Detalle en `docs/puertas.md`.

## El skill

`skill/SKILL.md` es lo que sigue la IA (o la persona): diez fases, empezando por **declarar el contrato antes de escribir código**. Trae un esqueleto (`python skill/esqueleto.py <id> "<Nombre>"`), referencias (`contrato`, `ganchos`, `panel`, `fallos-frecuentes`) y un plugin completo hecho siguiendo el skill (`skill/ejemplos/lista-deseos/`).

## Cómo se conecta al sistema

Solo con `plan.json` → `"aifec": "<ruta de una instalación>"`. La fábrica lee esa instalación, hace una copia en `estado/banco/` (sin `sites`, `storage`, cachés ni `.git`, ni `data-path.php`), crea ahí un sitio propio con las órdenes de AIFEC (`site:create`, con SQLite) e instala el candidato en `plugins/` del banco para pasarle las puertas. En la instalación de origen no escribe jamás. Si AIFEC no trae alguna orden que una puerta necesita, esa puerta sale con 2 («no aplica») y lo dice; no se imita la comprobación por otro lado.

## Las órdenes

```
python fabrica.py estado                  día, cupo, hechos hoy, en curso, atascados, siguiente, gasto
python fabrica.py calendario              qué haría cada día hasta vaciar la cola
python fabrica.py trabajar [--uno] [--slug X]     lo de hoy (o un solo encargo)
python fabrica.py parar | reanudar        acaba el encargo en curso y no empieza otro | vuelve a trabajar
python fabrica.py anadir --slug X --nombre "…" …   añade un encargo a la cola
python fabrica.py encargo <id>            escribe y enseña el encargo completo (lo que se le da al motor)
python fabrica.py puertas <id> [--solo ciclo,humo]   pasa las puertas a lo que hay en salida/<id>/
python fabrica.py aprobar <id> | rechazar <id> --motivo "…"   el visto bueno (o no) de una persona
python fabrica.py instalar <id> --en <instalación>   copia lo fabricado (solo si está hecho o aprobado)
python fabrica.py escaparate              rehace escaparate/index.html
python fabrica.py banco [--rehacer]       prepara o rehace el banco de pruebas
```

## Estados de un encargo

`pendiente` → `en_curso` → `en_puertas` → `hecho` → `aprobado`. Si las puertas (o una persona) lo rechazan pasa a `rechazado`, guarda el motivo y vuelve a la cola: el siguiente encargo que se le da al motor **incluye lo que falló**. Tras `intentos` intentos queda `atascado`.

`hecho` significa «pasa todas las puertas»; `aprobado`, «además lo ha mirado una persona». En `estado` y en el escaparate las dos cifras van separadas: no se llama terminado a lo que nadie ha mirado.

## Códigos de salida

| Código | Significado |
|---|---|
| 0 | bien |
| 1 | algo no pasa (una puerta, un atascado, una instalación que se niega) |
| 2 | uso incorrecto o plan inválido |
| 3 | parada por tope de gasto |
| 4 | parada por atascos seguidos |
| 5 | hay otra fábrica trabajando en esta carpeta |

## Qué hay dentro

- `fabrica.py` y `motor/`: el mecanismo, idéntico en la fábrica de temas y en la de plugins. Todo lo que distingue a una fábrica de otra está en `fabrica.json`.
- `puertas/`: las comprobaciones, propias de esta fábrica (y sus guiones de PHP, `_ciclo.php` y `_humo.php`, que corren dentro del banco).
- `skill/`: el skill, sus referencias, el esqueleto (`plantillas/esqueleto/`) y un plugin de ejemplo.
- `plantillas/`: el encargo que recibe el motor, la ficha de cada plugin y el esqueleto.
- `pruebas/`: `python -m unittest discover -s pruebas`; las «con sistema» se saltan solas si `AIFEC_RUTA` no apunta a una instalación de AIFEC.
- `docs/`: `como-funciona.md`, `plan.md`, `motores.md`, `puertas.md` y `primer-plugin.md`.

Licencia: ver `LICENSE.md`.
