# Integración gradual

La V3 se registra junto a las rutas existentes; no sustituye sus funciones:

```python
from historico_v3 import create_historico_v3_blueprint

config = {
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "port": int(os.getenv("DB_PORT", 3306)),
}

app.register_blueprint(create_historico_v3_blueprint(config))
```

No se deben imprimir `config` ni las credenciales en logs.

El proceso debe cargar además estas variables desde un archivo fuera del
repositorio:

```dotenv
HISTORICO_SESSION_SECRET=secreto-aleatorio-largo
HISTORICO_USER=usuario
HISTORICO_PASSWORD_HASH=hash-generado-por-werkzeug
```

Para el portal React se incluyen ejemplos en `frontend/`. Las solicitudes de
login usan `credentials: "include"`; el API debe permitir credenciales CORS
solo desde el origen exacto del portal.

## Protección temporal de V2

V2 sigue atendiendo consultas pequeñas. En producción se agregó un cortacircuito
para las solicitudes legacy de más de 100 resultados sin `fecha_inicio` ni
`fecha_fin`, porque ese patrón obliga al JOIN antiguo a recorrer y ordenar todo
el histórico. La respuesta es HTTP 422 e indica la ruta V3 recomendada.

Esta protección se puede retirar cuando todos los consumidores históricos hayan
migrado a V3.
