# Implementación en el servidor CMAS

Este documento describe la parte que se ejecuta en el servidor. No reemplaza la
guía general: aplica sus controles a este equipo y separa el estado actual de
los pasos requeridos para un proyecto nuevo.

No contiene contraseñas, tokens, claves privadas ni valores del entorno.

## Estado comprobado el 24 de agosto de 2026

En este servidor ya existen:

| Elemento | Estado o ubicación |
|---|---|
| MariaDB | servicio activo en el mismo equipo |
| Cron | servicio activo |
| API y entorno protegido | `/var/www/api_sensores` |
| Python actualmente utilizado | `/var/www/api_sensores/venv/bin/python` |
| Repositorio Aire Aconcagua | `/home/cmas/Documentos/aireaconcagua` |
| Exportador | `scripts/export_monthly_csv.py` |
| Publicador | `scripts/update_data.sh` |
| Configuración de estaciones | `config/stations.json` |
| Log local | `data-update.log`, ignorado por Git |
| Lock | `/tmp/aireaconcagua-update.lock` |
| Frecuencia | minuto 7 de cada hora |

Las últimas ejecuciones revisadas terminaron la exportación, crearon un commit
de datos y lo publicaron en GitHub. Esto demuestra que el circuito actual está
operativo.

El proyecto vigente usa web y datos en el mismo repositorio. No se debe migrar
ni reemplazar esa tarea durante la creación de la documentación. Para un proyecto
nuevo se recomienda la separación descrita a continuación.

## Lo que hay que crear en este servidor

```text
/home/cmas/servicios/NOMBRE-datos/        clon exclusivo del daemon
/home/cmas/servicios/venvs/NOMBRE/        entorno Python exclusivo
/home/cmas/servicios/config/NOMBRE.env    configuración protegida, fuera de Git
/home/cmas/backups/NOMBRE-FECHA/          respaldo previo a cambios
/etc/systemd/system/                      unidades instaladas por administrador
```

Las rutas son una propuesta. Antes de crearlas se debe verificar que no existe
otro servicio con el mismo nombre y definir propietario, grupo y responsable.

## Paso 1: crear repositorios y responsables

Crear en la cuenta institucional:

- `NOMBRE-sensores-web`, mantenido por las personas que editan la web;
- `NOMBRE-sensores-datos`, escrito por el publicador del servidor.

Registrar:

- propietario de ambos repositorios;
- persona responsable de revisar fallos;
- rama publicada;
- URL de GitHub Pages de la web y de los datos;
- correo institucional para alertas y contacto público;
- política de conservación de históricos.

## Paso 2: preparar un clon exclusivo

El clon automático no debe ser el que una persona abre en Visual Studio Code.
Debe pertenecer al usuario de servicio, normalmente `cmas`, y no contener
cambios manuales.

Procedimiento conceptual:

```bash
mkdir -p /home/cmas/servicios
git clone URL_REPOSITORIO_DATOS /home/cmas/servicios/NOMBRE-datos
cd /home/cmas/servicios/NOMBRE-datos
git config user.name "PUBLICADOR INSTITUCIONAL"
git config user.email "CORREO_NOREPLY_VERIFICADO"
```

Antes de continuar, comprobar por separado:

```bash
git config user.name
git config user.email
git remote -v
git status --short --branch
```

Esto evita que los commits aparezcan atribuidos a una cuenta personal
equivocada. La identidad del commit no sustituye a la credencial del `push`.

## Paso 3: entorno Python independiente

El exportador actual puede utilizar el entorno del API, pero para un proyecto
nuevo conviene no acoplar el daemon al ciclo de actualizaciones de Flask.

Crear un entorno exclusivo e instalar dependencias fijadas en un archivo de
requisitos. Como mínimo, el exportador actual necesita el conector de MariaDB o
MySQL usado por el proyecto.

```bash
python3 -m venv /home/cmas/servicios/venvs/NOMBRE
/home/cmas/servicios/venvs/NOMBRE/bin/pip install -r requirements-export.txt
```

Guardar las versiones exactas, ejecutar las pruebas con ese mismo Python y
actualizar dependencias solamente en una ventana controlada.

## Paso 4: acceso de solo lectura a MariaDB

