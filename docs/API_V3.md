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

La exportación exige sesión autenticada. Hay una sola exportación activa por
servidor; las solicitudes concurrentes esperan hasta 30 segundos y luego
reciben HTTP 429 con `Retry-After: 30`.

## Sesión temporal

```http
POST /v3/auth/login
Content-Type: application/json

{"username":"...","password":"..."}
```

El servidor guarda una cookie `Secure`, `HttpOnly` y `SameSite=Strict` con una
vigencia de ocho horas. La clave de firma, usuario y hash de contraseña se leen
desde `HISTORICO_SESSION_SECRET`, `HISTORICO_USER` y
`HISTORICO_PASSWORD_HASH`; nunca deben subirse al repositorio.

Los usuarios Microsoft del portal intercambian su ID token mediante
`POST /v3/auth/microsoft`. El backend valida firma RS256 con las claves JWKS de
Microsoft, audiencia, vencimiento, tenant y emisor antes de crear la misma
sesión HTTP-only. El identificador público de la aplicación se configura en
`HISTORICO_MICROSOFT_CLIENT_ID`.

## Decisiones de seguridad operativa

- Fechas obligatorias.
- Límite máximo aplicado por el servidor.
- Consultas parametrizadas.
- Sin `COUNT(*)`, `OFFSET`, Pandas ni pivot.
- Una conexión por descarga y dispositivos procesados secuencialmente.
- Autenticación obligatoria en las rutas de descarga.
- Exclusión mutua entre exportaciones CSV para proteger MariaDB.
- Los endpoints legacy siguen disponibles durante la migración.

Pendiente antes de exposición pública definitiva: integrar el proveedor de
identidad institucional, autorización por proyecto y una cola persistente de
trabajos para exportaciones masivas.
