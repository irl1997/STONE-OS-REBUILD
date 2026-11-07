# F1 — STONED (servicio de sistema)

Estado: **en implementación** bajo D-20 (autonomía). Rama `f1-stoned`. Fecha: 2026-11-07.
Arquitectura: M03, M04 (base), M05, M06.

## Qué entra

| Pieza | Origen | Destino |
| --- | --- | --- |
| `stoned`: API D-Bus `org.stonemachine.Performance1`, perfiles, CUSTOM con prueba, calibración, LKG, recuperación, Safe Mode, telemetría, vigilancia térmica, partidas de Steam (14 módulos) | rc23 `system_files/usr/lib/stone/stoned/` | `services/stoned/stoned/` (R-10). La imagen lo instala en `/usr/lib/stone/stoned` |
| `stoned`, `stonectl` (lanzadores) | rc23 | `system/usr/bin/` |
| `stoned.service`, `stoned-recover.service`, sysusers, tmpfiles | rc23 | `system/usr/lib/` |
| Política D-Bus, acciones polkit (con `stoned` como propietario), regla polkit | rc23 | `system/usr/share/` |
| `stability.json` (carga vkmark) | rc23 | `system/usr/lib/stone/` |
| Suite de pruebas de `stoned` (ids R, I, P, T, S, G, C, B) y regulador simulado | rc23 `tests/run_tests.py`, `fake_governor.py` | `tests/stoned_suite.py` (pytest la ejecuta con `tests/test_stoned.py`), `tests/fake_governor.py` |

Cambios respecto a rc23, todos justificados:

| Cambio | Motivo |
| --- | --- |
| **Configuración de referencia** (`stoned/reference.py`): en cada arranque se comparan los núcleos físicos en línea y los CU de este arranque con `STONE_REFERENCE_CPU_CORES` y `STONE_REFERENCE_GPU_CU` de `stone-release`. Si no coinciden o no se pueden leer, CUSTOM (global, de sesión y por juego), las pruebas de estabilidad y la calibración se rechazan con `Unsupported` y el motivo. Los perfiles de fábrica siguen disponibles. `GetCapabilities` añade `configuration` (`reference`, `detected`, `matches`, `reasons`; `matches` falta si la imagen no tiene referencia) | D-16, T-PERF-01 |
| La huella de la calibración incluye los núcleos de CPU (`cores`): cambiar el número de núcleos deja la calibración `stale` | D-16 (M11 y M04 usan la misma huella) |
| `stonectl display` sin STONE DISPLAY en la imagen responde «llega en F4» en lugar de fallar | STONE DISPLAY es F4 |
| La imagen declara `STONE_PHASE="F1"` y ya no lista `stoned` entre los módulos ausentes | Procedencia |

La regla polkit sigue como en rc23 (grupo `wheel`). Acotarla al usuario de la consola (R-09) necesita conocer cómo crea Bazzite ese usuario y se hará con la sesión STONE (F2), donde cambia el contexto de los procesos.

## Pruebas

| Suite | Dónde corre |
| --- | --- |
| `tests/stoned_suite.py`: 88 casos de rc23 + REF01–REF03 (configuración de referencia: coincide, no coincide y rechaza, imagen sin referencia) | CI y contenedor de desarrollo (D-Bus + PyGObject) |
| `tests/test_reference.py`: 7 casos (núcleos frente a hilos, CPU fuera de línea, topología ilegible, motivos, sin referencia) | En cualquier máquina |
| `validate.sh`: unidades de `stoned` (`systemd-analyze verify`), XML de D-Bus y polkit, `stoned` propietario de las acciones polkit, interruptores de prueba ausentes en las unidades | CI |

## Puerta de placa (diferida, D-19)

§0, §2–§13, §15 y T-PERF-01 en la BC-250, junto con la puerta de F0. La primera imagen que se instale en la placa incluirá `stoned` (F0-B).
