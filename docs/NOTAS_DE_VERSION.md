# STONE OS (rebuild) 1.0.0-rc1

La primera versión candidata de STONE OS para STONE MACHINE (AMD BC-250, 8 núcleos, 40 CU), con todo el plan del prompt maestro (D-31). Se instala desde cero con la ISO y arranca directamente en STONE.

**Es una versión candidata: todo está probado en software (CODE TESTED) y nada se ha observado todavía en la BC-250.** Instalar la ISO borra el disco de la consola.

## Llegar y jugar

- **Arranque directo:** la consola arranca en la sesión STONE: STONE Home delante y Steam oculto.
- **Guardia de arranque:** si dos arranques seguidos no llegan a mostrar Home, la consola vuelve sola al Game Mode de Bazzite y explica por qué.
- **FIRST RUN:** placa, núcleos y CU, comprobación del sistema, pantalla, oferta de activar 40 CU, cuenta de Steam y rendimiento en BALANCED.
- **Energía:** Apagar, Reiniciar, Escritorio («Volver a STONE» para regresar) y Opciones de arranque (Safe Mode, versión anterior).

## Diseño Estratos

Toda la interfaz en capas como roca vista en corte, con etiquetas de muestra, la veta ámbar y el estado de la máquina siempre a la vista.

## Rendimiento y salud

- **Perfiles:** SILENT, BALANCED y PERFORMANCE; CUSTOM con pruebas; perfil por juego; calibración; última configuración buena y Safe Mode.
- **40 CU desde STONE:** activar, probar 3 minutos y apagar, con confirmación; una guardia vuelve a 24 CU si hay errores de GPU.
- **STONE HEALTH** (Ajustes → Salud) y `stone-doctor`: CPU, memoria, discos, servicios y errores de GPU.
- **Caja negra:** los errores del arranque anterior, conservados para diagnóstico.

## Imagen

- **Escalado por juego:** FSR del juego, FSR de pantalla, OptiScaler y HelixSR.
- **STONE IMAGE:** aspectos NATURAL, CLARITY, CINEMA, VIVID y RETRO por juego (vkBasalt).
- **Generación de fotogramas** (experimental, con OptiScaler y nunca en juegos con anti-cheat ni en línea).
- **STONE DISPLAY:** la pantalla real y lo que cabe en la conexión.

## Inteligencia

**EXPERIENCE ENGINE**, con reglas fijas y sin IA generativa:
- confianza por juego;
- última medición (FPS, 1 % más lento, tirones);
- aviso cuando algo cambió desde la medición;
- mejor configuración medida para calidad, equilibrio y fluidez;
- previsión térmica en el modo técnico;
- autorreparación: apaga el aspecto de un juego que se cerró mal.

## Conexiones y ajustes

- **Bluetooth:** buscar, emparejar, conectar y olvidar mandos y auriculares, con su batería.
- **Audio:** salida y volumen.
- **Red:** cable, y Wi-Fi con teclado en pantalla.

## Biblioteca, descargas y almacenamiento

- **Almacenamiento:** espacio por disco con aviso, juegos por tamaño, caché de sombreadores y datos de Proton.
- **Descargas** de Steam en curso.
- **Limpiar caché** y **desinstalar** desde la interfaz de Steam.

## Emulación

- **Emuladores:** 12 de Flathub.
- **Tus juegos** en `~/Emulation/roms/<consola>`: STONE los añade a la biblioteca y se abren con su emulador como cualquier juego.

## Calidad

- **Pruebas en CI:** la consola, Home en navegadores reales, la sesión STONE y la firma.
- **Prueba de humo de la imagen:** antes de publicar se comprueban programas, servicios y módulos.
- **Firma:** imagen firmada sin clave (Sigstore).

## No incluido

- **NEURAL RENDER:** solo la arquitectura, sin ningún backend activo.
- **Menú superpuesto encima del juego:** se decide tras probar el botón guía en la placa.
- **Instalador con imagen propia:** de momento es Anaconda, con un informe de instalación.
