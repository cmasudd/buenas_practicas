# Guía pública para crear webs de sensores

Fecha: 2026-08-24

URL: `https://sensores.cmasccp.cl/protocolos`

## Objetivo

Publicar en el portal una versión segura y práctica de la guía para perfilar
datos, exportar históricos desde MariaDB local y servir CSV mensuales sin que
cada visitante repita consultas pesadas contra el servidor.

## Cambio aplicado

- La guía de buenas prácticas pasó a ser pública y no requiere iniciar sesión.
- Swagger continúa separado y requiere una sesión del portal.
- Se documentaron perfilado previo, centinelas, privacidad, arquitectura,
  contrato CSV/manifiesto, lectura reciente, automatización horaria, validación,
  monitoreo y reversión.
- Se enlazaron la guía completa y sus plantillas desde el repositorio público de
  buenas prácticas.
- Se agregó una presentación adaptable y una corrección acotada del menú para
  pantallas pequeñas.
- No se modificaron API, MariaDB, permisos ni rutas de escritura.

## Referencia fuente

- Repositorio: `https://github.com/cmasudd/SensorsWebApp`.
- Rama: `desarrollo`.
- Commit: `f13287ea4812d19e148e80123fad2bc524ba2579`.
- Tag productivo: `sensores-prod-protocolos-guia-v1`.
- Autor del commit y tag: `cmasudd` con correo público `noreply` configurado
  solamente en este clon.

Los cambios previos no relacionados de `dist/` permanecieron fuera del commit.

## Respaldo anterior

Copia completa del directorio servido:

```text
/home/cmas/backups/sensores-protocolos-before-2026-08-24-1705/public
```

Los archivos fuente productivos anteriores `ProtocolosPage.jsx` y `Navbar.jsx`
también quedaron bajo `source-before/` dentro del mismo respaldo. Luego se
sincronizaron con el commit canónico para que un build futuro no restaure la
versión antigua. Los demás cambios locales del worktree no se tocaron.

Hashes anteriores:

```text
public/index.html
dceb98acf642c52ac93cdee58952c83366faf3c09c046a1cd22e3561c0028fa8

public/assets/index-cec81e30.js
4fb519897a6d6c2be9d002b9dc1d49618f6d1e72b6838021de1a7c78e694d54c

public/assets/index-173f83ed.css
173f83edf41971483c359bc4e077eb11eec1247614fe694d27a3693e4ee8957d
```

## Artefacto desplegado

Se copiaron primero los assets con nombre versionado y después `index.html`.
El proceso estático PM2 no se reinició porque lee los archivos en cada
solicitud.

```text
public/index.html
61e3a58a37f95f6e2959d73f898be9931f791e29d8948fd5a471326957dab162

public/assets/index-dfc18f17.js
6429f03572076cd236d5a8cebd29256d4a3f7989fb5ce857859d1ec5accc5fba

public/assets/index-573109e2.css
573109e2ee56aff7aa501f6de3fa21f91e7dc13f122fadede33ea49788f3b7b6
```

Los tres archivos obtenidos nuevamente desde el dominio público coincidieron
byte por byte con el artefacto local.

## Pruebas

- `npm test`: cuatro archivos y diez pruebas correctas.
- Dos pruebas nuevas comprueban que la guía es pública y Swagger sigue
  protegido por sesión.
- `npm run build`: correcto con Vite 4.1.0.
- Revisión de formato Git: correcta.
- Escaneo del código y artefacto nuevo: sin patrones de claves privadas o
  tokens de GitHub.
- Captura local y pública a 1440 × 1000: correcta.
- Captura local y pública a 500 × 844: menú y contenido contenidos en el ancho.
- PM2 `sensores`: en línea, sin reinicio.

El build conserva una advertencia preexistente porque el bundle general supera
ligeramente 1.000 kB sin comprimir. Su tamaño comprimido fue 304,77 kB. La guía
no introduce una dependencia JavaScript adicional.

## Reversión

La reversión no toca la API ni la base de datos:

1. Copiar el `index.html` del respaldo sobre
   `/var/www/sensores/public/index.html`.
2. Comprobar que vuelve a apuntar a `index-cec81e30.js` e
   `index-173f83ed.css`; ambos assets anteriores siguen presentes.
3. Verificar los tres hashes anteriores y abrir `/protocolos`.
4. Revertir la fuente con `git revert f13287ea` y publicar ese commit en
   `desarrollo` si también se necesita retirar el cambio del repositorio.
5. Conservar los assets nuevos hasta terminar la ventana de verificación; no es
   necesario reiniciar PM2.
6. Si se revierte también el worktree productivo, restaurar desde
   `source-before/` solamente `ProtocolosPage.jsx` y `Navbar.jsx`, y retirar los
   nuevos CSS/pruebas solo después de confirmar que no están referenciados.

No se usa `git reset --hard` ni se elimina el directorio productivo.
