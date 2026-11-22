# STONE OS (rebuild) 3.1.0-rc16

Desde el informe de la rc15 en la consola (22-11-2026, 19:42): FSR 3.1 que no se activó en Batman: Arkham City, y HelixSR, que no aparecía.

## FSR 3.1 no se activó en Batman: Arkham City: por qué, y que no vuelva a pasar

- **STONE hizo lo que tenía que hacer:** vio que OptiScaler no se cargó dentro del juego, lo marcó como «No se activó», lo avisó y la siguiente partida usó una opción segura.
- **El error fue ofrecerlo en ese juego.** Arkham City es un juego de **32 bits**, y OptiScaler y HelixSR son de 64 bits: un juego de 32 bits no puede cargarlos nunca. Además, Arkham City no trae DLSS, FSR ni XeSS para reemplazar.
- **Ahora STONE lee si el juego es de 32 o 64 bits** (en la cabecera de su ejecutable, sin contar instaladores ni lanzadores). En los juegos de 32 bits, FSR 3.1, HelixSR y la generación de fotogramas aparecen como «No disponible: juego de 32 bits». STONE no los instala ni los elige, ni siquiera si ya estaban instalados de antes.
- Para Batman: Arkham Asylum y Arkham City quedan Nativo y los aspectos (vkBasalt), que sí funcionan.

## HelixSR siempre aparece

Hasta la rc15, HelixSR solo aparecía si ya estaba instalado en el juego. Ahora siempre está en Gráficos → Reescalado:
- **Si no está instalado:** dice «Lo instalas tú», y al elegirlo explica cómo. HelixSR se instala con HelixSR Desktop, la app de su autor, en el Modo escritorio. La primera vez descarga archivos de NVIDIA y AMD y te pide aceptar sus licencias. STONE nunca acepta una licencia por nadie ni ejecuta instaladores descargados, por eso ese paso lo haces tú.
- **Para que STONE pueda activarlo y quitarlo en cada partida,** el archivo tiene que quedar como winmm.dll y no como dxgi.dll (la guía de HelixSR lo permite).
- **Ya instalado,** se elige como cualquier otra opción, y STONE comprueba después de cada partida si funcionó.
- En juegos de 32 bits, con anti-cheat o en línea aparece «No disponible», con el motivo.

# STONE OS (rebuild) 3.1.0-rc15

Reescalado y generación de fotogramas, ordenados en una elección simple por juego, con STONE comprobando que de verdad funcionan.

## Gráficos de un juego: dos elecciones claras

Hasta la rc14, en GRÁFICOS había cuatro filas sueltas: «Imagen», «Ajuste de FSR», «Fotogramas» e «Instalar FSR (OptiScaler)». OptiScaler había que instalarlo aparte antes de poder elegirlo, y la generación de fotogramas solo funcionaba si además estaba elegido OptiScaler como imagen. Ahora hay dos elecciones:

- **Reescalado:** Automático · Nativo · FSR del juego · FSR 3.1 (OptiScaler) · HelixSR (si lo instalaste tú). Debajo, la calidad: Calidad, Equilibrado, Rendimiento o Ultra rendimiento.
- **Generación de fotogramas:** Desactivada · FSR 3 (OptiScaler).

Cada opción dice en una línea qué hace y su estado:
- **Lista**, se puede usar ya.
- **Se instala al elegirla:** STONE descarga OptiScaler de la página de su autor, revisa que el archivo no venga alterado (SHA-256) y lo instala en el juego, sin nada que hacer a mano.
- **No disponible**, con el motivo: anti-cheat, juego en línea, el juego no trae DLSS, FSR 2/3 ni XeSS para reemplazar, u otro reescalador ya instalado. Se muestra igual, para que se sepa por qué.

Si eliges generación de fotogramas, el reescalado pasa solo a FSR 3.1 (OptiScaler), que es lo que la hace funcionar. Si después cambias a otro reescalado, la generación de fotogramas se apaga y STONE lo dice.

## STONE comprueba que funcionan

- **En cada partida con FSR 3.1,** STONE mira dentro de los procesos del juego si el archivo que instaló (winmm.dll, en la carpeta del juego) de verdad se cargó. También acepta como prueba el registro que escribe el propio OptiScaler durante la partida, para que un fallo de esa lectura nunca le quite FSR 3.1 a un juego donde sí funciona. Cuál de las dos pruebas ve la consola falta comprobarlo en ella.
- **Lo recuerda por juego:** bajo cada opción aparece «Funcionó en la última partida (fecha)» o «No se activó en la última partida: …».
- **Si no se cargó, o el juego se cerró nada más empezar,** al volver a STONE aparece un aviso, y la siguiente partida usa sola una opción segura (FSR del juego o Nativo).
- **Nunca en juegos con anti-cheat ni en línea.**

Lo que STONE no puede hacer es que una herramienta funcione en un juego que no la admite. Por eso esas opciones salen como «No disponible», con su motivo. La generación de fotogramas se comprueba hasta donde se puede ver desde fuera: OptiScaler cargado y configurado para generar fotogramas. Si el juego le da o no lo que necesita depende del juego, y el contador de FPS cuenta también los fotogramas generados.

## APEX Neural Rendering (ANR)

Lo revisamos el 22-11-2026 y por ahora no se agrega:
- Hoy solo existe su generación de fotogramas (ANR FG), en beta, que funciona a través de OptiScaler y solo en juegos con la generación de fotogramas de NVIDIA (DLSS-G).
- Su reescalado (ANR SR) no ha salido y su código fuente no está publicado.
- La BC-250 no aparece en su lista de GPU.

# STONE OS (rebuild) 3.1.0-rc14

La imagen sin alta definición y con grano, desde el informe de la rc13 en la consola (20-11-2026, 23:20).

## Por qué la imagen no se ve en alta definición

Con la rc13 volvieron el sonido y la identificación completa de la TV (reiniciando con la TV encendida). Los datos nuevos del informe muestran la causa del grano que queda:

- **La TV es 4K, pero esa entrada funciona en modo HDMI 1.4.** Solo acepta hasta 300 MHz: 4K a 30 Hz como máximo, y 4K a 60 Hz necesita unos 594 MHz.
- **Por eso STONE envía 2560 × 1440 a 60 Hz**, lo mejor a 60 Hz que acepta esa entrada, y la TV lo agranda 1,5 veces a su pantalla 4K. Esa escala no es exacta, y el realce de bordes que la TV aplica al agrandar se ve como grano. Pasa en todo: en el Inicio, en EA SPORTS FC 26 (sin ningún aspecto) y en Batman.
- **Los aspectos de la rc13 ya se aplicaron**: vkBasalt corre con el suavizado de bandas al final. El grano que queda no viene de ellos.

Qué hacer para verlo en 4K a 60 Hz:
1. En la TV, activa el modo HDMI mejorado de esa entrada (HDMI UHD Color, Input Signal Plus, HDMI 2.0 o similar).
2. Usa un adaptador ACTIVO DisplayPort 1.4 → HDMI 2.0 que diga «4K 60 Hz» y un cable HDMI de alta velocidad.
3. Mientras tanto, en la TV usa el modo Juego o PC y baja la Nitidez y la reducción de ruido.
4. Para ver la interfaz en 4K ya: Ajustes → Pantalla → Meta de imagen → Máxima resolución (4K a 30 Hz; para jugar es mejor Fluidez).

Lo que cambia en STONE:
- **Ajustes → Pantalla → Conexión** dice «TV 4K: esta entrada solo acepta 4K a 30 Hz (modo HDMI 1.4)» y, al elegirla, todo lo anterior.
- **El informe tiene una comprobación nueva, «Resolución (alta definición)»**: qué se envía, qué acepta la TV y la conexión, y qué hacer. También hay un síntoma nuevo para marcar: «Imagen borrosa o con grano».

# STONE OS (rebuild) 3.1.0-rc13

Sonido, grano en la imagen y el aviso de descargas, desde la prueba de la rc12 en la consola (20-11-2026).

## Sin sonido: el informe ahora dice por qué

En la consola, la única salida de sonido era «Dummy Output», una salida vacía que el sistema crea cuando no encuentra ninguna real. El informe decía «Sonido: FUNCIONA» porque esa salida estaba al 100 %. Ahora:

- **El informe marca FALLA** cuando no hay ninguna salida real y explica la causa. Sus datos muestran que la TV no le dijo a la consola que acepta sonido: no llegó la información de audio por HDMI/DisplayPort. En la misma prueba, la TV se identificó sin su parte HDMI y sin HDR. En la rc10 la misma consola, con el mismo núcleo, tenía «Digital Stereo (HDMI) [Beyond TV]» y HDR. Por eso apunta a cómo arrancó la conexión con la TV (TV apagada o en otra entrada al arrancar, o el adaptador DisplayPort→HDMI), no a STONE.
- **Ajustes → Audio** muestra «Sin salida de sonido» con qué hacer, y al arrancar aparece un aviso si no hay sonido.
- **El informe guarda** lo que la TV dijo de su sonido (ELD) y su identificación (EDID, con el número de serie tapado), y la profundidad de color de la conexión (drm_info, que entra en la imagen). Así el próximo informe confirma la causa.

Qué hacer: con la TV encendida y en la entrada de la consola, reinicia la consola. Si sigue sin sonido, desconecta y vuelve a conectar el adaptador o el cable, y en la TV revisa que esa entrada HDMI tenga activada la señal mejorada (HDMI UHD Color, Enhanced o similar).

## Grano en la imagen

- **En los juegos, con los aspectos NEXT-GEN, REALISTA, NATURAL y CINEMA.** El filtro que suaviza las bandas de vkBasalt termina con un tramado muy fino a propósito. STONE lo aplicaba primero, y la nitidez y la curva de color lo agrandaban hasta verse como grano (Batman: Arkham Asylum con NEXT-GEN). Ahora ese filtro va al final, sobre la imagen terminada, y NEXT-GEN da un poco menos de nitidez y frena más el ruido.
- **En toda la imagen, también en el Inicio de STONE.** Las fotos muestran grano donde los aspectos no actúan. Coincide con la TV identificada sin su parte HDMI (lo mismo que dejó la consola sin sonido), y una conexión con menos bits de color se ve con grano. El informe ahora guarda la profundidad de color de la conexión para confirmarlo. Con el sonido de vuelta (TV encendida al arrancar), revisa si el grano del Inicio también desaparece.

