# 7. Solución de problemas

## Power BI muestra solo 1.000 filas

Causa: se pegó una URL directa en **Obtener datos → Web**.

Solución: usar `fnCargarDispositivoV3`, que sigue `next_cursor` hasta la última
página.

## Error de origen dinámico al publicar

Verificar que el código use:

```powerquery
Web.Contents(ApiBase, [RelativePath = ..., Query = ...])
```

No concatenar el cursor dentro de una URL completa.

## Los decimales aparecen multiplicados o con error

Convertir `valor` con cultura inglesa:

```powerquery
Number.FromText(Text.From([valor]), "en-US")
```

## La fecha aparece como texto

Usar la transformación incluida en la función. El resultado debe tener tipo
`datetime`.

## Una visualización V2 dejó de funcionar

V3 es normalizada. Buscar la antigua columna variable y reemplazarla por:

- `variable_descripcion` como categoría o leyenda;
- `valor` como medida;
- `unidad` como filtro.

## Error 400

Revisar formato y orden de las fechas. Deben existir ambas y usar `AAAA-MM-DD`.

## Error 429

El servidor está protegiendo una descarga o hay otra operación activa. Esperar
el tiempo indicado en `Retry-After` y no iniciar varias cargas simultáneas.

## Error 500, 502, 503 o 524

1. Detener la actualización repetida.
2. Esperar unos minutos.
3. Probar un rango de un día.
4. Informar dispositivo, fechas, hora y código de error al administrador.

No presionar **Actualizar** repetidamente; Power BI podría dejar solicitudes
superpuestas.

## La actualización funciona en Desktop pero no en Service

- Revisar credenciales del origen.
- Confirmar que la raíz de la URL sea fija.
- Revisar parámetros publicados.
- Comprobar zona horaria.
- Ejecutar manualmente **Actualizar ahora** y consultar el historial.
