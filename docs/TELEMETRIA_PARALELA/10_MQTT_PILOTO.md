# Especificación del piloto MQTT CMAS

Referencia: TELEMETRIA-MQTT-PILOTO-20261105-v1. Propuesta de implementación futura. No es configuración instalada ni resultado de pruebas físicas.

## 1. Alcance mínimo y recursos

Dos equipos físicos, un simulador de dispositivos, un broker aislado, receptor, emisor de recibos, proyector y esquema de laboratorio. Telemetría y estado; cargas de imágenes se prueban después del camino básico. Sin comandos remotos ni OTA en la primera aceptación.

Como presupuesto inicial de laboratorio, reservar 2 vCPU, 2 GiB RAM y 20 GiB de disco para broker y herramientas, separados del presupuesto de MariaDB. No son requisitos oficiales ni garantía de capacidad. Fijar versiones de Mosquitto/plugins, Python/Paho, ESP-IDF/ESP-MQTT/esp_modem, Arduino core y firmware SIM7600. Las páginas “latest” no reemplazan un inventario reproducible.

## 2. Parámetros de partida

| Parámetro | Propuesta de ensayo | Comprobación |
|---|---|---|
| Transporte | TLS TCP/8883, servidor validado | Conectividad real APN; nombre/CA/fecha incorrectos fallan |
| Protocolo | MQTT 3.1.1 | Verificar CONNACK y comportamiento de cada pila |
| QoS | Publicar 1, suscripción 1 | Verificar ambos saltos con captura sintética de laboratorio |
| Retained | Desactivado en broker piloto | Estado reconstruido desde DB; mensajes retained rechazados |
| Client ID | Fijo, asignado a identidad | Probar colisión y suplantación con otro usuario |
| Keepalive | 120 s | Medir NAT, red móvil y energía; no es periodo de captura |
| Payload | Hasta 4 096 bytes por evento | Serializar antes de transmitir; también validar en receptor |
| Paquete MQTT | Hasta 8 192 bytes | Incluye cabeceras/topic; no limitarlo a 4 096 exactos |
| Ventana de aplicación | 1 evento pendiente de ACK | Ensayar 4 luego; separar de inflight MQTT |
| Espera de ACK | 60 s iniciales | Ajustar a AT y p95 de red; no es timeout TLS universal |
| Reintento | Jitter aleatorio entre 0 y techo exponencial, techo 300 s | No reiniciar módem por ACK atrasado |
| Recuperación SD | Hasta 1 evento/s/equipo inicialmente | Repartir capacidad entre pendientes y actuales |
| Cuota de archivo MQTT | Cero imágenes en piloto | Metadatos únicamente |
| Sesión | Persistente con expiración operativa 7 días | Si se pierde sesión, reconstruir y recuperar desde SD |
| SD pendiente | Objetivo mínimo 72 h según tasa | Confirmar escritura y recuperación tras corte |

Los límites de colas salientes del broker deben cubrir el consumidor de toda la flota, no solo un dispositivo. Propuesta de ensayo: 1 000 mensajes o 8 MiB por cliente, lo que ocurra primero, con alerta al 70 %. Es un presupuesto de amortiguación breve, no la promesa de retener 72 h en broker. Para 100 equipos a un evento/minuto, 1 000 mensajes representan apenas 10 minutos de recepción detenida. Con dos equipos, la duración sería distinta. Medir memoria real del conjunto de clientes y acotar cantidad de conexiones; el límite por cliente no es un límite global.