## El aviso de descargas ya no tapa las secciones

«Descargando EA SPORTS FC™ 26 · 1…» agrandaba la cápsula de la hora hacia la izquierda hasta quedar debajo de MEDIA y TIENDA. Ahora el aviso se acorta («…») para dejar siempre espacio a las secciones, y el porcentaje no se corta nunca.

# STONE OS (rebuild) 3.1.0-rc12

Juegos de emuladores en el Inicio, carga desde USB a prueba de fallos, un sistema de emuladores más robusto y arranques más rápidos. Decisión D-47.

## Los juegos de emuladores, en el Inicio con los demás

- **En el Inicio.** La fila muestra ahora 8 juegos de Steam y de emuladores juntos, ordenados por la última vez que se jugaron. Un juego de emulador que aún no has jugado se ordena por cuándo llegó a la consola, así que lo que acabas de copiar desde un USB aparece primero. Si tienes juegos de emuladores y ninguno entra en la fila, los últimos ocupan sus dos últimos puestos, para que siempre estén en el Inicio. Los emuladores en sí (Dolphin, PCSX2…) siguen en la Biblioteca, que tiene un filtro «Emuladores».
- **Con su consola.** Cada juego dice de qué consola es («PlayStation 2», «GameCube»…), en su portada y en su ficha, en vez de «Acceso directo». Los nombres van sin las etiquetas de región: «God of War (USA) [!]» aparece como «God of War».
- **Un juego cuyo archivo ya no está** (borrado, o en un USB desconectado) **deja de aparecer** en vez de fallar al abrirlo, y vuelve si el archivo vuelve.

## Juegos desde un USB: STONE los reconoce y los copia enteros

- **Reconoce las imágenes de disco sueltas por su contenido.** Una `.iso`, `.rvz`, `.wia` o `.gcz` que esté fuera de una carpeta con el nombre de la consola ya no se ignora: STONE lee las marcas de su formato y sabe si es de GameCube, Wii, PS2, PSP, PS3 o Xbox.
- **Juegos de varios archivos:**
  - Un `.cue` con sus `.bin` o un `.gdi` de Dreamcast con sus pistas se copian completos. Las pistas ya no aparecen como juegos sueltos.
  - Un juego en su propia carpeta se copia con todo lo que tiene. Dentro de esa carpeta, STONE elige el archivo que abre el emulador.
  - En la consola se reconocen igual: `.cue`/`.gdi`/`.m3u` y carpetas.
- **Una copia que no puede quedar a medias.**
  - Cada archivo se escribe aparte, se comprueba su tamaño y se graba en disco antes de tomar su nombre definitivo.
  - Si se desconecta el USB o se corta la luz, lo que quedó a medias se borra antes de la siguiente copia.
  - Los juegos que sí se copiaron entran en la biblioteca aunque la copia se cortara después.
  - Un archivo de índice nunca puede señalar fuera de la carpeta del juego.
- **Si a un juego le falta su emulador, STONE te dice cuál instalar.** Y cuando lo instalas, los juegos que lo esperaban aparecen solos.

## Emuladores más robustos

- **Los juegos aparecen solos.** Los que pones en `~/Emulation/roms` por cualquier vía (el móvil, un USB, el escritorio) se añaden a la biblioteca sin tener que pulsar «Añadir juegos». STONE revisa esa carpeta cada 30 s, fuera de los juegos.
- **Al cambiar de emulador, los juegos siguen abriéndose.** Si quitas Eden e instalas Ryujinx, tus juegos de Switch pasan al emulador instalado al empezar la siguiente sesión.
- **JUGAR con el emulador desinstalado** te dice cuál instalar, en vez de que Steam falle sin explicación.

## Más rápido al abrir un juego

- **La carpeta del juego se revisa una sola vez.** STONE recorría toda la carpeta (anti-cheat y OptiScaler, hasta 4 niveles) en cada JUGAR y cada vez que abrías la ficha. Ahora guarda el resultado del mismo juego y la misma versión, y lo descarta cuando instala o quita algo en el juego.
- **La tabla de color del aspecto se calcula una sola vez.** Antes costaba unos 0,13 s en un Mac en cada JUGAR, y más en la consola. Ahora solo se recalcula si el aspecto cambia, y el resto de veces tarda 0,0001 s.
- **La pantalla se lee una vez por lanzamiento**, no dos seguidas.
- **«Opción de inicio» recuerda tu elección.** Con «RECORDAR: SÍ», un juego con varias formas de iniciarse, como Batman: Arkham City, empieza directamente la próxima vez, igual que con el «Siempre» de Steam. Se olvida en Propiedades.
- **Cada JUGAR anota cuánto tarda STONE antes de pedírselo a Steam**, y el informe muestra cuántos segundos pasan de JUGAR al juego.

## Encendido más rápido

- **STONE se muestra sin esperar a la preparación de Steam.** Antes, la sesión preparaba a Steam primero (sus ajustes y los accesos directos) y solo después abría la pantalla de STONE. Ahora la pantalla se abre primero, y la preparación sigue en paralelo antes de que arranque Steam.
- **Sin pasos lentos nuevos antes de la pantalla.** La revisión de emuladores lee directamente las carpetas de Flatpak, que es instantáneo, en vez de ejecutar `flatpak list`.
- **El informe incluye el arranque** («arranque.txt»):
  - los tiempos de STONE en cada encendido;
  - lo que mide systemd: firmware, kernel y sistema;
  - los 40 servicios más lentos y la cadena que esperó.

  Así el próximo informe dirá qué más se puede quitar del arranque, que hoy está fuera de STONE: BIOS, menú de arranque y servicios del sistema base.

## Nuevo estilo de Inicio: «Panorama»

En **Ajustes → Pantalla → Estilo de inicio** se elige entre **Cristal** (el de siempre) y **Panorama**. Panorama convierte el Inicio en una pantalla de cine:
- el arte del juego que tienes seleccionado ocupa toda la pantalla, con una sombra suave para que se lea lo que hay encima;
- el nombre del juego aparece en grande a la izquierda;
- todos los juegos, también los de emuladores, van en una sola fila de carátulas apaisadas en el tercio inferior;
- se quita la línea de datos, y las pestañas de arriba y la fila del sistema de abajo siguen donde estaban.

Al moverte por la fila, el fondo y el nombre cambian con cada juego. La elección se guarda.

## El buscador de la tienda vuelve a encontrar juegos

Steam cambió su búsqueda: sin el país de la conexión responde **0 resultados** para cualquier palabra, y por eso salía «no existen juegos». Ahora STONE le pregunta a Steam qué país asigna a la conexión de la consola y lo usa en cada búsqueda. Es el mismo dato con el que Steam ya elige los precios y la moneda, así que no se envía nada nuevo. Comprobado contra la tienda real: «batman» pasa de 0 a 9 resultados.

## Fondos de los juegos nítidos

La imagen grande que Steam da a cada juego mide 1920 × 620, tres veces más ancha que alta. Para cubrir la pantalla, STONE la agrandaba 2,3 veces en un televisor de 2560 × 1440 (3,5 veces en uno 4K) y le recortaba casi la mitad de los lados. Por eso fondos como el de Batman se veían pixelados. Ahora la imagen va arriba, a lo ancho de la pantalla y casi a su tamaño real, y se funde abajo en una copia suave de sí misma. Cuando Steam tiene la versión al doble de tamaño (3840 × 1240), se usa esa. Los juegos que solo tienen carátula (sin imagen grande) muestran sus colores difuminados, en vez de una carátula estirada. La página de un juego en la tienda usa la misma banda. Para Batman: Arkham Asylum y Arkham City, Steam no tiene nada más grande: ni versión doble ni capturas de más de 1280 × 720.

## Carátulas de los juegos de emuladores

El servidor de carátulas de libretro, del que STONE baja las portadas de los juegos de emuladores, está vacío: responde 404 a todas las consolas, así que ningún juego de emulador recibía su portada. Ahora STONE recurre a la copia que libretro mantiene en GitHub (la misma colección de imágenes) cuando el servidor no responde o no lista nada. Una lista vacía que se haya guardado antes se vuelve a pedir. Comprobado contra los servidores reales: «Metroid Prime (GameCube)» recibe su portada.

Las portadas de estos juegos son cajas verticales y, en las tarjetas anchas (la primera del Inicio y todas las de Panorama), se recortaba una franja del medio. Ahora la caja se ve entera, centrada sobre una copia oscurecida de sí misma. En la ficha del juego, la caja aparece nítida a la derecha. El fondo difuminado de estos juegos (y de todos los que lo usan) se hacía agrandando 30 veces una copia de 64 × 36 píxeles, y se veían manchas cuadradas. Ahora es una copia de 240 × 135 desenfocada una sola vez al crearla: es suave y no tiene bloques.

## Repaso de la interfaz

Recorrimos cada sección en el simulador (Inicio, Biblioteca, Explorar, Media, Tienda, la ficha de un juego y sus ventanas, y las 15 secciones de Ajustes) y buscamos de forma automática textos cortados o que se salen de la pantalla. No apareció ninguno. Lo que se corrigió:

- **Propiedades** de un juego se abría con «Desinstalar» ya elegido: un A de más llevaba a la pregunta de desinstalar. Ahora tiene solo «Volver» (y «Olvidar opción de inicio» si hay una), porque «Desinstalar» ya está en la página del juego.
- **Explorar** escribía dos veces qué hace cada tarjeta, en la tarjeta y debajo de la fila, y en la tarjeta elegida el texto se partía en dos líneas. Ahora la tarjeta lleva solo su nombre y la explicación va una vez, debajo.
- **El fundido de la imagen del juego** con su copia suave dejaba una línea horizontal en algunos juegos (Cyberpunk 2077). Ahora el fundido es más largo y gradual.

## Prueba de uso como consola (QA)

Probamos STONE OS como se prueba una consola antes de certificarla: botones B e Inicio en cada pantalla, que la selección vuelva a su sitio al salir de cada pantalla, 120 pulsaciones al azar seguidas, jugar y volver, y STONE en una consola nueva, sin sesión de Steam y sin internet. Lo que se corrigió:

