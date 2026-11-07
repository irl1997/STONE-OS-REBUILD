# Procedimiento de diagnóstico de solo lectura — AMD BC-250

Estado: **APROBADO por el propietario el 2026-11-06. Pendiente de ejecución en la BC-250.** Lo ejecuta el propietario en la consola: este Mac no tiene acceso SSH a ella.
Fecha: 2026-11-06. Script: [`stone-diag-readonly.sh`](stone-diag-readonly.sh), revisado línea por línea y con la sintaxis comprobada (`bash -n`).

## 1. Objetivo

Conocer el estado real del hardware y del software instalado antes de empezar F0, y resolver o acotar estos pendientes:

| Pendiente | Pregunta |
| --- | --- |
| P-01 | ¿Qué imagen de STONE y qué versión del regulador están instaladas? |
| P-02 | ¿Qué expone por D-Bus esa versión del regulador? |
| P-03 / P-04 | ¿Cuántos núcleos de CPU están activos? ¿Qué BIOS hay? ¿Cuántos CU están activos y cómo se activan? |
| P-05 / P-06 / P-07 | ¿Qué pantalla, conector y modos hay? |
| P-08 | ¿Qué valor tiene la propiedad `Enabled` del regulador? |
| P-09 | ¿Qué sensores dan lecturas? |
| P-11 | ¿Cómo lanza Steam los juegos (formato del `reaper`)? |
| P-12 / P-13 | ¿Hay watchdog de hardware? ¿Qué ventilador lee el sistema? |
| Nuevos | Conectividad (Bluetooth, USB, red), almacenamiento y sesión de escritorio disponibles (para CONNECT, DOWNLOADS y DESKTOP) |

## 2. Prohibido en esta sesión (y cómo lo garantiza el script)

| Prohibición | Garantía |
| --- | --- |
| Modificar BIOS o firmware | No hay `flashrom`, `fwupdmgr` ni herramientas de BIOS. Los datos de BIOS se leen de `/sys/class/dmi` y `dmidecode` (tablas SMBIOS, solo lectura). La inspección visual de la BIOS (sección 6) es opcional y sale **sin guardar** |
| Cambiar frecuencias o voltajes | No hay `busctl call`, ni métodos `Set*` del regulador, ni `stonectl calibrate`. El regulador solo se lee (`busctl introspect`) |
| Activar o desactivar núcleos o CU | No hay `stone-cu40 enable/disable/test/guard`, `rpm-ostree kargs`, ni escrituras en `/sys/devices/system/cpu` |
| Instalar o desinstalar paquetes | No hay `dnf`, `rpm-ostree install`, `flatpak install` ni `bootc switch/upgrade`. Lo que falta se anota como «no disponible» |
| Modificar servicios o configuraciones | No hay `systemctl start/stop/enable/mask`. `busctl --auto-start=no` impide que una consulta arranque un servicio. Bluetooth solo se consulta si ya está activo. No se usan los comandos de STONE que escriben (`stonectl display probe/diagnostics/goal/set-output/reset`, `stonectl safe-mode`, `restore-defaults`) |
| Pruebas de estrés | No hay vkmark, `stone-cu-verify`, `stone-game measure`, ni juegos lanzados por el script |

Lo único que se escribe es la carpeta del informe, `~/stone-diag-<fecha>/` (permisos 700). Efectos menores inevitables, ninguno de configuración:

- `sudo` deja una línea en el registro del sistema.
- `vulkaninfo` puede crear su caché de usuario.

El script no recoge números de serie, direcciones MAC ni direcciones IP.

## 3. Requisitos y forma de ejecución

1. Arranca la consola normalmente y deja Steam Game Mode abierto 2 minutos, con STONE Home en pantalla.
2. Abre una terminal sin cerrar Game Mode. Las dos opciones son:
   - por SSH desde otro equipo;
   - con una TTY: Ctrl+Alt+F3 y entrar con el usuario de la consola.

   Si usas el Modo Escritorio, la sección 11 (Steam y STONE Home) saldrá vacía, y está bien. **No reinicies para esto.**
3. Copia el script a la consola, por ejemplo con un pendrive o `scp`.
4. Ejecútalo **con el usuario de la consola, no como root**:

