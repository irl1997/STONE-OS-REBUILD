# STONE MACHINE — Especificación de arquitectura integral de STONE OS

Versión: 1.2 · Fecha: 2026-11-07 · Resuelve P-14 e integra el prompt maestro (D-25).
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
| A6 | **STONE es la experiencia; Steam es un componente interno.** La consola arranca en la sesión propia de STONE (M24), con STONE Home al frente. Steam corre en segundo plano para biblioteca, lanzamiento, Steam Input y descargas, y su interfaz no se muestra como experiencia. Steam Game Mode se conserva sólo como ruta de recuperación. *(v1.1 decía: «Steam sigue siendo el motor de la sesión»; sustituido por D-21)* | [C] D-21 |
| A7 | Mínimo privilegio: la interfaz nunca es root; `stoned` no es root; cada privilegio extra va en un ayudante de un solo propósito | [C] |
| A8 | Contratos de API versionados, únicos para producción, simulador y pruebas | [C] R-07 |
| A9 | La consola es un sistema atómico (bootc): todo se instala en la imagen; el estado del usuario vive en `/var` y `$HOME` | [C] |
| A10 | Un juego en primer plano tiene prioridad: STONE se duerme mientras se juega | [C] |
| A11 | Vocabulario único de estados: `CODE TESTED` → `READY FOR HARDWARE TEST` → `OBSERVED ON BOARD` → `HARDWARE VERIFIED`, más `EXPERIMENTAL` y `BLOCKED` para módulos, y `COMMUNITY REPORTED` sólo para perfiles de juego. No se usan otras listas | [C] D-08, D-23 |
| A13 | Producto, no conjunto de piezas: el objetivo es STONE OS 1.0 RC tal como lo define el prompt maestro (D-25), construido por fases F0–F9 con puerta de software y de placa en cada una | [C] D-25 |

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
┌──────┴─────────────── STONED (usuario `stoned`, systemd aislado) ───────────────┐   Steam (en segundo plano)
│ PERFORMANCE · CALIBRATION · RECOVERY/SAFE MODE · TELEMETRY · THERMAL · GAMES    │
└──────▲──────────────────────────────────────────────────────────────────────────┘
       │ D-Bus del regulador · sysfs/hwmon (lectura) · /proc
cyan-skillfish-governor-smu · amdgpu (24/40 CU) · k10temp · nct6683 · logind · BlueZ · NetworkManager
       │
STONE SESSION (Gamescope propia: STONE Home al frente, juegos, Steam oculto) · ruta de recuperación: Game Mode
PLATFORM (Bazzite bootc) · BOOT ENGINE (Plymouth, recover) · AMD BC-250 (8 núcleos, 40 CU)
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
| M13 | STONE DOWNLOADS + STONE LIBRARY (instalación, desinstalación, biblioteca unificada) | Usuario | host | Parcial |
| M14 | STONE EMULATION | Usuario | host | Parcial |
| M15 | STONE DESKTOP | Usuario + sesión | host + SDDM | Nuevo |
| M16 | STONE SETTINGS + STONE AUDIO (audio, red, idioma, sistema, accesibilidad) | Usuario | host | Parcial (vía Steam) |
| M17 | STONE IMAGE (postprocesado ligero) | Usuario | host + Gamescope / capa Vulkan | Nuevo |
| M18 | STONE NEURAL RENDER | Investigación | — | `EXPERIMENTAL` (desactivado) |
| M19 | STONE HEALTH (diagnóstico) | Usuario (vista) + sistema (datos) | host + `stoned` | Nuevo (sobre M06) |
| M20 | STONE STORAGE | Usuario | host | Nuevo |
| M21 | STONE INSTALLER | Instalador | ISO (Anaconda / bootc-image-builder) | Parcial (ISO de rc23) |
| M22 | FIRST RUN (primer encendido) | Usuario | host + Home | Nuevo |
| M23 | STONE EXPERIENCE ENGINE | Usuario + sistema | host + `stoned` | Nuevo |
| M24 | STONE SESSION (sesión gráfica propia) | Sesión | Gamescope + SDDM + systemd de usuario | Nuevo (D-21) |
| X1 | STONE SECURITY (transversal) | Todas | — | Existe |
| X2 | STONE API CONTRACTS (transversal) | Todas | — | Nuevo (R-07) |
| X3 | STONE DEV & TEST (simulador, contenedor, CI, validación) | Fuera de la imagen | — | Existe (a migrar) |

