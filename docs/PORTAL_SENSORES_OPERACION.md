# Operación del portal de sensores

## Fuentes canónicas

| Elemento | Ubicación |
|---|---|
| Portal público | `https://sensores.cmasccp.cl/` |
| Fuente de producción | `/var/www/sensores` |
| Repositorio canónico | `https://github.com/cmasudd/SensorsWebApp` |
| Repositorio histórico upstream | `https://github.com/CmasCcp/SensorsWebApp` |
| API | `/var/www/api_sensores`, `https://api-sensores.cmasccp.cl` |
| Proceso web | PM2 `sensores`, puerto 8103 |
| Directorio servido | `/var/www/sensores/public` |
| Bitácora técnica | `/home/cmas/Documentos/buenas_practicas/cambios` |

Antes de modificar producción se deben revisar `git status`, el asset indicado por
`public/index.html`, el proceso PM2 y la última entrada de la bitácora. Los
worktrees de producción pueden contener cambios aún no publicados en GitHub.

## Publicación segura

1. Trabajar en una copia o rama separada y preservar los cambios existentes.
2. Ejecutar `npm test` y `npm run build`.
3. Guardar una copia completa de `public` bajo `/home/cmas/backups/`.
4. Registrar SHA-256 de `index.html` y del bundle JavaScript anterior y nuevo.
5. Copiar primero el bundle con nombre versionado y después `index.html`.
6. Consultar el sitio público, confirmar el nombre y hash del asset y revisar los
   logs de PM2. El servidor estático no necesita reiniciarse para leer archivos
   nuevos.
7. Mantener el bundle anterior durante la ventana de verificación.

## Reversión

La reversión web no toca la base de datos. Se restaura el `public/index.html`
anterior y su bundle desde el respaldo fechado, se verifica su SHA-256 y se
consulta nuevamente el dominio público. Para revertir el código fuente se usa el
tag anterior o `git revert`; no se usa `git reset --hard` sobre producción.

## Credenciales

La sesión local V3 se configura con `HISTORICO_USER` y
`HISTORICO_PASSWORD_HASH` en el entorno protegido del API. Git contiene
solamente los nombres de variables y el procedimiento. Nunca se registran
contraseñas, hashes reales, cookies, tokens o archivos `.env`.

La visibilidad de botones en React no protege los endpoints de escritura. La
autorización servidor-side de `agregarDatos`, `modificarDatos` y `eliminarDatos`
permanece como mejora urgente.

## Política de borrado de dispositivos

- Un dispositivo solo se elimina físicamente cuando ninguno de sus sensores
  tiene mediciones.
- Antes de eliminar se bloquean las filas implicadas y se quitan las
  asociaciones; solo se eliminan sensores que queden huérfanos y sin datos.
- Si existe historial, el API responde 409 y el administrador ofrece cambiar el
  dispositivo al estado `Inactivo` (ID 2), conservando todas las mediciones.
- El borrado forzado con historial no está habilitado. Está registrado como
  propuesta futura de alto riesgo en la bitácora del 8 de agosto de 2026.
