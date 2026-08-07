# CRUD de sensores sin recarga completa

Fecha: 7 de agosto de 2026, zona horaria America/Santiago.

## Incidente y causa

Al agregar o editar desde el portal, el registro se guardaba pero la interfaz
ejecutaba `window.location.reload()`. Esto perdía proyecto, dispositivo, filtros
y posición del usuario. El alta de sensores además consultaba `ultimoValor`, por
lo que dos inserciones simultáneas podían usar el ID de otro usuario.

## Corrección

- El modal ejecuta una sola solicitud, bloquea dobles clics, conserva el
  formulario ante errores y notifica al padre mediante `onSuccess`.
- Las vistas actualizan solamente la colección afectada mediante `forceFetch`.
- El alta y la duplicación usan el `id` retornado por `POST /agregarDatos`; ya no
  consultan `ultimoValor`.
- Se agregaron pruebas de éxito, error, doble clic y altas concurrentes.

## Versiones y artefactos

| Concepto | Valor |
|---|---|
| Commit reconciliado previo | `4106f7d36d0b07e19a8abe057f5142a2aa7eaa09` |
| Tag previo | `sensores-prod-before-crud-20260807` |
| Commit de corrección | `ca146c0c0e214bce494069313d5fdadc3fc3b767` |
| Tag publicado | `sensores-prod-crud-no-reload-v1` |
| Bundle anterior | `index-43e174d6.js` |
| SHA-256 anterior | `616bab7783a2a3497b6a3811dc75b53666b2897f12566d8b92068cb8a71d183a` |
| Bundle publicado | `index-e816e901.js` |
| SHA-256 publicado | `04bc6206dbe62e15a36568a3cc6da9b178835d250e42f49937493ef8b385507b` |
| Respaldo web | `/home/cmas/backups/sensores-crud-2026-08-07/public-before` |

## Validación previa

- `npm test`: 2 archivos y 6 pruebas aprobadas.
- `npm run build`: aprobado con Vite 4.1.0; bundle de 995,28 kB.
- `git diff --check`: sin errores.
- Vista previa y producción cargaron correctamente mediante Chrome headless.
- El dominio público entregó `index-e816e901.js` después del despliegue.
- `api_sensores` quedó `online` después de rotar la credencial local.
- El nuevo login y su sesión devolvieron 200; la contraseña predeterminada
  anterior dejó de validar. La nueva clave existe solamente en
  `/home/cmas/.secrets/sensores-login-local.txt`, con permisos 600.

## Publicación del historial

La bitácora quedó publicada en `cmasudd/buenas_practicas`, commit `baf97f3`.
Los commits y tags de `SensorsWebApp` están en el repositorio local productivo.
El intento de publicarlos en `CmasCcp/SensorsWebApp` fue rechazado con HTTP 403
porque la cuenta configurada `cmasudd` no tiene permiso sobre esa organización.
No se creó un repositorio alternativo para evitar dividir la fuente canónica.

## Rollback

Restaurar `public/index.html` y el asset anterior desde el respaldo, comprobar
los hashes indicados y consultar `https://sensores.cmasccp.cl/`. El código puede
revertirse al tag previo sin modificar registros de MariaDB.

## Pendientes prioritarios

- Proteger los endpoints CRUD en el servidor.
- Convertir alta de sensor y asociación en una transacción backend única.
- Publicar mediante directorios de release y cambio atómico.
- Retirar secretos históricos que todavía estén embebidos en código o procesos.
