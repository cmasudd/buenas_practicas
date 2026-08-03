# Power BI con API V3 paginada

> Para una guía desde cero, ejemplos reutilizables y solución de problemas,
> comenzar en [`docs/powerbi/README.md`](powerbi/README.md).

## Por qué reemplazar V2

El manual original consulta `listarDatosEstructuradosV2` esperando que todo el
histórico llegue en una sola respuesta. En períodos grandes esa ruta construye
un JOIN amplio, ocupa un worker durante mucho tiempo y puede provocar timeouts
o varias consultas idénticas durante una actualización de Power BI.

La ruta específica `/v3/powerbi/proyectos/{id}/datos` recibe un proyecto,
resuelve internamente sus dispositivos y sensores y devuelve como máximo 1.000
filas anchas compatibles con V2. Cada respuesta contiene `next_cursor`; Power
Query lo envía en la solicitud siguiente. No se utilizan `OFFSET`, conteos
completos ni una consulta sin límite. La ruta exige `X-API-Key`.

## Prueba real de URA-00

El dispositivo del ejemplo del manual es:

```text
Proyecto:       22, URA
Dispositivo:    223, URA-00
Sensores:       1025, 1026 y 1027
Rango con datos: 2026-04-14 a 2026-06-20
```

La prueba del 3 de agosto de 2026 recorrió el rango completo mediante V3:

```text
Páginas:                 20
Tamaño máximo:           1.000 filas
Filas recuperadas:       19.281
Filas únicas:            19.281
Filas por sensor:        6.427
Tiempo total observado:  7,16 segundos
Duplicados:              0
```

La prueba fue secuencial. No se deben solicitar páginas concurrentes porque
cada cursor depende de la página anterior.

## Carga inicial recomendada en Power BI Desktop

1. Abrir **Transformar datos**.
2. Crear el parámetro de texto `PowerBIKey` con la clave entregada en privado.
3. Crear la función `fnCargarProyectoPowerBIV3` pegando
   `examples/powerbi/fnCargarProyectoPowerBIV3.m` en el Editor avanzado.
4. Crear otra consulta y llamar la función con proyecto y fechas.
5. Cuando Power BI solicite credenciales para
   `https://api-sensores.cmasccp.cl`, seleccionar **Anónimo**.
6. Configurar el nivel de privacidad institucional correspondiente.
7. Aplicar los cambios y comparar el resultado con el informe V2.

La raíz de `Web.Contents` permanece fija y el endpoint se entrega mediante
`RelativePath`. Los parámetros se entregan mediante `Query`; esto evita que
Power BI Service clasifique cada cursor como un origen dinámico diferente.

Las mediciones llegan en columnas dinámicas, igual que en la tabla web y la
consulta V2. El ejemplo público normalizado por dispositivo se conserva en
`examples/powerbi_v3_ura00.m` para modelos nuevos y pruebas aisladas.

## Actualizaciones programadas

No conviene volver a descargar todo el histórico en cada horario. La primera
actualización puede cargar el rango completo; después se recomienda configurar
actualización incremental:

1. Crear parámetros `RangeStart` y `RangeEnd` de tipo **Fecha/Hora**.
2. Usar en la consulta:

```powerquery
FechaInicio = Date.ToText(Date.From(RangeStart), "yyyy-MM-dd", "en-US"),
FechaFin = Date.ToText(
    Date.AddDays(Date.From(RangeEnd), -1),
    "yyyy-MM-dd",
    "en-US"
)
```

3. Después de convertir `fecha` a `datetime`, conservar el filtro requerido por
   Power BI:

```powerquery
Incremental = Table.SelectRows(
    TypedDates,
    each [fecha] >= RangeStart and [fecha] < RangeEnd
)
```

4. Configurar la política para conservar el histórico necesario y actualizar
   solo los últimos días.
5. Verificar una actualización en Power BI Service antes de aumentar la
   frecuencia.

`fecha_fin` en V3 es inclusiva; por eso se resta un día a `RangeEnd`, que Power
BI trata como límite exclusivo. El filtro final evita solapamientos entre
particiones.

## Límites operativos

- Usar `limite=1000`; valores mayores son reducidos por el servidor.
- Una sola cadena de páginas por proyecto.
- Definir siempre fecha inicial y final.
- No crear consultas paralelas por cada dispositivo del mismo proyecto.
- Para millones de filas, conservar la carga inicial fuera de los horarios de
  mayor uso y utilizar actualización incremental posteriormente.
- No usar `response.json()` sobre NDJSON desde Power BI: el endpoint paginado
  JSON es más sencillo y compatible con Power Query.

## Resultado recomendado

La API V3 recupera el rango completo sin perder registros, pero divide el
trabajo en consultas indexadas y acotadas. Para URA-00 la carga normalizada ya
quedó validada; la ruta de proyecto también se probó en el proyecto 13 con
páginas consecutivas sin solapamiento. El siguiente paso es reemplazar en una
copia del `.pbix` la consulta V2 por el código M protegido y comparar el panel.
