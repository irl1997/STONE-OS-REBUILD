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
