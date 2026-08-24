# Aire Aconcagua: reemplazo V7 por V1, fotos y gráficos estables

Fecha: 2026-08-24  
Sitio: `https://cmasudd.github.io/aireaconcagua/`  
Repositorio: `https://github.com/cmasudd/aireaconcagua`  
Rama: `main`

## Referencias de producción

- Estado anterior: commit `4e8a7a7a025266f50e032cca6b8945d418a25b7a`.
- Cambio funcional: commit `7895d4ee12b3d5d8dd73ff573f9034c87d82d649`.
- Primera ejecución horaria verificada: commit
  `8e74c16f6f686e52bc5d3c8f7e6627955d4b8e17`.
- Etiqueta del cambio funcional:
  `aire-prod-v1-photos-chartfix-2026-08-24`.
- GitHub Pages: ejecución `32756695544`, build y deploy exitosos.
- Autor de ambos commits: cuenta `cmasudd` con correo público `noreply` de
  GitHub. La configuración quedó limitada al repositorio.

## Respaldo previo

El respaldo está fuera de los repositorios Git en:

```text
/home/cmas/backups/aireaconcagua-v1-photos-2026-08-24/
```

Incluye los archivos anteriores, los CSV de V7, el manifiesto, `latest.csv`,
evidencia de las pruebas de navegador y el bundle
`aireaconcagua-before.bundle`. El documento fuente de fotografías y el log del
daemon se preservaron localmente y no se agregaron a Git.

## Cambios realizados

1. Escuela Viña Errázuriz pasó de `HIRIPRO-V7` (`device_id` 234) a
   `HIRIPRO-V1` (`device_id` 224) en la web vigente, la versión antigua, la
   lectura reciente, la configuración del exportador y el manifiesto.
2. Se generó el histórico de V1 por mes desde el MariaDB local: abril, mayo,
   junio, julio y agosto de 2026. Los CSV de V7 se retiraron del sitio.
3. El daemon horario continúa usando `scripts/update_data.sh`. Como el
   exportador lee `config/stations.json`, desde este cambio publica V1 y deja de
   consultar/publicar V7 sin requerir un segundo listado de sensores.
4. Chart.js y Leaflet se sirven desde `assets/vendor/`. Esto elimina la
   dependencia de CDN que podía detener toda la inicialización cuando Leaflet
   no cargaba.
5. La creación de gráficos se difiere hasta que el panel esté visible y se
   agrupan las actualizaciones simultáneas de CSV. Los gráficos se regeneran al
   cambiar pestaña, modo o tamaño de pantalla.
6. Se agregó la pestaña Fotos con 30 fotografías y un lienzo del proyecto. Las
   imágenes usan carga diferida.
7. Se agregó el aviso de uso responsable junto a la descarga, los créditos y
   el contacto `corporacioncaudal@gmail.com`.

## Protección del servidor

- El histórico se obtiene de CSV mensuales publicados por GitHub Pages; el
  navegador no solicita rangos históricos a la API.
- El mes vigente se reconstruye una vez por hora con consultas acotadas por
  sensor y fecha sobre el índice `idx_datos_sensor_fecha`.
- El backfill de meses anteriores solo se ejecuta manualmente con `--all`.
- La vista en vivo conserva una solicitud `limite=1` por estación cada diez
  minutos. Las solicitudes se espacian para evitar una ráfaga simultánea.
- `flock -n /tmp/aireaconcagua-update.lock` evita ejecuciones superpuestas del
  exportador horario.
- El daemon crea y sube un commit solo si cambió el directorio `data/`.
- Cada CSV se divide automáticamente antes de superar 40 MiB.

## Pruebas y resultados

- Sintaxis del JavaScript embebido: `node --check`, correcto.
- Pruebas unitarias: 4 de 4 correctas.
- Validación completa de CSV: encabezado, mes, orden cronológico, rutas del
  manifiesto y límite de tamaño, correcta.
- Mayor CSV publicado: 1.826.098 bytes, bajo el límite de 41.943.040 bytes.
- Prueba real de navegador en escritorio: cuatro ciclos Profesional → Escolar
  → Fotos → Monitoreo sin recargar, todos los gráficos con dimensiones y datos
  válidos.
