# STONE MACHINE — Especificación de arquitectura integral de STONE OS

Versión: 1.1 (borrador para aprobación) · Fecha: 2026-11-06 · Resuelve P-14 a nivel documental.
Plataforma única: AMD BC-250 (D-01). Este documento describe el **producto final**. Las fases F0–F9 son etapas de construcción, no recortes del alcance.

## Cómo leer este documento

Cada afirmación lleva su grado de certeza:

| Marca | Significado |
| --- | --- |
| **[C]** | Confirmado: decisión del propietario (D-xx en `DECISIONES_TECNICAS.md`), recomendación aprobada (R-xx) o comportamiento ya existente en rc23 |
| **[P]** | Propuesta técnica: falta información o decisión; se aplica sólo si se aprueba |
| **[V]** | Pendiente de verificación física en la BC-250 (P-xx) o de documentación |

Las especificaciones de diseño originales del proyecto no están disponibles (H-11). Todo lo que rc23 no implementa y el propietario no definió se presenta como **[P]**, y su vacío aparece en la sección 6.

---

## 1. Principios de arquitectura

| # | Principio | Grado |
| --- | --- | --- |
| A1 | **ACTUAL STATE > REQUESTED STATE**: la interfaz muestra lo que se lee de vuelta, nunca lo que se pidió | [C] |
| A2 | Nada que no haya pasado su prueba se aplica al arrancar; todo cambio de rendimiento es reversible y tiene última configuración buena | [C] |
| A3 | Una sola plataforma (BC-250); en cualquier otro equipo, cada función de hardware queda «no disponible», nunca simulada | [C] D-01 |
| A4 | El rendimiento de la GPU se cambia **sólo** a través del regulador. STONE no toca voltaje, ventilador, memoria ni límites de potencia, ni desactiva protecciones | [C] |
| A5 | Configuración de referencia: **8 núcleos y 40 CU** (D-16). STONE no desbloquea nada ni propone cambios de BIOS o firmware (D-17). Overclock y cambios de frecuencia: sólo a mano, con verificación, guardia de arranque y vuelta atrás; lo automático sólo puede **reducir o desactivar** | [C] D-04, D-16, D-17 |
| A12 | Ninguna frecuencia máxima, voltaje ni límite térmico es una constante de STONE: se leen del regulador, salen de la calibración o se toman de documentación citada y se revalidan | [C] D-18 |
| A6 | Steam sigue siendo el motor de la sesión, lanzador y red de seguridad: si STONE falla, la consola sigue usable con la interfaz de Steam | [C] |
| A7 | Mínimo privilegio: la interfaz nunca es root; `stoned` no es root; cada privilegio extra va en un ayudante de un solo propósito | [C] |
| A8 | Contratos de API versionados, únicos para producción, simulador y pruebas | [C] R-07 |
| A9 | La consola es un sistema atómico (bootc): todo se instala en la imagen; el estado del usuario vive en `/var` y `$HOME` | [C] |
| A10 | Un juego en primer plano tiene prioridad: STONE se duerme mientras se juega | [C] |
| A11 | Cuatro estados de madurez: `CODE TESTED` → `READY FOR HARDWARE TEST` → `OBSERVED ON BOARD` → `HARDWARE VERIFIED` | [C] D-08 |

---

## 2. Vista general

```
┌──────────────────────────────── STONE HOME (UI, usuario de la consola) ────────────────────────────────┐
│ Inicio · Biblioteca · Ficha · Menú rápido · Ajustes · Performance Center · Descargas · Conectar · ... │
└───────────────▲─────────────────────────────── HTTP local con token / SSE ─────────────────────────────┘
                │  contrato stone-home.v1 (api/)
┌───────────────┴────────────── STONE HOME HOST (Python, usuario de la consola) ──────────────────────────┐
│ módulos de usuario: STEAM BRIDGE · DISPLAY · GRAPHICS · OPTIMIZED · DOWNLOADS · EMULATION · CONNECT ·   │
│ DESKTOP (lanzador) · SETTINGS                                                                          │
└──────▲───────────────────────▲──────────────────────────────▲──────────────────────────────▲───────────┘
       │ D-Bus sistema         │ CEF local (adaptador)        │ D-Bus (BlueZ, NM, logind)    │ Flatpak / Steam
       │ stone-performance.v1  │                              │                              │
┌──────┴─────────────── STONED (usuario `stoned`, systemd aislado) ───────────────┐   Steam · Gamescope
│ PERFORMANCE · CALIBRATION · RECOVERY/SAFE MODE · TELEMETRY · THERMAL · GAMES    │
└──────▲──────────────────────────────────────────────────────────────────────────┘
       │ D-Bus del regulador · sysfs/hwmon (lectura) · /proc
cyan-skillfish-governor-smu · amdgpu (24/40 CU) · k10temp · nct6683 · logind · BlueZ · NetworkManager
       │
PLATFORM (Bazzite bootc) · BOOT ENGINE (Plymouth, recover, autoarranque) · AMD BC-250 (BIOS P3.00)
```

### 2.1 Mapa de módulos

| ID | Módulo | Capa | Proceso | Estado en rc23 |
| --- | --- | --- | --- | --- |
| M01 | STONE PLATFORM (imagen, actualizaciones) | Sistema | build / bootc | Existe |
| M02 | STONE BOOT ENGINE | Sistema + usuario | systemd, Plymouth | Parcial |
| M03 | STONED (servicio de sistema) | Sistema | `stoned` | Existe |
| M04 | STONE PERFORMANCE (perfiles, TUNING, CALIBRATION, 40 CU) | Sistema | dentro de `stoned` + `stone-cu40` | Existe |
| M05 | STONE RECOVERY & SAFE MODE | Sistema | `stoned-recover`, `stoned`, guardia 40 CU | Existe |
| M06 | STONE TELEMETRY & THERMAL | Sistema | dentro de `stoned` | Existe (fuentes [V]) |
| M07 | STONE HOME | Usuario | host + Chromium | Existe |
| M08 | STONE STEAM BRIDGE | Usuario | dentro del host | Existe (disperso) |
| M09 | STONE DISPLAY | Usuario | dentro del host | Existe |
| M10 | STONE GRAPHICS | Usuario | dentro del host | Parcial |
| M11 | STONE OPTIMIZED + STONE GAME PROFILE | Usuario | dentro del host + `stone-game` | Existe (sin mediciones) |
| M12 | STONE CONNECT (Bluetooth y mandos) | Usuario (+ sistema) | host | Nuevo |
| M13 | STONE DOWNLOADS (instalación y desinstalación) | Usuario | host | Parcial |
| M14 | STONE EMULATION | Usuario | host | Parcial |
| M15 | STONE DESKTOP | Usuario + sesión | host + SDDM | Nuevo |
| M16 | STONE SETTINGS (audio, red, sistema, accesibilidad) [P] | Usuario | host | Parcial (vía Steam) |
| X1 | STONE SECURITY (transversal) | Todas | — | Existe |
| X2 | STONE API CONTRACTS (transversal) | Todas | — | Nuevo (R-07) |
| X3 | STONE DEV & TEST (simulador, contenedor, CI, validación) | Fuera de la imagen | — | Existe (a migrar) |

