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
