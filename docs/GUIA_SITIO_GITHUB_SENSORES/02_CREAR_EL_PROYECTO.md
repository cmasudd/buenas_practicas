# Crear el proyecto

## 1. Reunir la información

Antes de escribir código, completar una ficha por estación:

| Campo | Ejemplo genérico |
|---|---|
| Identificador interno de dispositivo | `123` |
| Código técnico | `ESTACION-01` |
| Nombre público | `Escuela Ejemplo` |
| Localidad | `Comuna Ejemplo` |
| Coordenadas | latitud y longitud verificadas |
| Variables disponibles | MP2.5, MP10, temperatura, humedad |
| Modelo de cada sensor físico | nombre exacto en MariaDB |
| Unidad almacenada | por ejemplo ppm |
| Unidad publicada | por ejemplo ppb |

El nombre público se usa en la interfaz y en el archivo descargado. El código
técnico se conserva como clave estable, pero no debe reemplazar al nombre de la
escuela o estación ante el usuario.

## 2. Verificar MariaDB sin exportar

Confirmar:

- relaciones entre dispositivo, sensor físico y variable;
- primera y última fecha por sensor;
- centinelas de lectura ausente, como `-1`;
- zona horaria de las fechas;
- índice compuesto equivalente a `(id_sensor, fecha)`;
- plan real de la consulta mediante `EXPLAIN`.

No copiar `FORCE INDEX` de otra instalación hasta comprobar el nombre y el orden
de los índices locales.

## 3. Crear los repositorios

Configuración recomendada:

```text
proyecto-sensores-web/
  index.html
  assets/
    photos/
    vendor/
  README.md

proyecto-sensores-datos/
  data/
    manifest.json
    latest.csv
    ESTACION-01/
      2026-08-part-001.csv
  config/
    stations.json
  scripts/
    export_monthly_csv.py
    validate_export.py
    update_data.sh
  tests/
  README.md
```

El repositorio de datos debe ignorar `.env`, logs, temporales, respaldos,
documentos de trabajo y configuraciones del editor. Debe aceptar un
`.env.example` que contenga solo nombres de variables.

## 4. Configurar la identidad

Definir `user.name` y `user.email` en el clon exclusivo del daemon. Usar una
identidad institucional o de automatización que la organización pueda reconocer.
El correo puede ser la dirección `noreply` asociada a la cuenta de GitHub.

La identidad del commit y la credencial que autoriza el `push` son cosas
distintas. Ambas deben verificarse antes de activar el temporizador para evitar
atribuir los commits a una persona equivocada.

## 5. Adaptar el exportador

Tomar como referencia `scripts/export_monthly_csv.py` de Aire Aconcagua y
modificar solamente después de confirmar:

- tablas y columnas del esquema local;
- mapeo de modelos e identificadores de variable;
- conversiones de unidades;
- encabezado público;
- zona horaria;
- tamaño de lote;
- índice utilizado.

El exportador debe aceptar al menos:

```text
sin argumentos       mes vigente, todas las estaciones
--month AAAA-MM      un mes específico
--station CODIGO     una estación específica
--all                backfill completo y manual
```

Leer MariaDB en lotes limita cada respuesta SQL, pero no garantiza por sí solo
un uso acotado de memoria: un programa que acumula todo el mes en un diccionario
sigue reteniendo todas las filas. Durante la prueba se debe medir la memoria
máxima. Si resulta alta, ordenar y combinar fuentes mediante archivos temporales
o una base SQLite temporal, o cambiar a partes diarias que puedan escribirse en
streaming.

## 6. Ejecutar el backfill inicial

Hacerlo por etapas:

1. una estación y un mes;
2. validar el CSV y compararlo con MariaDB;
3. una estación completa;
4. revisar tiempo, memoria, espacio y tamaño;
5. continuar con el resto;
6. publicar solo cuando todas las validaciones pasen.

No activar el trabajo horario antes de completar esta prueba.

## 7. Crear la web

La web debe:

- cargar primero `manifest.json` y `latest.csv`;
- mostrar el nombre público de la estación;
- cargar CSV solamente al elegir estación y período;
- filtrar por variable en modo escolar o equivalente;
- generar la descarga con la selección visible;
- crear los gráficos cuando el contenedor ya tenga dimensiones;
- destruir o actualizar instancias anteriores del gráfico;
- reintentar de forma acotada solo errores de red transitorios;
- conservar el último CSV si falla la lectura en vivo;
- mostrar fecha de actualización y estado de datos atrasados;
- presentar el aviso de uso antes de la descarga;
- incluir contacto y atribuciones en todas las pestañas.

Las dependencias críticas de visualización deben quedar bajo `assets/vendor/`
para que una falla de CDN no impida iniciar mapas o gráficos.

## 8. Activar GitHub Pages

Para una web estática se puede publicar desde la rama principal. Si no se usa
Jekyll, agregar `.nojekyll` evita un procesamiento innecesario. Esperar el build
y verificar desde la URL pública el HTML, el manifiesto y al menos un CSV.

## 9. Activar la automatización

Instalar una sola opción: temporizador `systemd` o cron. Ejecutar manualmente el
mismo comando una vez, observar el commit, comprobar el `push` y confirmar el
despliegue antes de dejarlo desatendido.