Crear una cuenta local exclusiva para el exportador. Debe poder ejecutar
`SELECT` solamente sobre las tablas necesarias, por ejemplo:

- dispositivos y su configuración;
- relación entre dispositivos y sensores;
- tipos o modelos de sensor;
- tabla de mediciones.

La contraseña se define de forma interactiva o mediante el mecanismo protegido
del administrador. Nunca se escribe en un comando visible, un commit o esta
documentación.

El archivo de entorno debe vivir fuera del repositorio, pertenecer al usuario
del servicio y ser legible solo por ese usuario:

```text
/home/cmas/servicios/config/NOMBRE.env
```

Permiso objetivo: `0600`. Antes de endurecer un archivo ya utilizado por otro
servicio se debe confirmar con qué usuario se ejecuta ese proceso. No cambiar
permisos del entorno productivo del API sin esta verificación.

El archivo contiene nombres como `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y
`DB_PASSWORD`; sus valores nunca se imprimen. La conexión debe usar el host local
cuando MariaDB está en este mismo equipo.

## Paso 5: verificar esquema e índices

Antes del backfill:

1. confirmar las tablas y columnas reales;
2. verificar el mapeo dispositivo–sensor–variable;
3. comprobar unidades y centinelas;
4. ejecutar `EXPLAIN` sobre una estación y un mes;
5. confirmar el uso de un índice equivalente a `(id_sensor, fecha)`;
6. medir tiempo y filas examinadas;
7. probar primero un mes pequeño.

El exportador de Aire Aconcagua usa un nombre de índice comprobado en esta base.
Otro proyecto no debe copiar `FORCE INDEX` sin repetir `EXPLAIN`.

## Paso 6: instalar exportador, validador y configuración

El repositorio de datos debe contener:

```text
config/stations.json
scripts/export_monthly_csv.py
scripts/validate_export.py
scripts/update_data.sh
tests/
requirements-export.txt
```

El exportador debe recibir la ruta del entorno protegido; no debe asumir que las
credenciales están dentro del repositorio. El validador se ejecuta antes de cada
commit y debe rechazar:

- encabezados incorrectos;
- fechas fuera del mes declarado;
- filas desordenadas o duplicadas;
- rutas ausentes en el manifiesto;
- archivos temporales antiguos;
- CSV mayores de 40 MiB;
- variables no autorizadas;
- manifiestos cuya versión no reconoce la web.

## Paso 7: backfill inicial supervisado

Adquirir el mismo lock que usará el daemon. Ejecutar primero una estación y un
mes, validar y comparar muestras con MariaDB. Después ampliar gradualmente.

Durante el backfill observar:

- CPU, memoria y E/S de disco;
- consultas activas y tiempo de respuesta de MariaDB;
- tamaño de `data/`;
- tamaño máximo de cada CSV;
- filas y fechas por estación;
- espacio disponible en el servidor.

El backfill completo es manual. No se agrega a la tarea horaria.

## Paso 8: credencial Git limitada

El daemon necesita escribir solo en `NOMBRE-sensores-datos`. Para un repositorio
se puede registrar una deploy key SSH exclusiva con permiso de escritura:

1. generar un par de claves exclusivo como el usuario del servicio;
2. proteger la clave privada;
3. agregar solamente la clave pública en `Settings > Deploy keys`;
4. habilitar escritura exclusivamente en el repositorio de datos;
5. configurar el remoto SSH y probar autenticación;
6. hacer un commit de prueba sin datos sensibles;
7. documentar responsable, fecha y procedimiento de revocación.

No reutilizar la clave personal de otra persona ni una clave con acceso a varios
repositorios. Si la organización crece, usar una GitHub App con permisos más
finos y credenciales de corta duración.

## Paso 9: instalar una sola agenda

La opción recomendada para el proyecto nuevo es `systemd`, usando las plantillas:

- [`plantillas/sensor-data-update.service`](plantillas/sensor-data-update.service)
- [`plantillas/sensor-data-update.timer`](plantillas/sensor-data-update.timer)

Antes de instalarlas:

1. reemplazar todos los marcadores;
2. confirmar `User`, `Group`, rutas y nombre del servicio MariaDB;
3. apuntar al clon y Python exclusivos;
4. mantener `Nice` e prioridad de E/S;
5. confirmar que `ExecStart` usa `flock -n`;
6. ejecutar manualmente el mismo comando;
7. instalar con autoridad administrativa;
8. activar y observar la primera ejecución.

Verificación:

```bash
systemctl status sensor-data-update.timer
systemctl list-timers sensor-data-update.timer
journalctl -u sensor-data-update.service --since today
```

Si se elige cron, usar la línea genérica documentada en
[`04_AUTOMATIZACION_LOCAL.md`](04_AUTOMATIZACION_LOCAL.md). No instalar cron y
`systemd` simultáneamente.

## Paso 10: cierre de mes

El trabajo horario regenera solo el mes vigente. Para datos tardíos, implementar
y probar en el exportador una opción de cierre que:

- durante los días 1, 2 y 3 reconstruya el mes anterior una vez al día;
- no ejecute un backfill completo;
- comparta el mismo lock del trabajo horario;
- funcione al cambiar de diciembre a enero;
- no cree commit cuando no hay cambios.

Esta función debe probarse antes de crear su temporizador. Hasta entonces, el
cierre del mes anterior queda como tarea manual registrada.

## Paso 11: seguimiento automático

Crear un chequeo separado que termine con error y genere alerta cuando ocurra
alguna de estas condiciones:

- última ejecución fallida;
- tres fallos consecutivos;
- commit local sin publicar;
- manifiesto remoto atrasado;
- archivo mayor de 40 MiB;
- datos publicados sobre 700 MiB;
- sitio de Pages sin el commit esperado.

El monitoreo no debe leer ni enviar el contenido del `.env`. Debe registrar
solamente horas, estados, tamaños, rutas públicas y referencias Git.

Revisión manual mínima:

```bash
systemctl status sensor-data-update.timer
journalctl -u sensor-data-update.service -n 50
git -C /home/cmas/servicios/NOMBRE-datos status --short --branch
git -C /home/cmas/servicios/NOMBRE-datos log -5 --oneline
find /home/cmas/servicios/NOMBRE-datos/data -type f -name '*.csv' -size +40M -print
du -sh /home/cmas/servicios/NOMBRE-datos/data
```

El primer comando no sustituye la revisión de la fecha de medición. Un daemon
puede ejecutarse correctamente aunque una estación haya dejado de enviar datos.

## Paso 12: comprobación completa

Antes de declarar el sistema operativo, guardar evidencia de:

1. pruebas del exportador y validador;
2. consumo de recursos del backfill y de una hora normal;
3. identidad del commit automático;
4. `push` al repositorio de datos;
5. despliegue correcto de GitHub Pages;
6. hash local y remoto de `manifest.json` y un CSV;
7. lectura de la web desde los CSV públicos;
8. descarga por estación, variable y período;
9. lectura en vivo limitada a una fila;
10. respuesta de la web cuando el API no está disponible.

## Respaldo y reversión del servidor

Antes de instalar o cambiar una agenda:

- respaldar scripts, unidades y configuración sin publicar secretos;
- registrar el crontab o temporizador anterior mediante una copia protegida;
- registrar commit, rama y remoto;
- calcular hashes de scripts y artefactos;
- anotar quién autorizó el cambio.

Para revertir:

1. detener o desactivar la agenda nueva;
2. adquirir el lock;
3. restaurar scripts y unidad desde el respaldo;
4. ejecutar pruebas manuales;
5. restaurar la agenda anterior;
6. observar una ejecución completa;
7. comprobar el sitio público;
8. documentar referencias, hashes y resultado.

No se revierte con `git reset --hard` sobre un worktree productivo.

## Migrar Aire Aconcagua en el futuro

La separación de repositorios es una mejora propuesta, no una acción pendiente
automática. Para migrar el sistema actual se necesita una ventana aprobada:

1. respaldar repositorio, scripts, cron y artefactos;
2. adquirir `/tmp/aireaconcagua-update.lock`;
3. crear y llenar el repositorio de datos sin retirar el actual;
4. publicar sus archivos con Pages;
5. cambiar la URL base de datos en una rama de la web;
6. probar escritorio, móvil, gráficos y descargas;
7. publicar la web;
8. reemplazar la agenda solo después de la verificación pública;
9. mantener el repositorio anterior durante la ventana de reversión.

Hasta que esa migración sea solicitada, el cron operativo actual debe permanecer
sin cambios.