```bash
bash stone-diag-readonly.sh
```

5. Escribe la contraseña de `sudo` una vez. Si prefieres no darla, el script sigue y marca esas secciones como «omitido».
6. Duración aproximada: menos de 2 minutos. Ningún comando tiene más de 30 s de límite.
7. Revisa la carpeta `~/stone-diag-<fecha>/` y tráela al Mac para analizarla.

## 4. Comandos y qué información entrega cada uno

### 01 · Sistema e imagen instalada → P-01

| Comando | Qué entrega |
| --- | --- |
| `cat /usr/lib/stone-release` | Versión de STONE, canal, commit, kernel, Mesa, regulador y estado de 40 CU **de la imagen instalada** |
| `cat /etc/os-release`, `uname -r` | Versión de Bazzite y kernel en ejecución |
| `cat /proc/cmdline` | Argumentos de arranque: `amdgpu.bc250_cc_write_mode=3` (40 CU), `stone.safe=1`, `nomodeset` |
| `rpm-ostree status [--json]`, `bootc status` | Imagen arrancada, su **digest** (para compararlo con `build-metadata` de rc14–rc16 y rc23) y despliegue anterior para rollback |
| `mokutil --sb-state`, `/sys/firmware/efi` | Secure Boot (debe estar desactivado para el `amdgpu` de 40 CU) y arranque UEFI |

### 02 · CPU → P-03 (8 núcleos)

| Comando | Qué entrega |
| --- | --- |
| `lscpu` | Núcleos por socket, hilos por núcleo, CPU en línea y modelo |
| `nproc`, `/proc/cpuinfo` | CPU lógicas visibles (con 8 núcleos Zen 2 serían 16; con 6, 12) |
| `/sys/devices/system/cpu/{possible,present,online,offline}` | Si hay CPU presentes pero desactivadas por el sistema operativo |
| `core_id` únicos | Núcleos físicos activos, independiente de los hilos |
| `cpufreq` y MHz | Si existe control de frecuencia de CPU (la auditoría v1.0 dice que no: 3,5 GHz fijos) |
| `sudo dmidecode -t processor` (solo líneas de núcleos) | **Core Count** (físicos) frente a **Core Enabled** (habilitados por la BIOS): muestra si el desbloqueo viene del firmware |

### 03 · Firmware y memoria → P-03, P-04

| Comando | Qué entrega |
| --- | --- |
| `/sys/class/dmi/id/bios_*`, `board_*` | Fabricante, versión y fecha de la BIOS instalada (para saber si es P3.00 CHIPSETMENU u otra, como MeiMeiDXE) |
| `sudo dmidecode -t bios` (sin serie ni UUID) | Lo mismo con las características de la BIOS |
| `sudo dmidecode -t memory`, `free -h`, `meminfo` | Memoria total y la vista por el sistema |
| `mem_info_vram_total`, `gtt_total` | Reserva de VRAM (UMA) realmente aplicada (FIRMWARE.md pide 512 MB) |

### 04 · GPU y unidades de cálculo → P-01, P-03

| Comando | Qué entrega |
| --- | --- |
| `lspci -nn`, `lspci -nnk` | ID PCI de la GPU (esperado `1002:13fe`) y driver en uso |
| `/sys/module/amdgpu/parameters/bc250_cc_write_mode` | Si este arranque usa el desbloqueo de 40 CU (2 o 3) o no (0 o ausente) |
| `modinfo amdgpu` | Si el módulo instalado es el de STONE (con `bc250_cc_write_mode`) o el de Bazzite, y su `vermagic` |
| `stone-cu40 status` y `sudo stone-cu40 status` | Estado guardado de 40 CU, CU contados por el driver, última prueba y techo con 40 CU |
| `journalctl -k -b` (filtrado) | Mensajes del driver: CU activos, firmware, errores de este arranque |
| `journalctl -k -b -1` (errores) | Fallos de GPU del arranque anterior |
| `pp_dpm_sclk`, `gpu_busy_percent`, `gpu_metrics` (bytes 0x1c) | Comprobar otra vez si estas lecturas siguen sin ser fiables (P-09) |
| `vulkaninfo --summary` | Dispositivo Vulkan (RADV GFX1013, nunca llvmpipe) y versión de Mesa |