M16 es una propuesta. Hoy los ajustes de audio, red y sistema los da Steam, y no hay un módulo definido para ellos (vacío V-08).

### 2.2 Catálogo de interfaces

| Interfaz | Tipo | Productor → consumidor | Estado |
| --- | --- | --- | --- |
| `org.stonemachine.Performance1` (`/org/stonemachine/Performance1`) | D-Bus de sistema + polkit | `stoned` → host, `stonectl`, `stone-game` | [C] existe (20 métodos, 4 señales) |
| `stone-home.v1` | Tabla de métodos sobre HTTP 127.0.0.1 con ruta secreta + SSE | host → UI | [C] existe (35 métodos); se formaliza en `api/` [C] R-07 |
| `com.cyanskillfish.Governor` | D-Bus de sistema | regulador → `stoned` (sólo `stoned`) | [C]; versión [V] P-01/P-02 |
| Adaptador Steam (CEF 127.0.0.1:8080, `steam://`, VDF) | Local | Steam → STEAM BRIDGE | [C] existe; se aísla [C] R-06 |
| `org.freedesktop.login1` | D-Bus | logind → host (apagar/reiniciar) | [C] |
| `org.bluez` | D-Bus de sistema | BlueZ → CONNECT | [P] |
| `org.freedesktop.NetworkManager` | D-Bus de sistema | NM → SETTINGS | [P] |
| Flatpak (`flatpak --user`, o libflatpak) | Proceso / biblioteca | Flathub → EMULATION, DOWNLOADS | [C] existe (catálogo fijo) |
| `stone-release` / `build-metadata.json` | Archivo | PLATFORM → todos | [C] |
| Base de perfiles de juego (`/usr/share/stone/game-profiles`, `~/.local/share/stone/game-profiles`) | Archivos JSON con esquema | OPTIMIZED | [C] |

### 2.3 Estado persistente

| Ubicación | Dueño | Módulos |
| --- | --- | --- |
| `/var/lib/stone/` (0700) | `stoned` | PERFORMANCE, RECOVERY, CALIBRATION |
| `/var/lib/stone-cu40/` | root | 40 CU |
| `~/.config/stone/` | usuario | HOME (prefs), DISPLAY |
| `~/.local/state/stone/` | usuario | HOME (logs, IDs Steam), GRAPHICS (opciones de lanzamiento guardadas), OPTIMIZED (métricas) |
| `~/.local/share/stone/` | usuario | OPTIMIZED (perfiles auto/user), DOWNLOADS (componentes) |
| `/usr/...` | imagen | Todo lo de sólo lectura |

---

## 3. Especificación por módulo

Formato común: **Objetivo y funcionalidades · Responsabilidades · Dependencias · Interfaces · Integración con STONE HOME · Relación con STONED · Requisitos HW/SW · Fases · Aceptación y pruebas.**
Los números de prueba (§n) remiten a `HARDWARE_VALIDATION.md` de rc23. Los identificadores `T-<MOD>-nn` son pruebas nuevas **[P]**.

### M01 · STONE PLATFORM

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | Imagen del sistema: Bazzite `bazzite-deck` (Fedora 44) con la capa STONE [C]; base fijada por digest [C]; procedencia en `stone-release` y `build-metadata.json` [C]; sin reposo [C]; Handheld Daemon enmascarado [C]; comprobación de kernel [C]; actualizaciones atómicas por canal (`rc`, `dev`, después `beta`/`stable`) con rollback [C]; ISO instalable [C]; firma cosign obligatoria [C] R-09 |
| Responsabilidades | Construir de forma reproducible; fallar el build antes que producir una imagen sin una capa crítica; registrar las versiones exactas (kernel, Mesa, Gamescope, regulador, Chromium, WebKitGTK, 40 CU) |
| Dependencias | Bazzite, Fedora 44, COPR `filippor/bazzite` (sólo en build), OpenGamingCollective/linux (40 CU), bootc-image-builder, GitHub Actions/GHCR |
| Interfaces | `Containerfile` + `build.sh`; `/usr/lib/stone-release` (clave=valor); `build-metadata.json`; canal bootc |
| Integración con STONE HOME | Ajustes → Sistema / Acerca de / Actualizaciones lee `stone-release` y `rpm-ostree status --json` [C]; aplicar una actualización pasa por Steam/bootc [C]; un botón propio de STONE para actualizar es [P] |
| Relación con STONED | La imagen instala y habilita `stoned`; la calibración queda ligada a la configuración (kernel, amdgpu, regulador): un cambio de imagen la marca como `stale` [C] |
| Requisitos HW/SW | BC-250 con BIOS P3.00 y UEFI [C]; Secure Boot desactivado si se usa el `amdgpu` de 40 CU (sin firmar) [C] ([V] estado actual P-03); disco [V] (modelo y tamaño a registrar en el diagnóstico) |
| Fases | F0 |
| Aceptación y pruebas | Software: `validate.sh`, build + `bootc container lint`, ISO, checksums [C]. Placa: §0, §1, §14, §16, §21, §22. Además: `stone-release` coincide con `build-metadata.json` de la release instalada (T-PLAT-01 [P]) |

