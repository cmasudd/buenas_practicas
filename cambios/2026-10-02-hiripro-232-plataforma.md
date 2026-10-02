# Plataforma pública HIRIPRO-V5 / dispositivo 232

Fecha: 2 de octubre de 2026  
Repositorio upstream: `AleReb/HIRI232`  
Fork y fuente publicada: `cmasudd/HIRI232`  
URL: `https://cmasudd.github.io/HIRI232/`

## Alcance

- Se creó el fork institucional y se publicó GitHub Pages desde `main`.
- Se reemplazó el modo demostración por 12.047 ciclos reales iniciales del
  dispositivo interno 232, código comprobado `HIRIPRO-V5`.
- El navegador consulta una sola fila de `/v3/vista-previa` cada 10 minutos.
- El histórico CSV se reconstruye incrementalmente y se publica una vez por
  hora, al minuto 37, con `flock` no bloqueante.
- El clon automático separado vive en
  `/home/cmas/servicios/hiri232-publisher`.

## Perfil de datos

El perfil inicial abarcó 12.037 ciclos entre el 22 de abril y el 2 de octubre
de 2026. Se publicaron las ocho series con información real:

- PMS5003: PM1, PM2.5, PM10, temperatura y humedad;
- SHT40: temperatura y humedad;
- SIM7600G: intensidad de señal, conservada como valor adimensional 0–31.

SO₂, TVOC, eCO₂, latitud, longitud, velocidad, satélites y PM100 sólo
contenían `-1` y `0`. El voltaje tenía 11.972 ceros en 12.037 filas y ningún
valor positivo posterior al 31 de julio. Se excluyeron para no presentar
centinelas como mediciones. Los pares temperatura/humedad exactamente `0/0`
se reservan como ausentes; los ceros de material particulado se conservan.

## Referencias y publicación

- `baee318`: portal real, exportador, backfill, validador y documentación.
- `160d14e`: permisos ejecutables de los scripts del publicador.
- `b1c85af`: primera actualización automática comprobada, 12.049 registros.
- `f0538bf`: log local ignorado y reintento de commits pendientes aunque no
  aparezcan mediciones nuevas.
- Pages terminó en estado `built` para `b1c85af8b01faac77c21bf116f0e9f30a1a70bc5`.

La primera ejecución automática incorporó dos ciclos llegados después del
backfill y publicó el commit sin intervención manual. Una segunda ejecución
con el comando exacto del cron no generó commit vacío, dejó el worktree limpio
y confirmó `Everything up-to-date`.

## Cambio acotado del API

Se agregó únicamente `https://cmasudd.github.io` a las dos listas CORS
existentes de `/var/www/api_sensores/app.py`. Se preservaron todos los cambios
sin commit que ya tenía el worktree productivo. Después de recargar PM2
`api_sensores`, el proceso quedó `online` y la consulta real respondió HTTP
200 con `Access-Control-Allow-Origin: https://cmasudd.github.io`.

- SHA-256 anterior de `app.py`:
  `11cba4cd603a37b7ad58225b76d36325e4e9fd9344e9c1c9a61ccfbe92c45535`.
- SHA-256 activo de `app.py`:
  `478540eefee36c9af9b631863f9dd6d2990c2e8b84405d5265b0e6035d18a3f7`.
- Respaldo: `/home/cmas/backups/hiri232-2026-10-02/api/app.py.before`.

## Pruebas y artefactos

- `node --check app.js`: correcto.
- Pruebas del portal Node: correctas.
- `python3 -m unittest discover -s tests -v`: 6 pruebas correctas.
- Backfill completo y actualización incremental idempotente: correctos.
- `scripts/validate_export.py`: esquema, orden, unicidad, rangos y dispositivo
  correctos; 12.049 registros y última fila `2026-10-02T18:45:20Z`.
- Comprobación pública: `index.html`, `portal.json` y CSV descargados desde
  Pages coinciden byte a byte con el clon publicador.
- Revisión de secretos: correcta; no hay `.env`, claves ni tokens en Git.

SHA-256 públicos:

| Artefacto | SHA-256 |
|---|---|
| `index.html` | `3781cae2f3e2a27045b2fdffc6980394290d31217245b1b3d1b33dddfe3ed77b` |
| `app.js` | `d7cb2675cb722a52b8e624f8ece5ed1ec4af672afe85ae928dd52f526eb5635a` |
| `config/portal.json` | `6afcbe596860b71b49af69d05ae3368604f98014005e6b1999b5a9feb3487bf8` |
| `data/hiripro-232.csv` | `eff37ee997fb83ed7fcab8a76288efd6155b179ee5423b08c121cdd79e78c6ec` |

## Automatización y respaldo

La única tarea HIRI232 instalada es:

```cron
37 * * * * /usr/bin/flock -n /tmp/hiripro-232-update.lock /home/cmas/servicios/hiri232-publisher/scripts/update_data.sh >> /home/cmas/servicios/hiri232-publisher/data-update.log 2>&1
```

El crontab anterior quedó protegido con permiso `0600` en
`/home/cmas/backups/hiri232-2026-10-02/crontab.before`.

## Reversión

1. Restaurar el crontab respaldado o retirar sólo la entrada HIRI232.
2. Adquirir `/tmp/hiripro-232-update.lock`.
3. Revertir en Git `f0538bf`, `b1c85af`, `160d14e` y `baee318` mediante `git revert` y
   esperar el build de Pages; no usar `reset --hard`.
4. Si se retira la lectura viva, restaurar `app.py.before`, verificar su hash y
   recargar `api_sensores`.
5. Comprobar el estado PM2, la URL pública, CORS y los hashes publicados.

No se guardaron credenciales, hashes de autenticación, cookies, tokens ni
archivos `.env` en el repositorio o esta bitácora.
