# Arquitectura y propuesta

## El problema que se quiere evitar

Una web no debe pedir el histórico completo a MariaDB cada vez que una persona
abre un gráfico o descarga datos. Ese diseño repite la misma consulta pesada por
cada visitante y permite que varias solicitudes simultáneas saturen el
servidor.

Los datos históricos cerrados cambian poco. Conviene producir una copia estática
una vez y servirla muchas veces desde GitHub Pages.

## Propuesta recomendada: web y datos separados

Crear dos repositorios públicos:

| Repositorio | Contenido | Quién escribe |
|---|---|---|
| `proyecto-sensores-web` | HTML, CSS, JavaScript, imágenes y textos | personas responsables de la web |
| `proyecto-sensores-datos` | `manifest.json`, `latest.csv` y CSV históricos | daemon local del servidor |

Ambos pueden publicarse con GitHub Pages. Si pertenecen a la misma cuenta,
quedan bajo rutas del mismo dominio, por ejemplo:

```text
https://ORGANIZACION.github.io/proyecto-sensores-web/
https://ORGANIZACION.github.io/proyecto-sensores-datos/
```

La web recibe la URL base de datos mediante una constante de configuración y
consulta el manifiesto del segundo sitio.

### Ventajas

- La credencial del daemon solo tiene permiso sobre los datos.
- Un commit automático no puede incluir por accidente cambios manuales del HTML.
- Un fallo de publicación de datos no modifica el código de la web.
- El historial Git de archivos que cambian cada hora no hace crecer el clon de
  las personas que solo editan el sitio.
- Los datos se pueden rotar por año o trasladar sin rediseñar la interfaz.

### Costo

Hay que activar GitHub Pages en dos repositorios y configurar correctamente la
URL base de datos. Es una tarea inicial pequeña a cambio de una separación
operativa clara.

## Variante simple: un solo repositorio

Para una red pequeña se puede guardar la web y `data/` en el mismo repositorio.
Es el patrón probado inicialmente en Aire Aconcagua.

En ese caso el daemon debe usar un clon exclusivo, agregar solamente `data/` y
tener una identidad Git propia. No se debe ejecutar la automatización en el
mismo worktree donde una persona mantiene cambios sin commit.

## Flujo de datos

1. El exportador se conecta al MariaDB local.
2. Descubre los sensores físicos asociados a cada dispositivo configurado.
3. Consulta una estación, sensor y mes a la vez mediante paginación keyset.
4. Convierte las mediciones a un CSV ancho y cronológico.
5. Escribe primero un `.tmp`, ejecuta `fsync` y reemplaza el archivo visible.
6. Valida encabezados, fechas, orden, manifiesto y tamaños.
7. Crea un commit solamente si cambiaron los datos.
8. Hace `push` y GitHub Pages publica los archivos estáticos.
9. El navegador solicita solo los meses que intersectan el período elegido.

## Política temporal propuesta

### Cada hora

- Regenerar el mes vigente.
- Actualizar `latest.csv` y `manifest.json`.
- No tocar meses cerrados.

### Cierre de mes

Durante los primeros tres días de un mes, ejecutar una vez al día una
reconstrucción adicional del mes anterior. Esto incorpora mediciones tardías
sin volver a recorrer todo el historial cada hora.

### Corrección histórica

Ejecutar un backfill manual por estación y mes. Antes de hacerlo se debe estimar
la cantidad de filas, revisar `EXPLAIN`, adquirir el lock y vigilar recursos.

## Escalamiento propuesto

La partición mensual es la primera opción. Si un mes se acerca a 40 MiB, el
exportador crea `part-002` y el manifiesto enumera ambas partes.

Si los commits horarios hacen crecer demasiado el historial Git, se recomienda
pasar el mes abierto a partes diarias inmutables: solo el archivo del día actual
cambia cada hora; los días anteriores dejan de reescribirse. La web ya debe
leer una lista de archivos por período, por lo que este cambio no altera su
interfaz.

Si el tamaño publicado alcanza 700 MiB, hay que planificar antes de continuar:

- mantener en Pages una ventana reciente;
- crear repositorios de datos por año; o
- migrar los históricos a almacenamiento de objetos y conservar el mismo
  contrato de manifiesto.

No se debe esperar a llegar al límite del proveedor para tomar esta decisión.

## Por qué no usar GitHub Actions para consultar MariaDB

Un runner alojado en GitHub tendría que entrar al servidor por Internet o llamar
a la API pública. Eso amplía la superficie de seguridad y vuelve a cargar la red
y el API. La exportación debe ocurrir junto a MariaDB; GitHub Actions solo es
apropiado para validar o desplegar los archivos que ya fueron publicados.
