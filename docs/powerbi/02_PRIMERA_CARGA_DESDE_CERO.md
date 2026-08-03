# 2. Primera carga desde cero

## Requisitos

- Un computador con Windows.
- Power BI Desktop instalado.
- Acceso a `https://api-sensores.cmasccp.cl`.
- Una clave Power BI entregada por quien administra la API.
- Los archivos de `examples/powerbi/` de este repositorio.

## Paso 1: abrir Power Query

1. Abrir Power BI Desktop.
2. Crear un informe en blanco.
3. Seleccionar **Inicio → Transformar datos**.
4. En Power Query elegir **Inicio → Nueva fuente → Consulta en blanco**.

## Paso 2: crear el parámetro de la clave

1. Seleccionar **Inicio → Administrar parámetros → Nuevo parámetro**.
2. Usar el nombre `PowerBIKey`.
3. Elegir tipo **Texto**.
4. En **Valor actual**, pegar la clave recibida por un canal privado.
5. No escribir la clave directamente en una consulta ni en un archivo que se
   subirá a GitHub.

## Paso 3: crear la función de descarga por proyecto

1. En el panel izquierdo cambiar el nombre de la consulta a:

```text
fnCargarProyectoPowerBIV3
```

2. Seleccionar **Inicio → Editor avanzado**.
3. Borrar el contenido existente.
4. Copiar todo el archivo `examples/powerbi/fnCargarProyectoPowerBIV3.m`.
5. Presionar **Listo**.
6. Hacer clic derecho sobre la función y desactivar **Habilitar carga**.

## Paso 4: probar el proyecto 13

1. Crear otra **Consulta en blanco**.
2. Abrir su **Editor avanzado**.
3. Pegar:

```powerquery
let
    Datos = fnCargarProyectoPowerBIV3(
        13,
        #date(2025, 1, 1),
        Date.From(DateTime.LocalNow()),
        PowerBIKey
    )
in
    Datos
```

4. Cambiar el nombre de la consulta a `Proyecto_13_Agua`.
5. Si Power BI solicita credenciales, elegir **Anónimo**.
6. Elegir nivel de privacidad **Organizacional**.

La autenticación propia de la ruta viaja en `X-API-Key`; por eso el diálogo de
Power BI para el dominio se deja en **Anónimo**.

## Paso 5: comprobar el resultado

Verificar que existan estas columnas base:

```text
fecha
fecha_insercion
id_proyecto
codigo_interno
dispositivo_descripcion
```

Las mediciones aparecen en columnas cuyos nombres incluyen modelo, variable y
unidad. Es el formato ancho utilizado por la web y por las consultas V2.

## Paso 6: cargar los datos

1. Seleccionar **Inicio → Cerrar y aplicar**.
2. Esperar a que termine la carga.
3. Guardar el archivo como `.pbix`.

No cerrar Power BI mientras indique que está evaluando o cargando la consulta.

## Alternativa normalizada por dispositivo

Para un modelo nuevo que prefiera una fila por medición, usar
`fnCargarDispositivoV3.m`. Esa función no utiliza la clave de proyecto y sirve
también para comprobar una estación aislada.
