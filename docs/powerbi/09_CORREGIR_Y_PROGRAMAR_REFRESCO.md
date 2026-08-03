# 9. Corregir la función y programar el refresco

Esta guía sirve cuando el proyecto 13 descarga 14.196 filas y después Power BI
muestra un error al convertir `Sin sesión` a número.

## Reemplazar la función en Power BI Desktop

No es necesario crear nuevamente el informe ni cambiar la API.

1. Abrir el archivo `.pbix` que presenta el error.
2. Seleccionar **Inicio → Transformar datos**.
3. En el panel izquierdo seleccionar `fnCargarProyectoPowerBIV3`.
4. Seleccionar **Inicio → Editor avanzado**.
5. Borrar todo el código anterior.
6. Copiar el contenido completo de
   [`fnCargarProyectoPowerBIV3.m`](../../examples/powerbi/fnCargarProyectoPowerBIV3.m).
7. Pegar el código y seleccionar **Listo**.
8. Seleccionar **Actualizar vista previa**.
9. Confirmar que `id_sesion` tenga tipo **Texto** y pueda contener
   `Sin sesión`.
10. Seleccionar **Cerrar y aplicar** y esperar a que termine.
11. Guardar una copia nueva del `.pbix` antes de reemplazar el informe
    publicado.

La descarga comprobada del proyecto 13 contiene 14.196 filas en 15 páginas,
sin duplicados. La función corregida deja `id_sesion` como texto.

## Probar antes de programar

1. En Power BI Desktop seleccionar **Actualizar**.
2. Confirmar que la actualización termine sin errores.
3. Revisar las fechas máxima y mínima y comparar una visualización con V2.
4. Seleccionar **Inicio → Publicar** y elegir el workspace institucional.

## Configurar Power BI Service

1. Entrar a `https://app.powerbi.com`.
2. Abrir el workspace donde se publicó el informe.
3. Buscar su **modelo semántico** y abrir **Configuración**.
4. En **Parámetros**, comprobar que `PowerBIKey` tenga la clave entregada por
   el administrador. Si existen parámetros de proyecto o fechas, revisarlos
   también.
5. En **Credenciales del origen de datos**, editar
   `https://api-sensores.cmasccp.cl`.
6. Elegir autenticación **Anónima** y privacidad **Organizacional**. La ruta no
   queda pública: la función envía la clave en el encabezado `X-API-Key`.
7. No instalar un gateway para este único origen web, salvo que Power BI
   identifique además otro origen local dentro del mismo modelo.
8. Seleccionar **Actualizar ahora**.
9. Abrir **Historial de actualización** y confirmar que el resultado sea
   correcto antes de crear un horario.

## Activar el horario automático

1. En la configuración del modelo semántico abrir **Actualizar**.
2. Activar **Configurar una programación de actualización**.
3. Elegir zona horaria `America/Santiago`.
4. Programar inicialmente una actualización diaria fuera del horario de mayor
   uso del servidor.
5. Activar las notificaciones de error para el propietario del modelo.
6. Guardar la configuración.
7. Al día siguiente, revisar nuevamente **Historial de actualización**.

No compartir el `.pbix` con personas no autorizadas: quien pueda editar el
modelo podría inspeccionar el parámetro `PowerBIKey`.

## Si falla en la nube

- **Origen dinámico:** confirmar que la función conserve `ApiBase` fijo y use
  `RelativePath` y `Query` dentro de `Web.Contents`.
- **Credenciales:** volver a editar el origen y seleccionar **Anónimo**.
- **Error 401:** revisar `PowerBIKey` sin incluir espacios al principio o final.
- **Error 429:** esperar y evitar dos actualizaciones simultáneas.
- **Cuatro fallos consecutivos:** corregir el problema y volver a habilitar el
  horario, porque Power BI puede desactivarlo automáticamente.

Para históricos que crezcan hasta millones de filas, seguir la sección de
actualización incremental de [Publicar y actualizar](05_PUBLICAR_Y_ACTUALIZAR.md).