### M02 · STONE BOOT ENGINE

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | Encendido de consola continuo e ininterrumpido: Plymouth STONE (THE LINE) → vídeo de arranque de STONE en lugar del de Steam → STONE Home sobre la misma línea [C]; decisión de recuperación antes de la sesión [C] (detalle en M05); registro del acceso directo y autoarranque confirmado de STONE Home [C]; tiempos de arranque medidos y registrados [C]; opción de arranque de mantenimiento `stone.safe=1` [C]. **[P]:** menú de arranque de STONE accesible desde el mando (Safe Mode, versión anterior, escritorio); presupuesto de tiempo de arranque como criterio |
| Responsabilidades | Que la consola nunca quede en un estado sin salida: si STONE Home no abre, Steam Game Mode queda usable [C] |
| Dependencias | Plymouth + `plymouth-plugin-script`, dracut, SDDM, `gamescope-session-plus@`, Steam, M05, M07, M08 |
| Interfaces | Tema `/usr/share/plymouth/themes/stone`; `stone-home-register.service` y `stone-home-autostart.service` (usuario); drop-in de `gamescope-session-plus@.service.d`; `stone-home-session register|launch|status|diag` |
| Integración con STONE HOME | El vídeo termina en el primer fotograma de Home [C]; Home llama a `HomeReady` cuando está en pantalla [C] |
| Relación con STONED | `stoned-recover` decide antes de `display-manager.service` [C]; `HomeReady` habilita la aplicación del perfil guardado [C] |
| Requisitos HW/SW | GPU con salida activa durante el initramfs [V] (pantalla negra de 30–60 s reportada por la comunidad, sin medir en STONE); Steam Game Mode de Bazzite 44 |
| Fases | F0 (Plymouth, recover, sin reposo); F2 (registro, vídeo, autoarranque); F9+ (menú de arranque con mando [P]) |
| Aceptación y pruebas | Software: K02–K07 (`test_home.py`), R01–R12 (`run_tests.py`). Placa: §1 (×5), §16, §23. T-BOOT-01 [P]: tiempo desde encendido hasta Home registrado en 5 arranques, sin la pantalla de Steam visible durante más de N s (N a fijar con la medición) |

### M03 · STONED (STONE System Service)

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | Única pieza que habla con el hardware de rendimiento. Aloja M04, M05 y M06 [C] |
| Responsabilidades | Validar toda entrada (tipo, rango, `Range/Allowed`, Safe Mode, prueba en curso, estado térmico) [C]; aplicar y leer de vuelta, con rollback [C]; persistir estado de forma atómica en `/var/lib/stone` [C]; detectar partidas de Steam por `/proc` (`reaper SteamLaunch AppId=`) [C] ([V] P-11); emitir señales sólo como dueño del nombre [C] |
| Dependencias | `python3-gobject` (Gio/GLib), D-Bus de sistema, polkit, systemd (notify, watchdog), regulador, sysfs/hwmon, journal del kernel, vkmark, `stone-cu-verify` |
| Interfaces | `org.stonemachine.Performance1`: GetCapabilities, GetState, GetMetrics, Subscribe/Unsubscribe, HomeReady, SetProfile, SetSessionProfile, StartTest, CancelTest, MeasureBaseline, Save/DiscardTestResult, GetCalibration, Start/CancelCalibration, RestoreDefaults, Enter/ExitSafeMode, SetGameProfile; señales StateChanged, TestFinished, Metrics, ThermalEvent; 11 códigos de error [C]. Se versiona como `stone-performance.v1` [C] R-07. CLI `stonectl` [C] |
| Integración con STONE HOME | Por `bridge.py` (tipos fijos) [C]; Home no habla nunca con el regulador [C] |
| Relación con STONED | — (es STONED) |
| Requisitos HW/SW | Usuario `stoned` (grupos `render`, `systemd-journal`); aislamiento systemd (ProtectSystem=strict, PrivateNetwork, DevicePolicy closed + char-drm, UMask 0077) [C]; polkit acotado al usuario de la consola [C] R-09 |
| Fases | F1 |
| Aceptación y pruebas | Software: `run_tests.py` (88), prueba de contrato del regulador [C] R-03, `systemd-analyze security` ≤ 3.6. Placa: §0, §2, §3, §5, §9 |

### M04 · STONE PERFORMANCE (perfiles, TUNING, CALIBRATION, 40 CU, controlador)

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | Gestión de frecuencias de GPU dentro del rango del regulador [C]: SILENT / BALANCED (predeterminado) / PERFORMANCE / CUSTOM c1–c3 [C]; STONE TUNING (probar → guardar → usar provisional → validar con STANDARD + partida limpia) [C]; STONE TESTING quick/standard/extended + BEFORE/AFTER [C]; STONE CALIBRATION por consola y configuración [C] R-04; perfil por juego y de sesión [C]; controlador dinámico del techo (calor; objetivo de cuadros cuando exista fuente) [C].

**Configuración de referencia: 8 núcleos y 40 CU** [C] D-16:
- Los perfiles de fábrica, la calibración y los rangos se calculan **para 40 CU**. El caso de 24 CU sólo existe como estado degradado: guardia de arranque activada o módulo ausente. Se muestra como tal.
- `stoned` informa la **configuración detectada**: CU activos, núcleos e hilos en línea. Si no coincide con la referencia, se avisa en Home y se aplican sólo valores de fábrica del regulador, sin CUSTOM [P].
- **CPU de 8 núcleos:** STONE la detecta, la muestra (uso total y por núcleo, temperatura Tctl) y la incluye en la huella de configuración de la calibración. **No ajusta frecuencia ni voltaje de la CPU** [C] A4; la auditoría v1.0 documenta que no hay interfaz `cpufreq`.
- **40 CU:** se conserva el mecanismo de rc23 (`amdgpu` con `bc250_cc_write_mode`, `stone-cu40`, guardia) [C] D-17. No hay investigación nueva sobre desbloqueos.

