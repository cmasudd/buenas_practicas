# Migración y operación futuras

## Fases y entregables

| Fase | Trabajo | Criterio para avanzar | Reversión |
|---|---|---|---|
| 0. Inventario | Esquema, versiones, tasa, mapeos, amenazas y respaldo restaurable | Matriz por equipo y responsables completos | Solo documentación |
| 1. Laboratorio | Ingreso HTTP, broker, identidad, inbox y objetos con datos sintéticos | Contratos, ACL, duplicados y recuperación pasan | Descartar laboratorio |
| 2. Banco físico | Un ESP32 legacy y un S3 con SIM7600; comparar AT/PPP | TLS negativo/positivo, SD y GNSS estables | Firmware previo y provisión controlada |
| 3. Sombra | Copia de muestras del piloto solo a tablas nuevas | Valores, unidades, horas y calidad conciliados | Detener sombra sin tocar histórico |
| 4. Corte por equipo | Activar un escritor nuevo y cerrar rutas legacy de sus sensores | Portal y exportaciones equivalentes; bypass bloqueado | Detener proyector, conservar inbox, revertir modo autorizado |
| 5. Expansión | Lotes pequeños con ventana de observación | Operación estable y soporte disponible | Volver por dispositivo, sin borrar eventos |
| 6. Archivos y comandos | Fotos primero; comandos con autorización e idempotencia luego | Carga reanudable y cuotas; comandos expirables | Deshabilitar capacidad, conservar mediciones |
| 7. Retiro legacy | Solo cuando cada equipo tenga sucesor o excepción registrada | Ningún emisor legítimo depende de ruta retirada | Ventana temporal documentada |

La sombra no debe duplicar inserciones en `datos`. Para equipos sin modificación, una copia a partir del ingreso existente sirve para validar backend, pero no prueba seguridad ni retransmisión del firmware. No deduplicar mediciones históricas únicamente por valor/hora. Para un corte ambiguo, marcar ventana y conciliar IDs, no borrar por similitud.

## Pruebas de aceptación necesarias

| Prueba | Resultado exigido |
|---|---|
| Equipo A intenta topic/uid/sensores B | Denegado, sin escritura |
| Sin identidad, identidad revocada, CA o hostname incorrectos | Rechazo; nunca bajar automáticamente a HTTP |
| Mismo evento 100 veces y por ambos transportes | Una proyección; mismo recibo |
| Mismo ID y cuerpo distinto | Conflicto auditado |
| Corte después de commit y antes de ACK | Reenvío recupera ACK sin duplicado |
| Caída DB o consumidor | Sin falso ACK durable; SD retiene, recuperación posterior |
| Reinicio broker y expiración sesión | SD recupera; no depender de PUBACK |
| 72 h sin red y apagado durante escritura SD | Eventos completos pendientes recuperados, corrupción detectada |
| Horas fuera de orden y reloj inválido | Captura preservada o marcada desconocida |
| Sensor desconectado y GNSS sin fix | null y calidad; sin cero fabricado |
| Imagen interrumpida al 30 % y 90 % | Reanuda desde bloques confirmados |
| Archivo corrupto, enorme o tipo falso | Rechazo/cuarentena, cuota y limpieza |
| Legacy intenta escribir sensores migrados por V1/V2/CRUD | Denegado |
| Portal/CSV/Power BI después del corte | Mismos mapeos y convención temporal acordada |
| Restauración en máquina aislada | Eventos, referencias y objetos consistentes |

Propuesta de salida del piloto: 7 días de funcionamiento y ensayos de interrupción, 0 duplicados en proyección, 100 % de eventos de prueba persistidos en SD entregados dentro de la ventana de recuperación bajo capacidad acordada, sin reinicios injustificados. Medir latencia p95 y energía antes de fijar SLA productivo. Para ensayo conectado, objetivo inicial de ACK p95 menor a 30 s; no presentarlo como garantía celular.

## Operación

Métricas: tiempo desde última captura y última recepción, edad y tamaño de colas, rechazos por motivo, conflictos, latencia de ACK/proyección, conexiones, RAM, reinicios, señal, bytes celulares, espacio libre, carga DB, cargas huérfanas y certificados próximos a vencer. Separar pérdida de enlace de ausencia de muestreo. Alertas y destinatarios se configuran en implementación, no se enviaron mensajes durante esta investigación.

Runbooks: caída broker, DB lenta, disco bajo, credencial comprometida, expiración CA, falta de hora, SD corrupta, tormenta de reconexiones y objetos huérfanos. El consumidor reintenta con techo y cuarentena; no descarta errores. Respaldar MariaDB, configuración broker, inventario/mapeos y objetos; secretos en almacén protegido separado. Mantener copia externa y demostrar restauración conjunta. Réplica y disco anterior no reemplazan copia externa.

Retención propuesta pendiente de aprobación: payload crudo 30 días, tombstones/recibos durante todo el horizonte de replay, cargas incompletas 48 h, imágenes según proyecto, cola SD al menos 72 h. Antes de purgar comprobar entregas pendientes y obligaciones científicas. El RPO/RTO final depende del respaldo real; objetivo inicial de recuperación del piloto en 4 h, sin prometer pérdida cero frente a destrucción del único servidor.

## Registro obligatorio por cambio productivo

Antes de desplegar: preservar worktrees, respaldo del artefacto/configuración previos y migración reversible ensayada. Registrar commit/tag o referencia inequívoca, responsable, alcance por equipo, pruebas, sumas de artefactos calculadas en ubicación protegida y procedimiento de reversión. No incluir credenciales ni hashes de autenticación. No se calculan ni publican aquí valores de hashes reales.

Rollback: pausar proyección, mantener inbox y SD, conservar versión anterior, restituir configuración de ingreso por equipo según autorización y conciliar pendientes. No resetear producción ni borrar tablas históricas. No usar el rollback para reactivar silenciosamente escritura anónima de toda la flota.

## Backlog para implementar

1. Backend: esquema preciso y migraciones aditivas; contrato/OpenAPI/AsyncAPI y schemas validados; fixtures de unidades/mapeos.
2. Seguridad: aprovisionamiento, ACL, renovación, revocación y políticas de convivencia por sensor.
3. Ingreso: HTTP primero reutilizable por consumidor MQTT, inbox, ACK y proyector transaccional.
4. Firmware: cola durable, IDs, captura UTC/calidad, transporte y simulador; ambos targets compilables.
5. Archivos: sesiones reanudables, objetos, reconciliador, autorización y visualización futura.
6. Operación: métricas, límites, backups/restauración, pruebas de fallo y runbooks.

Responsables necesarios: backend/datos, firmware/hardware, infraestructura/seguridad y dueño científico del proyecto. Pueden ser las mismas personas, pero cada entregable necesita aceptación explícita de su responsable.
