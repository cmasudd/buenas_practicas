# 8. Guía del administrador

## Entrega recomendada

Para usuarios principiantes, entregar:

- una plantilla `.pbit` sin datos;
- este manual;
- una lista de proyectos y dispositivos autorizados;
- un canal de soporte;
- una política de frecuencia de actualización.

## Lista de validación antes de distribuir

- [ ] La consulta usa V3 y cursor, no `OFFSET`.
- [ ] Las fechas son obligatorias.
- [ ] El tamaño de página es 1.000 o menor.
- [ ] Dos páginas consecutivas no contienen filas repetidas.
- [ ] Las columnas de medición conservan el tipo esperado por el informe.
- [ ] `fecha` es `datetime`.
- [ ] Las consultas auxiliares tienen **Habilitar carga** desactivado.
- [ ] La carga inicial se prueba fuera del horario de mayor uso.
- [ ] La actualización incremental está configurada para históricos grandes.
- [ ] No existen claves en archivos, URLs ni repositorios.

## Pruebas mínimas

1. Un día con datos.
2. Un día sin datos.
3. Dos páginas consecutivas sin duplicados.
4. Rango completo de un dispositivo de prueba.
5. Actualización manual en Power BI Service.
6. Dos actualizaciones programadas consecutivas.

## Prueba V3 de referencia

El 3 de agosto de 2026, URA-00 (`id_dispositivo=223`) recuperó 19.281 filas
únicas en 20 páginas y 7,16 segundos. No quedaron consultas MariaDB superiores
a cinco segundos.

## Ruta protegida activa

La implementación actual:

1. Guarda únicamente el SHA-256 en `POWERBI_API_KEY_HASH`.
2. Valida `X-API-Key` con comparación constante.
3. Exige fecha inicial y final.
4. Limita cada página a 1.000 filas y cada proyecto a 25 dispositivos.
5. Serializa las consultas Power BI mediante un bloqueo del servidor.
6. No incluye la clave en la URL ni en los registros normales de Nginx.

Una clave controla acceso, pero no reduce el costo de una consulta. La ruta
protegida conserva la paginación V3. Como mejora futura, crear claves
individuales y revocables por modelo semántico en vez de una clave compartida.

## Activación y rotación

1. Generar una clave larga y aleatoria fuera del repositorio.
2. Calcular su SHA-256 y guardar solo el hash en `.env` del servidor.
3. Recargar `api_sensores` mediante PM2.
4. Comprobar HTTP 401 sin clave y HTTP 200 con la clave.
5. Entregar el secreto por un canal privado y registrarlo en `PowerBIKey`.
6. Para revocar, repetir el proceso con una clave nueva.
