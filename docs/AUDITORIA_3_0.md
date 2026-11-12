# Auditoría de STONE OS 3.0.0-rc1

Fecha: 2026-11-11. Pedida por el propietario tras instalar 1.0.0-rc5 en la BC-250: «STONE OS no visualiza los juegos de la biblioteca de Steam, ni tampoco permite comprar juegos»; mejorar el arranque; añadir Switch y un actualizador de emuladores; «la experiencia debe ser 100 % de una consola».

**Estado de todo lo de este documento: CODE TESTED** (pruebas automáticas y simulación de la interfaz en el navegador). Nada está observado todavía en la placa. Las pruebas de placa nuevas son T-STEAM-11 a 14, T-LIB-11 a 13, T-STORE-01, T-EMU-02, T-EMU-03 y T-BOOT-10 (`hardware/validation/matrix.yaml`).

## Cómo se revisó

1. **Código de Gamescope** (`src/steamcompmgr.cpp`): qué ventanas puede poner en pantalla y cómo elige una.
2. **Camino de la biblioteca**, de punta a punta: archivos de Steam → interfaz de Steam → host de STONE → página.
3. **Simulación** de cada pantalla, nueva y antigua, con el detector de superposición (`window.__overlap()`). Esta vez también con un aviso visible, con el texto a 1,5× y con alto contraste.
4. **Pruebas automáticas** nuevas para cada pieza, incluidas las expresiones que STONE ejecuta dentro de Steam (en Node, contra objetos de sustitución).

## Lo que se encontró y se arregló

| # | Dónde | Problema | Arreglo en 3.0.0-rc1 |
| --- | --- | --- | --- |
| 1 | Inicio de sesión de Steam | Imposible en la sesión STONE. Gamescope solo muestra ventanas con identificador de aplicación, y las ventanas propias de Steam (con `steam -silent`) no lo tienen: la ventana existía y nunca estaba en pantalla. Sin sesión no hay cuenta ni biblioteca | **Steam al frente (D-34):** STONE pide la ventana; el supervisor de la sesión la marca, la nombra ante Gamescope y devuelve la pantalla a STONE (botón guía, Steam la cierra, empieza un juego, o termina el inicio de sesión) |
| 2 | Biblioteca | Se leía una sola vez al arrancar, antes de que Steam respondiera. Nada la volvía a leer | El host vigila a Steam y avisa a la página, que se redibuja en su sitio con el mismo foco |
| 3 | Biblioteca | La lista de la cuenta dependía de una sola estructura interna de Steam. Si una fuente fallaba al leerse, fallaba toda la lectura (encontrado con la prueba en Node) | Se unen cuatro fuentes sin repetir juegos; cada una se lee protegida |
| 4 | Biblioteca | Tras reiniciar, los juegos no instalados desaparecían hasta que Steam respondía | La última lista de la cuenta se guarda (por cuenta) y se muestra desde el primer cuadro |
| 5 | Inicio | Con juegos en la cuenta y ninguno instalado, la pantalla fallaba al dibujarse. Era el caso de una consola recién instalada | La primera fila muestra los juegos de la cuenta, listos para instalar |
| 6 | Juego en curso | Al recargar la biblioteca, «el juego en curso» podía pasar a señalar otro juego: se guardaba su posición en la lista, no su identidad | Las posiciones siguen a su juego por AppID |
| 7 | Carátulas | Los juegos no instalados salían sin carátula: Steam solo guarda en disco las de juegos que ha mostrado | El host descarga las que faltan de los servidores de imágenes de Steam y las guarda. Si no existe la vertical, usa la imagen ancha de la tienda |
| 8 | Compras | «De pago: STONE no hace compras», sin ningún camino en la consola | Pestaña TIENDA, ficha del juego, COMPRAR EN STEAM, COMPRAR CON EL MÓVIL (código QR) e instalación automática al llegar la compra |
| 9 | Instalar | Si la interfaz de Steam devolvía un error inesperado, la petición quedaba sin respuesta para siempre | Toda petición se responde; si falla la interfaz, se usa la URL de instalación |
| 10 | Avisos | Tapaban la fila inferior de Inicio y la línea de selección de la Biblioteca. La auditoría de rc4 no lo vio: midió sin ningún aviso en pantalla | Carril propio, arriba a la derecha |
| 11 | Inicio, texto a 1,5× | La línea del juego pisaba «ESTRATO 02 · LA MÁQUINA» | El bloque sube y crece hasta 1,3× |
| 12 | Foco | Al volver de Ajustes caía en «Explorar»; al cerrar Energía, en «Ajustes» | Se busca por nombre, no por posición |
| 13 | Apagado por inactividad | Habría podido apagar la consola con la tienda de Steam en pantalla | No se apaga mientras Steam está al frente |
| 14 | Primer arranque de Steam | En una consola nueva, Steam descarga primero su propia actualización (minutos). El inicio de sesión se habría rendido a los 25 s | STONE espera a que Steam esté listo, hasta 10 minutos, y lo dice en pantalla |
| 15 | Arranque | STONE Home esperaba a Steam, a `rpm-ostree` y a sus propias importaciones antes de dibujar | Home arranca antes que Steam; Chromium se lanza antes de preparar el host; Inicio no espera a `rpm-ostree` ni a Steam; la espera fija de la animación baja de 2,0 s a 1,25 s |
| 16 | Emuladores | Sin Nintendo Switch y sin forma de actualizar | Eden y Ryujinx; actualizar uno o todos; versión instalada a la vista. Switch 2: fila que dice la verdad (no hay emulador publicado en Flathub) |
| 17 | Pruebas | Las pruebas que arrancan el host real habrían salido a internet a por carátulas | `STONE_HOME_NO_FETCH=1` en esas pruebas; sin red, el host hace una pausa en vez de reintentar sin parar |