### 05 · Regulador de GPU → P-01, P-02, P-08

| Comando | Qué entrega |
| --- | --- |
| `rpm -q cyan-skillfish-governor-smu` | **Versión exacta instalada** (v0.4.14 o v0.4.15) |
| `systemctl status …` | Si el servicio está activo |
| `cat /etc/cyan-skillfish-governor-smu/config.toml` | Configuración real: D-Bus activado, curva de voltaje, umbrales |
| `busctl introspect` del objeto principal y de `Range/Current`, `Range/Allowed`, `Range/Initial` | Métodos y propiedades que expone esta versión, con sus **valores actuales**, incluida `Enabled` (P-08). Es la base de la prueba de contrato de R-03 |
| `journalctl -u cyan-skillfish-governor-smu -b` | Mensajes del regulador en este arranque |

### 06 · Servicios y estado de STONE

| Comando | Qué entrega |
| --- | --- |
| `systemctl status` / `is-enabled` de `stoned`, `stoned-recover`, `stone-cu40-guard` y de las unidades de usuario | Qué servicios corren y cuáles están habilitados |
| `stonectl status`, `stonectl --json status` | Perfil elegido y aplicado, estado real del regulador, Safe Mode, contador de fallos, ranuras |
| `stonectl calibration` | Rango, máximo validado (¿1900 MHz?), último resultado, paso del cuelgue (2000 MHz) |
| `sudo ls/cat /var/lib/stone/...` | Estado completo de `stoned` (calibración ligada a la configuración, marcas) y el final del registro de carga |
| `journalctl -u stoned -u stoned-recover -b` y `-b -1` | Lo que decidió la recuperación en este arranque y en el anterior |
| `50-stone.rules`, `systemd-analyze security stoned` | Regla polkit instalada y nivel de aislamiento real |

### 07 · Reposo

| Comando | Qué entrega |
| --- | --- |
| `systemctl is-enabled sleep.target …` | Que los cinco targets de suspensión estén `masked` |
| `50-stone-no-sleep.conf` | Bloqueo de reposo de systemd presente |

### 08 · Sensores, ventilador y watchdog → P-09, P-12, P-13

| Comando | Qué entrega |
| --- | --- |
| Recorrido de `/sys/class/hwmon/*` | Cada sensor con su nombre (`amdgpu`, `k10temp`, `nct6683`, `nvme`…) y su lectura actual: temperaturas, ventiladores (`fan2`), potencia y voltajes. Solo lectura |
| `sensors` (si está instalado) | Lo mismo con etiquetas. **No** se ejecuta `sensors-detect`, porque carga módulos |
| `/dev/watchdog*`, `/sys/class/watchdog`, `lsmod` | Si existe un watchdog de hardware (`sp5100_tco`), sin activarlo |

### 09 · Pantalla y conexión de vídeo → P-05, P-06, P-07

| Comando | Qué entrega |
| --- | --- |
| `/sys/class/drm/card*-*/{status,enabled,modes}` | Conector en uso (DP-1, HDMI-A-1…) y modos que el kernel acepta en ese enlace. El primero es el preferido de la pantalla |
| `stonectl display --json` / `stonectl display` | Modelo de STONE DISPLAY: nombre y fabricante de la pantalla (EDID, **sin número de serie**), nativa, salida actual, VRR/HDR y presupuesto del enlace. Lee Steam por su interfaz local; no escribe nada |

### 10 · Almacenamiento y conectividad (CONNECT, DOWNLOADS)

| Comando | Qué entrega |
| --- | --- |
| `lsblk` (sin columna de serie), `df -h` | Discos, tamaño, modelo, conexión (NVMe, SATA, USB) y espacio libre |
| `nmcli device` (sin MAC ni IP) | Interfaces de red y su estado (Ethernet, Wi-Fi si existe) |
| `lsusb` | Dispositivos USB: adaptadores Bluetooth o Wi-Fi, mandos, hubs |
| `rfkill list` | Radios presentes y si están bloqueadas |
| `systemctl is-active bluetooth` + `busctl tree org.bluez` (solo si ya está activo) | Si hay un adaptador Bluetooth y lo ve BlueZ |
| `/proc/bus/input/devices`, `/dev/input/by-id` | Mandos y otros dispositivos de entrada conectados |

