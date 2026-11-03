# Clonación al SSD y recuperación del servidor CMAS

Esta guía registra la migración del sistema realizada el **2 de noviembre de
2026**, su verificación definitiva el **3 de noviembre de 2026** y los pasos
para recuperar el servidor sin depender de archivos guardados solamente en el
equipo.

No contiene contraseñas, tokens, cookies, archivos `.env` ni valores de
credenciales. Los comandos destructivos no forman parte del procedimiento
normal de recuperación.

## Resumen operativo

El sistema principal vive ahora en el SSD Kingston de 960 GB comerciales
(894,3 GiB visibles). El volumen PERC anterior de 279 GiB permanece conectado,
conserva el sistema previo —salvo la VM eliminada expresamente— y normalmente
está desmontado como recuperación de emergencia.

| Función | Modelo / entrada | UUID o identificador |
|---|---|---|
| Raíz principal | Kingston `CMAS_ROOT` | `bfc8d511-db35-43d1-9cc7-bc8f2cf6481a` |
| EFI principal | Kingston `CMAS_EFI` | `7596-58D3` |
| Partición EFI principal | GPT | `b2ad25f4-e11b-4921-a1bb-3bf9e66c63a4` |
| Raíz de recuperación | Volumen PERC anterior | `cf002c64-3f49-4b66-89d3-a3bf126c1deb` |
| EFI de recuperación | Volumen PERC anterior | `8096-0AFA` |
| Partición EFI anterior | GPT | `95f93eca-a6c2-4322-9ab3-d8078860267e` |

Los nombres `/dev/sda` y `/dev/sdb` **cambiaron después de migrar**. Nunca se
deben usar para decidir qué disco borrar, formatear o reparar. Se debe validar
modelo, etiqueta, UUID y PARTUUID.

## Estado UEFI validado

Después de dos arranques desde el Kingston se comprobó:

```text
BootCurrent: 0007
BootOrder: 0007,000B,000C,0009,0005,0008,0006,0000,0003,000A,0004
Boot0007: ubuntu-ssd
Boot000B: Kingston SSD fallback
Boot000C: ubuntu (apunta a la EFI del Kingston)
Boot0009: ubuntu (disco PERC anterior)
```

Los números de entrada pueden cambiar si se reinicia o actualiza el firmware.
Antes de ejecutar `efibootmgr -o`, hay que inspeccionar siempre `efibootmgr -v`
y comparar las rutas, etiquetas y PARTUUID.

El archivo `/etc/fstab` activo usa los UUID del Kingston:

```fstab
UUID=bfc8d511-db35-43d1-9cc7-bc8f2cf6481a /         ext4 errors=remount-ro 0 1
UUID=7596-58D3                            /boot/efi vfat umask=0077       0 1
```

## Comprobación cotidiana

Estos comandos son de solo lectura:

```bash
findmnt -n -o SOURCE,UUID,LABEL,FSTYPE /
findmnt -n -o SOURCE,UUID,LABEL,FSTYPE /boot/efi
lsblk -e7 -o NAME,PATH,SIZE,FSTYPE,LABEL,UUID,PARTUUID,MOUNTPOINTS,MODEL
efibootmgr -v
df -hT / /boot/efi
swapon --show
systemctl --failed --no-pager
```

El resultado correcto debe mostrar:

- `/` con UUID `bfc8d511-db35-43d1-9cc7-bc8f2cf6481a`;
- `/boot/efi` con UUID `7596-58D3`;
- `BootCurrent` asociado a `ubuntu-ssd`;
- el SSD Kingston primero en `BootOrder`;
- el volumen PERC visible, pero sin necesidad de estar montado.

Pruebas funcionales mínimas:

```bash
curl -fsS -o /dev/null https://sensores.cmasccp.cl/
curl -fsS -o /dev/null https://api-sensores.cmasccp.cl/apidocs/
curl -fsS -o /dev/null \
  'https://api-sensores.cmasccp.cl/listarSensores?limite=1'
```

La tercera consulta obliga al API a consultar MariaDB y sirve como prueba
pequeña de aplicación más base de datos.

## Por qué el disco antiguo no se monta solo

El UUID antiguo no está en `/etc/fstab`. El montaje bajo `/media/cmas/...` que
puede verse después de hacer clic en el disco desde el escritorio es temporal y
desaparece al reiniciar. El automontaje de GNOME se orienta principalmente a
medios removibles y no garantiza el montaje de una raíz Linux interna.

