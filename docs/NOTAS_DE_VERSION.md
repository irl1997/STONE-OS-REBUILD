# STONE OS (rebuild) 0.4.0-dev.1 — llegar y jugar

**La consola arranca directamente en STONE**, sin comandos (D-29). Incluye todo lo de 0.3.0-dev.1 (F0, F1 y F2).

## Novedades

- **Sesión STONE automática.** STONE Home delante y Steam oculto, desde el primer encendido.
- **Guardia de arranque.** Si dos arranques seguidos no llegan a mostrar STONE Home, la consola vuelve sola al Game Mode de Bazzite. `stone-session status` explica por qué y `sudo stone-session default on` la recupera.
- **Escritorio desde Home:** Energía → Escritorio. En el escritorio, «Volver a STONE». Un reinicio también vuelve a STONE.
- **Red:** el cable Ethernet funciona sin configurar nada. El Wi-Fi y el audio desde STONE llegan en F6.

## Estado

| | |
| --- | --- |
| Software | CODE TESTED |
| Hardware | NOT TESTED: nada se ha probado aún en la BC-250 (D-28). Instalar la ISO borra el disco |

---

## Lo que ya traía 0.3.0-dev.1 (F2)

Primera versión de la reconstrucción con la consola completa de STONE OS para STONE MACHINE: AMD BC-250 con 8 núcleos y 40 CU. Incluye F0, F1 y F2.

### Qué trae

- **Base:** Bazzite `bazzite-deck:stable-44`, fijada a la de las mediciones de rc14–rc23. Regulador de GPU v0.4.14, fijado. `amdgpu` con la opción de 40 CU, `stone-cu40` y la guardia de arranque. Tema de arranque STONE, sin reposo.
- **`stoned` (F1):** perfiles SILENT, BALANCED y PERFORMANCE; última configuración buena; Safe Mode; telemetría y límites térmicos; perfiles por juego; calibración; configuración de referencia de 8 núcleos y 40 CU.
- **Sesión STONE (F2):**
  - STONE Home delante, con Steam oculto;
  - el juego al frente al jugar;
  - el botón guía devuelve a Home y REANUDAR devuelve el juego;
  - si Home falla varias veces, la consola pasa al Game Mode de Steam.
- **STONE Home:** la interfaz de rc23, más:
  - FIRST RUN en una instalación nueva;
  - métricas de arranque BOOT TO VISUAL y BOOT TO READY (`stone-session boot`);
  - pantalla de actualizaciones adaptada a la sesión STONE.
- **STONE DISPLAY y STONE OPTIMIZED**, portados de rc23.
- **Procedencia completa** en `/usr/lib/stone-release`. Imagen firmada sin clave (Sigstore).

### Qué no trae todavía

- El Quick Menu superpuesto encima del juego: llega tras la prueba T-SESS-04.
- Performance Center y TUNING (F3), GRAPHICS (F4), EXPERIENCE ENGINE (F5), CONNECT (F6), DOWNLOADS (F7), EMULATION (F8) y DESKTOP (F9).
