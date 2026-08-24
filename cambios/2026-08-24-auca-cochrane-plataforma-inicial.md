# Plataforma inicial AUCA Cochrane

Fecha: 2026-08-24

Repositorio: `https://github.com/cmasudd/auca-cochrane`

Sitio: `https://cmasudd.github.io/auca-cochrane/`

## Alcance

- Web estática nueva con HTML, tres CSS y cinco módulos JavaScript separados.
- Dispositivos 241 a 244, códigos `HIRI-AUCA-1` a `HIRI-AUCA-4`.
- Backfill de julio y agosto desde MariaDB local.
- CSV por estación/mes, manifiesto y lectura reciente.
- Actualización horaria desde un clon exclusivo.
- GitHub Pages público.

## Perfil previo y minimización

Antes de diseñar el CSV se revisaron modelos, variables, cobertura, rangos,
constantes y centinelas. Se publicaron PM1, PM2.5, PM10, temperatura/humedad
ambientales, temperatura/humedad internas, relé y señal.

No se publicaron latitud, longitud ni velocidad porque la primera versión no
tiene geolocalización autorizada. Satélites se excluyó por contener solo `-1` y
voltaje por contener solo `0` en el período revisado. La decisión queda en
`docs/PERFIL_DATOS.md` del repositorio AUCA y originó la guía reutilizable
`08_PERFILAR_DATOS_ANTES_DE_PUBLICAR.md`.

## Referencias Git y Pages

- Commit inicial: `576691e3d4d2020ec27d6678f241e6c0dfcb200f`.
- Primera publicación horaria manual:
  `e1396dc0da8b22546a7eb7bc65e604a8602e218b`.
- Prueba de la línea exacta de cron:
  `67079445fb2030217d7aa4f78b9e49df99407d42`.
- Documentación operativa final:
  `bc32f4f`.
- Ejecución inicial de Pages: `32774262774`, correcta.
- Autor: `cmasudd` con correo público `noreply` configurado solamente en los
  clones AUCA.

## Servidor y automatización

- Edición: `/home/cmas/Documentos/auca-cochrane`.
- Clon del publicador: `/home/cmas/servicios/auca-cochrane-publisher`.
- Frecuencia: minuto 17 de cada hora.
- Lock: `/tmp/auca-cochrane-update.lock`.
- Log: `data-update.log` ignorado por Git dentro del clon del publicador.
- Respaldo protegido del crontab anterior:
  `/home/cmas/backups/auca-cochrane-cron-before-2026-08-24/crontab.cmas`.

La tarea existente de Aire Aconcagua permanece al minuto 7 y no fue modificada.
El piloto reutiliza la autenticación institucional ya comprobada en este
servidor. Una credencial exclusiva del repositorio queda recomendada antes de
considerarlo operación definitiva.

## Pruebas

- 257.526 mediciones procesadas en el backfill.
- Cinco pruebas unitarias correctas.
- Validación de manifiesto, latest, CSV, fechas, orden y límite correcta.
- Sintaxis de los cinco módulos JavaScript correcta.
- Auditoría npm sin vulnerabilidades después de retirar una dependencia temporal
  de prueba que presentaba alertas altas.
- Navegador real: cuatro tarjetas, nueve variables y 403 puntos iniciales.
- Cuatro ciclos de cambio de estación, variable y período sin recarga.
- Aviso previo a descarga correcto.
- Sin desbordamiento horizontal a 1440 × 1000 ni 390 × 844.
- Lectura reciente correcta y escalonada cada diez minutos.
- Artefacto público inicial coincidente byte por byte con el local.
- Dos ejecuciones reales del wrapper con commit y push correctos.

Mayor CSV comprobado después de la prueba horaria: 348.915 bytes. Directorio
`data/`: 1,5 MiB.

## Hashes comprobados

```text
index.html
d71ff3c0f0f6802cc075c2d2fbec701da82dff145cb242fdb417e89b9e097972

data/manifest.json
d904c57e7969ef53b587532972bda3d34c305c7856fba7fef71f1c13e9d107d3

data/latest.csv
91270c36ba278a6ae2261326d959c86886aa063db6cb3779a4a54e72384bf799

scripts/export_monthly_csv.py
84eb3b4512bb04c735b637293e1499c5ec259399f74afa201eafa447cfb14ed7

scripts/update_data.sh
9ee7e0dd87d2690c912ef280e0d44159c58828301b67f7e779fb46cb8a2e6bcd

scripts/validate_export.py
e724b75d7cef065d6ae773f2c3186e3f8a9d3d3dc218a0a5b27e162e7027ad4f
```

Los hashes de manifiesto y latest son móviles y corresponden al commit
`67079445`.

## Reversión

1. Restaurar el crontab protegido anterior con `crontab`.
2. Adquirir `/tmp/auca-cochrane-update.lock`.
3. Conservar clon y log para diagnóstico.
4. Revertir el commit que corresponda mediante `git revert`.
5. Esperar Pages y comprobar sitio, manifiesto y CSV.
6. Confirmar que la tarea de Aire Aconcagua continúa presente.

No se usa `git reset --hard` ni se borra el clon como primer paso de reversión.
