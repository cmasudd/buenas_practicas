# Kit de Power BI para la API de sensores

## Empiece aquí

Este directorio está pensado para una persona que nunca ha usado Power BI ni
Power Query. No es necesario conocer bases de datos ni programar cursores.

Lea los documentos en este orden:

1. [Conceptos básicos](01_CONCEPTOS_BASICOS.md).
2. [Primera carga desde cero](02_PRIMERA_CARGA_DESDE_CERO.md).
3. [Proyecto 13: Línea Base Pública - Agua](03_PROYECTO_13_AGUA.md).
4. [Crear una plantilla para otras personas](04_CREAR_PLANTILLA_PBIT.md).
5. [Publicar y actualizar](05_PUBLICAR_Y_ACTUALIZAR.md).
6. [Seguridad y claves](06_SEGURIDAD_Y_CLAVES.md).
7. [Solución de problemas](07_SOLUCION_DE_PROBLEMAS.md).
8. [Guía para quien administra el sistema](08_GUIA_DEL_ADMINISTRADOR.md).

## Archivos para copiar en Power Query

- `examples/powerbi/fnCargarProyectoPowerBIV3.m`: opción recomendada; carga un
  proyecto completo con clave y recorre automáticamente todas sus páginas.
- `examples/powerbi/Proyecto_13_Agua_Protegido.m`: consulta lista para el
  proyecto 13 usando la función protegida.
- `examples/powerbi/fnCargarDispositivoV3.m`: función que recorre todas las
  páginas de un dispositivo; se conserva como alternativa pública y para
  diagnósticos.
- `examples/powerbi/Proyecto_13_Agua.m`: carga y une AGUA-00, AGUA-01,
  AGUA-02 y AGUA-03.
- `examples/powerbi_v3_ura00.m`: ejemplo independiente ya validado con URA-00.

## Estado actual al 3 de agosto de 2026

| Función | Estado |
|---|---|
| V3 paginada por dispositivo | Disponible y probada |
| Proyecto 13 mediante cuatro dispositivos | Disponible con los ejemplos |
| Formato normalizado para análisis | Disponible |
| V3 de proyecto protegida con API key | Disponible |
| Formato ancho compatible con V2 | Disponible en la ruta Power BI |
| Plantilla `.pbit` binaria | Debe exportarse desde Power BI Desktop en Windows |

La clave real no aparece en estos documentos ni debe subirse a GitHub. Se
entrega por un canal privado y se guarda como parámetro en Power BI.
