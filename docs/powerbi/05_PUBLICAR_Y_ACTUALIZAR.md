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

La API se encuentra en una dirección HTTPS accesible desde Internet. Power BI
Service puede conectarse directamente y normalmente no necesita un gateway
local para este origen web.

1. Publicar el `.pbix` en un workspace de Power BI Service.
2. Abrir el **modelo semántico → Configuración**.
3. En **Parámetros**, comprobar `IdProyecto`, fechas y `PowerBIKey`.
4. En **Credenciales del origen de datos**, editar
   `https://api-sensores.cmasccp.cl` y seleccionar **Anónimo** con privacidad
   **Organizacional**. La clave sigue viajando dentro de `X-API-Key`.
5. Ejecutar **Actualizar ahora** y revisar **Historial de actualización**.
6. Cuando la prueba termine bien, activar **Configurar una programación de
   actualización**.
7. Elegir zona horaria `America/Santiago` y comenzar con una actualización
   diaria fuera del horario de mayor uso.
8. Activar la notificación de errores al propietario del modelo.

La consulta utiliza una raíz fija con `RelativePath` y `Query`, combinación que
Power BI Service admite para actualización aunque cambien las fechas y el
cursor. Si el servicio muestra que necesita gateway para este único origen,
revisar que la consulta publicada coincida con el ejemplo y que no se haya
construido la URL completa mediante concatenación.

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

En capacidad compartida se permiten hasta ocho actualizaciones programadas al
día y cada actualización importada dispone normalmente de hasta dos horas. Para
este servidor se recomienda empezar con una diaria, aunque la licencia permita
más.