Mantener el disco antiguo desmontado es la opción más segura mientras se use
como recuperación: evita modificaciones accidentales. Que no se monte solo no
es una falla del disco.

## Montar el disco antiguo temporalmente y en solo lectura

Primero confirmar su identidad:

```bash
lsblk -e7 -o NAME,PATH,SIZE,FSTYPE,LABEL,UUID,MOUNTPOINTS,MODEL
```

Luego montar por UUID, nunca por la letra del dispositivo:

```bash
sudo install -d -m 0755 /mnt/rescate-antiguo
sudo mount -o ro,nosuid,nodev \
  /dev/disk/by-uuid/cf002c64-3f49-4b66-89d3-a3bf126c1deb \
  /mnt/rescate-antiguo
findmnt /mnt/rescate-antiguo
```

Desmontar al terminar:

```bash
sudo umount /mnt/rescate-antiguo
```

No se ha configurado un montaje automático. Si más adelante se decide montar
siempre el disco en modo solo lectura, la entrada propuesta —todavía **no
aplicada**— sería:

```fstab
UUID=cf002c64-3f49-4b66-89d3-a3bf126c1deb /mnt/rescate-antiguo ext4 ro,nofail,nodev,nosuid,x-systemd.device-timeout=10 0 2
```

## Recuperar archivos individuales

Con el disco antiguo montado en solo lectura, comparar antes de copiar:

```bash
sudo rsync -aHAXn --numeric-ids \
  /mnt/rescate-antiguo/RUTA/ /RUTA/
```

Retirar `-n` solamente después de revisar la lista:

```bash
sudo rsync -aHAX --numeric-ids \
  /mnt/rescate-antiguo/RUTA/ /RUTA/
```

No se debe copiar `/var/lib/mysql` con MariaDB activo. Para recuperar una base
de datos se debe arrancar el sistema antiguo de forma aislada o usar un respaldo
lógico validado. No se mezclan archivos InnoDB entre instalaciones activas.

## Recuperación desde el menú UEFI

Orden recomendado en el administrador de arranque del firmware:

1. `ubuntu-ssd`;
2. `Kingston SSD fallback`;
3. la entrada `ubuntu` que apunta a la EFI del Kingston;
4. `ubuntu` del volumen PERC anterior.

Si el cargador principal falla, seleccionar `Kingston SSD fallback`. Si el SSD
completo falla, seleccionar la entrada `ubuntu` que apunte a la partición GPT
`95f93eca-a6c2-4322-9ab3-d8078860267e` del volumen PERC.

Desde el sistema funcional se puede solicitar **un solo** arranque por la
entrada antigua, sin cambiar el orden permanente:

```bash
sudo efibootmgr -v
sudo efibootmgr -n 0009
sudo reboot
```

El número `0009` era correcto el 3 de noviembre de 2026. Si cambian las
entradas, se debe usar el número que apunte a `\EFI\ubuntu\shimx64.efi` en la
partición GPT antigua. Para cancelar un `BootNext` antes de reiniciar:

```bash
sudo efibootmgr -N
```

## Recuperación desde la consola de GRUB

### Volver al menú del SSD

En la consola `grub>`:

```text
insmod part_gpt
insmod ext2
search --no-floppy --fs-uuid --set=root bfc8d511-db35-43d1-9cc7-bc8f2cf6481a
set prefix=($root)/boot/grub
insmod normal
normal
```

Si `normal` no carga el menú, iniciar el kernel validado manualmente:

```text
search --no-floppy --fs-uuid --set=root bfc8d511-db35-43d1-9cc7-bc8f2cf6481a
linux ($root)/boot/vmlinuz-6.8.0-138-generic root=UUID=bfc8d511-db35-43d1-9cc7-bc8f2cf6481a ro
initrd ($root)/boot/initrd.img-6.8.0-138-generic
boot
```

Si ese kernel no funciona, el kernel `6.8.0-124-generic` también estaba
instalado y validado en la configuración de GRUB.

### Cargar GRUB desde el disco antiguo

```text
insmod part_gpt
insmod ext2
search --no-floppy --fs-uuid --set=root cf002c64-3f49-4b66-89d3-a3bf126c1deb
configfile ($root)/boot/grub/grub.cfg
```

Después de arrancar hay que confirmar la raíz antes de hacer cualquier cambio:

```bash
findmnt -n -o SOURCE,UUID,LABEL /
```

