# Contrato de la API V3

V3 se agrega junto a los endpoints existentes. No elimina ni cambia rutas legacy.

## Consulta paginada

```http
GET /v3/dispositivos/224/mediciones
    ?fecha_inicio=2026-07-01
    &fecha_fin=2026-07-31
    &limite=500
    &cursor=CURSOR_OPCIONAL
```

La respuesta contiene `next_cursor`. Para continuar, se envía ese valor en la
siguiente solicitud. No se usa `OFFSET`. El cursor es opaco para el cliente y
representa la posición `(id_sensor, fecha, id_dato)`.

## Descarga NDJSON reanudable

```http
GET /v3/dispositivos/224/historico.ndjson
    ?fecha_inicio=2024-01-01
    &fecha_fin=2026-07-27
    &limite=500
```

El servidor resuelve los sensores asociados a `id_dispositivo`, consulta bloques
de hasta 1.000 filas y emite un checkpoint después de cada bloque:

```json
{"_meta":{"complete":false,"rows":500,"next_cursor":"..."}}
```

La última línea indica `complete: true`. El descargador conserva el último
checkpoint confirmado y puede reanudar tras un corte de red.

Esta ruta requiere la cookie de sesión obtenida mediante `POST /v3/auth/login`.

## Consulta protegida para Power BI

```http
GET /v3/powerbi/proyectos/13/datos
    ?fecha_inicio=2025-01-01
    &fecha_fin=2026-08-03
    &limite=1000
    &cursor=CURSOR_OPCIONAL
X-API-Key: CLAVE_CONFIGURADA
```

La ruta resuelve todos los dispositivos y sensores del proyecto, entrega la
misma forma ancha que utilizaba V2 y pagina mediante `next_cursor`. Esto permite
migrar paneles existentes sin hacer una consulta pesada por cada dispositivo.
`totalCount` es únicamente el tamaño de la página actual; `has_more` indica si
queda otra página. No se ejecuta un conteo total sobre el histórico.

La clave se envía solamente en el encabezado `X-API-Key`; el servidor guarda su
hash SHA-256 en `POWERBI_API_KEY_HASH`. Admite hasta 25 dispositivos por
proyecto y una sola consulta Power BI simultánea. Las solicitudes concurrentes
esperan como máximo 30 segundos y después reciben HTTP 429 con
`Retry-After: 30`.

## Exportación CSV para el portal

```http
GET /v3/historicos.csv
    ?id_dispositivo=224,225
    &fecha_inicio=2024-01-01
    &fecha_fin=2026-07-31
```

`fecha_inicio` y `fecha_fin` son opcionales solo en esta ruta. Si se omiten, se
usa desde `1970-01-01` hasta el día actual. La respuesta se transmite como
`text/csv` y procesa los dispositivos secuencialmente en páginas de 1.000 filas.
Admite como máximo 25 dispositivos por solicitud.

El formato predeterminado, `formato=web`, reproduce la tabla estructurada del
portal: una fila por fecha, metadatos de sesión y dispositivo, una columna
dinámica por modelo/variable y `id_dato_concatenado`. Las columnas se calculan
para los dispositivos solicitados; no están fijadas a una estación. El archivo
comienza con BOM UTF-8 para que Excel interprete correctamente tildes, `µ` y
`m³`. El formato normalizado anterior se conserva con `formato=largo`.

`Content-Disposition` usa los códigos reales y el rango solicitado, por ejemplo
`AIRE-01_2026-05-15_2026-07-31.csv`. Para varios dispositivos concatena sus
códigos y limita el componente a 120 caracteres seguros.

Para construir la forma ancha sin ordenar millones de filas, cada sensor se
recorre con el índice `idx_datos_sensor_fecha` y cursor descendente. El servidor
fusiona esas series por fecha mediante un heap acotado y emite bloques CSV de
64 KiB; no crea un DataFrame ni mantiene el histórico completo en memoria.

La exportación exige sesión autenticada. Hay una sola exportación activa por
servidor; las solicitudes concurrentes esperan hasta 30 segundos y luego
reciben HTTP 429 con `Retry-After: 30`.