**Valores numéricos** [C] D-18:
- Ningún límite es propio de STONE. Los rangos y umbrales se leen del regulador (`Range/Allowed`, `Range/Initial`, umbrales de temperatura).
- Los techos salen de la calibración de esta consola.
- Las cifras de rc23 se tratan como datos observados, no como límites: 1950 aprobados, cuelgue en el paso de 2000 y 1900 validado en rc15; 85 °C de fábrica del regulador; umbrales de vigilancia de la documentación comunitaria.
- Todo valor se revalida en la placa. |
| Responsabilidades | No superar nunca el máximo validado de esta consola [C]; no repetir un paso de calibración donde la placa se colgó, mientras siga la misma configuración [C] R-04; nunca subir un umbral térmico por encima del valor de fábrica que informa el regulador ni enviar 0,0 [C] |
| Dependencias | Regulador v0.4.14 candidata [C] R-03 ([V] P-01/P-02); `amdgpu` con opción 40 CU [C]; `stone-cu-verify`, vkmark [C]; M05, M06 |
| Interfaces | Métodos de `stoned` (M03); `stonectl calibrate|calibration`; `stone-cu40 status|enable|test|disable|guard` |
| Integración con STONE HOME | Performance Center, STONE TUNING, menú rápido (perfil de sesión), ficha del juego (perfil por juego), Ajustes → Rendimiento (configuración detectada frente a la de referencia: 8 núcleos y 40 CU; calibración) [C]. Arrancar la calibración desde Home es [P] (hoy sólo desde la terminal) |
| Relación con STONED | Implementado dentro de `stoned`; `stone-cu40` es un ayudante root separado que sólo cambia argumentos del kernel [C] |
| Requisitos HW/SW | 8 núcleos y 40 CU [C] D-16 (comprobación física diferida [V]); GPU Cyan Skillfish `1002:13fe` [V] P-01; disipación y alimentación según FIRMWARE.md. Condición térmica para iniciar la calibración: la de rc23 (GPU < 70 °C) se conserva como valor heredado, a revalidar [V] D-18 |
| Fases | F0 (módulo 40 CU y guardia en la imagen, para no perder la configuración actual); F1 (perfiles, configuración detectada, techo seguro); F3 (TUNING, CALIBRATION, gestión de 40 CU desde STONE) |
| Aceptación y pruebas | Software: P01–P19, I, C, G, T de `run_tests.py`; `test_cu40.py`; T-PERF-01 [P]: con una configuración detectada distinta de 8 núcleos y 40 CU, CUSTOM y la calibración quedan desactivados con su motivo. Placa: §5, §6, §7, §8, §18, §25, §28 (incluye P-15). Criterio: el valor que muestra la UI es igual al que lee `busctl introspect` del regulador en cada cambio |

### M05 · STONE RECOVERY & SAFE MODE

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | Última configuración buena (LKG), marcas en disco (prueba, provisional, calibración, arranque, apagado limpio), contador de fallos, Safe Mode (automático, manual, `stonectl`, `stone.safe=1`), RESTORE DEFAULTS, guardia de 40 CU, atribución de un cuelgue al paso de calibración en curso [C] |
| Responsabilidades | Decidir al arrancar sin tocar el hardware [C]; tras cualquier cuelgue o corte, la consola vuelve sola a fábrica (BALANCED) por diseño del regulador [C] |
| Dependencias | systemd (`stoned-recover` oneshot con ExecStop), `/var/lib/stone`, línea de arranque del kernel, M04 |
| Interfaces | `stoned --recover`, `stoned --mark-clean`, `/var/lib/stone/flags`, métodos Safe Mode/RestoreDefaults, `stone-cu40 guard` |
| Integración con STONE HOME | Cabecera «SAFE MODE», diálogo RESTAURAR / SEGUIR, motivo (`failures`, `kernel`, `manual`) [C] |
| Relación con STONED | Parte de `stoned` [C] |
| Requisitos HW/SW | Watchdog de hardware `sp5100_tco` [V] P-12 (sólo se usa si se verifica) |
| Fases | F1 |
| Aceptación y pruebas | Software: R01–R12, S01–S07, P05/P06/P17–P19. Placa: §9, §10, §11, §12, §15. **Evidencia existente:** recuperación real tras cuelgue a 2000 MHz (rc15) [C] (`OBSERVED ON BOARD`) |

### M06 · STONE TELEMETRY & THERMAL

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | Lecturas reales por suscripción (0 lecturas sin suscriptores) [C]; vigilancia térmica de fondo cada 5 s que sólo baja rendimiento [C]; detección de ventilador parado [C]; fiabilidad declarada por sensor [C] R-05 |
| Responsabilidades | Nunca inventar un valor: sensor ausente o no fiable = «—» [C] |
| Dependencias | amdgpu hwmon (edge, power1_average), k10temp, nct6683/nct6687 (`fan2`), `gpu_metrics` (con `fix-metrics` del regulador [V] P-09), `/proc/stat`, `/proc/meminfo`, `mem_info_*` |
| Interfaces | `GetMetrics`, `Subscribe(context)`, señal `Metrics`, `ThermalEvent` [C]; perfil de placa `hardware/bc250.yaml` con fuentes válidas [C] R-05 |
| Integración con STONE HOME | Performance Center (1 s), modo técnico (0,5 s), menú rápido [C] |
| Relación con STONED | Parte de `stoned` [C] |
| Requisitos HW/SW | Frecuencia real de GPU: hoy no hay fuente fiable (`pp_dpm_sclk` falso, el regulador no la publica) [C] H-07 → «velocidad real» de `stone-cu-verify` en calibración [C] R-05 |
| Fases | F1 (lecturas y térmico); F3 (Performance Center completo) |
| Aceptación y pruebas | Software: T01–T09. Placa: §0 (sensores), §2, §7, §13; T-TEL-01 [P]: cada sensor declarado «fiable» coincide con una referencia independiente (`sensors`, cuando exista) |