- **El teclado en pantalla (buscar, contraseñas Wi-Fi) no se podía cerrar con B.** B borraba la última letra y, con el texto ya vacío, no hacía nada. Solo se salía con la tecla ✕ de la última fila. Ahora B con el texto vacío cierra el teclado, y la ayuda de abajo dice «Salir».
- **El botón Inicio no hacía nada con una ventana abierta**, incluido el menú Apagar. Ahora cierra la ventana como lo haría B y lleva al Inicio. Si la ventana está sobre un juego abierto, vuelve al juego. Las ventanas que no se pueden cerrar con B (una pregunta que Steam espera, un trabajo en curso) siguen igual.
- **Ventanas que abrían con la opción peligrosa ya elegida:** la de un dispositivo Bluetooth («Olvidar»), la de un juego en Almacenamiento («Limpiar caché») y «Activar 40 CU» («Activar»). Ahora abren en «Volver» o «Cancelar», y los botones mantienen su orden.
- **Mensajes técnicos en pantalla:** sin internet, la tienda decía «no responde (URLError)». Al instalar o actualizar un emulador se veía el error interno de Python. Ahora se dice qué pasa con palabras («no hay conexión a internet», «no queda espacio en el disco», «tardó demasiado en responder…»), y el error exacto queda en el registro para el informe de diagnóstico.
- **El menú rápido en el juego:** «PERFORMANCE» llenaba su botón de borde a borde y quedaba más ancho que los otros tres perfiles. Ahora los cuatro botones miden lo mismo y tienen margen.

Lo que funcionó bien en la prueba: B vuelve atrás en todas las pantallas, la selección vuelve a la misma tarjeta al salir de un juego o de Ajustes, el botón Inicio lleva al Inicio desde cualquier sección, jugar → menú rápido → volver al juego, y no apareció ningún error tras las 120 pulsaciones al azar.

## Desinstalar juegos

- **Juegos de Steam:** «Desinstalar» está ahora en la propia página del juego. Antes solo estaba dentro de Propiedades y en Ajustes → Almacenamiento. Para dejarle sitio, «Experiencia» pasa a GRÁFICOS.
- **Juegos de emuladores:** ahora también se pueden desinstalar. Se borran de la consola con todas sus partes (pistas, carpeta del juego), y solo dentro de la carpeta de juegos de STONE. Tus partidas guardadas se conservan en el emulador.

## Auditoría de esta versión

Se revisó todo el código nuevo de la rc12 y se corrigieron 4 errores reales y 6 detalles:
- **Una carpeta con varios juegos** (por ejemplo «PS2/Colección/» con varias ISO) se tomaba como un solo juego y solo se veía el más grande. Ahora cada archivo es un juego. Solo cuentan como un único juego las carpetas con un archivo índice (`.cue`, `.gdi` o `.m3u`) y las de Switch, PS3 y Wii U, que traen el juego junto a sus actualizaciones.
- **Una ISO dañada o cortada** hacía fallar la búsqueda en todo el USB. Ahora esa imagen simplemente no se reconoce, y los demás juegos del USB se ofrecen igual.
- **Un `.gdi` suelto en la raíz del USB** se copiaba sin sus pistas. Ahora se copia con ellas.
- **Los juegos copiados a mano justo después de encender** podían no aparecer hasta reiniciar si la interfaz de Steam aún no respondía. Ahora STONE vuelve a intentarlo hasta que Steam responde.
- **Detalles corregidos:**
  - Al cambiar de televisor, el siguiente JUGAR vuelve a leer la pantalla.
  - Un HelixSR instalado con el instalador de su autor se ve en 30 s como mucho.
  - Si Steam no indica el país, la búsqueda lo dice en vez de responder que no hay juegos.
  - Al cancelar una desinstalación, el foco vuelve a «Desinstalar».
  - Al empezar la sesión, las peticiones viejas se descartan antes de abrir STONE.
  - El informe ya no ejecuta dos veces la misma consulta del arranque.

Comprobado:
- las 35 baterías de pruebas;
- el análisis estático de Python (ruff) y el de la página (ESLint);
- un recorrido completo en el simulador, sin errores de JavaScript: los dos estilos de Inicio, Explorar, Media, la Biblioteca con el filtro de emuladores, las fichas, GRÁFICOS, Propiedades, la búsqueda, la tienda, Ajustes e Informe.

Tres pruebas solo pueden ejecutarse en GitHub (necesitan GTK o un Python más nuevo que el del Mac).

## Además

- **Preferencias que se reiniciaban solas.** Guardar cualquier preferencia (un favorito, el volumen…) devolvía a su valor por defecto «Juegos ven», «Meta de imagen» y STONE OPTIMIZED. Ahora se conservan.

**Todo está probado en software (CODE TESTED) y en el simulador. Nada de esta versión se ha observado todavía en la BC-250.** Pruebas de placa: T-EMU-15 a 19, T-STORE-02, T-HOME-12, T-BOOT-11 y T-PERF-02.

# STONE OS (rebuild) 3.1.0-rc11

Hecha con el **cuarto informe de la consola** (19-11-2026, 22:55) y tus fotos: filtros que se notan más, dos filtros nuevos, menos grano, el error de OptiScaler y el diálogo «Opción de inicio». Decisión D-46.

## Filtros de imagen (Aspecto): más notables, nuevos y sin grano

- **El grano.** Todos los filtros afilaban la imagen con CAS, que también afila el ruido: el parpadeo del TAA y del FSR y el grano de película de algunos juegos. Ahora usan **DLS**, la nitidez de vkBasalt que se contiene donde hay ruido, y la mayoría suavizan además las **bandas** de cielos y nieblas. Las dos cosas están en la versión de vkBasalt de la imagen (0.3.2.10), según su código fuente.
- **Se notan más.** Los cambios de color son más marcados: VIVID, el doble; CINEMA, la mitad más. La tabla de color tiene ahora 33³ puntos en vez de 17³, así que los degradados quedan más suaves.
- **Tres aspectos nuevos:**
  - **NEXT-GEN:** luces que se suavizan en vez de quemarse, sombras profundas sin perder detalle, color más rico, bordes suavizados (SMAA) y detalle fino. Pensado para que los juegos antiguos parezcan de una generación nueva.
  - **REALISTA:** aspecto fotográfico. Contraste de cámara, calma los colores chillones sin tocar la piel ni la naturaleza, sombras algo más frías y detalle limpio.
  - **SIN GRANO:** para juegos que se ven granulados. Quita ruido y bandas sin tocar el color.
- **Elegir el aspecto** ya no es pasar uno por uno con A. Ahora se abre una lista con los 9 (Original y los 8 aspectos), cada uno con lo que hace, y el elegido lleva una marca.
- Si los juegos se siguen viendo granulados con SIN GRANO, hay dos causas más que conviene saber:
  - **La resolución de la imagen.** Con «Imagen: STONE decide» o FSR, el juego dibuja al 67 % y luego escala la imagen. Prueba «Imagen: Nativa».
  - **El adaptador DisplayPort → HDMI.** No pasa de 1440p a 60 Hz, así que el televisor escala esa señal a 4K y además le aplica su propia nitidez.

## OptiScaler

- En la foto salía: «files with the same name already exist in the game folder: libxess_fg.dll, libxess_dx11.dll, libxess.dll». Cyberpunk 2077 trae sus propias bibliotecas de XeSS, y OptiScaler también las incluye. Ahora STONE **conserva las del juego**: no las sobrescribe al instalar ni las borra al quitar OptiScaler, que usa las que encuentre. Al confirmar, STONE te dice qué archivos se conservan.

## El diálogo «Opción de inicio»

- Salía **«#STEAM_LAUNCHOPTION_GAME»**, que es una clave interna de Steam y no un texto, y el botón «CANCELAR» se salía del cuadro. Ahora las opciones usan los **textos en español de la propia Steam**, sacados de su archivo de traducción (por ejemplo «Jugar a «Batman: Arkham City GOTY»»). Se muestran como una lista y debajo solo queda CANCELAR.
- En cualquier diálogo, los botones que no caben pasan a la línea siguiente en vez de salirse del cuadro.

## El informe (y lo que mostró el de las 23:22)

- Ya no avisa de un aspecto que STONE apagó hace días si después volviste a jugar con aspecto.
- Un «no se abrió» que Steam reintentó y abrió enseguida ya no cuenta como fallo.
- **Cancelar no es un fallo.** El fallo que marcó el informe (Batman: Arkham City a las 22:54) fue el diálogo de la foto: se respondió CANCELAR, pero STONE esperó tres minutos y lo apuntó como «Steam no llegó a abrir». Ahora, al cancelar, STONE deja las opciones del juego como estaban en el siguiente segundo, y el informe no lo cuenta como fallo.
- **El filtro se comprueba ya dentro del juego, no en su lanzador.** A los 27 s, Cyberpunk seguía en su lanzador y todavía no usaba Vulkan, así que el informe habría dicho «no usa Vulkan». Ahora, si el juego aún no ha llegado a Vulkan, STONE vuelve a mirar a los 60 s y a los 2 minutos, y anota lo que ve dentro del juego.

**Todo está probado en software (CODE TESTED) y en el simulador. Nada de esta versión se ha observado todavía en la BC-250.** Pruebas de placa: T-LOOK-05, T-DL-05 y T-HOME-11.

# STONE OS (rebuild) 3.1.0-rc10

Hecha con el **tercer informe de la consola** (15-11-2026, 17:04) y con lo que pediste: que no parpadee, que se vea cuándo STONE está trabajando y que los cuadros de diálogo estén bien encuadrados. Además se hizo una auditoría con el informe y el código. Decisión D-45.

## Lo que el informe destapó (y estaba mal de verdad)

