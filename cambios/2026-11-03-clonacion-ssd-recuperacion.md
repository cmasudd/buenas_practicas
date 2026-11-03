# Migración del sistema al SSD Kingston y guía de recuperación

Fecha de migración: 2 de noviembre de 2026

Fecha de verificación final: 3 de noviembre de 2026

## Alcance

- Se migró la raíz del servidor desde el volumen PERC de 279 GiB a un SSD
  Kingston de 894,3 GiB visibles.
- Se creó una EFI propia en el Kingston y se instalaron el cargador
  `ubuntu-ssd` y el fallback estándar `EFI/BOOT/BOOTX64.EFI`.
- Se configuró el Kingston como primera opción UEFI permanente.
- El volumen PERC anterior conserva el sistema previo, salvo la VM eliminada
  expresamente; queda desmontado por defecto y disponible como recuperación de
  emergencia.
- Se eliminó, por solicitud expresa, la VM `win10` y `win10.qcow2` tanto del
  origen como de la copia.
- Se publicó la guía autocontenida
  `docs/README_CLONACION_SSD_RECUPERACION.md`.
- Se incorporó, por solicitud expresa, el PDF institucional
  `docs/Manual_breve_para_la_construcción_y_publicación_de_dashboards_en_Power_BI_a_partir_de_la_API_de_sensores.pdf`.

## Identificadores validados

| Elemento | UUID / PARTUUID |
|---|---|
| Raíz Kingston `CMAS_ROOT` | `bfc8d511-db35-43d1-9cc7-bc8f2cf6481a` |
| EFI Kingston `CMAS_EFI` | `7596-58D3` |
| PARTUUID EFI Kingston | `b2ad25f4-e11b-4921-a1bb-3bf9e66c63a4` |
| Raíz PERC anterior | `cf002c64-3f49-4b66-89d3-a3bf126c1deb` |
| EFI PERC anterior | `8096-0AFA` |
| PARTUUID EFI anterior | `95f93eca-a6c2-4322-9ab3-d8078860267e` |

Los nombres de dispositivo cambiaron entre arranques. La operación y la guía
usan UUID y PARTUUID, no letras `/dev/sdX`.

## Secuencia aplicada

1. Se comprobó SMART del Kingston: estado general `PASSED`, sin errores
   registrados.
2. Se creó una tabla GPT con EFI de 1 GiB y raíz ext4 en el espacio restante.
3. Se realizó una copia `rsync` preservando propietarios, ACL, atributos,
   enlaces duros y archivos sparse.
4. La sincronización final se hizo con servicios mutables detenidos y delta por
   bloques. Se procesaron 1.751.288 entradas; el árbol lógico final informado
   por `rsync` fue 200,58 GB y los datos literales de la última pasada fueron
   303,97 MB.
5. Se actualizó `fstab` a los UUID del Kingston y se recrearon los dos archivos
   swap.
6. Una primera instalación dentro de `chroot` no avanzó porque faltaba el punto
   de montaje `dev`; no se ocultó este fallo. Después de arrancar desde el SSD,
   GRUB se reinstaló correctamente sobre la EFI activa y se regeneró
   `/boot/grub/grub.cfg`.
7. Se instaló el cargador fallback y se fijó el orden UEFI permanente.
8. Se realizaron dos arranques desde `ubuntu-ssd`; el segundo no dependió de
   `BootNext`.

## Estado UEFI final

```text
BootCurrent: 0007
BootOrder: 0007,000B,000C,0009,0005,0008,0006,0000,0003,000A,0004
Boot0007: ubuntu-ssd
Boot000B: Kingston SSD fallback
Boot0009: ubuntu del disco anterior
```

El número de entrada es específico del firmware actual. La guía explica cómo
validar rutas y PARTUUID si se renumeran.

## Pruebas

- Segundo arranque: `/` usa UUID
  `bfc8d511-db35-43d1-9cc7-bc8f2cf6481a`.
- EFI activa: UUID `7596-58D3`.
- `BootCurrent=0007` y `BootOrder` comienza por `0007` sin `BootNext`.
- GRUB contiene los kernels `6.8.0-138-generic` y
  `6.8.0-124-generic`, ambos con el UUID de raíz nuevo.
- Swap activo: archivos de 2 GiB y 8 GiB.
- `https://sensores.cmasccp.cl/`: HTTP 200.
- `https://api-sensores.cmasccp.cl/apidocs/`: HTTP 200.
- `https://api-sensores.cmasccp.cl/listarSensores?limite=1`: HTTP 200;
  confirma API y consulta mínima a MariaDB.
- El volumen PERC se detecta sin errores EXT4, I/O ni buffer en el arranque.
- `win10.qcow2` no existe en la raíz activa.

## Artefactos y hashes

Los artefactos protegidos no se agregaron a Git:

- respaldo y registro de migración:
  `/home/cmas/backups/migracion-disco-20261030-133533/`;
- XML y evidencia de eliminación de la VM:
  `/home/cmas/backups/eliminacion-win10-20261102-140619/`;
- estado UEFI, `fstab` y `EFI.before.tar`:
  `/home/cmas/backups/arranque-ssd-20261102-164524/`.

Hashes de los scripts finales utilizados o conservados:

| Artefacto | SHA-256 |
|---|---|
| `finalizar_copia.sh` | `c49f2353bb845fffff31bd8c5a6c47639fe9da96abe17005b4103dae1d1e46f5` |
| `verificar_arranque.sh` | `3d478990099684b32d33c8b47e0fcdcd6f5f43aa531b54be7515e3f5f56b6ad3` |
| `fijar_arranque_ssd.sh` | `0a40756a7bba0071bf256d2e0ce946007cd35b852c55d8e6fb2f33a882438268` |
| `eliminar_vm_win10.sh` | `8e3b3816f7fcaef77bdbbb3ff7144ce5ef42db9cdc7650d17d5e80aed4788316` |
| `/etc/fstab` activo | `a97198d7832f5044677a88291dc909678ce1ee0a5780b3a14ea22fcba736e830` |
| `/boot/grub/grub.cfg` activo | `e223ea48c2b1802593c50417cd3f01ddc5292611531506e0fabbb9dae406c64e` |
| Manual Power BI PDF | `d2782f87caf3c16dcc6a31705b7f9a265b32fd65982f631eb58281af901722ff` |

Cada directorio protegido contiene sus propias sumas SHA-256 cuando la fase
alcanzó el cierre normal.

## Reversión

La reversión normal no modifica discos:

1. Elegir una sola vez la entrada UEFI antigua con `efibootmgr -n`, después de
   comprobar su número mediante `efibootmgr -v`.
2. Arrancar y confirmar que `/` usa UUID
   `cf002c64-3f49-4b66-89d3-a3bf126c1deb`.
3. Mantener el SSD intacto mientras se diagnostica.
4. Verificar servicios, MariaDB y portales.
5. Recuperar por separado los cambios posteriores al corte.

La guía incluye recuperación desde UEFI, consola GRUB y Ubuntu Live, además de
montaje de solo lectura y restauración de archivos individuales.

No existe rollback de la VM `win10`: su eliminación fue permanente y solicitada
expresamente.

## Seguridad

- No se documentaron contraseñas, hashes de autenticación, cookies, tokens ni
  archivos `.env`.
- Los respaldos que pueden contener configuración real permanecen fuera de Git
  con acceso protegido.
- El PDF se revisó mediante metadatos y extracción de texto. Contiene correos
  institucionales y se identifica como documento de uso institucional, pero no
  contiene secretos; se incluyó porque el responsable solicitó expresamente su
  publicación en este repositorio.