M13 incluye STONE LIBRARY (§15 del prompt maestro) y M16 incluye STONE AUDIO (§21). STONE UPDATE (§23) es parte de M01, con pantalla propia en Home. El «Visual Engine» de Home (§18) es parte de M07.

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
| Objetivo y funcionalidades | Encendido de consola continuo e ininterrumpido: Plymouth STONE (THE LINE) → sesión STONE (M24) → STONE Home sobre la misma línea, sin pantallas de Steam ni de escritorio [C] D-21; decisión de recuperación antes de la sesión [C] (detalle en M05); tiempos de arranque medidos y registrados [C]: **BOOT TO VISUAL** (primer fotograma de STONE) y **BOOT TO READY** (Home operable), tiempo por servicio (`systemd-analyze`), reintentos y comparación entre arranques, con línea base en la placa antes de optimizar; opción de arranque de mantenimiento `stone.safe=1` [C]. **[P]:** menú de arranque de STONE accesible desde el mando (Safe Mode, versión anterior, escritorio); presupuesto de tiempo de arranque como criterio. Nunca se retrasa la interfaz para ocultar que el sistema no está listo |
| Responsabilidades | Que la consola nunca quede en un estado sin salida: si la sesión STONE o Home fallan, se registra el error, se reintenta sin ciclos infinitos y, tras N fallos, se arranca la ruta de recuperación (Steam Game Mode de Bazzite) avisando del motivo [C] D-21 |
| Dependencias | Plymouth + `plymouth-plugin-script`, dracut, SDDM, `gamescope-session-plus`, Steam, M05, M07, M08, M24 |
| Interfaces | Tema `/usr/share/plymouth/themes/stone`; sesión STONE (M24); `stone-home-session status|diag`; registro de métricas de arranque (`~/.local/state/stone/boot-metrics.jsonl` [P]). El acceso directo «STONE» en Steam y el autoarranque vía `steam://` de rc23 pasan a ser sólo de la ruta de recuperación |
| Integración con STONE HOME | El vídeo termina en el primer fotograma de Home [C]; Home llama a `HomeReady` cuando está en pantalla [C] |
| Relación con STONED | `stoned-recover` decide antes de `display-manager.service` [C]; `HomeReady` habilita la aplicación del perfil guardado [C] |
| Requisitos HW/SW | GPU con salida activa durante el initramfs [V] (pantalla negra de 30–60 s reportada por la comunidad, sin medir en STONE); `gamescope-session-plus` de Bazzite 44 |
| Fases | F0 (Plymouth, recover, sin reposo); F2 (sesión STONE, métricas de arranque, recuperación de la sesión); F9+ (menú de arranque con mando [P]) |
| Aceptación y pruebas | Software: R01–R12 (`run_tests.py`), pruebas de la sesión (M24). Placa: §1 (×5), §16, §23. T-BOOT-01: BOOT TO VISUAL y BOOT TO READY registrados en 5 arranques, **ninguna pantalla de Steam ni de escritorio visible** |

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
| Objetivo y funcionalidades | La interfaz de consola, entera con mando [C]: Inicio (recientes), Biblioteca (instalados, no instalados, accesos directos), Ficha de juego (JUGAR/INSTALAR/REANUDAR, perfil, imagen), Menú rápido, Ajustes, Performance Center, STONE TUNING, Energía (apagar, reiniciar, apagar tras inactividad), sonido, THE LINE y STONE MOTION, sueño mientras se juega [C]. **Nuevo en v1.2** [C] D-25:
- Es la aplicación principal de la sesión STONE (M24), no un acceso directo de Steam.
- **Quick Menu propio** también durante el juego (mecanismo [V] V-13).
- **Visual Engine:** portadas y fondos a la resolución de la pantalla (corrige los fondos borrosos de rc23), caché, precarga de los elementos próximos y liberación de lo que no se ve, sin presión innecesaria sobre la memoria compartida.
- **Ciclo de vida** MOUNT → ACTIVE → BACKGROUND → SUSPENDED → UNMOUNT: con un juego delante, Home queda en SUSPENDED (sin animaciones, sin lectura del mando salvo el Quick Menu, sin precargas, telemetría mínima).
- Pantallas de Descargas, Biblioteca unificada, Conectar, Emulación, Salud, Almacenamiento, Actualizaciones y Escritorio (M12–M23).
- **[P]:** búsqueda en la biblioteca; notificaciones. |
| Responsabilidades | Mostrar el estado real de cada módulo; no ejecutar comandos, rutas ni URLs elegidas por la página [C]; consumir lo mínimo con un juego en primer plano [C]; no mostrar la interfaz de Steam como destino [C] D-21 |
| Dependencias | Chromium del sistema (motor objetivo único) [C] R-02; WebKitGTK 6 + GTK 4 como respaldo hasta cumplir R-02 [C] D-06; Python 3 + PyGObject; fuentes OFL incluidas |
| Interfaces | `stone-home.v1` (host ↔ UI) [C] R-07; transporte HTTP 127.0.0.1 con ruta secreta por arranque, comprobación de Host/Origin, SSE [C] |
| Integración con STONE HOME | — (es STONE HOME). Cada módulo M08–M16 se presenta como sección o pantalla de Home |
| Relación con STONED | Cliente de `org.stonemachine.Performance1` por `bridge.py`; llama a `HomeReady` [C]; `stoned` lo excluye de la detección de juegos [C] |
| Requisitos HW/SW | Dibujo por GPU a la resolución de la ventana (diseño a 1920×1080, escala hasta 4K) [C]; consumo de memoria y CPU [V] P-10; mando dentro de Home [V] P-16 |
| Fases | F2 (Home en la sesión STONE: biblioteca, JUGAR, vuelta, energía, Visual Engine, ciclo de vida, Quick Menu); F3 (Performance Center, Salud); después, cada módulo añade su pantalla |
| Aceptación y pruebas | Software: `test_home.py`, `test_server.py`, `chromium_selftest.py`, e2e Playwright, ESLint, regresión del diseño [C] R-08; prueba de ciclo de vida (en SUSPENDED: 0 cuadros dibujados, 0 temporizadores activos salvo el Quick Menu). Placa: §17, §19, §20, §26; T-HOME-01 [P]: el fondo de un juego seleccionado se ve nítido a la resolución de la pantalla; T-HOME-02 [P]: con un juego abierto, Home no cambia los FPS medidos |

