# 5. Publicar y actualizar

## Publicación inicial

1. En Power BI Desktop seleccionar **Publicar**.
2. Iniciar sesión con la cuenta institucional autorizada.
3. Elegir el workspace correcto.
4. Abrir Power BI Service y comprobar el informe y su modelo semántico.

No usar **Publicar en la web** si el informe no debe ser completamente público.

## Credenciales del origen

En Power BI Service:

1. Abrir el workspace.
2. Buscar el modelo semántico.
3. Entrar en **Configuración → Credenciales del origen de datos**.
4. Elegir **Anónimo** para el dominio. La función envía `X-API-Key` por separado.
5. Configurar privacidad **Organizacional**.

La consulta usa una raíz fija y `RelativePath`; esto ayuda a que Power BI
Service reconozca un solo origen aunque cambie el cursor.

Después de publicar, revisar el parámetro `PowerBIKey` del modelo semántico y
configurar allí el valor correcto. Solo los administradores del workspace deben
poder modificarlo.

## Actualización programada

1. Ejecutar primero **Actualizar ahora**.
2. Confirmar que termine correctamente.
3. Configurar zona horaria `America/Santiago`.
4. Empezar con una actualización diaria fuera del horario de mayor uso.
5. Aumentar la frecuencia únicamente después de observar varias ejecuciones.

## Actualización incremental

Para históricos grandes, crear parámetros `RangeStart` y `RangeEnd` de tipo
Fecha/Hora. La API debe recibir únicamente el intervalo de cada partición y la
tabla debe conservar este filtro:

```powerquery
Table.SelectRows(
    TypedDates,
    each [fecha] >= RangeStart and [fecha] < RangeEnd
)
```

Como `fecha_fin` de V3 es inclusiva, la fecha enviada a la API debe ser el día
anterior a `RangeEnd`:

```powerquery
Date.AddDays(Date.From(RangeEnd), -1)
```

La primera actualización crea el histórico. Las siguientes deben actualizar
solo los días recientes.