Mosquitto distingue tamaño del payload y del paquete y puede descartar mensajes al alcanzar límites de cola; una confirmación MQTT no prueba entrega al consumidor. Configurar persistencia y límites explícitos y ensayar saturación. [Manual de configuración](https://mosquitto.org/man/mosquitto-conf-5.html). No tomar sus defaults como política del piloto.

Retención broker no garantiza recuperación ante destrucción del host. Antes de liberar SD por accepted, acordar durabilidad real de DB, sincronización de commits, almacenamiento y respaldo. Si se exige RPO cero ante pérdida total del servidor, hace falta copia independiente confirmada antes del recibo o política de retención adicional en dispositivo. No se incluye esa garantía en el piloto inicial.

## 3. Ejemplos de contrato

El [evento completo v1](03_CONTRATOS_Y_DATOS.md) sigue siendo el contrato. Estos recibos complementan ese documento. Se publica a `cmas/v1/devices/equipo-demo-001/ack`.

Recibo de evento guardado:

```json
{
  "schema_version": 1,
  "device_uid": "equipo-demo-001",
  "event_id": "equipo-demo-001:7:1042",
  "state": "accepted",
  "duplicate": false,
  "received_at": "2026-11-05T14:00:03Z"
}
```

Reenvío idéntico produce `state=accepted`, `duplicate=true` y la recepción original. Un recibo puede recibirse repetido o fuera de orden. El equipo solo confirma el event_id correspondiente; nunca todos los anteriores por inferencia. Comprobar coherencia de uid/generación/secuencia; no usar el packet ID MQTT como identidad de medición.

Rechazo permanente:

```json
{
  "schema_version": 1,
  "device_uid": "equipo-demo-001",
  "event_id": "equipo-demo-001:7:1043",
  "state": "rejected",
  "reason": "SCHEMA_INVALID",
  "retryable": false
}
```

Si el servicio no pudo guardar, no envía accepted ni rejected permanente. Opcionalmente publica indicación temporal con estado `retry_later`, siempre incapaz de liberar SD. Si ni siquiera puede contestar, el timeout activa reenvío. Para confirmar rechazo no debe depender de guardar un payload malicioso completo; auditoría acotada, nunca secretos o coordenadas completas en logs.

Estado de conexión sintético:

```json
{
  "schema_version": 1,
  "device_uid": "equipo-demo-001",
  "connection_id": "conexion-demo-17",
  "state": "online",
  "firmware_version": "piloto-v1",
  "pending_events": 23,
  "sd_ok": true,
  "clock_quality": "gnss"
}
```

El LWT se prepara con `state=offline` y connection_id; no copiar pending_events inicial como si fuese estado actual. El observador agrega tiempo del servidor y conserva último mensaje válido por conexión. Si no sabe ordenar dos conexiones, marca incertidumbre y usa recepción reciente de telemetría para informar salud.

## 4. Datos adicionales y decisiones transaccionales

`ingest_receipts_outbox`: identificador de trabajo, evento, uid/topic derivado, respuesta, intentos, próxima fecha y estado de envío. Unicidad definida para recibo del mismo evento/resultado. El receptor crea o reactiva el trabajo al recibir un duplicado, de modo que el dispositivo pueda recuperar un ACK perdido aunque el broker ya haya confirmado el recibo anterior.

No guardar dos veces la muestra al rehacer un recibo. Los mensajes que van a DB llevan clave única por evento; la outbox es entrega de resultados, no un segundo histórico. Si PUBACK del recibo permite cerrar su intento de envío, eso únicamente indica aceptación del broker; el reenvío del dispositivo sigue siendo la recuperación ante pérdida del ACK final.

Resolver carreras con restricciones únicas y transacciones, no con SELECT seguido de INSERT sin protección. El proyector toma el evento por clave y comprueba estado bajo bloqueo. Guardar todas las filas numéricas y marcar projected en el mismo commit. El proyector no necesita credenciales MQTT de equipos. Emisor de recibos tampoco necesita permiso INSERT sobre `datos`.

Si la validación estructural pasa pero la proyección encuentra un error operativo, conservar evento y alerta para reparación; no enviar luego rejected para un accepted ya emitido. El significado de accepted es recepción durable, no éxito de toda explotación científica. Desplegar mapeos antes del corte y probarlos evita que esa cola crezca inadvertidamente.

## 5. Matriz de fallos y resultado esperado

| Interrupción | Estado seguro esperado | Evidencia de aprobación |
|---|---|---|
| Antes de guardar SD | No afirmar captura durable | Fallo de almacenamiento registrado; política de pérdida explícita |
| Tras SD, antes de publicar | Pendiente recuperable | Reenvío conserva ID y captura |
| Tras PUBACK, DB caída | Sigue pendiente en SD | Cero ACK accepted falso |
| Tras commit, antes de publicar ACK | DB conserva evento y outbox | Reinicio y duplicado devuelven recibo |
| Tras ACK, antes de checkpoint SD | Posible reenvío | Una sola proyección |
| Mitad de INSERT de canales | Transacción sin mitad visible | Todo o nada al reiniciar |
| Broker pierde sesión | Reconstruir suscripciones | Entrega desde SD sin intervención manual |
| Cola broker alcanza límite | Alarma; falta ACK durable; SD conserva | Recuperación eventual sin inventar entregas |
| Cola RAM receptor llena | Aplicar presión/reconexión controlada | Sin éxito prematuro ni crecimiento de RAM ilimitado |
| Memoria outbox MCU agotada | Reintentar desde SD tras liberar | Callback no borra eventos |
| Credencial revocada | Sesión termina, sin reconectar | Otros equipos siguen funcionando |
| Equipo A usa client ID/topic B | Conexión/publicación rechazada | Ningún dato B ni desconexión B inducida |
| 100 reenvíos, también por HTTP | Un evento y una proyección | Conteo por event_id en laboratorio |
| Mismo ID, contenido distinto | Conflicto | No sobrescribe primera versión |
| Reinicio del contador de firmware | Nueva secuencia no reutilizada | Reservas NVS sobreviven; reprovisión controlada |
| Reloj sin sincronizar | Captura marcada desconocida | No fabricar hora ni desactivar TLS |
| GPS activo mientras MQTT recibe | Sin mezclar UART/URC | Frames y eventos íntegros |

Tres duraciones de ensayo: prueba corta funcional, 24 h de estabilidad con señal cambiante y 72 h desconectado con recuperación. No declarar aprobada una combinación por una conexión exitosa. Mantener adquisición/UI medible durante conexión fallida y durante subida de archivo.

## 6. Cómo medir si MQTT vale la pena

Comparar AT MQTT/TLS, PPP MQTT/TLS y HTTPS POST según disponibilidad de targets, con el mismo evento, periodo, señal y alimentación. Medir:

- RAM mínima libre y pico de tareas/colas; uso CPU y fragmentación.
- Energía por captura entregada, incluyendo registro celular y reconexión.
- Bytes reales de SIM por día; handshakes, keepalive y reintentos incluidos.
- p50/p95/p99 de captura→accepted y accepted→projected por separado.
- Muestras perdidas, duplicadas, en cuarentena y pendientes después de recuperar.
- Tiempo de reconexión y tiempo para vaciar 72 h de backlog mientras continúa captura.
- Fallos de GNSS, SD y watchdog, distinguiendo causa de red y de alimentación.

No se necesita elegir MQTT si HTTPS satisface requisitos con menor energía y complejidad. Su ventaja esperada es más clara con mensajes frecuentes, conexión reutilizada y comunicación bidireccional. La decisión final se apoya en esas mediciones, no en que MQTT sea popular.

## 7. Entregables antes de habilitar un equipo productivo

Inventario de versiones y placa; catálogo de identidades/mapeos sin secretos; schemas de evento/ACK y fixtures sintéticos; configuración broker versionada con referencias a secretos; ACL probadas; firmware de ambos targets; migraciones DB ensayadas; outbox y proyector; tablero operativo; procedimiento de aprovisionar/revocar/rotar; reporte de fallo/recuperación; respaldo y rollback.

La operación administradora de Dynamic Security debe quedar en canal restringido, nunca en clientes de terreno. Usar herramientas que lean secretos desde ubicaciones protegidas o entrada interactiva; no documentar comandos con contraseñas visibles. La credencial de laboratorio no se mueve a producción.

Durante sombra, comparar inbox nueva con datos existentes sin insertar por ambos caminos. En el corte por equipo, registrar último evento esperado, modos de ingreso y relación de sensores, bloquear escritura legacy para esos sensores y habilitar proyección nueva. Revertir conserva inbox y SD; no borrar por similitud de valor/fecha. Registrar aprobación, versión, pruebas y respaldo siguiendo la operación CMAS.