### M08 · STONE STEAM BRIDGE

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | Integración con Steam en un único adaptador [C] R-06: biblioteca desde VDF/ACF/`localconfig.vdf`/`shortcuts.vdf` [C]; juegos no instalados desde la interfaz de Steam [C]; lanzar (`SteamClient.Apps.RunGame`, respaldo `steam://`) [C]; acceso directo «STONE» e identificadores [C]; abrir secciones de ajustes de Steam [C]; catálogo de ajustes Get/Set descubiertos (sólo sí/no) [C]; opciones de lanzamiento por juego (para M10/M11) [C]; detección de capacidades de la Steam instalada [C] R-06. **v1.2** [C] D-21, D-24:
- Steam corre en segundo plano dentro de la sesión STONE: el bridge lo arranca, comprueba que está listo y lo usa sin mostrar su interfaz.
- Descargas, pausas, verificación y actualizaciones de juegos van por este adaptador, con capacidades detectadas y marcadas «depende de Steam».
- Abrir secciones de la interfaz de Steam queda sólo como último recurso, y siempre avisado. |
| Responsabilidades | Aislar las APIs internas de Steam: ningún otro módulo llama a `SteamClient.*` [C]; modo degradado cuando una función no existe [C]; nunca escribir `shortcuts.vdf` con Steam abierto [C]; vigilar que Steam siga vivo y reiniciarlo sin ciclos infinitos [P] |
| Dependencias | Steam (se actualiza solo), puerto CEF `127.0.0.1:8080` con `.cef-enable-remote-debugging` [C] (riesgo N-05, revisión [C] R-06); modo de Steam en segundo plano [V] V-12, V-14, V-16 |
| Interfaces | API interna de Python con capacidades (`capabilities()`, `library()`, `launch()`, `install()`, `settings()`, `launch_options()`); se expone a la UI por `stone-home.v1` |
| Integración con STONE HOME | Biblioteca, ficha, JUGAR/INSTALAR, Ajustes → Steam [C] |
| Relación con STONED | Ninguna directa: `stoned` detecta las partidas por `/proc`, no por el bridge [C] |
| Requisitos HW/SW | Steam en segundo plano dentro de la sesión STONE [V]; formato del `reaper` en ese modo [V] P-11 |
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

