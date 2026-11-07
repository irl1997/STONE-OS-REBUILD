# STONE OS (rebuild) 0.3.0-dev.1 — F2

Primera versión de la reconstrucción con la consola completa de STONE OS para STONE MACHINE: AMD BC-250 con 8 núcleos y 40 CU. Incluye F0, F1 y F2.

**Es una versión de desarrollo para la primera sesión en la placa** (`docs/fases/F2_PRIMERA_SESION_PLACA.md`). Todo está en CODE TESTED: nada se ha observado aún en el hardware.

## Qué trae

- **Base:** Bazzite `bazzite-deck:stable-44`, fijada a la de las mediciones de rc14–rc23. Regulador de GPU v0.4.14, fijado. `amdgpu` con la opción de 40 CU, `stone-cu40` y la guardia de arranque. Tema de arranque STONE, sin reposo.
- **`stoned` (F1):** perfiles SILENT, BALANCED y PERFORMANCE; última configuración buena; Safe Mode; telemetría y límites térmicos; perfiles por juego; calibración; configuración de referencia de 8 núcleos y 40 CU.
- **Sesión STONE (F2), instalada pero no automática:**
  - STONE Home delante, con Steam oculto;
  - el juego al frente al jugar;
  - el botón guía devuelve a Home y REANUDAR devuelve el juego;
  - si Home falla varias veces, la consola pasa al Game Mode de Steam.
  - Se activa con `sudo stone-session default on` y se desactiva con `default off`.
- **STONE Home:** la interfaz de rc23, más:
  - FIRST RUN en una instalación nueva;
  - métricas de arranque BOOT TO VISUAL y BOOT TO READY (`stone-session boot`);
  - pantalla de actualizaciones adaptada a la sesión STONE.
- **STONE DISPLAY y STONE OPTIMIZED**, portados de rc23.
- **Procedencia completa** en `/usr/lib/stone-release`. Imagen firmada sin clave (Sigstore).

## Qué no trae todavía

- El Quick Menu superpuesto encima del juego: llega tras la prueba T-SESS-04.
- Performance Center y TUNING (F3), GRAPHICS (F4), EXPERIENCE ENGINE (F5), CONNECT (F6), DOWNLOADS (F7), EMULATION (F8) y DESKTOP (F9).

## Estado

| | |
| --- | --- |
| Software | CODE TESTED: CI con validación sin omisiones, pruebas de `stoned`, Home, sesión y navegadores reales |
| Hardware | NOT TESTED: primera sesión en la placa pendiente |
