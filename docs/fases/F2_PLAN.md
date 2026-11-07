# F2 — Sesión STONE y STONE Home

Estado: **en implementación** bajo D-20. Rama `f2-session`. Fecha: 2026-11-07.
Arquitectura v1.2: M24 STONE SESSION, M07 STONE HOME, M08 STEAM BRIDGE, M22 FIRST RUN, M02 (métricas de arranque), M01 (pantalla de actualizaciones). Decisión central: D-21.

## 1. Lo que se investigó antes de diseñar (V-12, V-13)

Leído en el código fuente. Commits consultados el 2026-11-07:

| Proyecto | Commit | Uso en Bazzite |
| --- | --- | --- |
| ChimeraOS `gamescope-session` | `73d2da8` | Lanzador de las sesiones `gamescope-session-plus@<nombre>` |
| ChimeraOS `gamescope-session-steam` | `1a3fdb7` | Define la sesión `steam` |
| ShadowBlip `OpenGamepadUI` | `0db5812` | Interfaz propia sobre Gamescope (la sesión `ogui-steam` de Bazzite 44) |
| ValveSoftware `gamescope` | `309eee7` | Compositor |

| Hallazgo | Evidencia | Consecuencia para STONE |
| --- | --- | --- |
| `gamescope-session-plus` carga la sesión `<nombre>` de `/usr/share/gamescope-session-plus/sessions.d/<nombre>` (también `/etc/…` y `~/.config/…`). Es un script de shell que exporta variables; la clave es **`CLIENTCMD`**, el programa principal de la sesión | `gamescope-session-plus`, líneas 8–10 y 329–334; `sessions.d/steam` define `CLIENTCMD="steam -gamepadui -steamos3 -steampal -steamdeck"` | La sesión STONE es un archivo `sessions.d/stone` cuyo `CLIENTCMD` arranca STONE (Home + Steam en segundo plano). Se activa como `gamescope-session-plus@stone.service`, igual que `@steam` o `@ogui-steam` |
| La sesión puede definir `short_session_recover` (se llama si la sesión dura muy poco) y `post_gamescope_start` | `sessions.d/steam` | Recuperación de M24: tras fallos rápidos, la consola vuelve a la sesión de Game Mode de Bazzite (ruta de recuperación, D-21) |
| `gamescope-session-plus@.service` corre en el gestor de systemd **del usuario** (`BindsTo=graphical-session.target`) | `usr/lib/systemd/user/gamescope-session-plus@.service` | STONE Home y Steam corren como el usuario de la consola, nunca como root (A7) |
| Gamescope reconoce estas propiedades X11: `STEAM_BIGPICTURE` (la ventana es la interfaz de base), `STEAM_GAME` (AppID del juego), `STEAM_OVERLAY` y `GAMESCOPE_EXTERNAL_OVERLAY` (capas superpuestas), `STEAM_INPUT_FOCUS`, `GAMESCOPECTRL_BASELAYER_APPID`, `GAMESCOPE_FOCUSABLE_APPS`, `GAMESCOPE_FOCUSED_APP` | `gamescope/src/steamcompmgr.cpp` (definiciones `GAME_PROP`, `STEAM_PROP`, `OVERLAY_PROP`, `EXTERNAL_OVERLAY_PROP`, más los `XInternAtom` de los demás) | **Home** se marca como la interfaz de base (`STEAM_BIGPICTURE`). El **Quick Menu durante el juego** es una ventana superpuesta (`STEAM_OVERLAY`) que toma el mando con `STEAM_INPUT_FOCUS`, con el mismo mecanismo que usa OpenGamepadUI en modo superpuesto |
| OpenGamepadUI en modo superpuesto marca su ventana como superpuesta, cambia `STEAM_INPUT_FOCUS` entre su ventana y la de debajo, y se lanza dentro de una Gamescope ya en marcha | `core/ui/card_ui_overlay_mode/card_ui_overlay_mode.gd` (líneas 298–315), `rootfs/usr/bin/opengamepadui` | Precedente real de la arquitectura de D-21 en la misma base (Bazzite 44) |

