# Contratos y almacenamiento propuestos

Todo lo siguiente es una especificación de diseño; las rutas y tablas nuevas aún no existen.

## Evento de telemetría v1

```json
{
  "schema_version": 1,
  "device_uid": "equipo-demo-001",
  "event_id": "equipo-demo-001:7:1042",
  "generation": 7,
  "sequence": 1042,
  "captured_at": "2026-11-05T14:00:00Z",
  "clock_quality": "gnss",
  "firmware_version": "propuesta-v1",
  "mapping_version": 3,
  "measurements": [
    {"channel": "pms.pm25", "value": 12.4, "unit": "ug/m3", "quality": "valid"},
    {"channel": "sht.temperature", "value": null, "unit": "Cel", "quality": "sensor_error"}
  ],
  "position": {"lat": -33.0, "lon": -71.0, "alt_m": 120.0, "fix": true, "hdop": 1.2},
  "media_ids": []
}
```

Ejemplo sintético. `device_uid` se verifica contra la identidad autenticada y el topic; declararlo en JSON no autentica. `generation` cambia únicamente mediante reprovisión controlada. `sequence` es monotónica y durable, asignada antes de transmitir; reservar bloques en NVS permite tolerar reinicios sin escribir flash por cada evento. Se permiten huecos, nunca reutilización. El mismo evento conserva ID y bytes en reintentos y cambios de transporte.

`captured_at` representa captura, siempre UTC; `received_at` lo añade el servidor. Sin reloj válido: null y calidad `unknown`; conservar secuencia y tiempo relativo, no inventar UTC. Sin fix GPS: coordenadas null y fix=false. Rangos de validación: latitud ±90, longitud ±180; rechazar NaN/Infinity y tipos incorrectos. Calidad física implausible se marca o pone en cuarentena según variable; no eliminar silenciosamente un extremo científico legítimo.

El backend mantiene un catálogo versionado de canales→sensor/variable/unidad/dispositivo. El equipo no puede elegir arbitrariamente IDs SQL. Capturas antiguas se proyectan con el mapeo vigente al capturarse; reemplazos de sensores necesitan vigencia temporal, no modificar el pasado.

## Transporte y recibos

MQTT base 3.1.1 para compatibilidad; MQTT 5 opcional sin dependencia obligatoria. Topics propuestos:

| Topic | Equipo publica | Equipo se suscribe | Retained |
|---|---|---|---|
| `cmas/v1/devices/{uid}/telemetry` | Sí, QoS 1 | No | No |
| `cmas/v1/devices/{uid}/ack` | No | Sí, QoS 1 | No |
| `cmas/v1/devices/{uid}/status` | Sí | No | Solo estado, nunca muestras |
| `cmas/v1/devices/{uid}/commands` | No | Sí, si se habilita | No |

La [ampliación MQTT](09_MQTT_EN_PROFUNDIDAD.md) concreta un piloto sin retained, incluso para estado; retained en estado queda como opción posterior.

Client ID estable ligado a la identidad. ACL sin comodines para dispositivos. Prohibir publicar ACK o datos de otro uid. Keepalive inicial 120 s y sesión persistente acotada por cuotas: parámetros de ensayo, ajustar con NAT/energía. LWT informa pérdida de conexión, no prueba falla del sensor. MQTT QoS 1 admite duplicados y PUBACK no certifica escritura del consumidor en DB. [OASIS MQTT](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html).

HTTPS equivalente: `POST /ingest/v1/events`, autenticación por equipo, mismo cuerpo e idempotencia. Límite inicial propuesto 4 KiB por evento y hasta 32 KiB por lote HTTP; comprobar primero buffers AT del hardware real. Los límites son de aplicación, no del estándar MQTT. JSON inicial; CBOR solo con codec, esquema y pruebas compartidas si el ahorro medido lo justifica.

ACK durable: `event_id`, `state=accepted`, `received_at`. Significa evento confirmado en inbox, pendiente o no de proyección. `state=projected` es consulta/aviso posterior; `rejected` identifica error permanente. El equipo puede liberar la cola solo con accepted válido o recibo duplicate equivalente. En HTTPS: 202 después del commit durable, 200 para duplicado idéntico, 409 para mismo ID con contenido distinto, 400/422 para formato/semántica, 401/403 identidad/permisos, 413 tamaño, 429 y 503 reintentables con Retry-After. No confirmar antes de persistir.

Un fallo entre commit y ACK se resuelve reenviando: devuelve el mismo resultado sin otra inserción. No confiar en la persistencia periódica del broker como única copia; mantener SD hasta ACK de aplicación. El ACK requiere canal TLS validado o autenticación específica de respuesta en el puente HMAC.

