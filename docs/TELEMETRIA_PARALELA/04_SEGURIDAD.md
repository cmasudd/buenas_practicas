# Seguridad y compatibilidad legacy

Cambiar GET por POST mejora semántica y evita datos en URL, pero no autentica. MQTT sin TLS y ACL tampoco soluciona suplantación. HTTPS protege el canal cuando se valida correctamente el servidor; además se necesita identidad única por equipo y autorización de qué puede escribir.

## Objetivo de seguridad

TLS 1.2 como mínimo de compatibilidad, validando cadena, nombre del servidor y vigencia; TLS 1.3 cuando la pila ensayada lo permita. Credenciales únicas, revocables y limitadas a un dispositivo. Para el piloto, contraseña aleatoria por equipo sobre TLS puede ser más simple; mTLS es preferible para flota administrada si se prueba aprovisionamiento y renovación. No compartir claves de toda la flota ni incluirlas en código, URLs, SD de diagnóstico o repositorios.

Mosquitto ofrece autenticación, ACL y certificados de cliente; la elección no sustituye configuración explícita y pruebas de aislamiento. [Configuración oficial](https://mosquitto.org/man/mosquitto-conf-5.html).

Aprovisionar por canal local controlado: asignar uid, vincularlo al catálogo, instalar identidad y CA, verificar conexión y registrar responsable. Rotar con superposición temporal controlada; revocar individualmente un equipo perdido y desconectar sus sesiones. Separar claves de telemetría y administración. En ESP32-S3 evaluar cifrado flash, Secure Boot y recuperación antes de quemar eFuses irreversibles.

## Tres poblaciones

| Población | Tratamiento |
|---|---|
| Firmware imposible de actualizar ahora | Mantener recepción delimitada y etiquetar `legacy_unverified`; cuotas y monitoreo; no prometer autenticidad |
| Legacy actualizable, TLS todavía inviable | Puente temporal firmado con HMAC y anti-replay; sin confidencialidad; plazo de retiro |
| Equipo con TLS validado | Nuevo ingreso, identidad por equipo y bloqueo de escritura legacy para sus sensores |

HMAC sobre HTTP solo es una mitigación transitoria para datos que puedan circular sin cifrado; no usarlo para imágenes privadas, comandos sensibles ni secretos. Una red/APN privada con acceso controlado es otra alternativa, pero tiene costo y exige coordinación con operador.

Diseño del puente HMAC: usar biblioteca criptográfica mantenida, clave aleatoria por equipo y MAC sobre versión de protocolo, método, ruta fija, uid, generación provisionada, secuencia y digest de **los bytes exactos** del cuerpo. Verificación en tiempo constante. Evitar canonicalización JSON improvisada. En GET temporal, definir codificación exacta sin parámetros ambiguos o duplicados, medir longitud y retirar logs de query; preferir POST si el AT lo permite.

El servidor verifica unicidad durable antes de confirmar; un ID repetido con cuerpo idéntico devuelve el recibo previo, con cuerpo distinto se rechaza. No crear una nueva generación porque el dispositivo la declaró ni borrar el registro anti-replay al reiniciar. Permitir mensajes atrasados únicos dentro de política acotada, evitando exigir llegada estrictamente creciente. Firma de respuesta con clave derivada y separación de dominio, ligada a event_id, digest y estado: un falso 200 no debe hacer borrar la SD. Aun así, un atacante puede observar, retrasar o bloquear mensajes; HMAC no evita eso.

## El cierre del bypass es obligatorio

Al migrar un equipo, bloquear **todas** las rutas antiguas capaces de insertar en sus sensores, tanto V1 como V2 y CRUD genérico. No basta filtrar un supuesto device_id en una ruta: la V1 recibe IDs de sensores. Resolver propiedad en servidor y comprobar cada elemento del lote. Un endpoint legacy puede mantener escritura para otros equipos, pero nunca para sensores ya migrados.

El cambio por dispositivo debe ser atómico respecto de su modo de ingreso. Primero preparar firmware/credencial y pruebas, después fijar modo nuevo. Un rollback autorizado puede volver temporalmente al modo anterior, registrando la pérdida de garantía. Nunca hacer fallback automático de TLS a HTTP anónimo.

Proteger CRUD y archivos con autorización servidor-side y privilegios de función. El usuario técnico nuevo no administra tablas ni usuarios y no borra histórico. Límites por identidad y tamaño, límites por IP secundarios (CGNAT comparte IP), backoff y cuarentena. Logs con event_id, motivo, latencia y estado; sin payload completo, coordenadas sensibles, credenciales o firmas de acceso.

Una identidad válida no prueba que la lectura física sea verdadera: equipo comprometido, sensor defectuoso o GPS manipulado siguen siendo posibles. Guardar procedencia y calidad; detectar incoherencias sin transformar una regla de plausibilidad en garantía científica.