Pendiente de la placa (sigue `[V]`): el comportamiento exacto de Steam sin interfaz (V-14), Steam Input y el primer inicio de sesión (V-15), y las actualizaciones del cliente de Steam (V-16).

## 2. Diseño

```
SDDM (inicio automático) → gamescope-session-plus@stone.service (usuario)
  └─ sessions.d/stone:  CLIENTCMD = stone-session
       stone-session (supervisor, usuario):
         1. arranca Steam en segundo plano (sin interfaz de Game Mode)    [V-14]
         2. arranca STONE Home (Chromium, ventana marcada STEAM_BIGPICTURE)
         3. vigila a los dos: reinicio controlado; tras N fallos rápidos → recuperación
       short_session_recover: vuelve a la sesión de Game Mode de Bazzite y deja el motivo registrado
  JUGAR → Steam lanza el juego (reaper, STEAM_GAME) → Gamescope lo pone al frente
  Botón guía → Quick Menu de STONE (ventana STEAM_OVERLAY + STEAM_INPUT_FOCUS)       [V-13]
  Salir del juego → foco de vuelta a Home (STEAM_BIGPICTURE)
```

Plan B de cada incógnita (si la placa lo contradice):
- **Steam no arranca sin interfaz (V-14):** se arranca con su interfaz normal, tapada por Home como capa de base. Steam queda vivo y nunca al frente.
- **El Quick Menu superpuesto no toma el mando (V-13):** el botón guía devuelve a Home y el juego sigue abierto en segundo plano (comportamiento de rc23).

## 3. Trabajo

| # | Pieza | Origen | Resultado verificable |
| --- | --- | --- | --- |
| 1 | `sessions.d/stone` + `stone-session` (supervisor con reinicio limitado y recuperación) | Nuevo, sobre el formato investigado | Pruebas con Steam y Home simulados: arranque, caída de Home, caída de Steam, N fallos → recuperación |
| 2 | STONE Home: host, puente con `stoned`, biblioteca de Steam, transporte HTTP seguro, Chromium | rc23 `stone_home/` (app, host, bridge, library, vdf, server, chromium, system, steamcef) | Pruebas de rc23 portadas (`test_home.py`, `test_server.py`) |
| 3 | Interfaz (`index.html`) con el diseño de rc23 | rc23 | Se porta tal cual en F2. La reconstrucción modular (R-08) es un paso propio dentro de F2, después de que la sesión funcione |
| 4 | Ventana de Home marcada como base y Quick Menu superpuesto | Nuevo | Prueba con un Xwayland simulado (Xvfb) que comprueba las propiedades X11 |
| 5 | FIRST RUN, métricas de arranque (BOOT TO VISUAL / BOOT TO READY), pantalla de actualizaciones | Nuevo + rc23 `system.py` | Pruebas de software |
| 6 | Imagen: Chromium, sesión `stone` como sesión automática, Game Mode como recuperación | `build.sh` | Build en CI; `STONE_PHASE="F2"` |

## 4. Puerta

- **Software:** CI completo (validación sin omisiones y todas las pruebas).
- **Placa:** §17, §19, §20, §23, §26, T-SESS-01 a 07, T-BOOT-01, T-FR-01, T-HOME-01 y 02.
- La primera sesión en la placa cambia a la imagen nueva **sin borrar nada** (`bootc switch`, con rc23 como despliegue anterior) e incluye el diagnóstico de solo lectura aprobado (D-14).

## 5. Estado (2026-11-07)

Estados según D-23. Nada de esto se ha observado todavía en la placa.