- La misma prueba en viewport móvil también pasó cuatro ciclos.
- Ejecución exacta del daemon: 435.480 mediciones procesadas; V1 incluyó 49.782
  mediciones de agosto y V7 no apareció.
- GitHub Pages: build en 25 segundos y deploy en 20 segundos, ambos correctos.
- Verificación pública: HTML, manifiesto, Chart.js, fotografía y CSV V1
  coincidieron byte por byte con el artefacto local.

## Hashes del artefacto desplegado

```text
index.html
5a587ac348265ac6560f44f80dd7d171f9044fde5927d1ead22f1a6e1d9d08da

data/manifest.json
c66040170a8a9da16ac87e78850c9f29cd78f1452a79517670f873e1bc3930b8

data/latest.csv
423cd2dc64c17ec8bb6bd46c3012a81f991e27ced7055f6e8d4db5d0528dc16e

assets/vendor/chart.umd-4.4.1.js
74401d738dd3e03ee5dfb3b6841210fe2c4ead8a960c4011ca4ba0b78a9fd8f3

assets/vendor/leaflet/leaflet-1.9.4.js
db49d009c841f5ca34a888c96511ae936fd9f5533e90d8b2c4d57596f4e5641a
```

Los hashes de `manifest.json` y `latest.csv` corresponden a la primera
ejecución horaria posterior al cambio. Es normal que cambien en cada hora.

## Reversión

Para volver exactamente al estado anterior sin reescribir el historial:

1. Adquirir el lock `/tmp/aireaconcagua-update.lock` para que cron no escriba
   durante la reversión.
2. En `/home/cmas/Documentos/aireaconcagua`, revertir primero el commit horario
   `8e74c16f` y después el funcional `7895d4ee` con `git revert`.
3. Ejecutar las pruebas unitarias y verificar que el árbol corresponde al
   commit anterior `4e8a7a7a`.
4. Subir los commits de reversión y esperar que GitHub Pages finalice.
5. Liberar el lock. El bundle y los archivos originales del respaldo permiten
   recuperación adicional si fuera necesaria.

La etiqueta `aire-prod-v1-photos-chartfix-2026-08-24` permite recuperar o
comparar rápidamente el artefacto funcional de este cambio.

## Ajuste posterior de footer, logos y descarga responsable

Referencia: commit `ee34f86b` del repositorio Aire Aconcagua. GitHub Pages se
desplegó correctamente en la ejecución `32762700154`.

- El contacto quedó en un footer fijo visible en Monitoreo, Proyecto y Fotos.
- Los cuatro logos tienen variables CSS independientes al comienzo de
  `index.html`. El Gobierno Regional usa por defecto 160 px de altura máxima y
  640 px de ancho máximo.
- El disclaimer aumentó a 820 px de ancho, título de 24 px y texto de 16 px.
- El botón de descarga abre primero el disclaimer y presenta allí el botón
  final `Descargar CSV`, sin casilla de aceptación.
- Se añadió `.gitattributes` para normalizar como LF los archivos de texto y
  evitar cambios masivos de finales de línea al editar con Visual Studio Code.

Se preservó la edición manual recibida y se respaldó antes de intervenir en:

```text
/home/cmas/backups/aireaconcagua-manual-before-footer-disclaimer-2026-08-24/
```

Pruebas: sintaxis JavaScript correcta, 4 de 4 pruebas unitarias correctas,
validación estática del flujo de descarga y revisión visual local a 1440 ×
1000. El HTML público coincidió byte por byte con el artefacto Git:

```text
index.html
de3ba68a5fae9ab222518ed2180319f9ac3a2d1bca4a28e6d276a18743c0d048
```

Reversión: adquirir `/tmp/aireaconcagua-update.lock`, ejecutar `git revert`
sobre `ee34f86b`, probar, subir el commit de reversión, esperar GitHub Pages y
liberar el lock. El respaldo anterior permite comparar o recuperar la edición
manual si fuera necesario.