### M07 · STONE HOME

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | La interfaz de consola, entera con mando [C]: Inicio (recientes), Biblioteca (instalados, no instalados, accesos directos), Ficha de juego (JUGAR/INSTALAR/REANUDAR, perfil, imagen), Menú rápido, Ajustes, Performance Center, STONE TUNING, Energía (apagar, reiniciar, apagar tras inactividad), sonido, THE LINE y STONE MOTION, sueño mientras se juega [C]. **[P]:** búsqueda en biblioteca; pantallas de Descargas, Conectar, Emulación y Escritorio (de M12–M15); notificaciones |
| Responsabilidades | Mostrar el estado real de cada módulo; no ejecutar comandos, rutas ni URLs elegidas por la página [C]; dormir con un juego en primer plano [C] |
| Dependencias | Chromium del sistema (motor objetivo único) [C] R-02; WebKitGTK 6 + GTK 4 como respaldo hasta cumplir R-02 [C] D-06; Python 3 + PyGObject; fuentes OFL incluidas |
| Interfaces | `stone-home.v1` (host ↔ UI) [C] R-07; transporte HTTP 127.0.0.1 con ruta secreta por arranque, comprobación de Host/Origin, SSE [C] |
| Integración con STONE HOME | — (es STONE HOME). Cada módulo M08–M16 se presenta como sección o pantalla de Home |
| Relación con STONED | Cliente de `org.stonemachine.Performance1` por `bridge.py`; llama a `HomeReady` [C]; `stoned` lo excluye de la detección de juegos [C] |
| Requisitos HW/SW | Dibujo por GPU a la resolución de la ventana (diseño a 1920×1080, escala hasta 4K) [C]; consumo de memoria y CPU [V] P-10; mando dentro de Home [V] P-16 |
| Fases | F2 (Home mínimo: biblioteca, JUGAR, vuelta, energía); F3 (Performance Center); después, cada módulo añade su pantalla |
| Aceptación y pruebas | Software: `test_home.py`, `test_server.py`, `chromium_selftest.py`, e2e Playwright, ESLint, regresión del diseño [C] R-08. Placa: §17, §19, §20, §26 |

### M08 · STONE STEAM BRIDGE

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | Integración con Steam en un único adaptador [C] R-06: biblioteca desde VDF/ACF/`localconfig.vdf`/`shortcuts.vdf` [C]; juegos no instalados desde la interfaz de Steam [C]; lanzar (`SteamClient.Apps.RunGame`, respaldo `steam://`) [C]; acceso directo «STONE» e identificadores [C]; abrir secciones de ajustes de Steam [C]; catálogo de ajustes Get/Set descubiertos (sólo sí/no) [C]; opciones de lanzamiento por juego (para M10/M11) [C]; detección de capacidades de la Steam instalada [C] R-06 |
| Responsabilidades | Aislar las APIs internas de Steam: ningún otro módulo llama a `SteamClient.*` [C]; modo degradado cuando una función no existe [C]; nunca escribir `shortcuts.vdf` con Steam abierto [C] |
| Dependencias | Steam (se actualiza solo), puerto CEF `127.0.0.1:8080` con `.cef-enable-remote-debugging` [C] (riesgo N-05, revisión [C] R-06) |
| Interfaces | API interna de Python con capacidades (`capabilities()`, `library()`, `launch()`, `install()`, `settings()`, `launch_options()`); se expone a la UI por `stone-home.v1` |
| Integración con STONE HOME | Biblioteca, ficha, JUGAR/INSTALAR, Ajustes → Steam [C] |
| Relación con STONED | Ninguna directa: `stoned` detecta las partidas por `/proc`, no por el bridge [C] |
| Requisitos HW/SW | Steam Game Mode de Bazzite; formato del `reaper` [V] P-11 |
| Fases | F2 (biblioteca, lanzar, acceso directo); F4–F5 (opciones de lanzamiento); F6+ (ajustes) |
| Aceptación y pruebas | Software: `test_home.py` L, K, H; pruebas de contrato con grabaciones de la Steam real [C] R-06. Placa: §4, §17, §23. T-STEAM-01 [P]: con el adaptador CEF desactivado, JUGAR y la biblioteca de instalados siguen funcionando |

### M09 · STONE DISPLAY

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | Detectar pantalla y enlace (EDID, DRM, Steam DisplayManager, Xwayland) [C]; cinco resoluciones separadas (nativa, salida, juegos, interna, final) [C]; presupuesto del enlace y «qué cabe» [C]; política «Juegos ven: Televisor/Steam» [C]; meta Fluidez/Máxima resolución [C]; diagnóstico sin números de serie [C]; `set-output` EXPERIMENTAL [C] |
| Responsabilidades | Lo desconocido es DESCONOCIDO [C]; nunca forzar un modo que el enlace no lleva [C]; todo cambio en Steam se deshace con la política «Steam» [C] |
| Dependencias | sysfs DRM, GUdev (hotplug), libX11, M08 (estado de pantalla de Steam), Gamescope |
| Interfaces | `display.status`, `display.gamePolicy`, `display.goal` (host); `stonectl display [--json|diagnostics|probe|set-output|reset|goal]` |
| Integración con STONE HOME | Ajustes → Pantalla (Televisor, Salida, Juegos ven, Conexión, Meta, Resolución de STONE) [C] |
| Relación con STONED | Ninguna directa [C]; [P] informar a M04 de los Hz objetivo para el controlador dinámico |
| Requisitos HW/SW | Salida DisplayPort de la BC-250 [V] P-07; adaptador DP→HDMI ~300 MHz observado [C] H-08, modelo [V] P-06; televisor [V] P-05. Para 4K60 hace falta un adaptador activo DP 1.4 → HDMI 2.0 [C] (rc18) |
| Fases | F4 |
| Aceptación y pruebas | Software: D01–D24. Placa: §27; T-DISP-01 [P]: el modelo coincide con lo que ofrece el televisor real (EDID) en cada modo |

### M10 · STONE GRAPHICS

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | Rutas de imagen por juego: nativo, upscaler del juego, FSR de Gamescope (orientación), OptiScaler (FSR 3.1), HelixSR [C]; selector Imagen/Calidad en la ficha [C]; activación sólo por lanzamiento con `WINEDLLOVERRIDES` y opciones guardadas/restauradas [C]; fallback HelixSR → FSR del juego → nativo [C]; nunca en juegos con anti-cheat u online [C].

