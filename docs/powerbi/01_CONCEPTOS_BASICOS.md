# 1. Conceptos básicos

## ¿Qué es Power BI?

Power BI Desktop es un programa de Windows que permite cargar datos, limpiarlos
y crear gráficos. Power BI Service es el sitio web donde se publica y actualiza
un informe.

## Palabras importantes

| Palabra | Explicación sencilla |
|---|---|
| API | Dirección web desde la que Power BI solicita datos |
| Power Query | Herramienta de Power BI que obtiene y transforma los datos |
| Código M | Lenguaje utilizado por Power Query |
| Consulta | Instrucciones para construir una tabla |
| Parámetro | Valor modificable, por ejemplo proyecto o fecha inicial |
| Cursor | Marca que indica dónde empieza la página siguiente |
| `.pbix` | Informe editable que puede contener datos |
| `.pbit` | Plantilla sin los datos cargados |
| Modelo semántico | Conjunto de tablas y relaciones publicado en Power BI |
| Actualización | Proceso que vuelve a consultar la API |

## Por qué V3 usa páginas

V2 intentaba obtener un histórico completo con una sola consulta. Para rangos
grandes eso podía ocupar MariaDB y los procesos de la API durante varios
minutos.

V3 divide el resultado:

```text
Power BI → página 1 → cursor → página 2 → cursor → ... → página final
```

Cada página contiene como máximo 1.000 mediciones. La función incluida en este
kit sigue el cursor automáticamente y al final entrega una sola tabla.

## Forma de los datos

V3 entrega una fila por medición:

| fecha | codigo_interno | id_sensor | variable_descripcion | unidad | valor |
|---|---|---:|---|---|---:|
| 2026-05-01 12:00 | AGUA-01 | 249 | pH ambiental | pH | 7.2 |

Este formato se denomina **normalizado**. En Power BI es conveniente porque un
solo gráfico puede usar `variable_descripcion` como leyenda y `valor` como eje.

V2 entregaba algunas variables como columnas diferentes. Un informe antiguo
puede necesitar adaptar sus visualizaciones al formato normalizado o pivotar la
tabla.