## Reparar GRUB desde un medio Live

Arrancar un Ubuntu Live compatible y confirmar los discos con `lsblk`. Montar
el Kingston por UUID:

```bash
sudo mount /dev/disk/by-uuid/bfc8d511-db35-43d1-9cc7-bc8f2cf6481a /mnt
sudo mount /dev/disk/by-uuid/7596-58D3 /mnt/boot/efi
sudo mount --rbind /dev /mnt/dev
sudo mount --make-rslave /mnt/dev
sudo mount -t proc proc /mnt/proc
sudo mount --rbind /sys /mnt/sys
sudo mount --make-rslave /mnt/sys
sudo mount --rbind /run /mnt/run
sudo mount --make-rslave /mnt/run
sudo chroot /mnt
```

Dentro del `chroot`:

```bash
update-initramfs -u -k all
grub-install --target=x86_64-efi --efi-directory=/boot/efi \
  --bootloader-id=ubuntu-ssd --recheck
grub-install --target=x86_64-efi --efi-directory=/boot/efi \
  --bootloader-id=BOOT --removable --no-nvram --recheck
update-grub
efibootmgr -v
exit
```

Desmontar en orden inverso:

```bash
sudo umount -R /mnt/run
sudo umount -R /mnt/sys
sudo umount /mnt/proc
sudo umount -R /mnt/dev
sudo umount /mnt/boot/efi
sudo umount /mnt
```

No se debe ejecutar `e2fsck` sobre un filesystem montado. Desde el medio Live,
con la raíz del Kingston desmontada, la comprobación no destructiva es:

```bash
sudo e2fsck -fn \
  /dev/disk/by-uuid/bfc8d511-db35-43d1-9cc7-bc8f2cf6481a
```

## Restaurar el orden UEFI permanente

Primero inspeccionar:

```bash
sudo efibootmgr -v
```

Solo si las entradas conservan los números y destinos documentados:

```bash
sudo efibootmgr -N
sudo efibootmgr -o 0007,000B,000C,0009,0005,0008,0006,0000,0003,000A,0004
```

Si los números cambiaron, construir el orden con las entradas que apunten a:

- `\EFI\ubuntu-ssd\shimx64.efi` en PARTUUID
  `b2ad25f4-e11b-4921-a1bb-3bf9e66c63a4`;
- `\EFI\BOOT\BOOTX64.EFI` en esa misma partición;
- finalmente `\EFI\ubuntu\shimx64.efi` en la partición anterior como respaldo.

## Reversión completa al disco antiguo

El disco antiguo conserva un sistema arrancable, pero es una fotografía previa
al corte. No incluye automáticamente cambios posteriores al 2 de noviembre de
2026.

1. Arrancar una sola vez desde la entrada UEFI antigua o cargar su `grub.cfg`.
2. Confirmar que `/` usa UUID
   `cf002c64-3f49-4b66-89d3-a3bf126c1deb`.
3. No borrar ni escribir el SSD mientras se determina la causa del fallo.
4. Verificar MariaDB, PM2, Nginx, Apache, cron y los portales públicos.
5. Recuperar por separado cualquier dato nuevo que exista solamente en el SSD.

La VM `win10` y `win10.qcow2` se eliminaron intencionalmente de ambos discos el
2 de noviembre de 2026. No forman parte de la recuperación.

## Respaldos y evidencias locales protegidas

Las evidencias detalladas están protegidas en el servidor y no se copian a Git:

- `/home/cmas/backups/migracion-disco-20261030-133533/`;
- `/home/cmas/backups/eliminacion-win10-20261102-140619/`;
- `/home/cmas/backups/arranque-ssd-20261102-164524/`;
- `/home/cmas/migracion_disco/` contiene los scripts utilizados.

El último directorio de arranque contiene el estado UEFI anterior, una copia de
`fstab`, el inventario de discos y un `EFI.before.tar` para reversión.

## Límites de este respaldo

- El disco PERC no se actualiza automáticamente.
- No sustituye respaldos lógicos periódicos de MariaDB.
- No conviene mantener dos raíces montadas en escritura durante operación
  normal.
- No se debe formatear el disco antiguo hasta completar una política formal de
  respaldo, retención y restauración probada.
- Antes de cualquier comando destructivo se comparan modelo, UUID, PARTUUID y
  punto de montaje; nunca se confía solamente en `/dev/sda` o `/dev/sdb`.
