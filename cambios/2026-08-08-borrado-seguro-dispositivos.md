# Borrado seguro de dispositivos

Fecha: 8 de agosto de 2026, zona horaria America/Santiago.

## Incidente

El editor intentaba borrar directamente `dispositivos`. MariaDB devolvía 1451
porque `sensores_en_dispositivo.id_dispositivo` mantiene una clave foránea. El
error evitaba corrupción, pero la interfaz no ofrecía una salida útil.

## Solución aplicada

- El API bloquea las filas implicadas dentro de la transacción.
- Si cualquier sensor asociado tiene registros en `datos`, no ejecuta ningún
  `DELETE`, revierte y responde HTTP 409 con `can_deactivate: true`.
- El editor ofrece marcar ese dispositivo como `Inactivo` (estado 2), sin borrar
  mediciones.
- Si no existen mediciones, elimina primero las asociaciones, después sensores
  que queden huérfanos y sin datos, y finalmente el dispositivo.
- El flujo genérico de eliminación de otras tablas no fue modificado.

## Versiones, artefactos y respaldo

| Concepto | Valor |
|---|---|
| Frontend commit | `028ace70` |
| Frontend tag | `sensores-prod-safe-device-delete-v1` |
| Repositorio | `https://github.com/cmasudd/SensorsWebApp` |
| Bundle | `index-2b2f2b66.js` |
| SHA-256 bundle | `1cd844e5bd9273889e4a180675d999a2823b1b47334a76292b1ad68a66391e37` |
| SHA-256 index | `12f857ab13f839cee35123d26ca9aebcac8a83182b31403fb1227c82146480de` |
| Respaldo frontend | `/home/cmas/backups/device-delete-safe-2026-08-08/public-before` |
| Manifiesto | `/home/cmas/backups/device-delete-safe-2026-08-08/public-before.MANIFEST.sha256` |
| Respaldo API | `/home/cmas/backups/device-delete-safe-2026-08-08/app.py.before` |

El módulo backend versionado está en `backend/device_deletion.py`; su copia
operativa vive en `/var/www/api_sensores/device_deletion.py`.

## Validaciones

- Cuatro pruebas unitarias del borrado aprobadas.
- Compilación/importación Python aprobadas.
- Integración real ejecutada dentro de una transacción revertida: caso vacío y
  caso protegido.
- Dispositivo real con 78.028 mediciones: HTTP 409 y existencia confirmada tras
  el intento.
- Prueba HTTP completa con dispositivo temporal sin datos: HTTP 200; borró una
  asociación, un sensor huérfano y un dispositivo, sin residuos.
- Frontend: 2 archivos, 6 pruebas aprobadas; `npm run build` aprobado.
- El dominio público entrega `index-2b2f2b66.js`.

## Reversión

1. Restaurar `/var/www/api_sensores/app.py` desde `app.py.before` y recargar
   solamente PM2 `api_sensores`.
2. Restaurar `/var/www/sensores/public` desde `public-before` y comprobar el
   manifiesto SHA-256. El servidor estático no requiere reinicio.
3. Para fuente frontend, revertir el commit `028ace70` o volver al tag
   `sensores-prod-crud-no-reload-v1`; no usar `git reset --hard` en producción.

## Zona de riesgo futura: borrado forzado con datos

**Propuesta no implementada y no habilitada.** Un borrado que incluya historial
puede destruir trazabilidad ambiental y afectar reportes. Solo debería
considerarse después de implementar conjuntamente:

1. permiso elevado independiente del administrador normal;
2. vista previa del número de sensores, asociaciones y mediciones afectadas;
3. exportación y respaldo verificable con manifiesto antes de confirmar;
4. confirmación escrita con el código exacto del dispositivo;
5. auditoría inmutable de solicitante, motivo, fecha y conteos;
6. eliminación diferida con período de retención y posibilidad de restauración;
7. proceso dedicado, nunca `ON DELETE CASCADE` ni el endpoint CRUD genérico.

Hasta que existan esas barreras, la única alternativa admitida para un
dispositivo con datos es marcarlo como `Inactivo`.
