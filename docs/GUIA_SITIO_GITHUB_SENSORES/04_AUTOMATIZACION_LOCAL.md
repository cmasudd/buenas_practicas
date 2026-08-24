# Automatización local

## Recomendación

Ejecutar el publicador en el equipo donde vive MariaDB mediante un temporizador
`systemd`. El proceso usa un clon exclusivo del repositorio de datos y una
credencial Git limitada a ese repositorio.

`systemd` facilita consultar estado, duración, salida y último resultado. Cron es
una alternativa correcta cuando ya existe una operación estable, siempre que se
use `flock` y un log local.

## Clon exclusivo

No usar el mismo directorio que una persona abre en Visual Studio Code. El clon
del daemon debe contener solamente cambios automáticos y tener permisos de
escritura restringidos al usuario del servicio.

Antes de cada exportación, la invocación del wrapper debe:

1. adquirir un lock no bloqueante;
2. comprobar que no hay cambios inesperados;
3. sincronizar la rama con `git pull --ff-only`;
4. ejecutar el exportador;
5. validar la salida completa;
6. crear un commit solo si `data/` cambió;
7. intentar el `push`, incluso si el commit pendiente viene de una ejecución
   anterior en que GitHub no respondió.

La plantilla [`plantillas/update_data.example.sh`](plantillas/update_data.example.sh)
implementa este orden sin almacenar secretos.

## Credencial de GitHub

Para un solo repositorio de datos, se puede usar una deploy key SSH con permiso
de escritura. La clave privada permanece en el servidor y la clave pública se
registra exclusivamente en ese repositorio.

Riesgos y controles:

- una deploy key de escritura permite modificar ese repositorio;
- normalmente no tiene fecha de expiración;
- debe tener permisos de archivo restrictivos;
- debe revocarse si el servidor se compromete o deja de publicar;
- una GitHub App es preferible cuando se administran muchos repositorios o se
  requiere expiración y permisos más finos.

No usar una credencial personal con acceso amplio como dependencia permanente
del daemon. Nunca guardar claves, tokens ni contraseñas en Git, el archivo de
servicio, la línea de cron o los logs.

## Temporizador `systemd`

Las plantillas incluidas ejecutan el trabajo al minuto 7 de cada hora, con un
pequeño retraso aleatorio. Se debe reemplazar cada marcador en mayúsculas y
revisar las rutas antes de instalar.

Archivos:

- [`plantillas/sensor-data-update.service`](plantillas/sensor-data-update.service)
- [`plantillas/sensor-data-update.timer`](plantillas/sensor-data-update.timer)

Instalar una unidad de sistema requiere autoridad administrativa. Después de
instalar, la verificación conceptual es:

```bash
systemctl status sensor-data-update.timer
systemctl list-timers sensor-data-update.timer
journalctl -u sensor-data-update.service --since today
```

No activar a la vez el temporizador y cron.

## Alternativa cron

Ejemplo genérico:

```cron
7 * * * * /usr/bin/flock -n /tmp/PROYECTO-sensor-data.lock /RUTA/REPO/scripts/update_data.sh >> /RUTA/LOGS/data-update.log 2>&1
```

El minuto 7 evita el cambio exacto de hora. GitHub advierte que los trabajos
programados alojados en su plataforma pueden retrasarse en momentos de alta
carga, especialmente al comienzo de la hora; aunque este cron es local, el
desfase también distribuye mejor las tareas del servidor.

## Cierre del mes anterior

Agregar una segunda tarea diaria durante los tres primeros días es posible,
pero debe llamar al mismo wrapper y compartir el mismo lock. El exportador puede
recibir el mes anterior como argumento calculado por una función interna segura.
No poner sustituciones complejas de fecha ni credenciales directamente en cron.

Una alternativa más simple es que el exportador horario detecte `day <= 3` y, en
una hora fija de madrugada, agregue el mes anterior a la lista. Esta decisión
debe quedar cubierta por pruebas de diciembre/enero y cambios de año.

## GitHub Pages

Una publicación por hora está muy por debajo del límite blando de diez builds
por hora de GitHub Pages. Para sitios estáticos simples se puede publicar desde
rama. Un workflow personalizado solo es necesario si hay un proceso de build o
si se deben combinar artefactos.

## Comprobación de extremo a extremo

La primera activación debe demostrar:

1. el servicio terminó en estado correcto;
2. el log no contiene secretos;
3. se creó el commit con la identidad esperada;
4. el commit llegó a la rama remota;
5. GitHub Pages terminó su despliegue;
6. `manifest.json` público tiene la medición esperada;
7. un CSV público coincide byte por byte con el local;
8. la web grafica y descarga ese período.