**Generación de fotogramas** [C] D-22:
- Apagada por defecto.
- Se activa sólo si la persona la elige o si una medición en esta consola muestra mejora: frametime, 1 % low, latencia y artefactos medidos, no sólo los FPS medios.
- Nunca en juegos online o con anti-cheat.
- Los FPS generados se muestran siempre aparte de los renderizados.
- Opciones a evaluar: la de FSR 3.1 vía OptiScaler y las que ofrezca cada juego [V].
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

**Ampliación v1.2: STONE LIBRARY** [C] D-25:
- Biblioteca unificada con el origen de cada juego: Steam, accesos directos, emuladores (M14) y juegos instalados a mano.
- Epic y GOG sólo mediante herramientas autorizadas (por ejemplo Heroic, que añade sus juegos como accesos directos) [P] V-05. No se promete compatibilidad universal.
- Descargas: instalar, pausar, reanudar, cancelar, actualizar, desinstalar, progreso y velocidad, a través de M08 («depende de Steam») [C] D-24.
- Nunca se muestra una operación que no se ejecutó.
- Prueba nueva: T-DL-03 [P], pausar y reanudar una descarga desde STONE, con el progreso coincidiendo con el de Steam.

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

**Ampliación v1.2: STONE AUDIO** [C] D-25:
- Salida por HDMI/DisplayPort (a través del adaptador DP→HDMI [V]), USB y Bluetooth (con M12).
- Selección de salida simple y persistente; reconexión automática.
- Sonidos de interfaz de Home, que se callan durante el juego.
- Prueba nueva: T-AUD-01 [P], la salida elegida se mantiene tras reiniciar y tras desconectar y reconectar el dispositivo.

### M17 · STONE IMAGE — Nuevo

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | Postprocesado ligero por juego: presets STONE NATURAL, CLARITY, CINEMA, VIVID, RETRO y CUSTOM; nitidez, debanding, ajuste tonal moderado, tratamiento de negros, filtros para emulación, HDR cuando lo haya [C] D-25 |
| Responsabilidades | Ningún filtro pesado por defecto (NATURAL = sin coste o casi); medir el coste de cada efecto y mostrarlo; desactivable por juego; nunca en juegos online o con anti-cheat si el filtro se inyecta en el proceso del juego [C] |
| Dependencias | Filtros de Gamescope (fuera del proceso del juego, preferidos) o capa Vulkan (vkBasalt u otra) [V]: elegir tras medir coste y compatibilidad |
| Interfaces | `image.presets`, `image.get(appid)`, `image.set(appid, preset)` en `stone-home.v1` [P]; se guarda en el perfil de juego (M11) |
| Integración con STONE HOME | Ficha del juego, junto a «Imagen» de M10 |
| Relación con STONED | Ninguna |
| Requisitos HW/SW | Coste medido en la BC-250 con 40 CU [V] |
| Fases | F4 |
| Aceptación y pruebas | Software: validación de presets y de su aplicación y retirada por lanzamiento. Placa: T-IMG-01 [P], coste por preset (FPS y frametime con y sin el filtro) registrado en el perfil |

### M18 · STONE NEURAL RENDER — `EXPERIMENTAL`

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | Arquitectura de backends intercambiables para reconstrucción o mejora de imagen con redes neuronales, preparada para backends futuros compatibles con GFX1013 [C] D-25 |
| Responsabilidades | Permanece **desactivado** mientras no exista un backend funcional y medible; no copia tecnologías propietarias que dependen de hardware ausente; nunca resta rendimiento general [C] |
| Dependencias | Ninguna en producción. Investigación: coste de cómputo, memoria, latencia y calidad en RDNA1/GFX1013 [V] |
| Interfaces | Ninguna expuesta hasta que haya un backend; después, una ruta más en M10 |
| Integración con STONE HOME | Ninguna mientras sea `EXPERIMENTAL` |
| Relación con STONED | Ninguna |
| Requisitos HW/SW | Desconocidos [V] |
| Fases | Sin fase: investigación paralela; entra en M10 sólo con medición en la placa |
| Aceptación y pruebas | Un backend sólo sale de `EXPERIMENTAL` con medición en la placa que muestre mejora de calidad a coste aceptable |

