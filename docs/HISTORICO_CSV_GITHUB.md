# Publicación de históricos en CSV sin saturar MariaDB

Esta guía documenta la solución aplicada al proyecto público
[`cmasudd/aireaconcagua`](https://github.com/cmasudd/aireaconcagua) para evitar
que las descargas históricas pesadas lleguen directamente al servidor de
sensores.

La solución separa dos necesidades con perfiles de carga diferentes:

- **Última lectura:** consulta pequeña a la API, actualizada cada 10 minutos.
- **Histórico y descargas:** archivos CSV estáticos publicados en GitHub Pages
  y actualizados cada hora desde el mismo equipo que ejecuta MariaDB.

## Problema original

La versión antigua del sitio pedía miles o decenas de miles de registros al
endpoint legacy desde cada navegador. Una selección como “todo el histórico”
podía provocar simultáneamente:

1. un `JOIN` amplio entre dispositivos, sensores, variables y datos;
2. ordenamiento de una cantidad grande de filas;
3. transferencia y serialización de respuestas JSON grandes;
4. varias solicitudes concurrentes si había más de un visitante;
5. repetición del mismo trabajo para datos históricos que ya no cambian.

Ese patrón hacía que el costo de una descarga dependiera de la cantidad de
usuarios. Además, el navegador podía abandonar la conexión mientras MariaDB
seguía trabajando.

## Arquitectura aplicada

```text
                         cada 10 minutos
Navegador ──────────────────────────────────> API legacy
           solo la última fila, limite=1       por estación

Navegador ──────────────────────────────────> GitHub Pages
           manifest.json, latest.csv y         archivos estáticos
           CSV mensuales bajo demanda

MariaDB local ──> export_monthly_csv.py ──> Git ──> GitHub Pages
                  una vez por hora
```

La consecuencia principal es que una descarga histórica ya no abre una
consulta en MariaDB. Diez, cien o más visitantes descargan la misma copia
estática desde GitHub Pages.

## Exportación local segura

El exportador se ejecuta en el mismo servidor que MariaDB. No llama a la API
pública para construir los archivos.

### Consultas acotadas

Cada trabajo se divide por:

- dispositivo;
- sensor físico;
- mes calendario;
- lote de 5.000 mediciones.

Las consultas incluyen siempre:

```sql
WHERE id_sensor = ?
  AND fecha >= ?
  AND fecha < ?
ORDER BY fecha, id_dato
LIMIT 5000
```

El recorrido usa el índice comprobado en producción:

```text
datos (id_sensor, fecha)
```

Para esta instalación se usa `FORCE INDEX (idx_datos_sensor_fecha)` porque se
comprobó que el optimizador podía elegir `id_variable` y ordenar millones de
filas al buscar el último valor. No se debe copiar `FORCE INDEX` a otra base sin
confirmar antes el nombre, orden y selectividad de sus índices con `EXPLAIN`.

### Variables publicadas

Solo se exportan las variables utilizadas por el sitio:

| Columna CSV | Sensor de origen | Unidad publicada |
|---|---|---|
| `mp25_ugm3` | PMS5003 | µg/m³ |
| `mp10_ugm3` | PMS5003 | µg/m³ |
| `so2_ppb` | Sensor electroquímico SO₂ | ppb |
| `cov_ppb` | ENS160 | ppb |
| `temperatura_c` | SHT40 | °C |
| `humedad_pct` | SHT40 | % |

SO₂ se almacena en ppm y se multiplica por 1.000 al exportar. El centinela `-1`
usado por equipos sin lectura se publica como celda vacía, por lo que no
aparece en gráficos ni estadísticas.

### CSV cronológico ancho

Cada fila representa una fecha y hora:

```csv
fecha,mp25_ugm3,mp10_ugm3,so2_ppb,cov_ppb,temperatura_c,humedad_pct
2026-04-22 15:34:24,40,49,0,0,21.801,49.188
```

Este formato redujo el conjunto inicial de aproximadamente 62 MiB en formato
largo a 11 MiB. En la validación inicial se publicaron 251.611 fechas únicas,
sin fechas duplicadas ni filas con una cantidad incorrecta de columnas.

### Escritura atómica

El mes se escribe primero en un archivo temporal:

```text
2026-07-part-001.csv.tmp
```

Después de escribir, vaciar buffers y ejecutar `fsync`, se reemplaza el CSV
visible con `os.replace`. Si el proceso falla a mitad de camino, GitHub conserva
la última versión completa.

### Límite preventivo

El límite configurado es 40 MiB por CSV. Al alcanzarlo, el exportador continúa
en:

```text
2026-07-part-002.csv
```

El manifiesto enumera todas las partes. El límite preventivo es muy inferior al
límite duro de GitHub y evita descubrir el problema recién durante el `push`.

## Actualización horaria

La tarea instalada en el servidor es:

```cron
7 * * * * /usr/bin/flock -n /tmp/aireaconcagua-update.lock /home/cmas/Documentos/aireaconcagua/scripts/update_data.sh >> /home/cmas/Documentos/aireaconcagua/data-update.log 2>&1
```

Decisiones:

- se ejecuta al minuto 7 para evitar concentrar trabajo al cambio de hora;
- `flock -n` impide que dos exportaciones se solapen;
- normalmente se regenera solo el mes vigente;
- los meses cerrados se vuelven a construir únicamente con un backfill manual;
- se hace commit y `push` solo si `data/` cambió;
- las credenciales se leen desde el entorno local y nunca se escriben en el
  repositorio ni en los logs.

El backfill completo se ejecuta manualmente:

```bash
cd /home/cmas/Documentos/aireaconcagua
/var/www/api_sensores/venv/bin/python scripts/export_monthly_csv.py --all
```

## Última lectura en vivo

El mapa y las tarjetas conservan una lectura reciente sin cargar históricos
desde la API:

```http
GET /listarDatosEstructuradosV2
    ?tabla=datos
    &disp.id_proyecto=18
    &disp.codigo_interno=HIRIPRO-V6
    &order_by=fecha_insercion
    &limite=1
```

Controles aplicados:

- refresco cada 10 minutos;
- `limite=1`;
- se usa únicamente la primera fila aunque el endpoint legacy entregue una
  fila extra;
- una solicitud por estación;
- las estaciones se escalonan 350 ms para no llegar simultáneamente;
- no hay reintentos infinitos: un error conserva el último CSV y espera el
  siguiente ciclo;
- las lecturas nuevas se incorporan a la ventana de 24 horas cargada desde CSV.

Esta consulta pequeña no sustituye la protección de V2 descrita en
`INTEGRACION.md`. El cortacircuito para consultas legacy históricas debe
permanecer activo.

## Carga bajo demanda en el navegador

Al abrir la página se descargan solamente:

- `data/manifest.json`;
- `data/latest.csv`.

Los archivos mensuales se solicitan cuando el usuario selecciona una estación o
un periodo. Por ejemplo:

- últimas 24 horas: mes actual y, si corresponde, el mes anterior;
- últimos 7 días: solo los meses que intersectan esa ventana;
- último mes: uno o dos archivos;
- total: todos los meses de la estación seleccionada.

El botón del modo escolar genera una descarga con la estación, variable y
periodo seleccionados. No vuelve a consultar MariaDB.

## Monitoreo operativo

### Confirmar que cron está activo

```bash
systemctl is-active cron
systemctl is-enabled cron
crontab -l | grep update_data.sh
```

### Revisar la última ejecución

```bash
tail -n 40 /home/cmas/Documentos/aireaconcagua/data-update.log
```

Una ejecución con cambios debe terminar con mensajes similares a:

```text
Exportación terminada
datos: actualización horaria
main -> main
```

### Revisar commits automáticos

```bash
cd /home/cmas/Documentos/aireaconcagua
git log -5 --format='%h | %ad | %s' --date=iso-local
```

Si no ingresaron mediciones nuevas, puede no existir un commit nuevo. El log
local sigue siendo la evidencia de que cron ejecutó el trabajo.

### Revisar la antigüedad del manifiesto

```bash
sed -n '1,8p' data/manifest.json
```

El campo `updated_at` representa la fecha de la medición más reciente incluida,
no simplemente la hora en que se ejecutó el script.

### Revisar tamaños

```bash
du -sh data
find data -type f -name '*.csv' -size +40M -print
```

El segundo comando no debe imprimir archivos.

## Comportamiento ante fallos

| Falla | Resultado |
|---|---|
| MariaDB no responde | No se reemplazan CSV completos ni se hace `push` |
| Se corta el exportador | El archivo temporal no sustituye la última copia |
| Un trabajo tarda más de una hora | `flock` rechaza el siguiente |
| GitHub no responde | El commit queda local para el siguiente diagnóstico |
| API en vivo falla | La web conserva el último CSV disponible |
| Un CSV llega a 40 MiB | Se crea otra parte y se actualiza el manifiesto |

## Lista de verificación antes de reutilizar el patrón

1. Confirmar con `EXPLAIN` que existe y se utiliza `(id_sensor, fecha)`.
2. Seleccionar únicamente las variables necesarias.
3. Dividir el histórico por dispositivo y mes.
4. Usar lotes con límite explícito.
5. Escribir archivos temporales y reemplazarlos atómicamente.
6. Definir un límite de archivo inferior al del proveedor Git.
7. Evitar que el navegador consulte históricos en MariaDB.
8. Mantener la lectura en vivo pequeña, espaciada y sin reintentos infinitos.
9. Usar `flock` en toda automatización periódica.
10. Monitorear log, antigüedad del manifiesto, tamaño y último `push`.

## Qué no hacer

- No usar `limite=100000` desde el navegador.
- No pedir todo el histórico al endpoint legacy.
- No usar `OFFSET` para recorrer tablas grandes.
- No ejecutar exportaciones simultáneas por cada usuario.
- No regenerar todos los años cada hora.
- No guardar contraseñas en scripts, cron, repositorios o logs.
- No asumir que el límite anunciado por GitHub es un objetivo de tamaño:
  siempre debe existir un margen preventivo.

