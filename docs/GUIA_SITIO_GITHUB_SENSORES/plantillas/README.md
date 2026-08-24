# Plantillas

Estos archivos son puntos de partida. Los marcadores en mayúsculas deben
reemplazarse y revisarse antes de instalar.

| Archivo | Propósito |
|---|---|
| `stations.example.json` | inventario público de estaciones |
| `.env.example` | nombres de variables esperadas, sin valores reales |
| `update_data.example.sh` | orden seguro de sincronización, exportación, validación y push |
| `sensor-data-update.service` | trabajo `systemd` de una sola ejecución |
| `sensor-data-update.timer` | ejecución horaria al minuto 7 |

No instalar estas plantillas sin:

1. crear un clon exclusivo para el daemon;
2. implementar `export_monthly_csv.py` y `validate_export.py`;
3. probar manualmente el wrapper;
4. configurar una credencial limitada al repositorio de datos;
5. reemplazar todas las rutas y usuarios de ejemplo;
6. elegir entre `systemd` y cron, nunca ambos.