### M19 · STONE HEALTH — Nuevo

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | Panel de diagnóstico: CPU (núcleos en línea), GPU (CU detectados), frecuencias, temperaturas, consumo cuando la telemetría sea válida, ventiladores, memoria, almacenamiento, controladores, errores de GPU, estabilidad (fallos, Safe Mode, LKG), estado de servicios. Incluye **Crash Black Box**: registros útiles antes y después de un fallo [C] D-25 |
| Responsabilidades | Distinguir siempre **medido / estimado / no disponible**; no inventar sensores [C] A1, D-18 |
| Dependencias | M06 (telemetría), M05 (recuperación), `systemd`, journal, `hardware/bc250.yaml` (fiabilidad de cada sensor) |
| Interfaces | `GetMetrics`, `GetCapabilities`, `GetState` de `stoned`; `health.services`, `health.errors` en `stone-home.v1` [P] |
| Integración con STONE HOME | Ajustes → Salud y un indicador discreto en Inicio |
| Relación con STONED | Lee de `stoned` (sólo lectura) |
| Requisitos HW/SW | Sensores reales de la BC-250 [V] |
| Fases | F3 |
| Aceptación y pruebas | Software: cada valor lleva su origen y su estado; sensor ausente = «no disponible». Placa: T-HLTH-01 [P], cada valor «medido» coincide con una lectura directa de sysfs/hwmon |

### M20 · STONE STORAGE — Nuevo

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | Espacio libre, juegos instalados y tamaño por juego, bibliotecas de Steam por disco, temporales, cachés, shader cache, recomendaciones de limpieza y alertas de espacio [C] D-25 |
| Responsabilidades | **Nunca** borrar partidas, configuraciones ni datos personales sin una confirmación explícita en pantalla; limpiar sólo cachés regenerables, y siempre avisado [C] |
| Dependencias | VDF/ACF de Steam (M08), `df`/`statvfs`, rutas de caché conocidas |
| Interfaces | `storage.summary`, `storage.cleanable`, `storage.clean(id)` (sólo elementos de una lista fija) en `stone-home.v1` [P] |
| Integración con STONE HOME | Ajustes → Almacenamiento; aviso de espacio antes de instalar (M13) |
| Relación con STONED | Ninguna |
| Requisitos HW/SW | Disco de la consola [V] P-17 |
| Fases | F7 |
| Aceptación y pruebas | Software: la limpieza sólo toca rutas de la lista fija (prueba con un árbol simulado que incluye partidas). Placa: T-STOR-01 [P], los tamaños coinciden con los de Steam |

### M21 · STONE INSTALLER — Parcial

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | Instalador con identidad STONE: detectar hardware (BC-250), verificar compatibilidad, identificar discos, avisar del borrado, particionar, instalar, preparar el primer arranque y generar un informe de instalación [C] D-25 |
| Responsabilidades | No sobrescribir una instalación existente sin confirmación; ISO publicada sólo si se construyó y verificó (SHA-256) [C] |
| Dependencias | bootc-image-builder (Anaconda ISO) de rc23/F0 [C]; personalización visual de Anaconda limitada [V] V-17 |
| Interfaces | `image/disk_config/iso.toml` (kickstart); informe en el primer arranque [P] |
| Integración con STONE HOME | FIRST RUN (M22) muestra el informe de instalación |
| Relación con STONED | El primer arranque arranca `stoned` con estado vacío (BALANCED, sin calibración) |
| Requisitos HW/SW | Pendrive y disco de la BC-250 [V] |
| Fases | F9 (identidad completa). La ISO funcional ya existe desde rc1 y se reconstruye cuando se acuerde |
| Aceptación y pruebas | §16 (instalación en la placa); T-INST-01 [P], instalar sobre un disco con datos pide confirmación explícita |

### M22 · FIRST RUN — Nuevo

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | Primer encendido guiado: detectar BC-250 y configuración (8 núcleos, 40 CU), comprobación de salud, pantalla y resolución, conectividad, mando, audio, inicio de sesión en Steam (una sola vez, integrado en la sesión STONE [V] V-15), preparar la biblioteca, perfil BALANCED [C] D-25 |
| Responsabilidades | Nunca overclock, calibración ni funciones experimentales en el primer arranque [C] A2 |
| Dependencias | M04, M09, M12, M16, M19, M08, M24 |
| Interfaces | Pantallas de Home; estado `firstrun.done` en `~/.config/stone/` [P] |
| Integración con STONE HOME | Es la primera vista de Home tras instalar |
| Relación con STONED | Lee capacidades; el perfil queda en BALANCED de fábrica |
| Requisitos HW/SW | Mando conectado o mando por USB [V] |
| Fases | F2 |
| Aceptación y pruebas | Placa: T-FR-01 [P], de la instalación a Home operable sólo con el mando y sin ninguna pantalla de Steam salvo el inicio de sesión |

