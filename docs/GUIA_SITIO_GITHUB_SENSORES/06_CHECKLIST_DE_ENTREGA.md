# Lista de entrega

Esta lista permite confirmar que otra persona puede operar el proyecto sin
depender de quien lo construyó.

## Datos y base

- [ ] Cada estación tiene ID interno, código, nombre, ubicación y variables.
- [ ] Los modelos e identificadores de variable fueron verificados en MariaDB.
- [ ] Las conversiones de unidades están documentadas y probadas.
- [ ] Los centinelas de lectura ausente se convierten en celdas vacías.
- [ ] `EXPLAIN` confirma un recorrido por índice adecuado.
- [ ] Las consultas usan rango de fechas, límite y paginación keyset.

## Exportación

- [ ] Existe configuración de estaciones sin credenciales.
- [ ] La escritura usa temporal y reemplazo atómico.
- [ ] El encabezado CSV y el manifiesto tienen versión documentada.
- [ ] El máximo es 40 MiB y se crean partes adicionales.
- [ ] El backfill se puede limitar por estación y mes.
- [ ] El trabajo normal regenera solo el período abierto.
- [ ] Hay pruebas automáticas de esquema, orden, fechas, partes y tamaño.

## Web

- [ ] Carga manifiesto y `latest.csv` al iniciar.
- [ ] Descarga meses solo bajo demanda.
- [ ] El nombre público aparece en pantalla y en la descarga.
- [ ] La descarga respeta estación, variable y período seleccionados.
- [ ] La lectura en vivo pide una sola fila cada diez minutos.
- [ ] Las estaciones se consultan en forma escalonada.
- [ ] Los gráficos funcionan después de varios cambios de pestaña sin recargar.
- [ ] Las librerías esenciales se sirven localmente.
- [ ] Aviso, contacto y atribuciones son visibles.
- [ ] Se probó en escritorio y móvil.

## GitHub y automatización

- [ ] La web y los datos están separados o se documentó por qué no.
- [ ] El daemon usa un clon exclusivo.
- [ ] Identidad del commit y cuenta que hace `push` fueron verificadas.
- [ ] La credencial solo alcanza el repositorio necesario.
- [ ] No hay secretos en Git, cron, unidades ni logs.
- [ ] Solo una agenda está activa: `systemd` o cron.
- [ ] Existe un lock no bloqueante.
- [ ] Una ejecución sin datos nuevos no crea commits vacíos.
- [ ] Un `push` fallido queda pendiente y es visible.
- [ ] El despliegue de Pages se comprobó desde la URL pública.

## Operación y traspaso

- [ ] Hay instrucciones para estado, logs, tamaños y antigüedad.
- [ ] Hay alertas o una revisión periódica asignada.
- [ ] Existe una política de cierre del mes anterior.
- [ ] Existe una estrategia antes de 700 MiB publicados.
- [ ] El respaldo previo y la reversión están documentados.
- [ ] Cada cambio registra commit, pruebas, hashes, respaldo y rollback.
- [ ] Otra persona ejecutó la guía sin ayuda y anotó las dudas encontradas.

## Evidencia final mínima

Guardar en la bitácora del proyecto:

```text
Fecha y responsable:
Repositorio web / rama / commit:
Repositorio datos / rama / commit:
URL web:
URL del manifiesto:
Pruebas ejecutadas y resultado:
SHA-256 de index.html:
SHA-256 de manifest.json:
SHA-256 de un CSV representativo:
Ruta del respaldo anterior:
Temporizador o cron instalado:
Última ejecución correcta:
Procedimiento de reversión:
```
