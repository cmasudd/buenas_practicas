# Plataforma pública Monitoreo de Calidad de Agua C+

Fecha: 9 de septiembre de 2026  
Repositorio: `cmasudd/calidadAgua`

## Alcance

- Web estática responsive con identidad C+/UDD.
- Mapa Leaflet para AGUA-01, AGUA-02, AGUA-03 y URA-01.
- Gráficos de pH, conductividad, temperaturas, oxígeno disuelto, voltaje y CSQ.
- Descarga por selección y descarga conjunta del histórico.
- Histórico mensual, `manifest.json` y `latest.csv` generados junto a MariaDB.
- Publicación horaria y consulta en vivo de una lectura por estación cada diez
  minutos.
- Comparación orientativa de pH y conductividad con NCh 1333 para agua de
  riego, sin presentarla como certificación ni evaluación oficial.

## Perfil y limpieza

Se perfilaron los dispositivos 94, 113, 216 y 256 antes de definir el contrato.
Se excluyen por modelo pH 0/14, conductividad 0 y temperatura DS18B20 -999. El
oxígeno disuelto de AGUA-03 se publica con estado de validación pendiente y el
pH de URA-01 quedó documentado como constante durante su cobertura inicial.

Los CSV públicos comienzan en 2025. Registros anteriores con fechas anómalas y
meses sin observaciones se excluyen del manifiesto.

## Licenciamiento

GPL-3.0-only para software, ODbL-1.0 para la base, una licencia de contenidos
por determinar y CC BY-SA 4.0 para documentación son **licenciamientos
propuestos y en revisión**. No se instalaron textos `LICENSE` definitivos.

## Recuperación

La web y los datos quedan versionados en Git. Ante una regresión se revierte el
commit afectado. El histórico se puede reconstruir desde MariaDB con
`scripts/export_monthly_csv.py --all`. La automatización se desactiva retirando
su única entrada de cron; nunca deben mantenerse dos programadores activos.