## Pruebas de un jugador (simulación)

| Prueba | Resultado en simulación |
| --- | --- |
| Consola sin cuenta: Inicio ofrece iniciar sesión; al terminar, aparece la biblioteca | Pasa |
| Steam todavía arrancando: «PREPARANDO STEAM», después su ventana | Pasa |
| Primer encendido: el paso STEAM inicia sesión y pasa a «conectada» | Pasa |
| Steam no muestra ventana: STONE lo dice y ofrece «Steam completo» | Pasa |
| Cuenta con juegos y nada instalado: Inicio los muestra; INSTALAR pasa a INSTALANDO… y a JUGAR | Pasa |
| La cuenta responde 6 s tarde: la Biblioteca pasa de 9 a 11 juegos sin perder el foco | Pasa |
| Las carátulas llegan después: sustituyen al nombre sin redibujar la pantalla | Pasa |
| Tienda: listas, precios, descuentos, buscar, sin conexión (mensaje y Reintentar) | Pasa |
| COMPRAR CON EL MÓVIL: código QR; la compra llega y STONE instala sola | Pasa |
| COMPRAR EN STEAM: el mando no mueve STONE mientras Steam está al frente; al volver, instala | Pasa |
| Emuladores: buscar versiones, actualizar uno, actualizar todos, Switch 2 | Pasa |
| Sorpréndeme y filtro «Por instalar» | Pasa |
| Parte de sesión tras un minuto de juego simulado | Pasa |
| Superposición de textos: Inicio, Biblioteca, ficha, Explorar, Media, Tienda, ficha de tienda, QR, Ajustes, con aviso largo visible | Sin superposiciones |
| Lo mismo con texto a 1,5× y alto contraste | Sin superposiciones |

## Pruebas automáticas

- **`pytest` en el Mac de desarrollo:** 117 pasan. 11 se omiten porque necesitan PyGObject, Xvfb o Chromium; corren en el CI.
- **Pruebas del host** (`tests/home_suite.py`) con un bucle de eventos de sustitución: 40 de 42. Las otras dos necesitan Python 3.10 o posterior y `dbus-daemon`; corren en el CI.
- **ESLint** sobre la página: 0 errores, 0 avisos.
- **Código QR:** el generador de STONE da los mismos módulos, uno por uno, que la biblioteca `python-qrcode` 8.2 en 13 textos (versiones 1 a 6). Cuatro de ellos quedan como referencia en `tests/test_qr.py`.
- **El CI no ha corrido todavía sobre esta rama** al escribir este documento. Corre al publicar la rama.

## Lo que solo la placa puede decir

| Qué | Si no es como se supone | Prueba |
| --- | --- | --- |
| Gamescope muestra la ventana de Steam una vez marcada | A los 25 s STONE lo dice y ofrece «Steam completo» | T-STEAM-11 |
| Steam, oculto, abre Big Picture con `steam://open/bigpicture`, y su ventana se titula «Big Picture» | A los 12 s se muestra la ventana más grande de Steam; si no hay ninguna, plan B | T-STEAM-12 |
| El botón guía se puede leer mientras Steam tiene el mando | Queda reiniciar la consola; al iniciar sesión STONE vuelve sola igualmente | T-STEAM-13, T-STEAM-14 |
| La interfaz de este Steam tiene las colecciones y el usuario donde STONE los busca | STONE muestra los instalados y la última lista guardada | T-LIB-11 |
| Eden abre un juego con `-f -g` y Ryujinx con `--fullscreen` | El emulador se abre sin el juego; se corrige el argumento | T-EMU-03 |
| Cuánto tarda el arranque | No se da ninguna cifra hasta medirlo | T-BOOT-10 |

## Límites

- **Inicio de sesión y pago son pantallas de Steam.** Es intencionado: STONE no maneja contraseñas ni tarjetas. En la ventana de inicio de sesión de Steam no hay teclado en pantalla: se usa su código QR con la app de Steam del móvil, o un teclado.
- **Los precios** son los que da la tienda pública de Steam para el lugar desde el que se conecta la consola. El precio final siempre es el de la pantalla de pago de Steam.
- **Nintendo Switch 2:** hoy no hay ningún emulador publicado en Flathub. STONE no instala ninguno ni promete compatibilidad.
- **Nintendo Switch:** las claves, el firmware y los juegos son de tu propia consola. STONE no los descarga.
- **Idioma:** la interfaz está solo en español.