### M23 · STONE EXPERIENCE ENGINE — Nuevo

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | Inteligencia adaptativa sobre M04, M06 y M11, con **reglas deterministas y estadística, sin IA generativa** [C] D-25. Funciones, cada una con su prueba, sólo cuando sus datos existan: Performance Autopilot (QUALITY / BALANCED / FLUID), Adaptive Experience con histéresis, 1 % Low Optimizer, Thermal Forecast, Efficiency Engine (sólo con potencia fiable), Stutter Hunter, VRR Intelligence, Smart Pre-Warm, Regression Guard (tras actualizar Proton, Mesa o kernel), Profile Evolution, Self-Healing (sólo reparaciones no destructivas), Auto Benchmark, Confidence System (estados de A11) |
| Responsabilidades | Predecible, auditable y reversible: cada cambio automático queda registrado con su motivo y se revierte si empeora; dentro de los límites validados de M04; nunca subir un límite [C] A5 |
| Dependencias | Fuente de FPS y frametime durante la partida [V] V-11 (hoy sólo el CSV de MangoHud al final); M06, M11, M04 |
| Interfaces | `experience.mode`, `experience.log` en `stone-home.v1` [P]; ajustes por `SetSessionProfile`/`SetGameProfile` de `stoned` |
| Integración con STONE HOME | Ficha del juego (modo de experiencia) y Quick Menu |
| Relación con STONED | Pide perfiles a `stoned`; nunca escribe en el hardware |
| Requisitos HW/SW | Mediciones reales por juego en la BC-250 |
| Fases | F5 en adelante, función a función |
| Aceptación y pruebas | Cada función: prueba de reglas con series simuladas (incluida la histéresis: sin cambios constantes) y prueba en la placa con mejora medida antes de activarse por defecto |

### M24 · STONE SESSION — Nuevo (D-21)

| Campo | Especificación |
| --- | --- |
| Objetivo y funcionalidades | Sesión gráfica propia de la consola: SDDM inicia automáticamente una variante de `gamescope-session-plus` llamada `stone` (archivo en `/usr/share/gamescope-session-plus/sessions.d/` [V] V-12), cuya aplicación principal es STONE Home. Steam se lanza dentro de la misma Gamescope en segundo plano, sin interfaz visible. Los juegos que lanza Steam aparecen al frente; al salir, el foco vuelve a Home [C] D-21 |
| Responsabilidades | Que nunca se vea la interfaz de Steam ni un escritorio como experiencia; mantener Steam vivo (reinicio controlado); arrancar la ruta de recuperación (Game Mode de Bazzite) tras N fallos seguidos de la sesión, con el motivo registrado; no romper el cambio a escritorio de Bazzite (M15) |
| Dependencias | `gamescope-session-plus` y Gamescope de Bazzite 44; Steam en modo segundo plano [V] V-14; SDDM y su configuración de inicio automático [V] V-12; M07, M08, M02, M05 |
| Interfaces | Archivo de sesión `stone`; unidades de usuario `stone-session` [P]; `session.state` en `stone-home.v1` [P]; registro de arranques de la sesión |
| Integración con STONE HOME | Home es la aplicación principal de la sesión; Quick Menu durante el juego mediante el mecanismo de superposición de Gamescope [V] V-13 |
| Relación con STONED | Ninguna directa; `stoned` sigue detectando partidas por el `reaper` de Steam [V] P-11 en este modo |
| Requisitos HW/SW | Mando con Steam Input dentro de la sesión [V] V-15; actualizaciones del propio cliente de Steam sin ventanas visibles [V] V-16 |
| Fases | F2 (prioritaria: decide la forma de toda la experiencia) |
| Aceptación y pruebas | Software: pruebas de la lógica de reintentos y recuperación con un Steam y una Gamescope simulados. Placa: T-SESS-01 de encendido a Home ×5 sin ninguna pantalla de Steam; T-SESS-02 JUGAR, juego al frente, salir y volver a Home; T-SESS-03 mando y Steam Input dentro del juego; T-SESS-04 Quick Menu durante el juego; T-SESS-05 la sesión falla a propósito → recuperación tras N intentos; T-SESS-06 Steam se actualiza sin mostrar su interfaz; T-SESS-07 primer inicio de sesión en Steam desde FIRST RUN |

