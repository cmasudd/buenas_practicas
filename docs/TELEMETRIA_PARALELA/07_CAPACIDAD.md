# Capacidad, costos y decisiones por cerrar

No se recibió todavía un volumen de flota/imágenes confirmado. Estos son escenarios, no mediciones de producción. Unidades decimales para tráfico; no incluyen TLS, TCP, cabeceras, índices, réplicas o retransmisiones.

Supuestos: evento 1 kB, 19 valores por evento, fotografía 200 kB, 30 días.

| Escenario | Eventos/día | Filas históricas/día | Telemetría/mes | Fotos/mes |
|---|---:|---:|---:|---:|
| 100 equipos, cada 5 min, 1 foto/h | 28 800 | 547 200 | 0.864 GB | 14.4 GB |
| 1 000 equipos, cada 1 min, 1 foto/h | 1 440 000 | 27 360 000 | 43.2 GB | 144 GB |

Un broker puede manejar mensajes pequeños mientras el crecimiento de la tabla EAV exige mucha más atención: el segundo escenario proyectaría unos 821 millones de filas en 30 días. No validar capacidad por disco libre solamente. Medir filas/evento reales, bytes/fila con índices, inserción sostenida, consultas y ventana de backup. Antes de otra base, evaluar frecuencia, agregaciones y retención de datos crudos según necesidades científicas.

Fórmulas: eventos/día = equipos × 86400 / intervalo_segundos; filas/día = eventos × canales; tráfico = eventos × bytes_evento + fotos × bytes_foto; almacenamiento = crecimiento medido × retención × copias más margen de índices, temporales y backups. Costo mensual = hosting + objetos + solicitudes + salida de datos + SIM + respaldo + horas de operación. Cotizar sin asumir que almacenamiento barato implica egreso barato.

Cola local de 72 h a un evento/minuto de 1 kB: 4.32 MB por equipo, antes de overhead. Una foto/hora de 200 kB agrega 14.4 MB. Dimensionar al menos con margen y ciclos de escritura, reservando capacidad para firmware/archivos. Si transmisión disponible es menor que generación sostenida, ninguna cola resuelve el déficit: reducir frecuencia/tamaño o mejorar enlace.

## Preguntas para cerrar diseño

- Cantidad de equipos actual y a dos años, intervalo por proyecto, cámaras y tamaño/frecuencia de imágenes.
- ¿Ubicación puntual, rutas completas o archivos GIS? ¿Quién puede ver posiciones precisas?
- Autonomía energética, cobertura, plan SIM, ventana máxima desconectada y pérdida aceptable.
- Modelo exacto ESP32-S3/PSRAM/flash, SIM7600 y firmware, UART disponible y control de alimentación.
- Acceso físico a legacy y plazo de visita; posibilidad de actualizar por cable/SD/OTA.
- Necesidad real de comandos remotos, configuración y actualización de firmware.
- Alojamiento local o externo, presupuesto y responsable de operación; RPO/RTO por proyecto.

El paso siguiente recomendado es un banco con dos equipos, mismo SIM7600 y dos rutas de transporte, antes de elegir definitivamente MQTT nativo AT o PPP/TLS. La separación entre contrato, transporte y almacenamiento permite cambiar esa elección sin rehacer la base ni los dashboards.
