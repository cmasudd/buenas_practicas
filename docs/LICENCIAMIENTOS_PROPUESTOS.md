# Licenciamientos propuestos para proyectos C+

## Estado

Todo el esquema descrito aquí está **en revisión**. Es una propuesta de trabajo,
no una política institucional aprobada, asesoría jurídica ni una concesión
automática de licencia. Cada proyecto debe completar la revisión de titularidad,
contratos, patentes, datos personales, derechos de terceros y transferencia
tecnológica antes de publicar una licencia definitiva.

## Matriz de referencia propuesta

| Tipo de activo | Licencia propuesta |
|---|---|
| Hardware | CERN-OHL-S-2.0 |
| Software | GPL-3.0-only |
| Firmware | GPL-3.0-only |
| Base de datos | ODbL-1.0 |
| Contenidos individuales de datos | DbCL-1.0 u otra licencia expresa, según el caso |
| Documentación | CC BY-SA 4.0 |
| Marcas y logos C+/UDD | Reservados y fuera de las licencias abiertas |

El principio propuesto es **abierto por defecto**, con términos alternativos
mediante acuerdo cuando exista una razón estratégica y C+/UDD controle los
derechos necesarios.

## Aplicación segura mientras esté en revisión

- Usar el rótulo `Licenciamiento propuesto — en revisión`.
- No crear un `LICENSE` definitivo ni declarar que la propuesta está vigente.
- No modificar los textos oficiales de licencias estándar.
- Separar código, hardware, datos, contenidos, documentación y marcas.
- Identificar dependencias, mapas, fotografías y demás materiales de terceros.
- Confirmar por separado la licencia de los contenidos individuales de una
  base publicada bajo ODbL.
- Incorporar un aviso sobre incertidumbre, continuidad, calibración y alcance
  no regulatorio de los datos de sensores.
- Sustituir el borrador por los textos oficiales completos únicamente después
  de la aprobación institucional.

## Caso `calidadAgua`

La propuesta inicial para `cmasudd/calidadAgua` contempla GPL-3.0-only para la
web y sus scripts, ODbL-1.0 para la base, licencia de contenidos aún por
determinar, CC BY-SA 4.0 para documentación y reserva de marcas C+/UDD. Los
archivos del proyecto deben expresar que todo lo anterior continúa en revisión.

## Fuente

Resumen operativo basado en
[`cmasudd/Propuesta_Licencia`](https://github.com/cmasudd/Propuesta_Licencia),
versión de propuesta 0.1. La fuente también declara expresamente que requiere
revisión jurídica y de transferencia tecnológica de UDD.

