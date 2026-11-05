# Fuentes y límites de investigación

Consultadas el 5 de noviembre de 2026. Las propuestas de cuotas, fases y arquitectura son decisiones de este diseño, no configuraciones observadas.

## Código y documentos locales

- Firmware [repositorio HIRI](https://github.com/AleReb/HIRI_PR0_FINAL_V01/tree/a51d2d74b8aab57183cf355cddbb31b1acf0e00a): sketch principal, http.ino, sd_card.ino y TinyGSM incluido. Inspección directa de copia de investigación; no modificación del repositorio remoto.
- `/var/www/api_sensores/app.py`, `insertarMedicionV2.py`, mapa de rutas V3 y código de recepción de imágenes.
- `/var/www/kuscaya/mqtt_parser.py`: integración MQTT existente, sin leer su configuración secreta.
- `/home/cmas/Documentos/buenas_practicas/README.md`, `docs/PORTAL_SENSORES_OPERACION.md` y `cambios/2026-11-03-clonacion-ssd-recuperacion.md`.
- `/home/cmas/Documentos/bitacora_servidor/README.md`, mapa de servicios y riesgos pendientes. Distinguir fotografías históricas de observaciones actuales.

- Metadatos information_schema consultados localmente: tipos, motores, índices y estimaciones de tamaño; sin lectura de filas de mediciones.

## Referencias primarias

- [MQTT 3.1.1, OASIS](https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html): semántica de transporte y QoS.
- [Mosquitto, configuración](https://mosquitto.org/man/mosquitto-conf-5.html): autenticación, TLS, ACL y límites.
- [SIMCom SIM7600, documentación de familia](https://www.simcom.com/product/SIM7600X-H-PCIE.html): catálogo MQTT(S), HTTP(S) y GNSS. La familia no certifica la revisión instalada.
- [SIMCom MQTT AT Command Manual, copia alojada por Waveshare](https://files.waveshare.com/upload/6/65/SIM7500_SIM7600_Series_MQTT_ATC_V1.01.pdf): documento del fabricante; confrontar versión y comandos con el módem real antes de programar.
- [TinyGSM upstream](https://github.com/vshymanskyy/TinyGSM): contrastar capacidades de biblioteca; el diagnóstico específico usa la versión incluida en HIRI.
- [Espressif esp_modem](https://docs.espressif.com/projects/esp-protocols/esp_modem/docs/latest/README.html): PPPoS, SIM7600 y modos de comunicación.
- [Espressif ESP-MQTT para ESP32-S3](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/protocols/mqtt.html): componente y ejemplos TLS.
- [Amazon S3, multipart](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html) y [límites](https://docs.aws.amazon.com/AmazonS3/latest/userguide/qfacts.html): cargas por partes y restricciones.
- [Cloudflare Tunnel, protocolos publicados](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/protocols/): diferencias entre publicación HTTP y TCP.

No se afirma rendimiento medido del sistema nuevo, compatibilidad TLS comprobada en hardware, auditoría integral de seguridad ni validación física del firmware. No se enviaron datos de prueba a producción ni se instalaron componentes.

## Referencias adicionales de la ampliación MQTT

- [Mosquitto Dynamic Security](https://mosquitto.org/documentation/dynamic-security/): roles, ACL, client ID y revocación.
- [Paho Python Client](https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html): confirmación manual y callbacks.
- [ESP-MQTT, guía del componente](https://docs.espressif.com/projects/esp-mqtt/en/latest/esp32/): TLS, outbox y retransmisión.
- [OASIS MQTT 5](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html): expiración y límites negociados.
- [PubSubClient](https://github.com/knolleary/pubsubclient): limitación de publicación a QoS 0.

El PDF de SIMCom alojado por Waveshare lleva V1.01 en el nombre de URL, pero su portada y metadatos internos indican V1.00 (2018). No se usa ese nombre externo para inferir la versión del firmware ni del manual compatible con la flota.