- **El «script de instalación» de Steam se confundía con el juego.** Antes de abrir un juego, Steam ejecuta su script de instalación (DirectX, VC++). Lo hace con el mismo proceso que STONE vigila, marcado `Install=1`. STONE lo tomaba por el juego, veía que «se cerraba» a los 6 s y lo contaba como un cierre en falso. Por eso apagó el aspecto CINEMA de Batman. Además, gamescope ponía delante una ventana que todavía no existía. Ahora STONE, gamescope y `stoned` ignoran ese proceso.
- **Las variables de STONE se quedaban en las opciones de lanzamiento del juego.** Un JUGAR que nunca arrancó (la consola se apagó entre medio), seguido de una restauración que no pudo hablar con Steam, dejó `ENABLE_VKBASALT=1 … STONE_LOOK=cinema` guardado en las opciones de Batman. STONE las tomó después por tuyas: el juego seguía recibiendo el aspecto con «Original» elegido. Ahora STONE reconoce sus propias variables por sus marcas y nunca las guarda como tuyas. Las que ya se habían quedado se quitan en el siguiente JUGAR, sin tocar las tuyas.
- **OptiScaler acabó en la carpeta equivocada.** En Batman: Arkham Asylum se instaló en `redist`, la carpeta de instaladores, porque ahí estaba el `.exe` más grande. Ahora esas carpetas se saltan. Si STONE ya lo había dejado ahí, lo retira solo al arrancar (solo los archivos que él mismo puso) para que puedas instalarlo bien.
- **OptiScaler necesita algo que reemplazar.** OptiScaler mejora el DLSS, el FSR 2/3 o el XeSS que ya trae el juego. Los Batman de 2009 y 2011 no traen ninguno. STONE ahora mira las bibliotecas del juego y, si no encuentra ninguna, te avisa antes de instalarlo.
- **Un error de la pantalla:** `Cannot read properties of null (reading 'onB')`. Un diálogo que se cerraba sin volver a una pantalla dejaba el mando sin respuesta. Ahora cualquier botón te devuelve a donde estabas.
- **Colores:** el informe ya mira lo que gamescope dice en ese momento. En tu consola la salida está ahora en SDR (HDR desactivado en Steam). Un JUGAR que quedó a medias porque la consola se apagó ya no cuenta como fallo.

## Sin parpadeos

- **Ajustes** se reconstruía entero en cada paso arriba o abajo. La fila elegida perdía el resaltado durante un instante y una lista larga saltaba arriba y volvía. **Emuladores** se reconstruía además cada 10 s. Ahora solo se redibuja lo que cambió, y la lista mantiene su posición.
- **Inicio y Biblioteca** se redibujaban cuando llegaba una carátula o terminaba una descarga: el juego elegido «crecía» otra vez y sus datos se apagaban y volvían a encenderse. Ahora el resaltado está puesto desde el primer instante.
- **Al abrir un juego**, STONE se dormía y despertaba varias veces en milisegundos, y cada vez pausaba y reanudaba todas las animaciones. Ahora solo se duerme cuando el juego lleva un momento delante; despertar sigue siendo inmediato.
- **Los cuadros de diálogo** ya no aparecen ni desaparecen de golpe: entran y salen con un fundido corto.

## Ahora se ve cuándo STONE está trabajando

- Arriba a la derecha, en cualquier pantalla, aparece un **anillo que gira** con lo que está pasando. Cubre:
  - la **actualización de STONE OS**, con su porcentaje real, leído del propio `uupd`;
  - las descargas de Steam;
  - la instalación de emuladores;
  - la copia desde un USB;
  - la descarga e instalación de OptiScaler;
  - el informe;
  - el cambio de Wi-Fi.
- En **Ajustes → Actualizaciones**, la fila muestra «Actualizando · 45 %» y qué parte va: el sistema o las aplicaciones. Al terminar avisa de que la actualización está lista. También funciona cuando la búsqueda la empieza el propio sistema.
- Cualquier fila que esté «Leyendo…» o «Buscando…» lleva el mismo anillo.

## Cuadros de diálogo bien encuadrados

Todos empezaban a 200 px del borde de arriba, fuera cual fuera su altura, y los espacios entre sus partes eran de 12, 17, 18, 25, 26 o 34 px según el diálogo. Ahora:
- todos van **centrados** en la pantalla;
- los espacios siguen **un único ritmo**: 24 px entre bloques, el título pegado a su epígrafe y los botones 36 px por debajo;
- el fondo queda algo más oscuro.

Se midieron 12 diálogos y ninguno se sale ni se corta.

**Todo está probado en software (CODE TESTED) y en el simulador. Nada de esta versión se ha observado todavía en la BC-250.** Pruebas de placa: T-HOME-08, T-HOME-09, T-HOME-10 y T-LOOK-04.

# STONE OS (rebuild) 3.1.0-rc9

Arreglos sacados del **segundo informe de la consola** (15-11-2026, 10:33, ya con la 3.1.0-rc8) y de la foto de la tele. Decisión D-44.

## Las herramientas de escalado vuelven a instalarse

En la tele salía **«No se pudo: OptiScaler (FSR 3.1): the latest release has no file I recognise (v0.9.4)»**.

- **El nombre del archivo:** desde la versión 0.9, OptiScaler llama a su archivo `Optiscaler_0.9.4-final.20260718._MM.7z`, con la «s» en minúscula. STONE buscaba `OptiScaler`, con mayúscula exacta, y no encontraba nada. Ahora da igual si va en mayúsculas o en minúsculas.
- **El archivo de la versión 0.9.4, probado de verdad:** se descargó, coincide con la suma SHA-256 que publica GitHub y se descomprimió con el propio código de STONE. Se copian 18 archivos al juego: `OptiScaler.dll` (con el nombre `winmm.dll`), su `.ini`, las DLL de FSR y XeSS y `D3D12_Optiscaler`. Los instaladores del autor (`setup_linux.sh`, `setup_windows.bat` y el LÉEME) ya no se copian: STONE instala OptiScaler por su cuenta.
- **Descomprimir `.7z` en la consola:** OptiScaler solo se publica en `.7z`. La imagen instala ahora `bsdtar`, y la construcción se detiene si no hay ninguna herramienta capaz de abrir `.7z`. Así no puede volver a salir una imagen sin ella.
- **HelixSR** sigue publicando `HelixSR-3.3.0.zip`, que STONE ya reconoce.

## El informe, sin falsas alarmas

- **«Filtros de imagen: la biblioteca de vkBasalt no existe».** Era falso. Fedora declara su ruta como `/usr/$LIB/vkbasalt/…`, donde `$LIB` es una palabra que el sistema convierte en `lib64`. Ahora se comprueba así.
- **«Steam rechazó 184 llamadas».** Eran antiguas: 171 del día anterior y 13 de las 09:26, antes de actualizar. Desde que arrancó la rc8 no hay ninguna, así que el arreglo de la rc8 funciona. El informe ya solo cuenta lo que ha dicho el Steam que está en marcha.
- **«Disco /: 0 GB libres de 0 GB».** En esta imagen, `/` es el sistema de solo lectura: ocupa 45 MB y está lleno a propósito. La rc8 solo lo ocultaba si medía 0 bytes; ahora se oculta cualquier disco de solo lectura.
- **Mandos:** la lista de dispositivos no se podía leer (*Invalid argument*), así que el informe no veía los mandos. Ahora se lee bien, y además reconoce un mando por su nombre.

## Steam de 64 bits

La consola ya usa el **cliente de 64 bits de Steam**, versión 1794536281. La herramienta que lee el código de Steam leía el de 32 bits, que se había quedado en una versión anterior. Ahora lee el de la consola. Comprobado contra la 1794536281: las 156 llamadas de STONE coinciden con las que usa Steam, sin ningún error.

## Lo que dijo el informe sobre los colores

Queda confirmado que la salida pasa a **HDR**: gamescope marca `GAMESCOPE_HDR_OUTPUT_FEEDBACK=1` a los 9 s de empezar la sesión. La tele está conectada por DisplayPort → HDMI con un adaptador. Para comprobar si esa es la causa: **Ajustes → Steam → «HDR en la salida de vídeo» → No**.

**Todo está probado en software (CODE TESTED). El archivo real de OptiScaler 0.9.4 se comprobó y se descomprimió en el Mac, pero nada de esta versión se ha observado todavía en la BC-250.** Pruebas de placa: T-DL-04 y T-HEALTH-08.

# STONE OS (rebuild) 3.1.0-rc8

Arreglos sacados del **primer informe de diagnóstico de la consola** (14-11-2026, 21:44). Es la primera versión hecha con los registros reales de la BC-250 en lugar de una foto. Decisión D-42.

## Steam ya no recibe llamadas a ciegas

El informe mostró a Steam lanzando errores del tipo «requires 2 arguments; only 1 given»: **121 en un minuto**, todos causados por STONE. La pantalla Ajustes → Steam armaba su lista llamando a todas las funciones de Steam que empiezan por `Get…`, sin argumentos: capturas, Remote Play, almacenamiento, VR, notas… Muchas necesitan datos, y algunas leen cosas que STONE no tiene por qué leer.

Ahora STONE lee los ajustes **como los lee la propia interfaz de Steam**:
- Los lee de su almacén de ajustes (`settingsStore.clientSettings`), **sin llamar a ninguna función**.
- Los cambia con la función de Steam que guarda cada ajuste.
- Muestra solo una lista cuidada, con nombre en español: soporte para mandos Xbox, PlayStation y Nintendo; superposición en el juego; sombreadores precompilados; descargar mientras se juega; Steam Cloud; avisos; capturas; y reducir movimiento.

## Sin falsas alarmas en Salud y en el informe

- **«20 errores de amdgpu»:** son mensajes que el kernel escribe en **cada arranque** de la BC-250 (`dal_irq_service_dummy`, `Unsupported clock type`, `Failed to clear hpd(rx) … on init`). No afectan al juego y ya no cuentan como errores. Un error real, como un cuelgue de la GPU, se sigue mostrando.
- **«Disco /: 0 GB libres de 0 GB»:** en esta imagen, `/` es el sistema de solo lectura y no tiene tamaño propio. Ya no aparece.
- **«El arranque anterior registró 147 errores (¿se colgó?)»:** eran los mismos mensajes normales del arranque, y la caja negra decía que había terminado bien. Ahora el informe solo habla de cuelgue si hay una señal real: reinicio de la GPU, una tarea colgada, falta de memoria o un error del kernel.
- **El informe cuenta solo los errores de STONE** y los graves. Los avisos propios de Steam, gamescope o el sistema base siguen dentro del archivo, pero no se suman. Con tus datos, el recuento pasa de 121 a 1.

## El informe trae el registro de STONE Home