## Modelo lógico aditivo

| Entidad nueva | Contenido y restricción |
|---|---|
| `telemetry_devices` | uid único, vínculo id_dispositivo, estado, capacidades y modo de migración |
| `device_credentials` | referencias de claves/certificados, versión, revocación; secretos fuera de documentación/Git |
| `channel_mappings` | dispositivo, canal, versión, vigencia, id_sensor, id_variable, unidad |
| `ingest_events` | ID único por dispositivo/generación/secuencia, bytes originales, digest calculado, captura/recepción, transporte, confianza, estado |
| `ingest_receipts_outbox` | Recibos pendientes creados con el evento en la misma transacción; reenvío tras reinicio |
| `projection_items` | evento y ordinal únicos, id_dato creado; trazabilidad e idempotencia |
| `media_objects` | media_id, propietario, evento opcional, object key, tamaño, tipo, integridad y estado |
| `upload_sessions` | sesión, propietario, vencimiento, bloques recibidos, cuotas |

Se confirmó que `datos` usa InnoDB. Creando inbox también en InnoDB en la misma instancia, insertar las mediciones y marcar proyección en una única transacción, bloqueando el evento y aplicando índices únicos. Verificar también triggers, aislamiento, durabilidad y privilegios en laboratorio. Con instancias separadas se necesita patrón inbox/outbox e idempotencia en el destino; dos commits independientes no bastan.

Conservar `datos` y sus índices. Su campo `valor` DECIMAL(21,7) recibe únicamente escalares numéricos compatibles; IDs textuales, calidad, versión, JSON y referencias de medios quedan en las tablas nuevas. La tabla `imagenes` existente ya modela rutas/enlaces y puede recibir una proyección de compatibilidad si algún consumidor lo necesita. Evitar ALTER masivo o índice nuevo en la tabla histórica hasta medir tamaño, bloqueo y espacio. El digest sirve para detectar conflicto, no para autenticar. No usar hash del valor/hora como identidad: dos medidas iguales pueden ser legítimas. La retención del registro de IDs debe cubrir todo el horizonte de reenvío; conservar tombstones compactos si se purga el payload.

El adaptador debe reproducir los grupos y unidades legacy, incluida la duplicación GPS cuando consumidores existentes la necesiten. Incorporar tiempo UTC mediante conversión explícita a la convención histórica verificada, conservando siempre UTC original en evento. Las imágenes y trayectorias se consultan mediante una API nueva; el portal actual no aprenderá a mostrarlas automáticamente.

## Imágenes y archivos

Guardar bytes en objetos privados; MariaDB almacena referencias. BLOB es técnicamente posible, pero incrementa carga de respaldo, restauración y replicación del histórico. Un filesystem dedicado con metadatos es alternativa inicial barata, con mayor trabajo manual para retención, acceso y copias. No presentar un directorio del mismo disco como respaldo.

Flujo propuesto:

1. Equipo solicita `POST /ingest/v1/uploads` con media_id estable, tipo, bytes, integridad calculada y captura; servicio autentica y asigna object key opaca.
2. Sube por HTTPS bloques de ensayo de 32–128 KiB, ajustables a RAM/buffer; el servicio confirma número/offset persistido. Nunca cargar toda la imagen en RAM.
3. Consultar `GET /ingest/v1/uploads/{id}` permite reanudar; bloque repetido idéntico es idempotente, distinto es conflicto. Autorizar propietario en cada operación.
4. `POST .../{id}/complete` verifica total, integridad y formato real. Publicar `ready` solo tras existencia durable del objeto y metadatos confirmados.
5. Evento MQTT transporta media_id y metadatos, no bytes base64 ni URL con autorización permanente. Si llega antes, mantener relación pendiente y reconciliar.

El gateway puede recibir bloques pequeños y ensamblar/transferir a S3. No confundirlos con multipart nativo S3, cuyas partes normales tienen mínimo 5 MiB salvo la última. [Límites S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/qfacts.html). Para fotos pequeñas en red estable, un PUT completo puede resultar más simple.

URL prefirmada es opción si el cliente soporta longitud, headers y método; darle vencimiento breve y alcance a un objeto, no registrarla en logs. El gateway autenticado con ruta corta evita ese problema en AT legacy. ETag multipart no equivale necesariamente al digest del archivo.

Estados: pending→uploading→verifying→ready, o failed/expired. Reconciliador elimina huérfanos según retención y detecta metadatos sin objeto. Lectura privada con autorización de proyecto; miniaturas y acceso público solo según política explícita. Validar MIME real, dimensiones y cuotas; quitar metadatos privados en derivados públicos, conservar original restringido si tiene valor científico.
