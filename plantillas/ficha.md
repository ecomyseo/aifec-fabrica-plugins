# {{nombre}}

- Encargo: `{{slug}}` ({{clase}})
- Estado: **{{estado}}** (hecho = pasa las puertas; aprobado = además lo ha mirado una persona)
- Qué hace: {{sector}}
- Idea: {{idea}}
- Fecha: {{fecha}}
- Intentos: {{intentos}}
- Motor: {{motor}}
- Gasto: {{gasto_eur}} €
- Puertas: {{resumen_puertas}}

Los datos que toca y a qué llama están en `plugin.json` (`contract.personal_data`, `contract.hosts`) y en el
`LEEME.md` del plugin: la ficha no los repite porque el motor solo le pasa el nombre, la función y la idea.

## Puertas

{{puertas}}
