# Plan hasta STONE OS 1.0 RC

Objetivo (D-25, D-28): una ISO que se instala y deja la consola lista para **llegar y jugar**, con todas las funciones del prompt maestro y un diseño propio de STONE MACHINE.

Fecha: 2026-11-07. Decisiones de partida:
- **D-28:** todo seguido, sin esperar a la placa.
- **D-29:** la sesión STONE es la automática desde la próxima versión.
- **D-30:** rediseño a partir del sistema visual actual.

## Cómo se trabaja

- **Una versión por bloque**, cada una con su imagen firmada, su ISO y su *release*: 0.4.0-dev.1, 0.5.0-dev.1… hasta 1.0.0-rc1.
- **El propietario** solo publica ramas, fusiona y sube la etiqueta de versión, con la guía paso a paso.
- **Estados (D-23):** sin placa, nada pasa de `CODE TESTED` / `READY FOR HARDWARE TEST`. La matriz `hardware/validation/matrix.yaml` lleva cada prueba de placa pendiente.
- **Funciones que dependen de datos que solo da la placa** (FPS, consumo, sensores): se implementan con la detección de si el dato existe. Si no existe, la función se muestra como «no disponible» y nunca se inventa la cifra (D-18).

## Bloques en orden

| Versión | Bloque | Contenido | Módulos |
| --- | --- | --- | --- |
| 0.4.0-dev.1 | **Llegar y jugar** | Sesión STONE automática en la imagen; guardia de arranque (dos arranques sin Home operable → vuelve el Game Mode y se explica); «Cambiar a escritorio» y «Volver a STONE» desde Home, porque en la sesión STONE no hay menú de Steam; FIRST RUN con red (Wi-Fi), mando y audio básicos; ISO que instala sin preguntas técnicas | M24, M02, M05, M15 (base), M22, M21 (base) |
| — | **Direcciones de diseño** | 2 o 3 direcciones visuales sobre piedra, basalto y THE LINE, con Home, Ficha de juego y Menú rápido de ejemplo. El propietario elige una | D-30 |
| 0.5.0-dev.1 | **Nuevo diseño + Home modular** | Reconstrucción modular de la interfaz (R-08) con el lenguaje elegido: componentes, temas, sonido, movimiento; Plymouth y FIRST RUN a juego; sin perder nada de lo que hay | M07, M02 |
| 0.6.0-dev.1 | **F3 · Rendimiento y salud** | Performance Center completo, STONE TUNING, CALIBRATION desde la interfaz, 40 CU gestionados desde STONE (activar, probar, desactivar con confirmación), STONE HEALTH con Crash Black Box | M04, M06, M19 |
| 0.7.0-dev.1 | **F4 · Imagen** | DISPLAY ampliado, GRAPHICS (rutas por juego, OptiScaler, HelixSR, generación de fotogramas con las condiciones de D-22), STONE IMAGE (presets NATURAL, CLARITY, CINEMA, VIVID, RETRO, CUSTOM) | M09, M10, M17 |
| 0.8.0-dev.1 | **F5 · Inteligencia** | STONE OPTIMIZED ampliado y EXPERIENCE ENGINE: Autopilot, Thermal Forecast, Stutter Hunter, Regression Guard, Self-Healing, Confidence System… Reglas deterministas, sin IA generativa | M11, M23 |
| 0.9.0-dev.1 | **F6 · Conexiones y ajustes** | STONE CONNECT (Bluetooth, mandos, batería, jugador), SETTINGS propios (audio, red, idioma, hora, accesibilidad, sistema) | M12, M16 |
| 0.10.0-dev.1 | **F7 · Biblioteca y descargas** | Pantalla de Descargas con cola y progreso, desinstalar juegos, LIBRARY unificada, STONE STORAGE (espacio, cachés, limpieza, alertas) | M13, M20 |
| 0.11.0-dev.1 | **F8 · Emulación** | ROMs y BIOS aportados por la persona, juegos de emulador en la biblioteca de Home, perfiles por emulador | M14 |
| 1.0.0-rc1 | **F9 · Cierre** | DESKTOP completo, menú de arranque con mando (Safe Mode, versión anterior, escritorio), instalador con identidad STONE e informe de instalación, revisión final | M15, M02, M21 |
| — | **NEURAL RENDER** | Arquitectura de backends, marcada `EXPERIMENTAL`; ningún backend activo sin medición en la placa | M18 |

## Riesgos que se aceptan con D-28

| Riesgo | Si la placa lo confirma | Plan |
| --- | --- | --- |
| La sesión STONE no arranca bien en la BC-250 | Pantalla negra en el primer arranque | Guardia de arranque de 0.4.0 y vuelta al Game Mode; `Ctrl+Alt+F3` en la guía |
| El botón guía o el foco de Gamescope no se comportan como en el código fuente | No se vuelve a Home desde un juego | Plan B ya implementado (V-13); se ajusta tras la placa |
| Steam muestra ventanas (inicio de sesión, actualización) delante de Home | Se ve Steam un momento | V-14, V-16: se registran y se tapan en cuanto se sepa cuáles son |
| Datos de sensores o FPS que no existen | Funciones de F5 sin datos | Se muestran «no disponible» (D-18) |

## Lo que necesita el propietario en cada versión

1. Publicar la rama en GitHub Desktop.
2. Fusionar el Pull Request cuando el CI esté en verde.
3. Crear y subir la etiqueta `v<versión>`.
4. Instalar la ISO o cambiar de versión con la guía, cuando quiera.