STONE Home escribe sus propios mensajes en `~/.local/state/stone/home.log`, y el informe no los incluía. Ahora sí, el de este arranque y el anterior. Además, los archivos de estado se guardan con una clave por línea, para que una palabra como «token» borre solo esa línea y no el archivo entero.

## El informe dice qué funciona y qué no

El primer informe traía todos los registros, pero no decía lo que viste: **los filtros de imagen no cambian nada** y **los colores del inicio se destiñen a los pocos segundos**. Ahora el informe comprueba cada función y la marca como **FUNCIONA**, **FALLA**, **ATENCIÓN** o **SIN DATOS**, con el motivo y las pruebas. Decisión D-43.

- **Primero preguntas tú.** Al pulsar *Informe de diagnóstico* aparece **«¿Qué no funciona?»**. Puedes marcar filtros de imagen, colores, un juego que no abre, descargas, sonido, mando, Wi-Fi, Steam, emuladores u otra cosa. Lo que marcas va primero en el informe, junto a la comprobación que puede explicarlo.
- **Filtros de imagen (Aspecto).** Con el juego abierto, STONE mira dentro de sus procesos si le llegó el aspecto y si vkBasalt se cargó de verdad. Así distingue entre:
  - el aspecto no llegó al juego;
  - el juego no usa Vulkan;
  - vkBasalt no se cargó;
  - STONE lo apagó.

  vkBasalt deja además su propio registro de cada juego dentro del informe.
- **Colores (HDR).** El informe muestra en qué segundo la salida de vídeo pasó a HDR y si el ajuste **«Activar HDR»** de Steam está encendido. También guarda lo que gamescope tiene configurado en pantalla. Tu informe del 14-11 ya lo mostraba: la salida pasó a HDR **6 s** después de arrancar gamescope, justo cuando arrancó Steam. Es la causa probable de los colores desvaídos, porque la pantalla de inicio de STONE está hecha en SDR.
- **Además:** abrir juegos, Steam (incluye las llamadas que rechazó y si su ventana se abrió y dejó volver), sonido, mandos, Wi-Fi, disco y emuladores.
- **Registro de eventos** (`eventos.jsonl`). STONE apunta qué hizo y qué resultado tuvo: cada JUGAR con su aspecto, cuándo arrancó y terminó cada juego, y cada vez que Steam se puso delante. Los registros de texto no permitían contar estas cosas.

## Los aspectos ya no se apagan solos sin avisar

Hasta ahora, si un juego se cerraba antes de 60 s con un aspecto puesto, STONE apagaba el aspecto **sin decir nada**. Bastaba con abrir un juego para ver el aspecto y salir enseguida. En tu informe, `looks.json` estaba vacío. Ahora solo se apaga si el juego se cierra **dos veces seguidas en los primeros 20 s**, y STONE avisa en pantalla. Una partida normal pone el contador a cero.

## HDR desde STONE

En **Ajustes → Steam** aparece **«HDR en la salida de vídeo»**. Es el ajuste «Activar HDR» de Steam, que se lee y se cambia con el mismo mecanismo que usa Steam. Sirve para comprobar si los colores dejan de desteñirse.

**Todo está probado en software (CODE TESTED). La comprobación se hizo con los registros reales del informe, pero nada de esta versión se ha observado todavía en la BC-250.** Pruebas de placa: T-STEAM-24, T-HEALTH-06, T-HEALTH-07 y T-LOOK-03.

# STONE OS (rebuild) 3.1.0-rc7

## Informe de diagnóstico

Hasta ahora, cuando algo fallaba en la consola, lo único que llegaba era una foto de la tele. Ahora, en **Ajustes → Salud → Informe de diagnóstico**, STONE reúne en un archivo todo lo necesario para encontrar la causa:

- **Los registros de este arranque:** STONE Home y la sesión, el servicio de rendimiento (`stoned`) y los avisos del sistema.
- **Los errores del arranque anterior**, por si la consola se colgó o se apagó de golpe.
- **Los registros de Steam:** consola, descargas, compatibilidad.
- **El estado de STONE:** sus ajustes, las opciones de inicio que cambió, la red y la Salud.
- **Una comprobación en vivo** de que el Steam de la consola tiene las 27 funciones que STONE usa. Así se ve al momento si una actualización de Steam rompió algo.

En la tele aparece un resumen: la versión, los errores, las funciones de Steam y los hallazgos. El archivo se lleva **al móvil** con un código QR, por el mismo Wi-Fi, o **a un USB**.

**Sin datos personales.** Antes de escribir nada se borran:
- Los correos y los identificadores de cuenta de Steam.
- La parte final de las direcciones IP y MAC.
- Cualquier línea que nombre una contraseña, un token o una cookie.

Las contraseñas de Wi-Fi nunca se leen. STONE no envía el informe a ningún sitio: el archivo solo sale si tú te lo llevas.

**Todo está probado en software (CODE TESTED). Nada de esta versión se ha observado todavía en la BC-250.** Prueba de placa: T-HEALTH-05.

# STONE OS (rebuild) 3.1.0-rc6

Auditoría del sistema completo después de probar 3.1.0-rc5 en la consola (14-11-2026), con los emuladores que no se abrían y sin carátulas, juegos desde un USB o desde el móvil (iCloud y otras nubes) y los ports de Switch 2. La regla: **llegar y jugar, como en SteamOS**. Lo que la pantalla dice tiene que ser verdad y de Steam siempre se vuelve a STONE. Llega a la consola **por actualización en línea**. Decisiones D-39 y D-40.

**Todo está probado en software (CODE TESTED): pruebas automáticas y la simulación de la interfaz. Nada de esta versión se ha observado todavía en la BC-250.** Pruebas de placa: T-NET-01, T-NET-02, T-NET-03, T-STEAM-22, T-HOME-07, T-EMU-10, T-EMU-11, T-EMU-12, T-EMU-13 y T-EMU-14 en `hardware/validation/matrix.yaml`.

## Steam desde STONE: siempre se vuelve

Se revisaron todas las formas de llegar a Steam desde STONE: iniciar sesión, la tienda, comprar un juego, el diálogo de instalación, los ajustes, las descargas y «Steam completo».

- **Mientras Steam arranca**, la cortina «PREPARANDO STEAM» puede durar minutos en una consola nueva. Antes solo el botón guía cancelaba la espera, y la pantalla no lo decía. Ahora **B vuelve a STONE sin esperar**, y la cortina lo dice.
- **Tienda y compra:** al salir de la tienda con B, STONE vuelve sola, como con los ajustes. STONE sigue la página de Steam y trata la tienda, sus páginas web y la **confirmación del pago** como una sola, así que nunca te saca a mitad de una compra.
- **Si Steam no consigue abrir sus ajustes**, STONE recupera la pantalla y lo dice, en lugar de dejarte en el inicio de Steam.
- Si cancelas antes de que Steam se abra, el aviso dice «Steam no llegó a abrirse», y no «lo que hayas comprado aparece en tu biblioteca».
- El botón guía vuelve a STONE desde **cualquier** pantalla de Steam. «Steam completo» se deja con el botón guía mantenido 3 segundos, al cerrar Steam o al reiniciar la consola.

## Depuración completa

Antes de esta versión se revisó todo el sistema.

**Análisis automático de todo el código:**
- **La interfaz:** todo su JavaScript, unas 10 000 líneas, pasó por un analizador estático. No hay ninguna función ni variable usada sin definir.
- **Python:** el host, los módulos de juegos y pantalla y el servicio de rendimiento pasaron por reglas estrictas. No hay nombres sin definir ni errores probables.
- **Scripts de shell:** pasaron `shellcheck`.

**Revisión a mano de los filtros de imagen y los reescaladores:**
- Los filtros (NATURAL, CLARITY, CINEMA, VIVID, RETRO) son correctos.
- FSR y OptiScaler se descargan solo de sus autores, con la suma comprobada, y nunca pisan tus archivos.
- La generación de fotogramas es correcta.
- Tus opciones de inicio en Steam se guardan antes de cambiarlas y se restauran incluso tras un cuelgue.

**Arreglos de lo visto en pantalla:**
- **Gráficos:** el valor de cada opción quedaba desalineado y en letra muy pequeña. Ahora va en su fila y se lee desde el sofá. «Calidad: Calidad» pasa a ser «Ajuste de FSR», y las mayúsculas son coherentes.
- **Ficha del juego:** ya no repite «STONE RECOMMENDED … Recomendado por STONE».
- **Primer encendido:** el paso Inicio ya no muestra dos filas de «no se pudo leer» si falta un dato, y el paso Internet dice a qué red estás conectado.
- **Acerca de:** muestra los núcleos que lee la consola, no un cálculo del navegador.

## Emuladores: ahora se abren

**La causa:** STONE creaba los accesos directos de Steam con los datos en un orden equivocado. La interfaz de Steam crea un acceso directo con (nombre, programa, **argumentos**, línea de comandos), y STONE pasaba (nombre, programa, **carpeta**, argumentos). Steam guardaba «/» como argumentos y cada emulador ejecutaba `flatpak /`, que no abre nada.

- Los accesos directos se crean ahora como los crea Steam, con el nombre, el programa, la carpeta y las opciones en su sitio.
- **Los emuladores que ya instalaste se reparan solos** al arrancar la sesión, antes de que se abra Steam.
- Los nombres con comillas u otros símbolos ya no impiden añadir un juego al momento.

## Carátulas para los juegos de los emuladores

- **La carátula real** de cada juego se descarga de la colección pública de libretro, la que usan RetroArch y otros. STONE busca el nombre del juego aunque el archivo no se llame exactamente igual (sin región, versión ni signos, y con o sin tildes). La guarda donde Steam guarda las imágenes de los accesos directos, así que se ve en STONE y en Steam.
- **Si no hay carátula**, por ejemplo con Switch, o mientras se descarga, el juego lleva la portada de STONE con su consola y su nombre, en lugar de un hueco vacío. Los emuladores llevan «EMULADOR».

## Tus juegos desde un USB

