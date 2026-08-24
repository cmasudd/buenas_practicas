# Guía para publicar una web de sensores con GitHub Pages

Esta carpeta permite que otra persona reproduzca el patrón usado por Aire
Aconcagua: una web pública muestra y descarga históricos desde archivos CSV de
GitHub Pages, mientras el servidor de sensores conserva solamente una consulta
pequeña para la lectura reciente.

La guía no contiene credenciales ni depende de los identificadores de una
instalación concreta. Antes de usarla hay que adaptar la lista de estaciones, el
modelo de MariaDB, las variables y los textos del proyecto.

## Resultado esperado

```text
MariaDB local
     |
     | exportación acotada cada hora
     v
repositorio de datos -----> GitHub Pages de datos
                                  |
                                  | CSV y manifest.json
                                  v
repositorio de la web ----> GitHub Pages del proyecto ----> visitantes
                                  |
                                  +---- API: solo última lectura
```

La separación en dos repositorios es la opción recomendada para proyectos
nuevos. La variante de un repositorio, como la implementación inicial de Aire
Aconcagua, sigue siendo válida para un portal pequeño.

## Orden de lectura

1. [Arquitectura y propuesta](01_ARQUITECTURA_Y_PROPUESTA.md)
2. [Creación del proyecto](02_CREAR_EL_PROYECTO.md)
3. [Contrato de datos y comportamiento de la web](03_CONTRATO_DE_DATOS_Y_WEB.md)
4. [Automatización local](04_AUTOMATIZACION_LOCAL.md)
5. [Operación, capacidad y recuperación](05_OPERACION_Y_RECUPERACION.md)
6. [Lista de entrega](06_CHECKLIST_DE_ENTREGA.md)
7. [Implementación en el servidor CMAS](07_IMPLEMENTACION_EN_SERVIDOR_CMAS.md)

Las plantillas copiables están en [`plantillas/`](plantillas/README.md).

## Implementación de referencia

La experiencia comprobada está documentada en:

- [`../HISTORICO_CSV_GITHUB.md`](../HISTORICO_CSV_GITHUB.md): consultas,
  partición mensual, archivos atómicos y monitoreo.
- [`../../cambios/2026-08-24-aireaconcagua-v1-fotos-graficos.md`](../../cambios/2026-08-24-aireaconcagua-v1-fotos-graficos.md): cambio aplicado,
  pruebas, hashes, respaldo y reversión.
- `cmasudd/aireaconcagua`: ejemplo funcional de la web, el exportador y el
  manifiesto. Se debe reutilizar como referencia, no copiar identificadores de
  sensores sin verificarlos.

## Decisión resumida

- Históricos: CSV estáticos, no API.
- Frecuencia: una vez por hora, en un minuto distinto de `00`.
- Trabajo horario: mes vigente; el mes anterior solo durante su cierre.
- Backfill: manual y supervisado.
- Exclusión: `flock` o una unidad `systemd` que no permita solapamientos.
- Publicación: solo cuando los archivos cambian y después de validarlos.
- Autenticación Git: credencial exclusiva para el repositorio de datos.
- Lectura en vivo: una fila por estación cada diez minutos, escalonada.
- Límite preventivo: 40 MiB por CSV.
- Alerta de capacidad: antes de que el sitio publicado llegue a 700 MiB.
