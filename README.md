# Buenas prácticas para históricos de sensores

Repositorio de referencia para migrar gradualmente desde los endpoints legacy a
una API V3 por dispositivo.

## Objetivos

- Mantener funcionando las rutas antiguas.
- Ocultar al cliente la relación dispositivo–sensores.
- Evitar consultas masivas con `OFFSET` o listas enormes de sensores.
- Permitir descargas NDJSON reanudables y CSV desde la web autenticada.
- Acotar memoria y trabajo de MariaDB.

## Componentes

- `historico_v3.py`: Blueprint Flask que implementa V3.
- `download_v3.py`: cliente de descarga con checkpoints, reintentos y gzip.
- `docs/API_V3.md`: contrato y decisiones operativas.
- `docs/INTEGRACION.md`: registro junto a las rutas legacy.
- `docs/HISTORICO_CSV_GITHUB.md`: arquitectura aplicada para publicar
  históricos mensuales en GitHub sin saturar MariaDB.
- `tests/`: pruebas unitarias de cursores y validación.

## Uso del descargador

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

python download_v3.py \
  --username USUARIO \
  --device-id 224 \
  --start-date 2026-07-23 \
  --end-date 2026-07-23 \
  --output-dir descargas
```

El cliente descarga un dispositivo completo; no requiere conocer sus sensores.
Solicita la contraseña de forma interactiva y no la guarda ni la muestra en la
línea de comandos.
Durante una caída conserva `.part` y `.state.json`. Al completar genera
`ndjson.gz` y elimina los temporales.

## Descarga desde sensores.cmasccp.cl

El sitio usa una sesión HTTP-only validada por el servidor. La descarga CSV
acepta uno o varios `id_dispositivo`; si se omiten las fechas, recorre todo el
histórico disponible. MariaDB se consulta en páginas keyset de 1.000 filas y la
respuesta se transmite sin construir el archivo completo en memoria.

El CSV predeterminado usa la misma forma ancha que la tabla web y genera sus
columnas según los sensores de cada dispositivo. Para procesamiento automático
se puede solicitar la forma normalizada con `formato=largo`.

Solo se permite una exportación CSV activa. Una segunda solicitud espera hasta
30 segundos y, si el turno sigue ocupado, recibe HTTP 429 con `Retry-After: 30`.
Esto es un cortacircuito seguro, no una cola persistente de trabajos.

La tabla del portal muestra mediante V3 las 25 mediciones estructuradas más
recientes, sin recorrer todo el histórico. La descarga CSV usa el rango completo
seleccionado. Los cambios de filtros se
agrupan durante 500 ms y las solicitudes HTTP reemplazadas se abortan para
evitar duplicados mientras el usuario completa el formulario.

## Índices comprobados en producción

La implementación aprovecha los índices existentes:

```text
datos:                      (id_sensor, fecha)
sensores_en_dispositivo:    (id_dispositivo, id_sensor)
```

No se incluyó ninguna migración de base de datos.

Los resultados se ordenan por `id_sensor`, `fecha` e `id_dato`. Este orden
permite recorrer el índice sin ordenar todo el rango histórico en cada página.

## Estado

La API V3 mantiene consultas paginadas y streaming reanudable para integraciones
controladas. El portal de sensores puede exportar CSV autenticado directamente;
la publicación de cortes mensuales en GitHub sigue siendo una alternativa para
datos abiertos de alta demanda.
