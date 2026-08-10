# Administración de usuarios y protocolos API

Fecha: 10 de agosto de 2026, zona horaria America/Santiago.

## Objetivo

Permitir administrar cuentas locales de visita y administrador desde el portal,
registrar la cuenta de visita solicitada y reemplazar los protocolos simulados
por la documentación Swagger viva del API.

## Cambios aplicados

- Nueva tabla aislada `portal_usuarios`, sin cambios en tablas de sensores.
- Correos únicos normalizados, contraseña almacenada como hash, roles `visita` y
  `administrador`, estado activo y fechas de creación/actualización.
- Login local múltiple con compatibilidad para la cuenta histórica configurada
  por entorno.
- Rutas protegidas `GET/POST /v3/admin/users` y
  `PUT /v3/admin/users/{id_usuario}`.
- Las visitas reciben 403 en las rutas administrativas; ningún endpoint devuelve
  hashes.
- Interfaz `Administrador > Usuarios` para crear, cambiar rol, desactivar y
  cambiar contraseña.
- `Protocolos` ahora permite visualizar Swagger embebido o abrirlo en otra
  pestaña; se retiraron las tarjetas PDF simuladas.
- Swagger documenta las rutas nuevas. También se corrigió la clave YAML `Null`
  del esquema legacy, que generaba un error interno de serialización aunque el
  servidor aplicaba un fallback.
- Se registró la cuenta solicitada como visita activa. La contraseña no se
  incluyó en archivos, commits, logs ni documentación.

## Versiones y artefactos

| Concepto | Valor |
|---|---|
| Frontend commit | `022255ee` |
| Frontend tag | `sensores-prod-user-admin-v1` |
| Repositorio | `https://github.com/cmasudd/SensorsWebApp` |
| Bundle publicado | `index-cec81e30.js` |
| SHA-256 bundle | `4fb519897a6d6c2be9d002b9dc1d49618f6d1e72b6838021de1a7c78e694d54c` |
| SHA-256 index | `dceb98acf642c52ac93cdee58952c83366faf3c09c046a1cd22e3561c0028fa8` |
| Respaldo | `/home/cmas/backups/portal-users-2026-08-10` |

## Pruebas

- Backend: 7 pruebas unitarias focalizadas y 22 pruebas de regresión del
  repositorio aprobadas, incluyendo históricos y borrado seguro existente.
- Frontend: 3 archivos y 8 pruebas aprobadas; build Vite aprobado.
- Swagger candidato y público: 29 paths; rutas de usuarios presentes.
- Cuenta solicitada: login público 200, rol `visita`; intento de listar usuarios
  403.
- Sesión administradora de prueba: crear 201, listar 200, editar 200; hash ausente
  en la respuesta. La cuenta temporal se eliminó al finalizar.
- Procesos PM2 `api_sensores` y `sensores`: online.
- El dominio público entrega `index-cec81e30.js`; `/apidocs/` devuelve 200.

## Reversión

1. Restaurar `app.py` y `historico_v3.py` desde
   `/home/cmas/backups/portal-users-2026-08-10/api-before/` y recargar solamente
   PM2 `api_sensores`.
2. Restaurar el frontend desde
   `/home/cmas/backups/portal-users-2026-08-10/public-before/` o revertir al tag
   `sensores-prod-safe-device-delete-v1`.
3. La tabla `portal_usuarios` puede permanecer sin uso durante la reversión. No
   debe eliminarse hasta respaldarla y confirmar que no se necesita recuperar
   cuentas.

## Riesgo pendiente

Para conservar el comportamiento anterior, una sesión Microsoft válida que no
esté registrada se considera administradora. Debe migrarse a una lista explícita
de administradores institucionales después de inventariar las cuentas actuales,
para no bloquear accidentalmente a los operadores existentes.
