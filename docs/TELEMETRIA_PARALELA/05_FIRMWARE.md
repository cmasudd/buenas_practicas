# Plan de firmware

## Dos rutas compatibles

Mantener rama/target de ESP32 actual y target ESP32-S3; compartir modelo de datos, serialización, cola y pruebas. Evitar una reescritura simultánea de UI, sensores y comunicaciones. No se ha compilado ni ensayado firmware nuevo en este trabajo.

La copia revisada incluye TinyGSM 0.12.0; su README declara no soportado TLS para SIM7500/7600/7800 y su driver SIM7600 implementa TCP. Sin embargo, la transmisión real usa comandos HTTP AT directamente. Eso no demuestra que el módem carezca de TLS. SIMCom publica notas MQTT(S) y HTTP(S), pero la capacidad debe confirmarse para variante y revisión exactas. [Documentación SIMCom](https://www.simcom.com/product/SIM7600X-H-PCIE.html).

| Camino | Trabajo | Puerta de aceptación |
|---|---|---|
| AT nativo HTTP(S)/MQTT(S) | Implementar comandos y URC según manual de revisión instalada | TLS con CA/nombre/fecha y errores negativos; tamaños reales |
| TinyGSM TCP + wrapper TLS MCU | Integrar biblioteca TLS compatible con Client y RAM disponible | Streaming, validación TLS, reconexión y mantenimiento del wrapper |
| ESP-IDF + PPPoS + TLS MCU | esp_modem, esp_netif, cliente MQTT y HTTP | UART/CMUX/GNSS estable, energía y memoria medidas |

Preferencia ESP32-S3: PPPoS con SIM7600 y TLS en MCU. esp_modem documenta soporte SIM7600 y modo PPP; esto respalda la viabilidad, no certifica la placa concreta. [esp_modem](https://docs.espressif.com/projects/esp-protocols/esp_modem/docs/latest/README.html). Mantener Arduino como componente o migrar drivers gradualmente son opciones; congelar versiones y construir ambos targets en CI. ESP-MQTT tiene ejemplos TLS y en IDF 6 pasó a componente separado: fijar dependencia, no asumir APIs de otra versión. [ESP-MQTT](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/protocols/mqtt.html).

## Organización propuesta

- `BoardProfile`: GPIO, UART, SD, I2C, batería y cámara por placa.
- `Acquisition`: captura sin depender de red, instante y calidad.
- `EventCodec`: JSON v1, límites y tests compartidos con servidor.
- `DurableQueue`: archivo append-only, CRC, checkpoint y recuperación tras apagado.
- `ModemManager`: único propietario UART/AT/URC, estados y deadlines.
- `TelemetryTransport`: MQTT/TLS o HTTPS POST, mismo event_id.
- `MediaUploader`: lectura SD por bloques y reanudación.
- `IdentityStore`: aprovisionamiento y rotación, sin impresión de secretos.
- `Diagnostics`: memoria mínima, fallos SD/red, muestras pendientes y versión.

El propietario único del módem evita que TinyGSM, HTTP AT, GNSS y una tarea MQTT lean respuestas de otra. Con PPP, resolver comandos GNSS mediante CMUX validado, canal adicional o alternancia planificada; no enviar AT arbitrario dentro del flujo PPP. Revisar límites y defectos CMUX de la combinación instalada.

## Máquina de estados

Capturar→guardar evento durable→esperar red→validar TLS→transmitir→esperar ACK de aplicación→marcar confirmado→compactar. Reintentos conservan identidad, contenido y captura. Backoff con jitter y techo, prioridad telemetría sobre imágenes, cuota de recuperación para no inundar servidor. Error permanente pasa a cuarentena local; autenticación revocada no provoca un bucle de intentos rápidos.

Una foto se escribe primero a SD y se sube por streaming. JPEG suele ser preferible a base64; este último agrega aproximadamente un tercio al tamaño. Rutas HTTP no determinan el tamaño del cuerpo. Un fallo de foto no detiene sensores ni telemetría.

No confundir CSV diario con cola: el CSV puede seguir como respaldo legible; la cola requiere ID, estado, integridad, confirmación y persistencia de checkpoint. Tras corte de energía, descartar solo registro incompleto y reenviar los completos no confirmados. La cuota llena necesita política explícita: alarmar y preservar lo prioritario; nunca sobrescribir silenciosamente información científica pendiente. Sin SD saludable, declarar modo degradado y pérdida potencial.

## Verificaciones de placa y módem

Inventariar ATI/CGMR, variante regional, APN, antenas, fuente y picos de corriente; guardar inventario sin identificadores privados innecesarios. Ensayar señal débil, DNS, CA, SNI, cadena intermedia, reloj incorrecto, vencimiento, renovación, nombre equivocado y certificado no confiable. Nunca “arreglar HTTPS” desactivando la validación.

ESP32-S3 no conserva automáticamente GPIO, ADC, strapping, periféricos o disponibilidad de PSRAM del ESP32 previo. Confirmar módulo exacto, flash, PSRAM, UART hardware, SD, GPIO de cámara y alimentación. No asumir que la placa actual tiene cámara. Priorizar RTS/CTS si disponible para PPP y datos largos. A 115200 baud con 8N1 el techo físico UART es 11.52 kB/s antes de overhead: una foto de 200 kB ya necesita al menos unos 17.4 s; medir velocidad efectiva y energía.

La recuperación no debe reiniciar un módem sano por HTTP 500. Distinguir sin SIM, registro, PDP, DNS, TLS, autenticación y servidor. Watchdog supervisa progreso; no alargarlo indefinidamente para ocultar bloqueos. OTA firmada y particiones A/B se incorporarán después del transporte estable; probar rollback y recuperación física antes de habilitar despliegue remoto.