- Conecta un pendrive con carpetas por consola (`ps2`, `gba`, `switch`, `PlayStation 2`…). Valen también las carpetas `roms/` y `Emulation/roms/` de EmuDeck y RetroDECK.
- **STONE lo detecta en unos segundos y ofrece copiar los juegos**, como una consola que instala desde un disco. Después siguen funcionando sin el USB.
- La copia muestra su avance y se puede cancelar. Deja siempre 2 GB libres, no copia dos veces el mismo juego y añade los juegos a la biblioteca al terminar.
- Si nadie montó el USB, STONE lo monta. Solo se permiten unidades extraíbles.

## Tus juegos desde el móvil: iCloud, Google Drive y otras nubes

STONE nunca inicia sesión con tu contraseña. Por eso la nube se alcanza a través del móvil, que ya tiene tu sesión:

- Ajustes → Emuladores → **Juegos desde el móvil** muestra un código QR.
- El móvil, conectado al mismo Wi-Fi, abre una página de la consola. Ahí eliges los juegos con el selector de archivos del móvil (en iPhone, «Archivos» incluye iCloud Drive).
- Cada juego va directo a la carpeta de su consola. Al terminar, se añaden a la biblioteca.
- Seguridad: la página solo existe mientras esa pantalla está abierta, con 30 minutos como máximo. Lleva una clave al azar, solo acepta archivos de juegos y nunca ejecuta nada.

## Switch 2: ports y emulador experimental

STONE no hace ports: un port es el trabajo de meses de un proyecto, para un juego concreto. Lo que STONE hace es **instalar los ports que esos proyectos publican para Linux**, desde su propia página en GitHub, comprobando cada descarga con la suma que publica GitHub, y añadirlos a la biblioteca.

- **Mario Kart World** (mkw-recomp, licencia MIT).
- **Eglantine**, un emulador de Switch 2 muy experimental (GPL-3.0).
- Los dos necesitan **tu propia copia** del juego, volcada de tu consola. STONE no descarga juegos, claves ni herramientas para volcarlos.
- Todo es experimental: los proyectos tienen días o semanas.
- Se revisaron otros. El de Star Fox solo tiene versión para Windows y el de Pokémon Pokopia no tiene aún un paquete que STONE pueda comprobar, así que se añadirán cuando los tengan.

## Wi-Fi: siempre se puede volver a conectar

En la consola, después de DESCONECTAR el Wi-Fi no había forma de volver a conectarlo. STONE volvía a leer el estado de la red, pero conservaba la lista anterior de redes, donde tu red seguía diciendo «Conectada». Al elegirla respondía «Ya conectada».

Ajustes → Red funciona ahora como en SteamOS:

- **Wi-Fi activado / desactivado**, con A.
- **La red en uso** abre sus opciones: **DESCONECTAR**, **OLVIDAR** (borra también la contraseña guardada) o VOLVER.
- **Las redes guardadas** se vuelven a conectar **sin escribir la contraseña**. Si la red la pide de nuevo, aparece el teclado.
- **Internet:** dice si hay salida a internet, si la red no la tiene o si pide iniciar sesión en una página web, como en hoteles y cafeterías.
- Después de cada cambio se vuelve a leer todo: la lista, el estado y el icono.
- El primer encendido también permite activar el Wi-Fi si está apagado, y se conecta a redes guardadas sin pedir la contraseña.

## El icono de red dice la verdad

El icono de arriba a la derecha era un dibujo fijo de Wi-Fi con señal completa: se veía igual sin red. Ahora es real y se actualiza cada 15 segundos:

- **Cable** si estás conectado por cable.
- **Wi-Fi con 1, 2 o 3 barras** según la señal.
- **Un «!»** si la red no tiene internet.
- **Tachado** si no hay conexión o el Wi-Fi está apagado.

Cuando se pierde internet, STONE lo avisa una vez, y otra vez cuando vuelve. Lo que necesita internet (descargar un juego, la tienda, iniciar sesión, buscar actualizaciones) lo dice antes de intentarlo, en lugar de terminar en «Steam no respondió».

## Abrir en Steam y volver a STONE

«Abrir en Steam» en Ajustes pedía a Steam que mostrara sus ajustes, pero su ventana no pasaba al frente y no había un camino de vuelta. Ahora funciona igual que la tienda y el inicio de sesión:

- **Una transición suave:** STONE se cubre primero con su cortina oscura y entonces aparece Steam. Al volver, STONE reaparece con un fundido, sin cortes.
- Steam abre **sus ajustes en la sección pedida** (Pantalla, Red, Audio…).
- **Para volver a STONE, sal de los ajustes con B**, como en cualquier pantalla de SteamOS. También funciona el botón guía del mando.
- Lo mismo vale para la pantalla de Descargas de Steam.

## Menú rápido durante el juego

En la sesión STONE, Steam funciona sin su propia interfaz de consola, así que el menú rápido de Steam (botón ···) puede no responder. El menú de STONE (botón ☰ durante el juego) tiene ahora:

- **Volumen**, que se cambia con ← →.
- **El estado de la red.**

## Coherencia de las pantallas

- **Pantalla:** «Encuadre» y «Área segura» hacían lo mismo. Queda solo **Encuadre**, que es el que ajusta la imagen, y las esquinas de ajuste aparecen al elegirlo. Antes aparecían sobre la fila «Televisor».
- **Almacenamiento:** los discos se llaman «Disco de la consola» o «Disco externo» en lugar de su ruta de Linux. Una descarga abre la ficha del juego, donde se puede pausar. Antes decía que seguía «con la consola en reposo», y esta consola no tiene modo reposo.
- **Sistema y Mandos** dicen qué hay en los ajustes de Steam (idioma, fecha y hora, botones, vibración…), en lugar de «Panel nativo de Steam».
- **Ajustes → Steam:** los niveles se muestran en porcentaje («70 %» y no «0.7»). Ya no aparecen el brillo de pantalla, que es de la Steam Deck, ni el modo desarrollador.
- **Acerca de:** NEURAL RENDER, que hoy no funciona, solo aparece en el modo técnico.

# STONE OS (rebuild) 3.1.0-rc5

Revisión de todo lo que STONE le pide a Steam, **comprobado contra el código de la propia interfaz de Steam** (cliente 1792618285) y no deducido. Corrige tres fallos encontrados en esa revisión y añade dos cosas que faltaban para usar la consola sin entrar a Steam: **cerrar un juego** y **pausar una descarga**. Llega a la consola **por actualización en línea**. Decisión D-38.

**Todo está probado en software (CODE TESTED): pruebas automáticas, el código que STONE ejecuta en Steam probado contra un Steam simulado, y la simulación de la interfaz. Nada de esta versión se ha observado todavía en la BC-250.** Pruebas de placa: T-LIB-14, T-STEAM-20, T-STEAM-21 y T-DISP-02 en `hardware/validation/matrix.yaml`.

## Cerrar un juego

Hasta ahora, si un juego se colgaba o no tenía un menú para salir, no había forma de cerrarlo desde STONE.

- **Cerrar juego** está en el menú rápido (botón de menú mientras juegas) y en la ficha del juego abierto, donde ocupa el lugar de «Rendimiento», que solo se aplica al iniciar el juego.
- Pregunta lo mismo que Steam: **«¿Salir del juego? Los datos no guardados podrían perderse.»**, con el foco en CANCELAR.
- **SALIR DEL JUEGO** cierra el juego con la misma orden que el botón «Salir del juego» de Steam y vuelve al inicio. Si el juego no se cierra en 20 segundos (puede estar guardando), STONE lo avisa.

## Pausar y reanudar descargas

- En la ficha de un juego que se descarga, **A abre las opciones de la descarga**: **PAUSAR**, **REANUDAR** o, si está en cola, **DESCARGAR AHORA**.
- Al pausar, Steam pausa todas sus descargas, igual que su propio botón de pausa. La ficha, la carátula y el indicador de arriba dicen «En pausa».

## Fallos corregidos

- **Juegos que desaparecían de la biblioteca.** Para decir si un juego está instalado, STONE leía un dato que en Steam corresponde al equipo de la cuenta que más tiene, que puede ser **otro PC**. Un juego instalado en tu PC no estaba ni instalado ni «en tu cuenta» en la consola, y no aparecía. Ahora STONE mira solo esta consola, y deja fuera lo que Steam conoce pero la cuenta no posee.
- **Resolución por juego.** STONE leía la resolución de cada juego con una función que la interfaz de Steam no usa. Si esa función no existe, el ajuste fallaba sin avisar. Ahora la lee de los detalles del juego, como Steam.
- **Ajustes y Descargas de Steam:** revisados, ya eran correctos. Las 11 secciones que abre STONE son rutas de Steam.

## Cómo se comprueba ahora

- `dev/steam/steam_api.py` descarga la interfaz que Valve publica con cada versión del cliente (comprobando su suma SHA-256; se lee, nunca se ejecuta) y compara **cada llamada, número de argumentos y dato** que STONE usa: 144 coincidencias y 2 funciones opcionales documentadas.
- En cada compilación, una prueba repite esa comparación sin internet. Si un cambio de STONE le pidiera a Steam algo que Steam no hace, la compilación falla.
- La guía `docs/steam/COMO_HABLA_STONE_CON_STEAM.md` explica cada caso y cómo hacer un arreglo cuando cambie Steam.

# STONE OS (rebuild) 3.1.0-rc4

Arregla lo que se vio en la consola con 3.1.0-rc3 (12 y 13-11-2026, fotos del propietario): **Batman: Arkham City no se abría** (se quedaba en «SIGUE CARGANDO»), **instalar un juego respondía «Steam no respondió»**, **las carátulas de los juegos sin instalar se transparentaban** y **los fondos se veían pixelados** en el televisor 4K. Añade la **barra de descarga e instalación**. Decisión D-37.

**Todo está probado en software (CODE TESTED): pruebas automáticas, el código de instalación ejecutado contra un Steam simulado, y la simulación de la interfaz. Nada de esta versión se ha observado todavía en la BC-250.** Pruebas de placa: T-STEAM-15 (actualizada), T-STEAM-17, T-STEAM-18 y T-HOME-06 en `hardware/validation/matrix.yaml`.

## Abrir juegos

Steam abre un juego por pasos y en algunos se detiene a preguntar: qué opción de inicio usar, aceptar el contrato de licencia, qué partidas usar si las de la nube no coinciden, qué hacer si falló la instalación de un componente (DirectX, Visual C++) o si otra sesión está jugando. En la sesión STONE esas preguntas se abrían en ventanas ocultas de Steam y el juego quedaba esperando para siempre.

