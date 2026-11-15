# Encargo: {{nombre}} ({{slug}})

Eres el motor de «{{titulo}}» y fabricas {{clase}} de AIFEC. Este encargo es uno de ellos.

## El encargo

{{encargo}}

Los campos que importan para el contrato son **`sector`** (qué hace el plugin), **`datos`** (qué datos de
personas toca: `email`, `name`, `address`, `phone`, `customer_id`…) y **`llamadas`** (a qué servicios
externos llama, o «ninguna»). Con ellos se rellena **primero** la declaración de `plugin.json` (`contract.hosts`,
`contract.personal_data`, `contract.tables`, `contract.capabilities`), antes de escribir una línea de código. Lo
que el encargo no diga se decide con sentido común y se anota en el `LEEME.md` del plugin; un dato que falte
**no se inventa del mundo real** (direcciones, precios, claves): se deja como ajuste.

## Dónde escribir

Solo en `{{trabajo}}`. Tiene que quedar ahí el plugin completo, con su `{{manifiesto}}`, listo para copiar a
`{{carpeta_destino}}/` de una instalación de AIFEC. Nada fuera de esa carpeta.

## Qué seguir

{{skill}}

## Dónde está AIFEC, para leerlo

La copia de trabajo está en `{{banco}}`. Solo se lee: el código del sistema, `plugins/hello-aifec/` como
modelo pequeño y `docs/07-referencia/_generado/ganchos.md` para la lista completa de ganchos.

## Lo que ya existe y no hay que repetir

{{existentes}}

## Cómo comprobar el trabajo antes de darlo por terminado

`{{comprobar}}`

Sale con 0 si todas las puertas pasan y con 1 si alguna no pasa; el informe dice cuál y por qué
(`python skill/informe.py {{slug}}` enseña el detalle). Una puerta que sale como «no aplica» no bloquea, pero
tampoco demuestra nada: dilo en tu informe.

## Lo que falló la vez anterior

{{anterior}}

## Prohibido

Tocar AIFEC o su copia de trabajo, salir a Internet, escribir fuera de `{{trabajo}}`, recorrer históricos para
mandar correos o llamar a terceros, y dar por bueno lo que no has comprobado.
