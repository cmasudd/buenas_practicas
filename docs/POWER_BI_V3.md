# Power BI con API V3 paginada

## Por qué reemplazar V2

El manual original consulta `listarDatosEstructuradosV2` esperando que todo el
histórico llegue en una sola respuesta. En períodos grandes esa ruta construye
un JOIN amplio, ocupa un worker durante mucho tiempo y puede provocar timeouts
o varias consultas idénticas durante una actualización de Power BI.

V3 recibe un `id_dispositivo`, resuelve internamente sus sensores y devuelve
como máximo 1.000 mediciones normalizadas. Cada respuesta contiene
`next_cursor`; Power Query lo envía en la solicitud siguiente. No se utilizan
`OFFSET`, conteos completos ni una consulta sin límite.

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

## Carga inicial en Power BI Desktop

1. Abrir **Transformar datos**.
2. Crear una **Consulta en blanco**.
3. Abrir **Editor avanzado**.
4. Pegar el contenido de `examples/powerbi_v3_ura00.m`.
5. Cuando Power BI solicite credenciales para
   `https://api-sensores.cmasccp.cl`, seleccionar **Anónimo**.
6. Configurar el nivel de privacidad institucional correspondiente.
7. Aplicar los cambios y comprobar que `id_dato` no tenga duplicados.

La raíz de `Web.Contents` permanece fija y el endpoint se entrega mediante
`RelativePath`. Los parámetros se entregan mediante `Query`; esto evita que
Power BI Service clasifique cada cursor como un origen dinámico diferente.

El campo `valor` llega como texto decimal con punto. La consulta lo transforma
con cultura `en-US`, conservando la corrección indicada en el manual original.

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
- Una sola cadena de páginas por dispositivo.
- Definir siempre fecha inicial y final.
- Para varios dispositivos, crear una consulta por dispositivo y evitar que el
  servicio actualice muchas consultas históricas en paralelo.
- Para millones de filas, conservar la carga inicial fuera de los horarios de
  mayor uso y utilizar actualización incremental posteriormente.
- No usar `response.json()` sobre NDJSON desde Power BI: el endpoint paginado
  JSON es más sencillo y compatible con Power Query.

## Resultado recomendado

La API V3 recupera todos los datos sin perder registros, pero divide el trabajo
en consultas indexadas y acotadas. Para URA-00 la carga completa ya quedó
validada. El siguiente paso es reemplazar en el archivo `.pbix` la consulta V2
por el código M de ejemplo y publicar una actualización de prueba.
