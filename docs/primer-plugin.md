# Tu primer plugin: de una frase a un plugin instalado

El recorrido completo, a mano (motor `manual`), con un encargo de una frase. Lo mismo hace una IA con un motor `orden`: la diferencia es solo quién escribe `salida/<id>/`.

## 0. Antes de empezar

```
cp plan.ejemplo.json plan.json      edita "aifec" (tu instalación), "php" (con pdo_sqlite) y "php_versiones" (7.4 y 8.4)
python fabrica.py estado            comprueba que el plan vale
python fabrica.py banco             prepara el banco de pruebas (una copia de trabajo de AIFEC)
```

## 1. Un encargo de una frase

```
python fabrica.py anadir --slug lista-deseos --nombre "Lista de deseos" \
    --sector "lista de deseos de los clientes con cuenta" \
    --idea "un botón en la ficha y una página en Mi cuenta" \
    --campo datos=customer_id --campo llamadas=ninguna
```

Un encargo completo trae además `capacidades`, `huecos`, `ajustes` y `no_hacer` (mira `cola.ejemplo.json`, con tres: lista de deseos, aviso de vuelta de existencias y puntos de recogida). Cuanto más concreto sea, menos hay que inventar.

## 2. Que la fábrica escriba lo que hay que hacer

```
python fabrica.py trabajar --uno
```

Con el motor `manual` deja el encargo en `estado/encargos/lista-deseos.encargo.md` (el texto completo: qué hacer, dónde, con qué skill, cómo comprobarlo) y el encargo en `en_curso`. También se ve con `python fabrica.py encargo lista-deseos`.

## 3. Declarar el contrato antes de programar

Sigue `skill/SKILL.md`. Lo primero es la declaración de `plugin.json`: **qué dominios usará** (`hosts`), **qué datos de personas toca** (`personal_data`), **qué tablas crea** (`tables`) y **si toca precios** (`capabilities`). Para la lista de deseos: ningún dominio, `customer_id`, `lista_deseos_items` y ninguna capacidad. Se apunta antes de escribir una línea; después las puertas miden que es verdad.

## 4. El esqueleto

```
python skill/esqueleto.py lista-deseos "Lista de deseos"
```

Crea `salida/lista-deseos/` con un plugin pequeño y completo que ya pasa las siete puertas (una nota por producto). **Cámbialo** por lo que haga tu plugin y borra lo que no uses. Antes de escribir, mira `skill/ejemplos/lista-deseos/`: el mismo encargo, ya hecho siguiendo el skill.

## 5. Datos, ganchos, panel, tienda y traducción

Fases 3 a 7 del skill: migraciones y tablas declaradas; ganchos y rutas; ajustes y recursos del panel; huecos de la tienda (sin sustituir plantillas del núcleo); y cada cadena visible en inglés con su traducción en `lang/es.php`. Para ver qué falta por traducir:

```
python fabrica.py puertas lista-deseos --solo traducciones
```

## 6. Pruebas

`tests/<Espacio>Test.php`, con las cuatro mínimas (se activa, hace lo suyo, se desactiva, pasa el contrato) y las de lo que hace. Una prueba que no falla cuando el código está mal no vale: rompe una línea, mira que salta y deshazla.

## 7. Pasar todas las puertas

```
python fabrica.py puertas lista-deseos
python skill/informe.py lista-deseos
```

Acaba en `PUERTAS: 7 de 7 pasan` (con las que «no aplican» explicadas). Arregla la causa de cada `no_pasa` leyendo el informe y repite.

## 8. Cuando pasan: mirarlo y aprobarlo

Pasar las puertas es **hecho**, no **aprobado**: lo aprueba una persona después de mirarlo.

```
python fabrica.py trabajar --slug lista-deseos      pasa las puertas y lo deja «hecho», con su ficha en escaparate/
python fabrica.py escaparate                        rehace escaparate/index.html
python fabrica.py aprobar lista-deseos              el visto bueno
python fabrica.py instalar lista-deseos --en <instalación>
```

`instalar` copia el plugin a `plugins/` de una instalación (solo si está hecho o aprobado) y **nunca pisa** uno que ya exista sin `--forzar`. El plugin se instala **desactivado**: se activa desde el panel o con `php aifec plugin:enable lista-deseos`.

## Si te atascas

| Qué pasa | Qué mirar |
|---|---|
| `sintaxis` dice «Parse error» con php-7.4 | algo de PHP 8 (`match`, `readonly`, tipos unión, `?->`, argumentos con nombre) |
| `sintaxis` dice «Deprecated» con php-8.4 | `Tipo $x = null` se escribe `?Tipo $x = null` |
| `contrato` rechaza un dominio | añádelo a `contract.hosts` (y llama con `$app->http()`) o quita la llamada |
| `ciclo`: «crea la tabla X y no la declara» | la migración y `contract.tables` tienen que coincidir |
| `ciclo`: «se queda el ajuste X» | los ajustes propios llevan el prefijo `<id_bajo>.` |
| `humo`: «el registro del sitio gana una línea nueva» | un oyente lanza: `python skill/informe.py <id> --puerta humo` dice la línea y el gancho |
| `traducciones` enseña cadenas | pégalas en `lang/es.php`; el `name` y la `description` del manifiesto también cuentan |
| Todo sale «no aplica» | `python fabrica.py banco`; revisa `php` y `aifec` en `plan.json` |

Más: `skill/referencias/fallos-frecuentes.md` y `docs/puertas.md`.