### 11 · Steam, STONE Home y Game Mode → P-11, P-16

| Comando | Qué entrega |
| --- | --- |
| `stone-home-session status` / `diag` | Acceso directo registrado, identificadores de Steam, vídeo de arranque, tiempos de apertura, registro de STONE Home |
| `ps -eo … \| grep gamescope\|steamwebhelper\|SteamLaunch\|stone-home\|chromium` | Procesos de la sesión. Si hay un juego abierto (opcional, abierto a mano antes), muestra el formato real `reaper SteamLaunch AppId=` (P-11) |
| `systemctl --user list-units gamescope-session-plus@*` | Variante de sesión de Game Mode (`@ogui-steam` u otra) |
| Preferencias y estado de usuario de STONE | Motor elegido (Chromium o WebKit), `home.env`, si se aplicó `set-output` experimental, componentes descargados (OptiScaler, HelixSR) |

### 12 · Software instalado

| Comando | Qué entrega |
| --- | --- |
| `rpm -q chromium webkitgtk6.0 gtk4 vkmark mangohud …` | Versiones reales de los dos motores, de las cargas de prueba y de MangoHud (para R-02 y P-10) |
| `flatpak list --user` | Emuladores u otras apps instaladas por el usuario |
| Sesiones en `/usr/share/wayland-sessions`, `steamos-session-select` | Qué sesión de escritorio existe y cómo se cambia (para STONE DESKTOP) |
| `plymouth-set-default-theme` (sin argumentos) | Tema de arranque activo (`stone`); sin argumentos solo lo muestra |

Al final, `SUMMARY.txt` reúne en una pantalla: versión, regulador, imagen arrancada, CPU, 40 CU, BIOS, GPU y conectores.

## 5. Datos físicos a registrar a mano (sin herramientas)

| Dato | Cómo |
| --- | --- |
| Televisor o monitor: marca, modelo, puerto usado | Etiqueta trasera o menú del televisor |
| Adaptador DP→HDMI: marca, modelo, si es activo o pasivo y qué promete («4K60», «HDMI 2.0») | Etiqueta o caja |
| Cable HDMI: certificación (High Speed / Premium / Ultra) | Etiqueta |
| Adaptador Bluetooth USB (si hay) | Modelo |
| Mandos usados | Modelo |
| Refrigeración (disipador original, ventilador de la caja y su conexión: J4003 u otra controladora) | Inspección visual |
| Fuente de alimentación: modelo y potencia | Etiqueta |
| Temperatura ambiente durante el diagnóstico | Termómetro, aproximado |

## 6. Inspección de la BIOS (opcional, solo mirar)

Solo si se quiere ver la configuración de la BIOS que el sistema no expone (UMA, IOMMU, curva del ventilador, opciones de núcleos):

1. Al encender, pulsa **Supr** para entrar en la BIOS.
2. **No cambies ningún valor.** Fotografía estas pantallas:
   - Chipset → GFX Configuration;
   - Advanced → CPU Configuration (núcleos, SMT);
   - la configuración del ventilador;
   - Boot.
3. Sal con **Exit → Discard Changes and Exit** (o Esc → «No» a guardar). **Nunca F10.**

Riesgo: cambiar algo por error. Si no te sientes seguro, sáltate este paso: la sección 03 del script ya da la versión de la BIOS.

## 7. Qué hacer con los resultados

1. Trae `~/stone-diag-<fecha>/` y las fotos al Mac, por ejemplo a `02_AUDIT/diagnostico-<fecha>/`.
2. Se analizan y se actualiza cada P-xx del documento de decisiones con estado y evidencia. Lo que se vea se marca `OBSERVED ON BOARD`, nunca `HARDWARE VERIFIED` (D-08).
3. **Si los 8 núcleos están activos:** se documenta el método existente (versión de BIOS, Core Count frente a Core Enabled) y no se toca nada.
4. **Si no lo están:** se registra el estado y P-04 sigue abierto, para decidirlo más adelante. En esta etapa no se modifica la BIOS.
