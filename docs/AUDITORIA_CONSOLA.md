# Auditoría de experiencia de consola (1.0.0-rc4)

> Continúa en `docs/AUDITORIA_3_0.md` (3.0.0-rc1), que corrige dos conclusiones de este documento: los avisos sí tapaban texto en Inicio y en la Biblioteca, y con el texto a 1,5× sí había un solapamiento en Inicio.

Fecha: 2026-11-08. Pedida por el propietario tras instalar 1.0.0-rc1/rc2 en la BC-250: «la experiencia debe ser como una consola de Sony o Xbox, sin terminal y sin ver la interfaz de Steam».

**Estado de todo lo de este documento: CODE TESTED** (simulación de STONE Home en el navegador y pruebas automáticas). Nada está observado todavía en la placa; las pruebas de placa nuevas son T-SETUP-01, T-FRAME-01, T-LOAD-01, T-ASK-01, T-MEDIA-01 y T-UNINST-01 (`hardware/validation/matrix.yaml`).

## Cómo se revisó

1. Se recorrió la consola como un jugador: primer encendido, Inicio, Biblioteca, Explorar, Media, ficha de un juego, jugar, menú rápido, Ajustes (las 15 categorías), Energía.
2. Se buscó en todo el código de la interfaz cualquier texto que mandara a la terminal (`stonectl`, `stone-game`, `stone-doctor`) o que abriera una pantalla de Steam.
3. Se añadió a la simulación un **detector de superposición** (`window.__overlap()` en `dev/home/sim_panel.html`). Mide la caja real de cada texto visible y avisa si dos textos se pisan o si un texto se sale de la pantalla de 1920 × 1080. Tiene en cuenta los paneles que recortan su contenido y la capa que está delante (diálogo, configuración, energía, menú rápido). Se pasó por cada pantalla, con nombres de juego muy largos y con el texto en tamaño grande (accesibilidad).

## Lo que se encontró y se arregló

| # | Dónde | Problema | Arreglo en rc4 |
| --- | --- | --- | --- |
| 1 | Primer encendido | Un cuadro de diálogo pequeño; sin red, mando, sonido ni encuadre | Configuración a pantalla completa en 8 pasos: Inicio, Mando (emparejar por Bluetooth), Internet (Wi-Fi con teclado en pantalla), Pantalla (encuadre), Sonido (salida y volumen), Rendimiento (40 CU), Steam, Listo. Se completa solo con el botón A |
| 2 | Televisor | No había forma de corregir el sobrebarrido (bordes cortados) | **Encuadre** de 0 a 6 % en la configuración y en Ajustes → Pantalla, con esquinas ámbar para ver dónde acaba la imagen |
| 3 | Ficha del juego | 11 acciones en una fila: «Propiedades» se salía por la derecha | 5 acciones (Favorito, Rendimiento, Gráficos, Experiencia, Propiedades). Las opciones de imagen están en el panel **Gráficos**, una por línea con su valor |
| 4 | Al pulsar JUGAR | Dos textos superpuestos abajo a la izquierda (aviso de ajustes y «en curso») | **Pantalla de carga**: arte del juego que se asienta, nombre, ajustes que se usarán, barra ámbar y pasos (Preparando → Steam abre el juego → Cargando). El aviso va dentro, sin superponerse |
| 5 | Al pulsar JUGAR | Pantalla casi negra sin información mientras el juego abre | La misma pantalla de carga, con un sonido propio de arranque |
| 6 | Juego que no abre | A los 90 s STONE dejaba de esperar sin decir nada | STONE pregunta: «Esperar» o «Volver al inicio», y explica dónde ver si Steam lo está actualizando |
| 7 | Al pulsar JUGAR | Si el servicio veía el juego antes de que STONE empezara a esperarlo, la pantalla de carga no se quitaba (encontrado en la simulación) | STONE comprueba el estado justo al empezar a esperar |
| 8 | Preguntas de Steam | En la sesión STONE la interfaz de Steam está oculta: si Steam preguntaba algo (partidas en la nube que no coinciden, opciones de arranque, licencias), el juego parecía no arrancar | STONE lee la pregunta de Steam y la muestra con su propio diseño («STEAM PREGUNTA»); la respuesta pulsa el botón de Steam. Se vigila al jugar, instalar y desinstalar **[VERIFICAR EN PLACA]** |
| 9 | Instalar HelixSR | Mandaba a la terminal (Ctrl+Alt+F3) | Quitado de la consola: su instalador oficial solo funciona en una terminal. HelixSR ya instalado se sigue detectando |
| 10 | Pantalla, Salud, Safe Mode | Textos con `stonectl`, `stone-doctor` o «terminal» | Reescritos sin terminal |
| 11 | Explorar y Media | Abrían la Tienda, las Descargas y las Capturas de Steam | Explorar: Buscar juegos, Descargas (en Ajustes → Almacenamiento) y Emuladores. Media: **galería de capturas propia**, con visor a pantalla completa |
| 12 | Propiedades | Decía «en la ficha del juego en Steam» | Panel propio (origen, tamaño, tiempo jugado, perfil) con **Desinstalar**, con confirmación y sin diálogo de Steam |
| 13 | Almacenamiento | «Desinstalar abre la confirmación de Steam» | STONE desinstala directamente |
| 14 | Inicio sin juegos | La tarjeta abría la tienda de Steam | Abre Buscar |
| 15 | Juego de pago | Mandaba a comprarlo «desde el escritorio» | App de Steam del móvil o `store.steampowered.com/app/<id>`; aparece solo en la biblioteca |
| 16 | Energía | «Escritorio» junto a Apagar y Reiniciar | Movido a Ajustes → Sistema → Modo escritorio (avanzado), con confirmación |
| 17 | Ajustes | En listas largas, las últimas filas pasaban bajo las ayudas de botones | La lista termina siempre por encima de las ayudas |
| 18 | Inicio | Un nombre largo ocupaba dos líneas y pisaba «ESTRATO 02 · LA MÁQUINA» | Una línea, con «…» |
| 19 | Visor de capturas | Botones sobre las ayudas de botones | Movidos encima |
| 20 | Configuración | El foco por defecto estaba en «ACTIVAR 40 CU»: pulsar A seguido lo activaba | El foco empieza en «AHORA NO»; 40 CU solo si se elige |
| 21 | Tras responder a Steam | La línea de foco quedaba en medio del juego | Se oculta al volver al juego |
| 22 | Cuenta de Steam | Si se dejaba para más tarde, no había dónde iniciar sesión | Ajustes → Steam → Cuenta de Steam |

