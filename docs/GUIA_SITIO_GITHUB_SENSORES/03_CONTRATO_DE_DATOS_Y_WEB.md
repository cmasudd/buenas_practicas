# Contrato de datos y comportamiento de la web

## Manifiesto

`manifest.json` es el contrato entre el publicador y la web. Debe incluir:

- versión del esquema;
- zona horaria;
- fecha de la medición más reciente publicada;
- límite configurado por archivo;
- estaciones y nombres públicos;
- variables disponibles;
- meses y lista ordenada de partes CSV.

Ejemplo abreviado:

```json
{
  "schema_version": 1,
  "updated_at": "2026-08-24T14:20:00-04:00",
  "timezone": "America/Santiago",
  "max_csv_bytes": 41943040,
  "stations": [
    {
      "code": "ESTACION-01",
      "name": "Escuela Ejemplo",
      "variables": ["mp25", "mp10", "temp", "hum"],
      "months": {
        "2026-08": [
          "data/ESTACION-01/2026-08-part-001.csv"
        ]
      }
    }
  ]
}
```

`updated_at` debe representar la medición más reciente incluida, no la hora en
que se inició el proceso.

## CSV histórico

Formato ancho recomendado:

```csv
fecha,mp25_ugm3,mp10_ugm3,so2_ppb,cov_ppb,temperatura_c,humedad_pct
2026-08-24 14:20:00,12,19,,,21.4,48.2
```

Reglas:

- UTF-8 y fin de línea LF;
- encabezado idéntico en todas las partes;
- fechas cronológicas y sin duplicados dentro de una estación;
- celdas vacías para lecturas ausentes;
- unidades escritas en el nombre de la columna;
- ningún valor centinela se grafica como medición real;
- archivo menor o igual al límite preventivo de 40 MiB.

El formato ancho reduce tamaño cuando varias variables comparten la misma fecha.
Si los sensores tienen frecuencias completamente distintas, se debe medir antes
si conviene un formato largo.

## Lectura reciente de respaldo

`latest.csv` permite mostrar algo útil aunque el API no responda:

```csv
codigo,fecha,variable,valor
ESTACION-01,2026-08-24 14:20:00,mp25,12
```

La web puede reemplazar esos valores con una lectura en vivo, pero no debe
perderlos cuando una solicitud falla.

## Carga eficiente en el navegador

Al iniciar:

1. solicitar el manifiesto;
2. solicitar `latest.csv`;
3. dibujar la estructura del mapa y las tarjetas;
4. consultar la lectura reciente en forma escalonada;
5. no descargar el histórico hasta que exista una selección.

Para un período, calcular qué meses intersecta y solicitar solo las partes
listadas para esos meses. Una solicitud anterior debe poder abortarse cuando la
persona cambia de estación, variable o rango.

## Lectura en vivo

Controles recomendados:

- intervalo de diez minutos;
- una solicitud por estación;
- `limite=1` y orden descendente por fecha;
- inicio escalonado, por ejemplo 350 ms entre estaciones;
- tiempo máximo de solicitud;
- sin ciclos infinitos de reintento;
- indicador visual cuando el valor está atrasado.

El API en vivo nunca se usa para reconstruir gráficos históricos.

## Descarga coherente con la interfaz

El archivo entregado debe corresponder a:

- estación seleccionada;
- variable seleccionada, como PMS, temperatura o humedad;
- período seleccionado;
- nombre público, no solo código técnico.

Antes de iniciar la descarga se muestra el aviso de uso responsable. No es
necesario registrar aceptación si el proyecto solo requiere que el texto sea
visible, pero el botón final debe estar dentro del mismo cuadro.

## Gráficos estables

Una causa frecuente de gráficos intermitentes es crearlos dentro de una pestaña
oculta, cuando su contenedor tiene ancho o alto cero. Para evitarlo:

- esperar a que la pestaña esté visible;
- usar `requestAnimationFrame` antes de medir y crear;
- agrupar respuestas simultáneas antes de redibujar;
- destruir la instancia anterior antes de reemplazar el lienzo;
- actualizar al cambiar pestaña, modo y tamaño;
- probar varios ciclos de navegación sin recargar la página.
