# Plataforma pública Aire Aysén

Fecha: 11 de septiembre de 2026  
Repositorio: `cmasudd/aireAysen`

## Alcance

- Web estática responsive con identidad C+/UDD.
- Quince sensores: 26–33 para INDOOR y 34–40 para OUTDOOR.
- MP1, MP2,5 y MP10 agregados por sensor y hora.
- Mapa con coordenada exacta sólo para los sensores 31 y 39; los demás se
  describen en el área general de Coyhaique sin inventar posiciones.
- Gráficos horarios para 24 horas y 7 días; promedios diarios con banda
  mínimo–máximo para 30 días y el histórico completo.
- Descarga por selección y ZIP generado en GitHub Pages con un CSV separado
  por sensor.
- Referencias orientativas DS 12/2011 para MP2,5 y DS 12/2021 para MP10.

## Fuente externa

Los datos no provienen de MariaDB CMAS. `scripts/download_looker.py` descubre
la versión vigente de Looker Studio y reproduce las consultas públicas de los
gráficos `data Aysen`. La extracción inicial ampliada obtuvo 59.300
combinaciones sensor–hora hasta el 11 de septiembre de 2026 a las 22:00.

El endpoint de Looker no constituye una API pública documentada. Cada ejecución
valida el contrato, sensores, columnas, cantidad de campos y respuesta antes de
reemplazar archivos. Un cambio incompatible falla sin publicar datos parciales.

## Perfil y publicación

Los CSV se dividen por sensor y mes. No se interpolan brechas. Los valores
negativos o superiores a 5.000 µg/m³ se reservan como vacíos; los ceros se
conservan. La interfaz carga sólo los meses necesarios y revisa el manifiesto
cada diez minutos.

El clon exclusivo `aireAysen-publisher` actualiza Google al minuto 43 de cada
hora, protegido por `/usr/bin/flock`. El manifiesto omite tiempos de revisión
volátiles, por lo que no se crean commits si las observaciones no cambian.

## Licenciamiento

GPL-3.0-only para software, ODbL-1.0 para base derivada y CC BY-SA 4.0 para
documentación son propuestas en revisión. El repositorio fuente no declara
licencia; se requiere confirmar autorización antes de adoptar términos
definitivos. Las marcas C+/UDD quedan reservadas.

## Recuperación

El cron se desactiva retirando su única entrada. La copia anterior del crontab
se guardó en `/tmp/crontab-before-aireAysen-2026-09-11`. Los datos se pueden
reconstruir ejecutando `python3 scripts/download_looker.py` en el clon
publicador.
