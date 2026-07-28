# Buenas prácticas para históricos de sensores

Repositorio de referencia para migrar gradualmente desde los endpoints legacy a
una API V3 por dispositivo.

## Objetivos

- Mantener funcionando las rutas antiguas.
- Ocultar al cliente la relación dispositivo–sensores.
- Evitar consultas masivas con `OFFSET` o listas enormes de sensores.
- Permitir descargas NDJSON reanudables.
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
  --device-id 224 \
  --start-date 2026-07-23 \
  --end-date 2026-07-23 \
  --output-dir descargas
```

El cliente descarga un dispositivo completo; no requiere conocer sus sensores.
Durante una caída conserva `.part` y `.state.json`. Al completar genera
`ndjson.gz` y elimina los temporales.

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
controladas. Para el sitio público Aire Aconcagua, los históricos se publican
como CSV mensuales en GitHub Pages y la API se reserva para una última lectura
acotada. La implementación y las verificaciones operativas se describen en
`docs/HISTORICO_CSV_GITHUB.md`.