**Diseñado para la GPU de 40 CU** [C] D-16:
- La ruta recomendada por juego se elige por **medición en esta consola con 40 CU** (vía M11), no por tablas genéricas.
- Las rutas que dependen del rendimiento de la GPU (resolución interna, calidad del upscaler) se guardan junto con la configuración en que se midieron (CU, calibración, regulador).
- Si la consola arranca en el estado degradado de 24 CU, esas recomendaciones se marcan como no válidas y se vuelve a la ruta segura (nativo o FSR del juego) [P].
- Ninguna resolución, calidad o tasa de cuadros «esperada» para 40 CU se fija de antemano: no hay mediciones [C] D-18. |
| Responsabilidades | Reversibilidad completa, también si Home o la consola se caen [C]; no tocar archivos del juego salvo instalación pedida (M13) [C] |
| Dependencias | M08 (opciones de lanzamiento), M13 (componentes), detección de anti-cheat (`detect.py`) |
| Interfaces | `game.image`, `game.setImage`, `game.modes`, `game.apply` (host) |
| Integración con STONE HOME | Ficha de juego [C] |
| Relación con STONED | Ninguna directa; la parte de rendimiento va siempre por M04 [C] |
| Requisitos HW/SW | Proton/Wine de Steam; carga real de OptiScaler en la placa [V] |
| Fases | F4 |
| Aceptación y pruebas | Software: G03–G10, G19–G21. Placa: parte de §29; T-GFX-01 [P]: las opciones de lanzamiento quedan idénticas a las originales después de salir, de un cuelgue del juego y de un reinicio |

### M11 · STONE OPTIMIZED + STONE GAME PROFILE

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | JUGAR → STONE RECOMMENDED [C]; STONE GAME PROFILE por AppID en tres capas (incorporado, medido, usuario) con estados UNKNOWN → AUTO_GENERATED → RECOMMENDED → USER_MODIFIED → HARDWARE_VERIFIED (sólo lo pone una persona) [C]; invalidación por cambios de juego, Proton, componentes, CU, regulador, calibración, pantalla o reglas [C]; STONE OPTIMIZER con matriz de pruebas medida con MangoHud [C]; STONE EXPERIENCE SCORE [C]; optimización guiada [C]; recuperación tras caídas del juego [C]; STONE PROFILE DATABASE incorporada, con distribución futura firmada [P].

**Diseñado para 8 núcleos y 40 CU** [C] D-16:
- Los perfiles incorporados y las mediciones se declaran para la configuración de referencia. La huella de configuración de cada medición incluye núcleos e hilos en línea, además de lo que ya incluye en rc23: CU, regulador, calibración, kernel y pantalla.
- Una medición tomada con otra configuración no sirve como recomendación.
- La matriz de pruebas del optimizador usa como eje de rendimiento sólo los perfiles de M04 (SILENT/BALANCED/PERFORMANCE con el techo validado de esta consola). Nunca usa frecuencias fijas.
- El perfil de Cyberpunk 2077 sigue siendo un punto de partida sin números hasta medirlo [C] D-18. |
| Responsabilidades | Mejor experiencia, no el número más grande [C]; nunca aplicar una frecuencia por su cuenta ni activar generación de cuadros [C] |
| Dependencias | M04 (perfil por juego), M08, M09, M10, MangoHud [V] (registro CSV en la versión de la imagen) |
| Interfaces | `game.profile`, `game.recommended`, `game.launchOptimized`, `game.status`, `game.restoreRecommended`, `game.optimizeStatus/Start` (host); CLI `stone-game` [C]; esquema de perfil versionado (`schema.py`) [C] |
| Integración con STONE HOME | Ficha: «STONE RECOMMENDED · … · estado», botón Optimizar (n/total); preferencia `optimized` [C] |
| Relación con STONED | Pide perfiles por juego por `SetGameProfile`; `stoned` aplica y retira según la partida detectada [C] |
| Requisitos HW/SW | Mediciones reales en la BC-250; Cyberpunk 2077 como juego de referencia [C] |
| Fases | F5 |
| Aceptación y pruebas | Software: G01–G22. Placa: §29; criterio: un perfil RECOMMENDED tiene al menos una medición real de esta consola |

### M12 · STONE CONNECT (Bluetooth y mandos) — Nuevo

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | **[P]** Emparejar, conectar, olvidar y ver el estado de dispositivos Bluetooth (mandos, auriculares, teclado); lista de mandos conectados (USB y Bluetooth), batería si se informa, asignación de jugador; acceso directo a la configuración de Steam Input. **[C]** Hoy lo hace Steam y queda como respaldo (A6) |
| Responsabilidades | [P] Usar BlueZ y la detección de mandos del sistema sin duplicar Steam Input; no tocar el firmware de los mandos |
| Dependencias | [P] BlueZ (`org.bluez`), adaptador Bluetooth [V], `udev`/evdev para mandos, M08 (Steam Input) |
| Interfaces | [P] Métodos del host `connect.devices`, `connect.scan`, `connect.pair(id)`, `connect.forget(id)`, eventos `connect.changed`; el host llama a BlueZ por D-Bus de sistema como usuario de la consola |
| Integración con STONE HOME | [P] Ajustes → Conectar y una entrada en el menú rápido |
| Relación con STONED | Ninguna [P] |
| Requisitos HW/SW | [V] La BC-250 **no tiene Bluetooth documentado en este proyecto**: hace falta registrar las interfaces físicas (USB, Ethernet) y un adaptador Bluetooth USB (modelo y chip) en el diagnóstico; permisos de BlueZ fuera de la sesión de logind (mismo problema que polkit en rc4) [V] |
| Fases | F6 |
| Aceptación y pruebas | [P] Software: pruebas contra un BlueZ simulado (bus de sesión). Placa: T-CONN-01 emparejar y volver a conectar un mando tras reiniciar; T-CONN-02 Steam Input sigue funcionando; T-CONN-03 sin adaptador → «no disponible» |