### X1 · STONE SECURITY (transversal)

Contenido:
- [C] Modelo de privilegios de A7.
- [C] polkit acotado al usuario de la consola (R-09).
- [C] Firma obligatoria de cada imagen, sin clave (Sigstore, identidad del flujo de GitHub) [C] D-26.
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
| F2 | **Sesión STONE propia** + STONE Home (Visual Engine, ciclo de vida, Quick Menu) + Steam Bridge en segundo plano + FIRST RUN + métricas de arranque + pantalla de actualizaciones | M24, M07, M08, M22, M02, M01 (UPDATE) | CI + §17, §19, §20, §23, §26, T-SESS-01..07, T-BOOT-01, T-FR-01, T-HOME-01..02 |
| F3 | Performance Center, TUNING, CALIBRATION, gestión de 40 CU desde STONE, STONE HEALTH | M04, M06 (UI), M19 | CI + §18, §25, §28, T-HLTH-01 |
| F4 | DISPLAY + GRAPHICS (con generación de fotogramas, D-22) + STONE IMAGE | M09, M10, M17 | CI + §27, T-DISP-01, T-GFX-01, T-IMG-01 |
| F5 | OPTIMIZED + GAME PROFILE + EXPERIENCE ENGINE (función a función) | M11, M23 | CI + §29 |
| F6 | CONNECT + SETTINGS y AUDIO | M12, M16 | T-CONN-01..03, T-AUD-01 |
| F7 | DOWNLOADS + LIBRARY + STORAGE | M13, M20 | T-DL-01..03, T-STOR-01 |
| F8 | EMULATION | M14 | T-EMU-01 |
| F9 | DESKTOP + menú de arranque con mando [P] + INSTALLER con identidad STONE → **STONE OS 1.0 RC** | M15, M02, M21 | T-DESK-01..02, T-INST-01, validación final |
| — | NEURAL RENDER (investigación, `EXPERIMENTAL`) | M18 | Sólo con medición en placa |

