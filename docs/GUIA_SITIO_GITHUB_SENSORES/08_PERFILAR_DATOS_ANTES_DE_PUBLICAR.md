# Perfilar los datos antes de publicarlos

Esta revisión es obligatoria antes de diseñar columnas, gráficos, descargas o
automatizaciones. Una variable no se publica solamente porque exista en la base
de datos.

## Por qué se hace primero

Publicar sin revisar puede provocar:

- gráficos de variables constantes o compuestos solo por centinelas;
- unidades incorrectas o mezcladas;
- dos sensores distintos presentados como si midieran lo mismo;
- valores ausentes interpretados como mediciones reales;
- exposición de coordenadas u otra información innecesaria;
- archivos y commits más grandes sin beneficio para las personas;
- una interfaz difícil de explicar y mantener.

## Control de publicación

Cada variable candidata debe responder estas preguntas:

| Dimensión | Pregunta |
|---|---|
| Propósito | ¿Ayuda al objetivo declarado de la web? |
| Significado | ¿Se conoce el sensor, variable y procedimiento que la producen? |
| Unidad | ¿La unidad almacenada y la unidad pública están confirmadas? |
| Cobertura | ¿Existe en las estaciones y fechas que se presentarán? |
| Calidad | ¿Cuáles son mínimo, máximo, nulos, constantes y centinelas? |
| Duplicidad | ¿Existe otro campo con el mismo nombre pero distinto origen? |
| Privacidad | ¿Puede revelar ubicación, movimiento u otra información sensible? |
| Interpretación | ¿Una persona responsable puede explicar el dato y sus límites? |
| Costo | ¿Justifica el espacio, historial Git y complejidad visual? |
| Reversión | ¿Puede retirarse sin romper el contrato anterior? |

Una respuesta desconocida no se completa con una suposición: la variable queda
fuera hasta que exista evidencia o autorización.

## Perfil mínimo por dispositivo y sensor

Revisar, sin imprimir credenciales:

- identificador y código del dispositivo;
- sensor físico y modelo;
- variable y unidad registradas;
- primera y última fecha;
- cantidad de filas;
- mínimo y máximo;
- nulos y valores centinela conocidos;
- cantidad de valores distintos o presencia de una constante;
- frecuencia aproximada y vacíos temporales.

Los agregados deben ejecutarse sobre dispositivos y períodos acotados. Si la
tabla es grande, consultar por sensor y usar el índice de fecha; no lanzar un
perfil global desde el navegador.

## Distinguir centinelas de valores reales

Un valor como `-1` no se elimina globalmente sin revisar el contexto. Puede ser
un centinela en humedad y, al mismo tiempo, una temperatura real posible.

Para decidir:

1. comparar campos del mismo ciclo de medición;
2. revisar el firmware o protocolo del equipo;
3. buscar repeticiones simultáneas en variables relacionadas;
4. confirmar rangos físicamente posibles;
5. documentar a qué modelo y variable se aplica la regla;
6. preferir un campo de calidad explícito cuando el firmware lo permita.

La limpieza debe estar limitada por modelo y variable, cubierta por pruebas y
registrada en el contrato de datos.

## Privacidad y minimización

No publicar por defecto:

- latitud, longitud o rutas;
- números de serie;
- identificadores de sesión sin finalidad pública;
- diagnósticos internos que no aportan al objetivo;
- datos personales o de contacto obtenidos desde la operación;
- columnas constantes o sin significado validado.

La configuración pública puede mantener un código técnico estable y un nombre
amigable, pero los identificadores internos de base solo se incluyen cuando son
necesarios para el exportador local.

## Clasificación de la decisión

Cada variable queda en uno de cuatro estados:

- `publicar`: útil, explicable y validada;
- `publicar como diagnóstico`: visible en un grupo operativo, no mezclada con
  indicadores ambientales;
- `reservar`: existe, pero requiere autorización o validación adicional;
- `excluir`: constante, centinela, duplicada, sensible o irrelevante.

La decisión se registra en una tabla con fecha, evidencia y responsable.

## Caso AUCA Cochrane

La primera revisión de los dispositivos 241 a 244 encontró:

- PM1, PM2.5, PM10, temperatura y humedad con cobertura en los cuatro equipos;
- temperatura/humedad internas, relé y señal útiles como diagnóstico;
- satélites compuesto solamente por `-1` en el período revisado;
- voltaje compuesto solamente por `0`;
- coordenadas y velocidad presentes, pero innecesarias para una primera web sin
  geolocalización autorizada;
- variables genéricas del calefactor que duplicaban conceptos ambientales.

Por eso la primera versión publicó variables ambientales y diagnósticos
justificados, reservó GPS/velocidad y excluyó satélites/voltaje. Esta decisión
redujo el contrato y evitó presentar valores inválidos como información real.

## Antes de modificar el exportador

- [ ] Perfil actualizado por dispositivo, sensor y variable.
- [ ] Unidad confirmada.
- [ ] Centinelas documentados por modelo y campo.
- [ ] Riesgo de privacidad evaluado.
- [ ] Nombre público y categoría definidos.
- [ ] Columna, unidad y decimales definidos.
- [ ] Manifest, CSV, web y descarga contemplan el cambio.
- [ ] Prueba con una estación y un mes.
- [ ] Comparación contra MariaDB.
- [ ] Tamaño y crecimiento estimados.
- [ ] Respaldo y rollback registrados.

## Revisión periódica

Repetir el perfil cuando:

- se agrega o reemplaza un dispositivo;
- cambia el firmware;
- cambia el modelo de sensor;
- aparece una nueva variable;
- una serie se vuelve constante o sale de rango;
- se autoriza geolocalización u otro dato antes reservado;
- cambia el objetivo público del sitio.

La selección de datos es una decisión versionada, no una configuración que se
define una vez y se olvida.
