# Diagnóstico del sistema existente

## Alcance y trazabilidad

Revisión de solo lectura del 5 de noviembre de 2026. Se leyeron los documentos de contexto exigidos, la última entrada de cambios del 3 de noviembre y el código productivo pertinente. No se hicieron llamadas a rutas de escritura, pruebas de inyección, reinicios ni escaneos ofensivos.

Firmware revisado: [AleReb/HIRI_PR0_FINAL_V01](https://github.com/AleReb/HIRI_PR0_FINAL_V01), commit `a51d2d74b8aab57183cf355cddbb31b1acf0e00a`. API: `/var/www/api_sensores`, HEAD `f151913d7ab458b0e453a540b66e8aabcada4553`, con modificaciones locales y módulos sin seguimiento. Ese HEAD **no representa por sí solo el código productivo**. El firmware del repositorio tampoco prueba qué versión ejecuta cada equipo de terreno.

Portal canónico: `cmasudd/SensorsWebApp`; producción en `/var/www/sensores/public`, PM2 `sensores`, puerto 8103. API Flask/Gunicorn y MariaDB permanecen como destino de compatibilidad. La API V3 protege consultas y exportaciones; esa protección no implica que todas las rutas antiguas estén protegidas.

## Hallazgos verificables en código

| Evidencia | Observación | Consecuencia para el diseño |
|---|---|---|
| Firmware principal, línea 151 | API_BASE usa HTTP sin TLS | El enlace del dispositivo no proporciona confidencialidad |
| `buildMeasurementUrl`, líneas 540–593 | Construye listas paralelas de sensores, variables y valores; no agrega `times` | El servidor asigna hora de recepción; el firmware conoce IDs internos |
| `http.ino`, líneas 79–186 | Usa AT HTTPINIT/HTTPPARA/HTTPACTION=0; acepta cualquier 2xx | Cambiar TinyGsmClient no cambia automáticamente esta ruta AT |
| `http.ino`, línea 82 | Advierte URL superior a 512 caracteres | Es advertencia del código, no límite universal demostrado del SIM7600 |
| `sendCurrentMeasurement`, líneas 596–611 | Incrementa contador al recibir éxito; registra URL fallida | El contador de éxitos no sirve como identificador durable de cada muestra |
| `sd_card.ino`, líneas 120–158 | Registra fallos sin retransmisión automática | SD actual es registro local, no una cola de entrega confirmada |
| Firmware, líneas 545–575 | Algunos valores ausentes pasan a cero; GPS se duplica en grupos | Hace falta calidad explícita y mapeo de compatibilidad |
| `app.py`, líneas 504–673 | GET insertarMedicion usa IDs del cliente y hace INSERT parametrizado | Falta autenticar y autorizar el dispositivo; no se afirma inyección SQL en ese INSERT |
| `insertarMedicionV2.py`, línea 208 y siguientes | También recibe GET y resuelve sensores por dispositivo/tipo | Cambiar a V2 no agrega identidad criptográfica |
| `app.py`, líneas 2176, 2300 y 2458 | CRUD genérico separado de V3 | Debe revisarse y protegerse para evitar que el nuevo ingreso sea eludido |
| `app.py`, líneas 2576–2614 | Ya admite imágenes POST y las guarda en `uploads` | La separación archivo/base ya existe parcialmente, pero falta un ciclo seguro de carga |
| `agregar_imagen` | Usa nombre suministrado por cliente, extensión y guardado directo | Revisar traversal, colisiones, contenido real, cuota y autorización antes de reutilizar |
| `/var/www/kuscaya/mqtt_parser.py` | Suscriptor Paho transforma MQTT y llama `requests.get` a API | Hay experiencia MQTT local; no constituye un ingreso autenticado completo |

El análisis de rutas no encontró autenticación de dispositivo en insertarMedicion/V2 ni un filtro global en app.py. No se auditó exhaustivamente el perímetro Cloudflare/Nginx ni se demostró explotación externa. CORS no autentica a un módem ni impide llamadas de clientes ajenos al navegador.

## Datos y servidor

El código escribe `datos(id_sensor, valor, fecha, id_variable, id_sesion, fecha_insercion)`. La documentación operativa confirma índices `(id_sensor, fecha)` y `(id_dispositivo, id_sensor)` en asociaciones. `variables`, `sensores`, `sensores_tipo` y `sensores_en_dispositivo` definen el catálogo que deberá consumir el adaptador nuevo. No se debe deducir el dispositivo a partir del ID visible de HIRI ni asumir que existe un solo sensor de cada tipo.

La conversión actual de épocas usa `datetime.fromtimestamp` y no fija UTC en ese bloque. Hay que comprobar la zona efectiva del proceso y la semántica histórica antes de proyectar horas nuevas; no reinterpretar todo el histórico automáticamente.

La fotografía actual de disco indicó unos 667 GiB disponibles sobre una raíz de 879 GiB; memoria disponible cercana a 25 GiB. Esto reemplaza la fotografía de agosto, anterior a la migración de SSD. No constituye prueba de capacidad de escritura sostenida ni autoriza consumir el margen reservado a respaldos.

## Metadatos de MariaDB confirmados

Consulta acotada a information_schema, en transacción de solo lectura con límite de 5 s por sentencia; no se leyeron mediciones ni se ejecutó COUNT sobre el histórico. La conexión inicial estuvo bloqueada por aislamiento y la consulta se realizó con autorización de acceso local.

- Las seis tablas revisadas son InnoDB. `datos` tiene una estimación del motor de 162 017 652 filas, unos 10.95 GB de datos y 15.84 GB de índices. TABLE_ROWS es aproximado y no equivale a conteo exacto.
- `datos.valor` es DECIMAL(21,7), nullable: adecuado para números, no para cadenas, JSON, imágenes ni estructuras GPS completas. Proyectar solo campos numéricos compatibles; conservar metadatos/textos en eventos nuevos.
- `datos.id_dato` es INT firmado, clave primaria; `fecha` y `fecha_insercion` son DATETIME sin zona almacenada. Antes de crecimiento importante revisar AUTO_INCREMENT y techo del identificador; la cantidad de filas no informa por sí sola el máximo ID usado. Un cambio a BIGINT sería proyecto separado con ensayo y respaldo.
- Se verificó `idx_datos_sensor_fecha(id_sensor, fecha)` y la clave primaria compuesta `(id_dispositivo,id_sensor)` en `sensores_en_dispositivo`.
- `imagenes` ya contiene `id_imagen`, `id_dispositivo`, `fecha`, `ruta`, `nombre` y `enlace`, con aproximadamente 244 filas según estadísticas. No contiene BLOB. La existencia de estos registros no demuestra que cada archivo referido exista o esté respaldado.
- Las estadísticas indican aproximadamente 185 filas en dispositivos y 1 088 en sensores; no representan flota activa ni número de equipos SIM7600. No se consultaron personas ni ubicaciones.

La nueva entidad media_objects puede complementar imagenes y ofrecer una vista/adaptador para consumidores antiguos. Primero inventariar referencias y autorización; no copiar o mover fotos existentes automáticamente.

## Pendiente de verificar antes de desarrollar

Inventario por placa y versión SIM7600/ATI/CGMR; firmware instalado, APN y cobertura; TLS/SNI/certificados; restricciones, triggers y privilegios completos del esquema; volumen diario real; usuarios y privilegios DB; publicación TCP entrante; políticas del túnel y proxy; existencia de cámaras; frecuencia y retención; pruebas reales de respaldo/restauración. No se inspeccionaron secretos ni se incluyeron sus valores en estos documentos.
