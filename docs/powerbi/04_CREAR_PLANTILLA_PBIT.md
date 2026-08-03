# 4. Crear una plantilla `.pbit`

Una plantilla permite que otra persona use el informe sin escribir código.

## Crear parámetros fáciles de completar

En **Transformar datos → Administrar parámetros**, crear:

| Nombre | Tipo | Ejemplo |
|---|---|---|
| `FechaInicio` | Fecha | 01-01-2025 |
| `FechaFin` | Fecha | fecha actual |
| `IdProyecto` | Número decimal o entero | 13 |
| `PowerBIKey` | Texto | clave entregada en privado |

Después, la consulta puede llamar:

```powerquery
fnCargarProyectoPowerBIV3(IdProyecto, FechaInicio, FechaFin, PowerBIKey)
```

## Exportar la plantilla

1. Terminar tablas, relaciones y gráficos.
2. Eliminar visualizaciones de prueba.
3. Seleccionar **Archivo → Exportar → Plantilla de Power BI**.
4. Escribir una descripción y guardar el archivo `.pbit`.
5. Abrir la plantilla en otro computador y comprobar que solicite los
   parámetros.

El `.pbit` contiene consultas, modelo y gráficos, pero no las filas cargadas.

## Qué recibe otra persona

La persona solamente debe:

1. Abrir el `.pbit`.
2. Completar dispositivo o proyecto y fechas.
3. Ingresar la clave que recibió por un canal privado.
4. Seleccionar credenciales del origen **Anónimas**.
4. Presionar **Cargar**.

No distribuir una plantilla con un valor real precargado en `PowerBIKey`.