## Vista previa reciente

```http
GET /v3/vista-previa?id_dispositivo=92&limite=25
```

También acepta `fecha_inicio`, `fecha_fin` y el `cursor` opaco entregado por la
página anterior:

```http
GET /v3/vista-previa?id_dispositivo=92&limite=25
    &fecha_inicio=2026-05-01&fecha_fin=2026-05-31
    &cursor=CURSOR_OPCIONAL
```

La respuesta incluye `has_more`, `next_cursor`, `page_size` y el rango efectivo.
El cliente muestra “Hay más datos disponibles” cuando `has_more` es verdadero;
no se calcula un total exacto sobre la tabla histórica.

Devuelve las mediciones estructuradas más recientes con la misma forma ancha de
la web. Recorre cada sensor en orden descendente mediante
`idx_datos_sensor_fecha` y no ejecuta el JOIN legacy sobre todo el histórico.
Acepta hasta 10 dispositivos y un máximo de 100 filas.

## Disponibilidad mensual

```http
GET /v3/disponibilidad?id_dispositivo=7&mes=2026-05
```

Devuelve las fechas del mes que contienen al menos una medición para los
dispositivos seleccionados. Acepta hasta 10 dispositivos y no cuenta ni
descarga sus registros. Realiza como máximo 31 comprobaciones acotadas usando
`idx_datos_sensor_fecha`; el portal utiliza la respuesta para marcar en verde
los días disponibles.

```http
GET /v3/disponibilidad-meses?id_dispositivo=7&anio=2026
```

Devuelve los meses del año que contienen al menos una medición. Realiza 12
comprobaciones indexadas y permite que el portal marque los meses disponibles
antes de consultar sus días.

## Sesión temporal

```http
POST /v3/auth/login
Content-Type: application/json

{"username":"...","password":"..."}
```

El servidor guarda una cookie `Secure`, `HttpOnly` y `SameSite=Strict` con una
vigencia de ocho horas. Las cuentas locales se guardan en `portal_usuarios` con
correo normalizado, hash Werkzeug, rol `visita` o `administrador` y estado
activo. `HISTORICO_USER` y `HISTORICO_PASSWORD_HASH` se conservan como acceso
legacy compatible; nunca deben subirse al repositorio.

Los usuarios Microsoft del portal intercambian su ID token mediante
`POST /v3/auth/microsoft`. El backend valida firma RS256 con las claves JWKS de
Microsoft, audiencia, vencimiento, tenant y emisor antes de crear la misma
sesión HTTP-only. El identificador público de la aplicación se configura en
`HISTORICO_MICROSOFT_CLIENT_ID`.

## Administración de usuarios

```http
GET  /v3/admin/users
POST /v3/admin/users
PUT  /v3/admin/users/{id_usuario}
```

Estas rutas requieren una cookie con rol `administrador`. Permiten listar,
crear, cambiar rol, cambiar contraseña y activar/desactivar cuentas. Los hashes
nunca se incluyen en respuestas. No existe borrado físico: desactivar conserva
la trazabilidad básica. El API impide retirar el último administrador local
activo.

Swagger en `/apidocs/` documenta interactivamente estos contratos y la página
`Protocolos` del portal permite visualizarlo embebido o abrirlo en otra pestaña.

## Decisiones de seguridad operativa

- Fechas obligatorias.
- Límite máximo aplicado por el servidor.
- Consultas parametrizadas.
- Sin `COUNT(*)`, `OFFSET`, Pandas ni pivot.
- Una conexión por descarga y dispositivos procesados secuencialmente.
- Autenticación obligatoria en las rutas de descarga.
- Autorización de administrador verificada en servidor para gestionar usuarios.
- Exclusión mutua entre exportaciones CSV para proteger MariaDB.
- Los endpoints legacy siguen disponibles durante la migración.

Pendiente antes de exposición pública definitiva: integrar el proveedor de
identidad institucional, autorización por proyecto y una cola persistente de
trabajos para exportaciones masivas.