## Pruebas de un jugador (simulación)

| Prueba | Resultado en simulación |
| --- | --- |
| Encender y llegar a Inicio pulsando solo A | Pasa (8 pulsaciones de A, sin errores en la consola del navegador) |
| Conectar a un Wi-Fi con contraseña con el mando | Pasa (lista de redes, teclado en pantalla, conectar) |
| Ajustar el encuadre y volver a 0 % | Pasa |
| Abrir un juego y ver la carga hasta el juego | Pasa; también con un juego que tarda 12 s |
| Responder a una pregunta de Steam durante la carga | Pasa (pregunta simulada de la nube) |
| Cambiar la imagen, la calidad y el aspecto de un juego | Pasa, en el panel Gráficos |
| Desinstalar un juego desde Propiedades | Pasa; vuelve a Inicio |
| Ver capturas a pantalla completa | Pasa |
| Recorrer las 15 categorías de Ajustes | Sin textos superpuestos ni fuera de pantalla |
| Nombre de juego de 70 letras en Inicio, ficha y Biblioteca | Sin superposiciones |
| Texto grande (accesibilidad, 150 %) en Inicio y ficha | Sin superposiciones |
| Menú rápido durante un juego | Sin superposiciones |

## Lo que STONE no puede ocultar (límites honestos)

- **Inicio de sesión de Steam:** es la única pantalla de Steam que se ve, una vez. Las credenciales solo deben ir a Steam; se puede usar el código QR con la app de Steam del móvil.
- **Compras:** STONE no hace pagos.
- **Menús de Steam dentro del juego:** el botón STEAM y el botón ··· abren los menús de Steam (rendimiento, teclado de Steam). El botón STONE abre el menú rápido de STONE.
- **Lanzadores de otras empresas** (EA app, Ubisoft Connect, Rockstar): algunos juegos abren su propia ventana antes de empezar. No es Steam y STONE no puede controlarla.
- **Ajustes de Steam que no son sí/no:** se muestran en Ajustes → Steam, pero no se cambian desde STONE.
- **Idioma:** la interfaz está solo en español.
- **Las preguntas de Steam** se leen de la interfaz de Steam por su estructura. Si una versión de Steam cambia esa estructura, STONE no verá la pregunta y el juego esperará como antes. Esto se comprueba en la placa (T-ASK-01).