### M13 · STONE DOWNLOADS (instalación y desinstalación) — Parcial

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | **[C] existe:** INSTALAR un juego de Steam abre el asistente de Steam; descarga de OptiScaler/HelixSR desde el repositorio oficial del autor con SHA-256 y desinstalación exacta; instalación de emuladores desde Flathub. **[P]:** una única pantalla de Descargas con cola y progreso (Steam, Flatpak, componentes), desinstalación de juegos (por Steam), espacio libre por disco, aviso antes de llenar el disco |
| Responsabilidades | Toda instalación la pide una persona [C]; componentes de terceros desactivados por defecto [C] R-09; nunca en juegos con anti-cheat [C]; nada se instala en la imagen (sólo usuario) [C] |
| Dependencias | M08 (descargas e instalaciones de Steam), Flatpak, GitHub releases (componentes), `bsdtar`/`7z` para .7z [V] |
| Interfaces | Existe: `install`, `components`, `game.installPlan`, `game.install`, `game.uninstallImage`, `emuInstall`. [P] `downloads.queue`, `downloads.cancel`, `storage.summary` |
| Integración con STONE HOME | [P] Sección Descargas + estado en la ficha |
| Relación con STONED | Ninguna [C] |
| Requisitos HW/SW | Red (Ethernet [V]); disco y espacio libre [V] |
| Fases | F7 (con lo existente disponible antes: INSTALAR en F2, componentes en F4) |
| Aceptación y pruebas | Software: G20, G21 (descarga, SHA-256, ruta maliciosa). Placa: T-DL-01 instalar y desinstalar un juego por Steam desde STONE; T-DL-02 instalar y quitar OptiScaler deja la carpeta idéntica |

### M14 · STONE EMULATION — Parcial

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | **[C] existe:** catálogo fijo de Flathub (RetroDECK, RetroArch, Dolphin, PCSX2, PPSSPP, RPCS3, Cemu, Azahar, melonDS, mGBA, Flycast, xemu), instalación `--user` y acceso directo en Steam. **[P]:** detección de juegos (ROMs) y BIOS aportados por la persona, presentación de esos juegos en la biblioteca de Home, perfiles de rendimiento por emulador |
| Responsabilidades | STONE no distribuye juegos ni BIOS [C]; la página sólo envía una clave del catálogo [C] |
| Dependencias | Flatpak/Flathub, M08 (accesos directos), M13 |
| Interfaces | `emulators`, `emuInstall` [C]; [P] `emulation.library` |
| Integración con STONE HOME | Ajustes → Emuladores [C]; [P] categoría propia en la biblioteca |
| Relación con STONED | Los emuladores lanzados desde Steam se detectan como partidas (ID de acceso directo) y pueden tener perfil por juego [C] |
| Requisitos HW/SW | Rendimiento por emulador en la BC-250 [V] |
| Fases | F8 |
| Aceptación y pruebas | Software: pruebas del catálogo en `test_home.py`. Placa: T-EMU-01 instalar, lanzar y cerrar un emulador desde STONE con vuelta a Home y al perfil global |

### M15 · STONE DESKTOP — Nuevo

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | **[P]** Pasar de STONE/Game Mode al escritorio de Bazzite (KDE Plasma) y volver a la consola de forma guiada y segura; acceso a la terminal para `stonectl`/`stone-game`; aviso de que en el escritorio STONE Home no está |
| Responsabilidades | [P] No dejar la consola arrancando en escritorio sin camino de vuelta; mantener el perfil global y la vigilancia térmica en el escritorio |
| Dependencias | [V] Mecanismo de cambio de sesión de Bazzite 44 (`steamos-session-select` u otro) y la sesión Plasma presente en la imagen `bazzite-deck` |
| Interfaces | [P] Método del host `desktop.switch()` (sólo destino fijo) y acceso directo «Volver a STONE» en el escritorio |
| Integración con STONE HOME | [P] Energía / Sistema → «Ir al escritorio» |
| Relación con STONED | `stoned` sigue activo; los juegos de Steam en el escritorio se siguen detectando por el `reaper` [V] |
| Requisitos HW/SW | Sesión de escritorio disponible [V] (diagnóstico) |
| Fases | F9 |
| Aceptación y pruebas | Placa: T-DESK-01 ida y vuelta ×5 sin perder la sesión de Steam; T-DESK-02 reinicio desde el escritorio vuelve a STONE |

### M16 · STONE SETTINGS — Propuesta

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | [P] Ajustes propios para audio (salida, volumen), red (Ethernet/Wi-Fi), idioma, hora, accesibilidad y sistema. Hoy existen los ajustes sí/no de Steam (M08) y abrir secciones de Steam [C] |
| Responsabilidades | [P] Leer y escribir sólo por APIs del sistema (PipeWire/WirePlumber, NetworkManager, logind/timedated) |
| Dependencias | [P] PipeWire, NetworkManager, systemd |
| Interfaces | [P] `settings.*` en `stone-home.v1` |
| Integración con STONE HOME | Ajustes |
| Relación con STONED | Ninguna |
| Requisitos HW/SW | [V] Salida de audio real (HDMI a través del adaptador) |
| Fases | F6–F7 (con CONNECT) [P] |
| Aceptación y pruebas | [P] Placa: cambio de volumen y salida reflejado en la pantalla y en `wpctl status` |

### X1 · STONE SECURITY (transversal)

Contenido:
- [C] Modelo de privilegios de A7.
- [C] polkit acotado al usuario de la consola (R-09).
- [C] Firma cosign obligatoria.
- [C] Acciones de CI fijadas por SHA.
- [C] Sin red para `stoned`.
- [C] CSP sin orígenes externos y proxy nulo en Chromium.
- [C] Componentes de terceros desactivados por defecto.
- [C] Riesgo del puerto CEF, revisado en F2.

Aceptación: revisión de seguridad por fase y `validate.sh`, que comprueba la regla polkit y que no hay interruptores de prueba en las unidades.

### X2 · STONE API CONTRACTS (transversal)

Contenido:
- [C] `api/stone-performance.v1` y `api/stone-home.v1` (R-07). [P] Formato: JSON Schema.
- De los contratos salen la validación del host, el cliente JS y el *mock* del simulador.
- Cada cambio incompatible sube la versión.

Aceptación: prueba de contrato en CI para el productor y para el consumidor.

### X3 · STONE DEV & TEST (transversal, fuera de la imagen)

Contenido:
- [C] Contenedor Fedora 44 para macOS y CI (R-11).
- [C] pytest, conservando los identificadores de los casos.
- [C] Simulador sobre el *mock* del contrato.
- [C] Matriz de validación de placa en formato legible por máquina, con fecha y versión de imagen (`hardware/validation/`).

---

## 4. Plataforma de hardware (lo que se sabe y lo que no)