| # | Pieza | Estado | Dónde |
| --- | --- | --- | --- |
| 1 | Sesión STONE y supervisor | CODE TESTED | `supervisor.py`, `sessions.d/stone`, `tests/test_session.py` |
| 2 | Host de Home, puente, biblioteca, Chromium | CODE TESTED | `stone_home/`, `tests/home_suite.py`, `tests/server_suite.py` |
| 3 | Interfaz de rc23 | CODE TESTED (portada) | `dev/home/` → `apps/stone-home/ui/index.html` |
| 4 | Foco de Gamescope: Home como interfaz principal y el juego delante | CODE TESTED (Xvfb en CI) | `gamescope_x11.py`, `tests/test_gamescope_x11.py` |
| 4 | Botón guía durante un juego: Home al frente, el juego sigue detrás; REANUDAR lo devuelve (plan B de V-13) | CODE TESTED | `guide.py`, `supervisor.FocusKeeper`, `host.m_session_resume`; `tests/test_guide.py`; placa T-SESS-04 |
| 4 | Quick Menu superpuesto y transparente encima del juego (plan A de V-13) | Pendiente de la placa | Se decide después de T-SESS-04 |
| 5 | Métricas de arranque | CODE TESTED | `bootmetrics.py`, `stone-session boot`; prueba en placa T-BOOT-01 |
| 5 | FIRST RUN | CODE TESTED | `firstrun.py`, `home_parts/power_boot.js`; prueba en placa T-FR-01 |
| 5 | Pantalla de actualizaciones | CODE TESTED | `system.update_timer`, `home_parts/catrows.js`; V-18, T-UPD-01 |
| 6 | Imagen con la sesión instalada (no automática) | CODE TESTED (build en CI) | `build.sh` §6d |

**Métricas de arranque.** Se registran dos momentos por arranque, en segundos desde que arranca el kernel:
- **BOOT TO VISUAL:** aparece el primer fotograma de STONE Home, la línea sobre negro.
- **BOOT TO READY:** Home responde al mando.

Si un arranque se mide dos veces, vale la primera, así que reiniciar Home no cambia los números. El tiempo del firmware y del cargador no entra en estas cifras: se guarda aparte, tal como lo da `systemd-analyze time`. Plymouth sale antes que BOOT TO VISUAL y no se mide. Los datos van a `~/.local/state/stone/boot-metrics.jsonl` y se consultan con `stone-session boot`.

**FIRST RUN.** Se muestra una vez en una instalación nueva; una consola que ya tiene ajustes de Home no lo ve. Son cuatro pantallas que solo leen:
1. Bienvenida, con la configuración detectada (placa, núcleos y CU frente a la referencia) y Safe Mode si está activo.
2. Pantalla conectada.
3. Cuenta de Steam. Si no hay ninguna, ofrece iniciar sesión (V-15).
4. Rendimiento en BALANCED.

FIRST RUN no sube frecuencias, no calibra y no activa nada experimental (A2). Conectividad y audio llegan con CONNECT y SETTINGS en F6. Para volver a verlo, se borra `~/.config/stone/firstrun.json`.

**Actualizaciones.** La pantalla muestra tres cosas:
- la versión instalada;
- la versión preparada, si la hay, con el botón «Reiniciar y actualizar»;
- el estado de la comprobación automática de Bazzite, leído en systemd sin privilegios: activa o no, la última vez y la próxima.

Dentro de la sesión STONE ya no remite al botón STEAM, que ahí no está a la vista. La búsqueda manual queda abierta en V-18.

**Pendiente conocido (V-19).** Las filas «Abrir en Steam» de Ajustes asumen la interfaz de Steam al frente. En la sesión STONE hay que comprobarlas en la placa (T-SESS-08).

**Botón guía en la sesión STONE (plan B de V-13).** El supervisor lee el botón guía directamente de los mandos con python-evdev, así que no depende de cómo trate Steam ese botón (V-14).

Con un juego al frente, pulsarlo pone STONE Home delante y el juego sigue abierto detrás. Home muestra entonces su pantalla de juego:
- A reanuda la partida.
- ☰ abre el menú de STONE.
- B vuelve al inicio.

REANUDAR quita la marca `STONE_HOME_FRONT` de la ventana raíz y el supervisor vuelve a poner el juego al frente. La marca también se quita sola cuando el juego termina o empieza otro.

Una misma pulsación puede llegar por dos dispositivos, el mando y el mando virtual de Steam; las pulsaciones con menos de 0,6 s de diferencia cuentan una sola vez.

Queda por comprobar en la placa (T-SESS-04):
- si Steam también reacciona al botón;
- si Chromium recibe el mando al volver al frente.

El plan A, con el menú superpuesto y transparente como hace OpenGamepadUI (`STEAM_OVERLAY` y `STEAM_INPUT_FOCUS` en su ventana), se decide después de esa prueba.
