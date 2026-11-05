# Propuesta documental de telemetría paralela

Fecha: 5 de noviembre de 2026. Referencia documental: TELEMETRIA-PARALELA-20261105-v1.

Se agregó `docs/TELEMETRIA_PARALELA/` con diagnóstico de API, firmware HIRI y esquema MariaDB; alternativas MQTT/HTTPS; archivos privados; contratos; seguridad legacy; plan ESP32/ESP32-S3 con SIM7600; migración, pruebas y capacidad. El README principal enlaza la propuesta.

Investigación: lectura de código y documentación; referencias oficiales; consulta acotada de information_schema en transacción de solo lectura. No se enviaron muestras a producción ni se instalaron componentes, modificaron esquemas, flashearon equipos o reiniciaron procesos. La investigación inicial dejó los documentos locales; su publicación en GitHub fue solicitada posteriormente por el usuario.

Validación: revisión de enlaces relativos, coherencia con tipos e índices reales, separación entre hechos y propuestas, comprobación de formato Git. Las pruebas de hardware, integración y carga enumeradas son futuras, no ejecutadas.

No es un cambio de producción: no corresponde respaldo de artefacto desplegado ni rollback de servicios. Para retirar esta propuesta, revertir únicamente la adición documental y su enlace, preservando otros cambios. Los futuros despliegues deben registrar versión, pruebas, sumas de artefactos, respaldo previo y reversión según la operación del portal. No se documentan secretos ni valores reales de hashes.

## Ampliación MQTT

A solicitud del usuario se añadieron diseño detallado MQTT y especificación del piloto: cadena SD→broker→inbox→proyección, recibos durables con outbox, ACL/identidad, opciones SIM7600, límites y pruebas de fallos. Se precisó que retained queda deshabilitado en el piloto. Solo documentación; las pruebas enumeradas no se ejecutaron en producción.

## Publicación de la documentación

Destino autorizado: `https://github.com/cmasudd/buenas_practicas`, rama `main`.
El commit de esta entrada identifica la versión publicada de la propuesta y sus
once documentos. Incluye el enlace en README y la ampliación MQTT. Validación
previa: enlaces relativos, cuatro ejemplos JSON y formato Git. El detector de
secretos del repositorio de bitácora señaló ocho referencias a variables y
llamadas de código preexistente, sin hallazgos en los archivos de este cambio;
se revisaron como falsos positivos. No se desplegaron servicios ni firmware.
