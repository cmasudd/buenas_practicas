# Operación, capacidad y recuperación

## Revisión diaria

- Temporizador activo y próxima ejecución programada.
- Último servicio terminado sin error.
- Antigüedad de `manifest.json` dentro del umbral esperado.
- Ningún `.tmp` antiguo.
- Ningún CSV sobre 40 MiB.
- Repositorio local sincronizado con el remoto.
- GitHub Pages desplegado correctamente.

No siempre debe existir un commit nuevo: si no ingresaron mediciones, una
ejecución correcta puede terminar sin cambios. El estado del servicio y el log
son la evidencia primaria.

## Alertas propuestas

El daemon debe terminar con código distinto de cero ante cualquier fallo. Un
monitor separado puede revisar cada 15 minutos:

- último resultado de `systemd`;
- edad de `updated_at`;
- divergencia entre rama local y remota;
- tamaño total publicado;
- archivos sobre el límite;
- último despliegue de Pages.

Umbrales iniciales:

| Indicador | Advertencia | Crítico |
|---|---:|---:|
| Edad de la medición más reciente | 2 horas | 6 horas |
| Tamaño de un CSV | 35 MiB | 40 MiB |
| Tamaño publicado | 700 MiB | 850 MiB |
| Ejecuciones consecutivas fallidas | 1 | 3 |

La edad de la medición debe interpretarse con el comportamiento real de los
sensores: una estación apagada no significa necesariamente que el daemon falló.
Por eso también se registra la hora de ejecución exitosa por separado.

## Capacidad de GitHub

No confundir límites distintos:

- GitHub bloquea archivos Git individuales mayores de 100 MiB y advierte sobre
  archivos mayores de 50 MiB.
- GitHub recomienda repositorios idealmente menores de 1 GB.
- GitHub Pages recomienda una fuente menor de 1 GB y el sitio publicado no puede
  superar 1 GB.
- El límite de 2 GB corresponde al tamaño de una operación `push`, no a una meta
  segura para el repositorio o el sitio.

Por estas razones el proyecto usa 40 MiB como límite preventivo y empieza a
planificar migración al llegar a 700 MiB publicados.

## Medir crecimiento real

Registrar cada mes:

```bash
du -sh data .git
git count-objects -vH
find data -type f -name '*.csv' -size +40M -print
```

El tamaño de `data/` mide la instantánea publicada; `.git` mide también todas
las versiones horarias. Un conjunto actual pequeño puede tener un historial Git
grande si el mismo CSV mensual se reescribe 24 veces al día.

Si `.git` crece mucho más rápido que `data/`, aplicar primero partes diarias
inmutables. No ejecutar limpiezas destructivas del historial sin respaldo,
ventana de mantenimiento y plan de reclonado de todos los consumidores.

## Fallos esperados

| Falla | Comportamiento seguro |
|---|---|
| MariaDB no responde | no reemplazar CSV ni publicar |
| Exportador interrumpido | conservar archivo anterior y dejar `.tmp` aislado |
| Trabajo anterior activo | `flock` rechaza la nueva ejecución |
| Validación falla | no crear commit |
| GitHub no responde | conservar commit local y reintentar el `push` después |
| Rama remota diverge | detenerse; una persona resuelve, sin merge automático |
| API en vivo falla | mostrar `latest.csv` y marcar su antigüedad |
| CSV llega al límite | abrir otra parte y actualizar manifiesto |

## Respaldo antes de cambios

Antes de modificar exportador, contrato o automatización guardar fuera de Git:

- commit y rama actuales;
- copia de scripts y unidades instaladas;
- `manifest.json` y una muestra de CSV;
- salida de pruebas;
- hashes SHA-256 de los artefactos publicados;
- estado del temporizador;
- ruta del respaldo y propietario.

No copiar `.env` a un repositorio. Si el respaldo contiene configuración
protegida, debe permanecer en una ubicación privada con permisos restrictivos.

## Reversión

1. Desactivar temporalmente el temporizador o adquirir el mismo lock.
2. Identificar el último commit correcto y el artefacto respaldado.
3. Revertir mediante un commit nuevo; no reescribir la rama publicada.
4. Ejecutar validaciones y comparar hashes.
5. Publicar y esperar el despliegue de Pages.
6. Verificar manifiesto, CSV, gráficos y descarga desde la URL pública.
7. Reactivar el temporizador y observar una ejecución completa.

Cada cambio de producción debe registrar referencia Git, pruebas, hashes,
respaldo anterior y este procedimiento adaptado al cambio concreto.

## Fuentes oficiales de GitHub

- [Archivos grandes y tamaño recomendado del repositorio](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)
- [Límites operativos del repositorio y del `push`](https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits)
- [Límites de GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
- [Creación de un sitio de GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site)
- [Administración de deploy keys](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/managing-deploy-keys)
