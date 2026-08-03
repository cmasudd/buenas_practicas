# 3. Proyecto 13: Línea Base Pública - Agua

## Dispositivos

| ID | Código | Descripción |
|---:|---|---|
| 75 | AGUA-00 | Estación de prueba para calidad de Agua |
| 94 | AGUA-01 | Estación Agua 01 |
| 113 | AGUA-02 | Estación Agua 02 |
| 216 | AGUA-03 | Mantagua |

Las cuatro URLs V3 fueron comprobadas con datos desde el 1 de enero de 2025.

## Cargar el proyecto completo

La opción recomendada hace una sola carga lógica por proyecto. La API resuelve
internamente AGUA-00, AGUA-01, AGUA-02 y AGUA-03 y entrega páginas pequeñas.

1. Crear el parámetro privado `PowerBIKey`, siguiendo la guía 2.
2. Crear la función `fnCargarProyectoPowerBIV3` con el contenido de
   `examples/powerbi/fnCargarProyectoPowerBIV3.m`.
2. Crear una nueva consulta en blanco.
3. Cambiar su nombre a `Proyecto_13_Agua`.
4. Abrir **Editor avanzado**.
5. Pegar `examples/powerbi/Proyecto_13_Agua_Protegido.m`.
6. Presionar **Listo** y después **Cerrar y aplicar**.

Para cambiar la fecha inicial, editar:

```powerquery
FechaInicio = #date(2025, 1, 1)
```

## Crear un gráfico sencillo

1. Insertar un **Gráfico de líneas**.
2. Arrastrar `fecha` al eje X.
3. Arrastrar `valor` al eje Y.
4. Arrastrar `variable_descripcion` a la leyenda.
5. Agregar segmentadores para `codigo_interno` y `unidad`.

No sumar variables que usan unidades diferentes. Filtrar una unidad o variable
antes de interpretar el resultado.

## Reemplazar un informe V2 existente

1. Hacer una copia del `.pbix` original.
2. Agregar V3 como una tabla nueva; no borrar V2 todavía.
3. Comparar fechas, dispositivos y variables.
4. Cambiar una visualización a la vez para usar `valor` y
   `variable_descripcion`.
5. Cuando todo funcione, deshabilitar la carga de V2.

La ruta Power BI conserva las columnas dinámicas de V2. Aun así, no conviene
reemplazar la consulta antigua sin revisar tipos, nombres y visualizaciones.

## Alternativa por dispositivo

`Proyecto_13_Agua.m` y `fnCargarDispositivoV3.m` siguen disponibles. Generan
formato normalizado y son útiles para modelos nuevos, pero no son la opción más
directa para reemplazar un panel V2 existente.
