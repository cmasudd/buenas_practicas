# 6. Seguridad y claves

## Situación actual

La ruta V3 paginada por dispositivo está disponible sin API key porque los
datos ambientales son públicos. La ruta específica para Power BI por proyecto
sí exige una clave válida.

## Cómo funciona

La ruta protegida utilizará un encabezado:

```text
X-API-Key: valor-secreto
```

El servidor no guarda la clave original: compara su hash SHA-256 en tiempo
constante. La clave no debe aparecer en:

- URLs;
- GitHub;
- documentos;
- capturas de pantalla;
- código M compartido;
- registros de Nginx.

## Compartir con otras personas

No repartir una misma clave a todos. Lo recomendable es una clave por usuario,
institución o modelo semántico, con posibilidad de revocarla y aplicar límites.

Una persona con permisos para editar el `.pbix` puede inspeccionar parámetros y
consultas. Para evitar entregar la clave, usar un Dataflow administrado:

```text
API con clave → Dataflow institucional → informes de usuarios
```

El administrador configura la credencial una vez y los autores de informes
consumen la tabla resultante.

## Configurar el parámetro

Crear `PowerBIKey` como parámetro de texto y utilizar:

```powerquery
Headers = [
    Accept = "application/json",
    #"X-API-Key" = PowerBIKey
]
```

Power BI seguirá mostrando el dominio como origen **Anónimo**: eso no vuelve
pública la ruta, porque el encabezado sigue siendo obligatorio en cada página.

Si una clave se comparte por error, quien administra la API debe generar otra,
actualizar su hash en el servidor, recargar el servicio y sustituir el parámetro
en los modelos autorizados.
