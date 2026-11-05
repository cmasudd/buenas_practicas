# Propuesta de telemetría paralela CMAS

Fecha: 5 de noviembre de 2026. Estado: diseño para revisión e implementación futura.
No se instalaron servicios, no se alteró firmware ni se modificaron datos productivos.

La recomendación es **conservar MariaDB y agregar una recepción autenticada, con MQTT sobre TLS para telemetría y HTTPS para archivos**. Usar almacenamiento de objetos privado para imágenes; MariaDB conserva las mediciones y los metadatos que permiten encontrarlas. HTTPS POST también debe aceptar el mismo contrato de telemetría, para equipos que transmiten esporádicamente o redes donde MQTT resulte inconveniente.

MQTT, HTTPS y MariaDB cumplen funciones diferentes: los dos primeros transportan información; MariaDB la almacena y consulta. Un broker MQTT distribuye mensajes, pero no reemplaza la base histórica ni garantiza por sí solo que un dato haya quedado guardado.

Una posición GPS es pequeña: latitud, longitud, hora y calidad caben holgadamente en un mensaje de telemetría. Lo voluminoso es una trayectoria extensa, una fotografía, audio o una colección de muestras. MQTT admite contenido binario, pero conviene transportar por él el aviso y la referencia del archivo, dejando su transferencia a HTTPS.

## Lectura y entregables

1. [Diagnóstico y evidencias](01_DIAGNOSTICO.md): sistema y firmware realmente revisados, hallazgos y límites.
2. [Arquitectura y alternativas](02_ARQUITECTURA.md): opciones, pros y contras, componentes y conectividad.
3. [Contrato de datos y persistencia](03_CONTRATOS_Y_DATOS.md): mensajes, ACK, deduplicación, MariaDB e imágenes.
4. [Seguridad y convivencia legacy](04_SEGURIDAD.md): identidad, permisos, protección transitoria y cierre de accesos antiguos.
5. [Firmware SIM7600, ESP32 y ESP32-S3](05_FIRMWARE.md): módulos, alternativas TLS, cola SD y pruebas de hardware.
6. [Migración, operación y aceptación](06_MIGRACION_Y_PRUEBAS.md): fases, criterios de avance, recuperación y backlog.
7. [Capacidad, costos y decisiones pendientes](07_CAPACIDAD.md): escenarios ilustrativos ajustables.
8. [Fuentes](08_FUENTES.md): referencias oficiales y código inspeccionado.
9. [MQTT en profundidad](09_MQTT_EN_PROFUNDIDAD.md): broker, topics, identidad, entrega durable, SIM7600 y alternativas.
10. [Especificación del piloto MQTT](10_MQTT_PILOTO.md): parámetros, recibos, outbox, pruebas de fallo y criterios de aceptación.

## Decisiones propuestas

| Decisión | Propuesta | Motivo |
|---|---|---|
| Base histórica | Mantener MariaDB y las tablas actuales | Conservar portal, CSV y Power BI |
| Recepción | Servicio separado de la API de consulta | Separar permisos, límites y fallos |
| Transporte | MQTT 3.1.1/TLS y HTTPS POST con contrato común | Compatibilidad y posibilidad de comparar en terreno |
| Broker inicial | Mosquitto en entorno aislado | Piloto acotado; decidir alojamiento después de validar conectividad |
| Imágenes | Objetos privados y metadatos en MariaDB | Retención independiente y recuperación de cargas |
| ESP32-S3 | Evaluar ESP-IDF + esp_modem/PPPoS + TLS en MCU | Evitar depender exclusivamente del TLS AT del módem |
| Legacy | Adaptador y migración por equipo | Mantener servicio mientras se actualiza la flota |
| Confirmación | ACK de aplicación después de persistencia durable | Un PUBACK no prueba inserción en MariaDB |

No propongo comenzar migrando toda la base, desplegando Kafka ni convirtiendo cada foto en cientos de mensajes MQTT. Primero se debe demostrar seguridad, recuperación y compatibilidad con uno o dos equipos físicos.

Este diseño contiene decisiones implementables y criterios de aceptación. Los valores de capacidad, versiones finales, DDL y pinout deben cerrarse con el inventario y las pruebas indicadas; no se presentan como mediciones ya realizadas.