| Elemento | Valor | Grado |
| --- | --- | --- |
| Placa | AMD BC-250; la BIOS instalada se registrará como dato informativo | [C] · [V] versión instalada (diagnóstico diferido) |
| CPU | Zen 2, **8 núcleos desbloqueados**: configuración definitiva | [C] D-16 (propietario) · [V] comprobación física diferida |
| GPU | Cyan Skillfish gfx1013, `1002:13fe`, **40 CU habilitadas**: configuración definitiva | [C] D-16 · [V] comprobación física diferida |
| Mecanismo de 40 CU en la imagen | `amdgpu` de STONE con `bc250_cc_write_mode` + guardia de arranque (rc8–rc23), que se conserva | [C] D-17 · 40 CU `OBSERVED ON BOARD` en rc15 |
| Frecuencias, voltajes, límites térmicos | No se fijan en el diseño: se leen del regulador o salen de la calibración; las cifras de rc23 son observaciones | [C] D-18 · [V] revalidación en placa |
| Memoria | 16 GB GDDR6 compartidos; UMA de 512 MB en la BIOS | [C] documentado · [V] actual |
| Regulador | v0.4.14 en rc14–rc16; v0.4.15 en rc23 | [C] H-02/H-03 · [V] P-01/P-02 |
| Sensores | edge, Tctl, PPT, `fan2`; reloj y carga no fiables | [C] H-07 |
| Vídeo | DisplayPort → HDMI con adaptador de ~300 MHz; televisor 4K | [C] observado · [V] modelos P-05/P-06/P-07 |
| Conectividad (Ethernet, USB, Bluetooth, Wi-Fi) | No documentada en el proyecto | [V] diagnóstico |
| Almacenamiento | No documentado | [V] diagnóstico |
| Refrigeración | BIOS en modo Customize; curva sin valores | [V] P-13 |
| Reposo | No vuelve de s2idle: suspensión desactivada | [C] |
| Watchdog de hardware | Desconocido | [V] P-12 |

---

## 5. Fases de construcción y puertas

| Fase | Contenido | Módulos | Puerta (software + placa) |
| --- | --- | --- | --- |
| F0 | Imagen base, arranque, sin reposo, procedencia, regulador v0.4.14 fijado, módulo 40 CU y guardia | M01, M02 (base), M04 (40 CU en la imagen), X1, X3 | CI ahora; placa diferida (D-19): §0, §1, §2, §14, §16, §21, §22, §25 (sólo lectura del estado) |
| F1 | `stoned` núcleo: perfiles, configuración detectada (8 núcleos / 40 CU), LKG, recuperación, Safe Mode, telemetría, térmico, partidas | M03, M04 (base), M05, M06 | CI + §3–§13, §15 |
| F2 | STONE Home mínimo + Steam Bridge + autoarranque | M07, M08, M02 (Home) | CI + §17, §19, §20, §23, §26 |
| F3 | Performance Center, TUNING, CALIBRATION, gestión de 40 CU desde STONE | M04, M06 (UI) | CI + §18, §25, §28 |
| F4 | DISPLAY + GRAPHICS | M09, M10 | CI + §27, T-DISP-01, T-GFX-01 |
| F5 | OPTIMIZED + GAME PROFILE | M11 | CI + §29 |
| F6 | CONNECT (+ SETTINGS audio/red [P]) | M12, M16 | T-CONN-01..03 |
| F7 | DOWNLOADS unificado | M13 | T-DL-01..02 |
| F8 | EMULATION | M14 | T-EMU-01 |
| F9 | DESKTOP + menú de arranque con mando [P] | M15, M02 | T-DESK-01..02, T-BOOT-01 |

Reglas:
- [C] Cada fase se cierra cuando su CI pasa y sus pruebas de placa están ejecutadas y registradas.
- [C] Ninguna funcionalidad de rc23 se pierde: cada fase porta lo existente de sus módulos o lo deja declarado como «no presente todavía», nunca simulado.
- [P] El orden de F6–F9 es una recomendación y está pendiente de confirmación del propietario.

---

## 6. Vacíos de información y propuestas

| ID | Vacío | Propuesta [P] | Qué la resuelve |
| --- | --- | --- | --- |
| V-01 | No existen las especificaciones de diseño originales (UX, design system, «arquitectura STONE MACHINE») | Este documento pasa a ser la referencia; el diseño visual se toma de la interfaz de rc23 | Aprobación del propietario |
| V-02 | ~~Núcleos de CPU activos y método de desbloqueo~~ **Cerrado:** 8 núcleos y 40 CU confirmados (D-16); el desbloqueo queda fuera de alcance (D-17) | — | Comprobación física diferida |
| V-03 | Bluetooth en la placa | Adaptador USB compatible con BlueZ | Diagnóstico + compra/registro del modelo |
| V-04 | Mecanismo de cambio a escritorio en Bazzite 44 | Usar el de Bazzite, sin reimplementarlo | Diagnóstico (sesiones disponibles) |
| V-05 | Alcance de DOWNLOADS más allá de Steam y Flatpak (Heroic, GOG, Epic) | Sólo Steam + Flatpak en F7; otros lanzadores, como accesos directos de Steam | Decisión del propietario |
| V-06 | Biblioteca de ROMs en EMULATION | Carpeta fija del usuario + RetroDECK como gestor | Decisión del propietario |
| V-07 | Distribución futura de STONE PROFILE DATABASE | Con las actualizaciones de imagen; descarga firmada más adelante | Decisión del propietario |
| V-08 | Ajustes propios (audio, red, idioma) frente a los de Steam | Módulo M16 | Decisión del propietario |
| V-09 | Presupuesto de tiempo de arranque | Fijar tras medir 5 arranques | Diagnóstico + §1 |
| V-10 | Plugin de STONE dentro del juego (menú rápido de Steam) | Evaluar en F6+ | Decisión del propietario |
| V-11 | Fuente fiable de FPS para el controlador dinámico | Sólo registro CSV de MangoHud al terminar la partida | §29 |

## Registro de cambios

| Versión | Fecha | Cambio |
| --- | --- | --- |
| 1.0 | 2026-11-06 | Primera especificación integral (P-14), pendiente de aprobación |
| 1.1 | 2026-11-06 | Configuración de referencia 8 núcleos / 40 CU (D-16, D-17); principio A12 sin cifras inventadas (D-18); M04, M10 y M11 rediseñados para esa configuración; F0 incluye el módulo de 40 CU; V-02 cerrado |