- STONE sigue los pasos de Steam con sus propios avisos (los mismos que usa la interfaz de Steam) y **la pantalla de carga dice en qué está**: comprobando la configuración, sincronizando con la nube, instalando componentes, preparando sombreadores (con porcentaje), abriendo el juego.
- **Las preguntas las hace STONE** con el mando y le pasa tu respuesta a Steam: la opción de inicio, el contrato de licencia (con código QR), las partidas de la nube, el componente que falló y la otra sesión. Los pasos que Steam resuelve con un simple «Aceptar» se aceptan solos.
- **Si Steam no puede abrir el juego**, STONE dice por qué con las palabras de Steam (por ejemplo «falló la herramienta de compatibilidad (Proton)» o «no hay espacio suficiente») y una línea de detalle técnico.
- Si tarda, el aviso ofrece ESPERAR, CANCELAR y, mientras prepara sombreadores, **OMITIR**.
- **Juegos de Windows:** STONE activa «Steam Play para todos los títulos» (Proton Experimental) si nadie lo eligió antes en Steam. Lo hace al arrancar la sesión, con Steam cerrado, y guarda una copia de la configuración de Steam. Si ya elegiste otra versión de Proton, se respeta. Batman: Arkham City es solo para Windows: es la causa más probable de tu foto. Se confirma en la placa (T-STEAM-19).

## Instalar: la causa del fallo

STONE pedía la instalación a Steam con una llamada incompleta. La interfaz de Steam llama a su instalador con **dos datos** (los juegos y en qué equipo instalarlos, porque Steam ya permite instalar en otro equipo de la cuenta) y STONE pasaba solo uno. Además STONE buscaba el juego en un campo de la respuesta que la interfaz de Steam no usa. Es la causa más probable del «Steam no respondió» de la consola; que quede resuelto se confirma en la placa (T-STEAM-15).

Esta vez las llamadas no se dedujeron: se leyeron del código de la propia interfaz de Steam, que Valve publica con cada versión del cliente (paquete del 12-11-2026).

- La instalación se pide como la pide Steam, y se sigue paso a paso con los avisos del propio instalador.
- Desinstalar tenía el mismo defecto (faltaba un dato) y también está corregido.
- La prueba de que empezó sigue siendo el archivo del juego en la biblioteca de Steam, y ahora se mira **siempre**, respondiera lo que respondiera el instalador.
- Si aun así no empieza, el mensaje incluye una línea de **detalle técnico** con los pasos que dio Steam. Una foto de esa pantalla basta para saber dónde se detuvo.
- **«Ver en Steam»** ahora abre primero el diálogo de instalación de Steam. Antes no había ninguna ventana que mostrar («Steam no mostró su ventana»).

## Contrato de licencia sin entrar a Steam

Muchos juegos piden aceptar un contrato de licencia (EULA) antes de instalarse. Ahora se resuelve en STONE:

- STONE muestra la dirección del contrato y un **código QR** para leerlo en el móvil.
- El foco está en **NO ACEPTO**. Si eliges **ACEPTO E INSTALAR**, STONE le comunica tu aceptación a Steam (la misma llamada que hace el diálogo de Steam) y la instalación sigue sola.
- STONE no acepta nada por su cuenta: sin tu respuesta, el juego no se instala.

## Barra de descarga e instalación

El avance sale de Steam en vivo (la misma información que usa su pantalla de descargas), no del archivo en disco, que Steam solo actualiza de vez en cuando.

- **En la ficha del juego:** la etapa (Descargando, Reservando espacio en disco, Instalando, Verificando archivos, En cola, En pausa), el porcentaje, una barra, los GB descargados, la velocidad y el tiempo que falta.
- **En la carátula** del juego, en Inicio y en la Biblioteca: el porcentaje y una barra pequeña.
- **Arriba a la derecha**, junto al reloj, en cualquier pantalla: «↓ 23 %».
- Al terminar, STONE avisa «listo para jugar» y el botón pasa a JUGAR.
- Si Steam actualiza un juego antes de abrirlo, la pantalla de carga muestra la misma información.

## Carátulas y fondos

- **Carátulas sólidas.** Los juegos sin instalar se dibujaban con toda la tarjeta al 72 % de opacidad y el fondo se veía a través de la carátula. Ahora la carátula es opaca, con una sombra ligera y una **marca de descarga** en la esquina.
- **Fondos al doble de resolución.** El fondo era una imagen de 1920 × 620 estirada unas 3,5 veces en un televisor 4K. STONE descarga ahora la versión de 3840 × 1240 del juego que estás mirando, cuando Steam la tiene (los juegos más recientes; los antiguos, como Batman: Arkham City, no la tienen).
- **Sin bloques.** Cuando la imagen aún debe ampliarse mucho, se suaviza: se ve desenfocada en vez de pixelada. Con «Efectos ligeros» (o sin GPU) no se aplica.
- **Arte muy claro.** Con fondos casi blancos, la sombra bajo los textos se hace más profunda según el brillo de la imagen.
- Los botones de los diálogos ya no se tocan entre sí.
- Al pasar a «Steam completo», el aviso aparece de una vez. Antes la pantalla podía quedar congelada a medio fundido, con el texto de la ficha encima.

## Límites

- Las llamadas al instalador de Steam son internas de Steam y pueden cambiar con una versión futura. Si cambian, STONE lo dice con el detalle técnico y ofrece «Ver en Steam».
- La barra en vivo necesita que la interfaz de Steam responda. Si no responde, STONE muestra las cifras que Steam escribió por última vez en disco.
- El contrato de licencia se lee en el móvil; STONE no muestra su texto en el televisor.

# STONE OS (rebuild) 3.1.0-rc3

Es 3.1.0-rc2 con una prueba automática corregida: la compilación de 3.1.0-rc2 se detuvo en las pruebas de la sesión y nunca se publicó.

Arregla lo que se vio en la consola con 3.0.0-rc1 (12-11-2026): **instalar juegos desde STONE no funcionaba bien**, **Steam ponía su inicio de sesión encima de la configuración inicial** y **las actualizaciones no llegaban**. Trae el diseño Cristal de 3.1.0-rc1. Decisión D-36.

**Todo está probado en software (CODE TESTED): pruebas automáticas y simulación de la interfaz. Nada de esta versión se ha observado todavía en la BC-250.** Pruebas de placa nuevas: T-STEAM-15, T-STEAM-16, T-SETUP-02 y T-UPD-03 en `hardware/validation/matrix.yaml`.

## Instalar juegos: STONE dice lo que Steam hizo de verdad

En 3.0.0-rc1, STONE abría el instalador de Steam, esperaba 1,5 segundos, lo continuaba a ciegas y respondía "instalando" pasara lo que pasara. Si Steam pedía algo (aceptar un contrato de licencia, más espacio, una clave) o no respondía, la instalación nunca empezaba y STONE no se enteraba.

- STONE sigue paso a paso el instalador de Steam y solo lo continúa donde Steam esperaría un clic en "Instalar": la carpeta y, en un juego gratis que pediste, su licencia gratuita.
- **La prueba es el archivo de Steam.** STONE da la instalación por empezada solo cuando aparece el archivo del juego (`appmanifest`) en la biblioteca de Steam.
- **Si Steam pregunta algo que solo tú puedes contestar** (un contrato de licencia, una clave, una contraseña), STONE lo explica y ofrece **Ver en Steam** (muestra la ventana de Steam con la pregunta) o **Ahora no**. STONE nunca acepta un contrato por ti.
- **Si no cabe**, STONE dice cuánto necesita y cuánto queda libre, sin empezar nada.
- **Si Steam no responde o falla**, STONE lo dice y ofrece **Reintentar** o **Ver en Steam**.
- **El avance se ve en la ficha del juego**: "INSTALANDO · 23 %" y cuántos GB van de cuántos. Si Steam actualiza un juego antes de abrirlo, la pantalla de carga lo dice con su porcentaje, y STONE no lo da por atascado mientras avance.
- Desinstalar espera a que Steam borre el juego de verdad antes de decir "se desinstaló".
- Un juego comprado con el móvil se instala por el mismo camino, con los mismos avisos.

## Primer encendido sin Steam encima

- **Steam no arranca mientras dura la configuración.** Arranca al llegar al paso STEAM, o al terminar si eliges MÁS TARDE. Sin Steam en marcha, ninguna ventana suya puede aparecer sobre la configuración.
- **Guardia permanente:** si una ventana de Steam aparece sin que STONE la pida, se le quita la marca que la pone en pantalla y se aparta fuera de la vista. El registro de la sesión anota qué ventana era (`~/.local/state/stone/session.log`). Vuelve cuando STONE la pide (iniciar sesión, la tienda, una pregunta de Steam).
- Los botones del paso STEAM tienen más espacio entre sí.

## Actualizaciones que llegan

La imagen base (Bazzite, variante deck) trae apagada su comprobación automática: espera a que la interfaz de Steam la pida, y en la sesión STONE esa interfaz no se muestra. Por eso 3.1.0-rc1 nunca llegó a la consola.

- **Comprobación diaria activada** (`uupd.timer`): a las 4:00, o al encender si la consola estaba apagada a esa hora.
- **Ajustes → Actualizaciones → Buscar actualizaciones**: busca y descarga la versión nueva en el momento, sin contraseña. Mientras trabaja dice "Buscando y descargando…"; al terminar aparece **Reiniciar y actualizar**.

**Si tu consola tiene 3.0.0-rc1 o 3.1.0-rc1, la primera vez hay que pedir la actualización a mano** (esas versiones no tienen el botón): Ajustes → Acerca de → Modo escritorio, abre Konsole y escribe `systemctl start uupd-manual.service`; cuando vuelva el cursor, abre "Volver a STONE" y reinicia. O instala desde la ISO nueva. Desde 3.1.0-rc3 ya no hace falta.

## Límites

- El instalador de Steam se lee por su interfaz interna (`SteamClient.Installs`), según las definiciones de la comunidad de Decky. Si una versión de Steam la cambia, STONE lo dice ("Steam no respondió") y ofrece la ventana de Steam.
- La ventana de Steam con una pregunta es la de escritorio: se maneja mejor con teclado y ratón.

