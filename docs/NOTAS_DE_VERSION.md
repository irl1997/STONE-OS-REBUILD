# STONE OS (rebuild) 0.2.0-dev.1 — F0

Primera imagen de la reconstrucción de STONE OS para STONE MACHINE (AMD BC-250, 8 núcleos, 40 CU).

**Es una imagen de validación, no una versión para la consola.** No trae `stoned` ni STONE Home: no la instales para uso diario (F0-B). Nada está verificado en hardware.

## Qué trae

- Base Bazzite `bazzite-deck:stable-44` fijada a la de las mediciones de rc14–rc23.
- Regulador de GPU v0.4.14, fijado y con su paquete archivado en la release.
- Módulo `amdgpu` con la opción de 40 CU, `stone-cu40` y la guardia de arranque.
- Tema de arranque STONE.
- Consola sin reposo.
- Procedencia completa en `/usr/lib/stone-release`.

## Qué no trae todavía

`stoned` (F1), STONE Home (F2), Performance Center y calibración (F3), DISPLAY y GRAPHICS (F4), OPTIMIZED (F5), CONNECT (F6), DOWNLOADS (F7), EMULATION (F8) y DESKTOP (F9).

## Estado

| | |
| --- | --- |
| Software | CODE TESTED (CI) |
| Hardware | NOT TESTED: puerta de placa diferida (D-19) |
