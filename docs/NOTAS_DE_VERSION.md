# STONE OS (rebuild) 1.0.0-rc4

Auditoría de experiencia de consola: todo se hace con el mando, sin terminal y sin pantallas de Steam salvo el inicio de sesión. Detalle completo en `docs/AUDITORIA_CONSOLA.md`. **Probado en simulación (CODE TESTED); nada observado todavía en la placa.**

## Cambios en rc4

- **Configuración del primer encendido** a pantalla completa, como la de una consola: mando, internet (Wi-Fi con teclado en pantalla), pantalla y encuadre, sonido, rendimiento (40 CU solo si lo eliges), cuenta de Steam.
- **Encuadre** para televisores que cortan los bordes: Ajustes → Pantalla → Encuadre.
- **Pantalla de carga** al jugar, con el arte del juego, los ajustes que se usarán y una barra que avanza hasta que el juego está delante. Si el juego no se abre, STONE pregunta qué hacer.
- **Preguntas de Steam en STONE:** si Steam pregunta algo (partidas de la nube, opciones de arranque), STONE lo muestra con su diseño y responde por ti.
- **Ficha del juego ordenada:** las opciones de imagen están en «Gráficos»; «Propiedades» muestra los datos del juego y permite desinstalarlo.
- **Media:** tus capturas (STEAM + R1 durante el juego), con visor a pantalla completa.
- **Explorar:** Buscar juegos, Descargas y Emuladores, sin abrir Steam.
- Sin terminal: se quitaron todas las indicaciones de comandos. HelixSR ya no se instala desde la consola (su instalador solo funciona en terminal).
- El escritorio de Linux pasa a Ajustes → Sistema → Modo escritorio.
- Corregidos textos superpuestos o cortados en la ficha del juego, al jugar, en Inicio con nombres largos, en Ajustes y en el visor.

# STONE OS (rebuild) 1.0.0-rc3

## Cambios en rc3

- **Actualizaciones más pequeñas.** La imagen se reparte ahora en capas estables (chunkah, igual que Bazzite): cada paquete va siempre en la misma capa, así que la consola solo descarga lo que cambia entre versiones. Hasta rc2, cambiar un solo archivo obligaba a bajar casi toda la imagen (rc1 → rc2: unos 7 GB).
- **Aviso:** la actualización de rc2 a rc3 todavía es grande, una sola vez, porque las capas cambian de forma. A partir de rc3, cada actualización baja solo las capas que cambian.
- Cada compilación dice en su resumen cuánto descargará una consola que esté en la versión anterior del canal.

## Cambios en rc2

Primera corrección tras instalar 1.0.0-rc1 en la BC-250.

- **La biblioteca muestra los juegos de tu cuenta que no están instalados.** Hasta ahora STONE solo los leía de la interfaz de Big Picture, que no se carga con Steam oculto en la sesión STONE. Ahora usa también la lista de aplicaciones que Steam carga siempre. Y en una instalación nueva, la conexión con la interfaz de Steam funciona desde el primer arranque.
- **Instalar desde STONE:** INSTALAR descarga el juego sin abrir el diálogo de Steam, que en la sesión STONE quedaba oculto. La descarga se ve en Ajustes → Almacenamiento. Desinstalar tampoco abre diálogos: STONE pregunta antes.
- **Buscar juegos:** botón Y o «Buscar» en Inicio y en la Biblioteca. El teclado en pantalla busca en tu biblioteca y en la tienda de Steam. Un juego gratis se instala desde STONE; uno de pago se compra en Steam y aparece en tu biblioteca.
- **Ajustes → Salud** dice si la interfaz de Steam responde.

## Lo que trae 1.0.0-rc1


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