# STONE OS (rebuild) 3.1.0-rc1

Llega **Cristal**, el diseño nuevo de STONE Home, hecho con los materiales de la STONE MACHINE. Es una actualización en línea: una consola instalada desde una ISO candidata (rc) sigue el canal `rc` y la recibe sola. Se aplica al reiniciar.

**Todo está probado en software (CODE TESTED): pruebas automáticas y simulación de la interfaz. Nada de Cristal se ha visto todavía en la BC-250 ni en un televisor.** Las pruebas de placa nuevas están en `hardware/validation/matrix.yaml` (T-HOME-03 a 05 y T-UPD-02). Decisión D-35.

## Cómo llega a la consola

- La consola busca versiones nuevas por su cuenta. Ajustes → Actualizaciones → Comprobación automática dice cuándo fue la última vez y cuándo será la próxima.
- Cuando la versión nueva está descargada, Ajustes → Actualizaciones muestra «Actualización lista: 3.1.0-rc1» y la opción **Reiniciar y actualizar**.
- Solo cambia STONE Home. Como la imagen se trocea por paquetes (D-32), la descarga debería ser mucho menor que la imagen completa. El tamaño real no está medido: lo registra T-UPD-02.
- Si algo sale mal, la versión anterior queda guardada: en el menú de arranque, la segunda entrada.

## Diseño Cristal

- **Los materiales de la consola.** Los paneles son de cristal negro brillante, como el cuerpo de la STONE MACHINE, con su reflejo cortado en diagonal. La barra de secciones y el estado llevan la banda de piedra facetada. Lo que eliges se vuelve blanco, como el panel superior. La línea de luz blanca va bajo el juego elegido y bajo el logotipo.
- **Liquid Glass.** La barra de secciones y el estado curvan lo que tienen detrás, como una lente.
- **La tipografía del logotipo.** Jost en sus pesos finos: títulos, pestañas y botones en mayúsculas finas y espaciadas, y el texto que se lee en Jost normal. Las cifras que se comparan (temperatura, MHz) siguen en letra monoespaciada.
- **El color sale del juego.** El acento de la interfaz se toma del arte del juego elegido. Las pantallas sin arte usan la luz de estudio del retrato de la consola, teñida con ese color.
- **Carátulas de los apartados.** Biblioteca, Tienda, Buscar juegos, Sorpréndeme, Descargas, Emuladores, Capturas e Iniciar sesión llevan la banda de piedra, su símbolo en blanco y la línea de luz. Las dibuja la propia interfaz, sin imágenes.
- **Las carátulas de los juegos van sin nombre encima.** Un juego sin arte muestra la consola en miniatura.
- **Más aire.** La ficha del juego, Ajustes y los menús tienen más espacio entre textos. El menú de Ajustes es simétrico y sin números, y las listas ya no cortan el resaltado del elemento elegido.
- **Contraste sobre arte claro.** La sombra detrás del texto de Inicio y de la ficha del juego es más profunda arriba y a la izquierda, y el texto lleva una sombra suave propia. El arte conserva su color.
- La fila «La máquina» de Inicio desaparece.

## Efectos de cristal: normales o ligeros

Ajustes → Pantalla → Efectos de cristal. «Ligeros» dibuja los mismos paneles sin desenfoque ni lente, y gasta menos GPU. Sin aceleración por GPU, STONE usa siempre los ligeros. Cuánto cuesta el cristal en la BC-250 no está medido: lo dice T-HOME-03.

## Límites

- La lente depende de Chromium (`backdrop-filter` con un filtro SVG). Si la versión de Chromium de la consola no la dibuja, queda el desenfoque normal.
- La legibilidad a distancia de los pesos finos de Jost no está comprobada en un televisor: es T-HOME-04.

# STONE OS (rebuild) 3.0.0-rc1

Vuelve STONE Home, la interfaz propia de la consola (la de 1.0.0-rc5), con lo que le faltaba: la biblioteca de tu cuenta, una tienda para comprar y un arranque más corto. Auditoría completa en `docs/AUDITORIA_3_0.md`.

**Todo está probado en software (CODE TESTED): pruebas automáticas y simulación de la interfaz. Nada de esta versión se ha observado todavía en la BC-250.** Las pruebas de placa nuevas están en `hardware/validation/matrix.yaml` (T-STEAM-11 a 14, T-LIB-11 a 13, T-STORE-01, T-EMU-02 y 03, T-BOOT-10). La versión 2.0.0-rc1 (tema sobre el Modo Juego de Steam) queda abandonada.

## Por qué no se veía la biblioteca en rc5

En la sesión STONE, Steam funciona oculto. Su ventana de inicio de sesión existía, pero el compositor de la consola (Gamescope) solo muestra ventanas que tienen un identificador de aplicación, y las ventanas propias de Steam no lo tienen. Sin poder iniciar sesión, Steam no tenía cuenta ni juegos que dar. Además, STONE leía la biblioteca una sola vez al arrancar, antes de que Steam estuviera listo.

## Biblioteca

- **Iniciar sesión funciona.** Inicio, Ajustes → Steam y la configuración del primer encendido muestran la ventana propia de Steam, con su código QR para la app de Steam del móvil. STONE nunca ve la contraseña. Al terminar, STONE vuelve sola y lee la biblioteca.
- **La biblioteca se actualiza sola.** STONE vigila a Steam: cuando Steam responde, cuando termina una instalación o cuando llega un juego comprado, la pantalla se redibuja en su sitio, con el mismo foco.
- **Completa desde el primer cuadro.** STONE guarda la lista de juegos de tu cuenta que Steam dio la última vez y la muestra al arrancar, sin esperar a Steam.
- **Carátulas de los juegos no instalados.** Steam solo guarda en disco las de los juegos que ha mostrado. STONE descarga las que faltan de los servidores de imágenes de Steam.
- **Consola nueva:** si hay cuenta pero ningún juego instalado, Inicio muestra los juegos de la cuenta listos para instalar. Antes ese caso dejaba Inicio en blanco.
- Filtro nuevo «Por instalar». Ajustes → Steam → Estado de Steam dice qué sabe STONE de Steam en ese momento.

## Tienda y compras

- **Pestaña TIENDA** (RB desde Inicio): ofertas, lo más vendido, novedades y próximos lanzamientos, con los precios de Steam en la moneda de tu país. Buscar con Y.
- **Ficha de cada juego** con descripción, precio y descuento.
- **COMPRAR EN STEAM:** abre la ficha del juego en la interfaz propia de Steam (Big Picture), delante de STONE. El pago se hace en Steam, con tu cuenta. El botón guía vuelve a STONE.
- **COMPRAR CON EL MÓVIL:** STONE dibuja un código QR de la página del juego. Lo compras desde el móvil.
- **Instalación automática:** un juego comprado por cualquiera de los dos caminos se instala solo en cuanto Steam lo añade a tu cuenta.
- Los juegos gratis se instalan desde su ficha.
- **Plan B, «Steam completo»** (Ajustes → Steam, y ofrecido si la ventana de Steam no aparece): Steam ocupa toda la pantalla con su propia interfaz. STONE vuelve al iniciar sesión, al mantener el botón guía 3 segundos o al reiniciar.

## Arranque

- STONE Home arranca antes que Steam, no después.
- Chromium se lanza antes de preparar el resto de STONE Home, que se carga mientras Chromium abre.
- El tamaño de pantalla se lee sin cargar GTK.
- Inicio ya no espera a `rpm-ostree` ni a Steam para aparecer.
- La espera fija de la animación de arranque baja de 2,0 s a 1,25 s.

El tiempo total de arranque no está medido en la placa: la consola lo registra en cada arranque y la prueba T-BOOT-10 lo compara con rc5.

## Emuladores

- **Nintendo Switch:** Eden y Ryujinx (Ryubing), desde Flathub. Los juegos van en `~/Emulation/roms/switch`. Las claves y el firmware de tu consola los pones tú, dentro del emulador.
- **Actualizar:** Ajustes → Emuladores busca versiones nuevas en Flathub al abrirse. Pulsa A sobre un emulador instalado para actualizarlo, o usa «Actualizar todos». Cada fila muestra la versión instalada.
- **Nintendo Switch 2:** aparece en la lista como no disponible. Hoy no hay ningún emulador de Switch 2 publicado en Flathub; los proyectos que existen son experimentales. STONE no instala nada para Switch 2 ni promete compatibilidad.

## Otras novedades

- **Sorpréndeme** (Explorar y Biblioteca): STONE elige uno de tus juegos instalados, entre los que llevan más tiempo sin abrirse.
- **Parte de sesión:** al terminar un juego, cuánto jugaste y la temperatura de la GPU en ese momento. Se apaga en Ajustes → Rendimiento.
- Los avisos tienen un carril propio arriba a la derecha. Antes tapaban la fila inferior de Inicio y de la Biblioteca.
- Con el texto a 1,5×, la línea del juego en Inicio ya no pisa la etiqueta «ESTRATO 02».
- Al volver de Ajustes o de Energía, el foco cae en el elemento correcto de la fila inferior.

## Límites

- **El pago y el inicio de sesión son pantallas de Steam.** Es intencionado: STONE no maneja contraseñas ni tarjetas.
- **Steam al frente depende de Gamescope y de Steam.** Está escrito según el código de Gamescope y no se ha visto en la placa. Si falla, queda el plan B, y la compra con el móvil no depende de ninguno de los dos.
- **La lista de juegos de la cuenta** se lee de la interfaz de Steam por su estructura interna. Si una versión de Steam la cambia, STONE muestra los juegos instalados y la última lista guardada.
- La tienda y las carátulas necesitan internet.

# STONE OS (rebuild) 1.0.0-rc5

Corrige la instalación. Trae todo lo de rc4.

## Cambios en rc5

- **La ISO de rc4 no se podía instalar:** el instalador paraba con «Parsing manifest layout: Missing ostree.final-diffid». Las actualizaciones a rc3 y rc4 habrían fallado igual. La imagen conservaba una etiqueta de Bazzite que apuntaba a una capa que ya no existía tras el cambio de capas de rc3.
- **Comprobación nueva en cada compilación:** la imagen se importa como lo hace el instalador antes de publicarse; una imagen mala se detiene en GitHub y no llega a la consola.

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