Reglas:
- [C] Cada fase se cierra cuando su CI pasa y sus pruebas de placa están ejecutadas y registradas.
- [C] Ninguna funcionalidad de rc23 se pierde: cada fase porta lo existente de sus módulos o lo deja declarado como «no presente todavía», nunca simulado.
- [C] Bajo la autonomía de D-20, Claude avanza dentro y entre fases sin pedir aprobación. Las puertas de placa dependen de las sesiones del propietario con la consola.
- [P] El orden de F6–F9 es el recomendado. La equivalencia con las fases del prompt maestro está en `REVISION_PROMPT_MAESTRO.md` §5.
- **Bloqueos P0 de una versión candidata** (prompt §30) [C]: no arranca; no aparece STONE Home; no se puede iniciar un juego; se pierde la recuperación; hay operaciones privilegiadas inseguras; se aplica hardware sin protección; se pierden datos; una actualización fallida deja la consola irrecuperable.

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
| V-10 | ~~Plugin de STONE dentro del menú rápido de Steam~~ **Sustituido** por el Quick Menu propio de la sesión STONE (V-13) | — | D-21 |
| V-11 | Fuente fiable de FPS durante la partida (controlador dinámico, EXPERIENCE ENGINE) | Registro CSV de MangoHud al terminar; evaluar lectura en vivo de mangoapp | §29 |
| V-12 | Formato del archivo de sesión de `gamescope-session-plus` en Bazzite 44 y cómo elige SDDM la sesión automática sin romper el cambio a escritorio | Variante `stone` en `sessions.d`, junto a la `ogui-steam` de Bazzite | Leer la imagen base en CI + prueba en placa |
| V-13 | Cómo mostrar el Quick Menu de STONE encima de un juego en Gamescope | Ventana superpuesta de Gamescope (el mecanismo que usa la interfaz de Steam); si no es viable, el botón de Home devuelve a STONE con el juego en pausa de foco | Prueba en placa (T-SESS-04) |
| V-14 | Steam en segundo plano sin interfaz: modo de arranque, botón Steam/guía, overlay del juego, notificaciones | Arrancar Steam sin su interfaz de Game Mode y capturar el botón guía en STONE | Prueba en placa |
| V-15 | Steam Input y mandos para Home y juegos fuera de Game Mode; inicio de sesión de Steam la primera vez | Home lee el mando por la API Gamepad; inicio de sesión de Steam una sola vez dentro de FIRST RUN | Prueba en placa (T-SESS-03, T-SESS-07) |
| V-16 | Actualización del propio cliente de Steam sin ventanas | Actualizar en segundo plano; si Steam abre una ventana, mostrarla tapada por la pantalla de STONE | Prueba en placa (T-SESS-06) |
| V-17 | Cuánto se puede personalizar visualmente el instalador Anaconda | Marca STONE en lo que Anaconda permita; si no basta, evaluar un instalador propio en F9 | Investigación en F9 |
| V-18 | Actualizaciones dentro de la sesión STONE: qué temporizador usa Bazzite 44 (`uupd.timer`), si sigue la imagen de STONE en GHCR y cómo buscar una actualización a mano sin la interfaz de Steam | Home lee el temporizador por D-Bus (sólo lectura) y ofrece reiniciar cuando hay una versión preparada; la búsqueda manual queda para cuando se sepa si hace falta un método privilegiado en `stoned` | Prueba en placa (T-UPD-01) |
| V-19 | Las filas «Abrir en Steam» de Ajustes dentro de la sesión STONE, donde la interfaz de Steam no está al frente | Abrir el panel de Steam y ponerlo delante con el mismo control de foco que los juegos; si no es posible, sustituir cada fila por una pantalla propia | Prueba en placa (T-SESS-08) |
| V-20 | Ventanas propias de Steam en la sesión STONE (inicio de sesión, tienda y pago). En 1.0.0-rc5 no se veían: Gamescope solo muestra ventanas con identificador de aplicación y, con `steam -silent`, las de Steam no lo tienen. Cierra en la práctica V-15 (inicio de sesión) y V-19 | **Steam al frente (D-34, M24 y M08):** Home pide la ventana (`STONE_STEAM_FRONT` en la raíz de X); el supervisor marca las ventanas de Steam, nombra la que se muestra y devuelve la pantalla a Home. Big Picture para la tienda. Plan B: la interfaz de Modo Juego de Steam toma la sesión y el supervisor la recupera. La biblioteca se vigila y se guarda entre arranques (M13); la tienda se lee de la API pública de Steam | Prueba en placa (T-STEAM-11 a 14, T-LIB-11 a 13, T-STORE-01) |

## Registro de cambios

| Versión | Fecha | Cambio |
| --- | --- | --- |
| 1.5 | 2026-11-12 | 3.1.0-rc3 (D-36): instalación comprobada y preguntas de Steam en M08 y M13; Steam en espera durante el primer encendido (M22) y guardia de ventanas en M24; comprobación diaria y Buscar actualizaciones en M01 y M16 |
| 1.4 | 2026-11-12 | 3.1.0-rc1 (D-35): capa visual Cristal en M07 (STONE Home); la preferencia «Efectos de cristal» en M16. Llega por el canal `rc` de M01 |
| 1.3 | 2026-11-11 | 3.0.0-rc1 (D-34): V-20, Steam al frente y plan B en M24; biblioteca vigilada, tienda y carátulas en M13 y M08; Switch y actualizador en M14; arranque reordenado en M02 y M07. Detalle en `docs/AUDITORIA_3_0.md` |
| 1.0 | 2026-11-06 | Primera especificación integral (P-14), pendiente de aprobación |
| 1.2 | 2026-11-07 | Prompt maestro integrado (D-20 a D-25): A6 sustituido por la sesión propia (M24); A11 con vocabulario único; A13 nuevo; módulos M17–M24 (IMAGE, NEURAL RENDER, HEALTH, STORAGE, INSTALLER, FIRST RUN, EXPERIENCE ENGINE, SESSION); LIBRARY en M13 y AUDIO en M16; M02, M07, M08 y M10 actualizados (métricas de arranque, Visual Engine, ciclo de vida, Steam en segundo plano, generación de fotogramas con condiciones); fases F2–F9 reordenadas hacia 1.0 RC; bloqueos P0; V-12 a V-17 |
| 1.1 | 2026-11-06 | Configuración de referencia 8 núcleos / 40 CU (D-16, D-17); principio A12 sin cifras inventadas (D-18); M04, M10 y M11 rediseñados para esa configuración; F0 incluye el módulo de 40 CU; V-02 cerrado |
