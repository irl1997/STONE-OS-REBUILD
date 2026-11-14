# STONE OS — Registro de decisiones técnicas

Proyecto: reconstrucción integral de STONE OS para STONE MACHINE (AMD BC-250).
Versión del documento: 1 · Fecha: 2026-11-06 · Estado: **antes de empezar la reconstrucción**. Todavía no hay código en este repositorio.

Este documento separa tres cosas que no deben mezclarse:

- **Sección 1. Decisiones confirmadas:** las tomó el propietario y son de obligado cumplimiento.
- **Sección 3. Recomendaciones técnicas:** son propuestas. Cada una necesita aprobación antes de aplicarse.
- **Sección 4. Datos pendientes de verificación:** nada de esto se puede dar por cierto hasta comprobarlo.

La sección 2 recoge hechos documentados, con su evidencia.

Documentos relacionados:

- `../../02_AUDIT/STONE OS — Hardware Performance  Overclock Audit v1.0.docx`: la auditoría original.
- `../../02_AUDIT/STONE_OS_Auditoria_Tecnica_v2.0_rc23.md`: auditoría de continuidad sobre rc23.
- `../../INVENTARIO_TECNICO_STONE_OS.md`: inventario del proyecto anterior.

---

## 1. Decisiones confirmadas

| ID | Decisión | Consecuencia práctica |
| --- | --- | --- |
| D-01 | **Plataforma única: AMD BC-250.** No se desarrolla para otras generaciones de hardware. El objetivo es la placa con **8 núcleos de CPU y 40 CU de GPU**. | El backend y los perfiles están escritos para la BC-250. Otros equipos sólo sirven para pruebas de software y deben quedar con todo en «no disponible». |
| D-02 | **Alcance integral.** STONE OS se reconstruye como sistema completo, no como versión básica permanente. | La arquitectura contempla desde el principio todos los módulos de la sección 5. |
| D-03 | **Implementación por fases.** F0–F3 forman la base estable y funcional; los demás módulos se añaden después, uno a uno. | La primera imagen de validación no necesita todos los módulos, pero cada módulo ausente se declara como tal y no se simula. |
| D-04 | **40 CU contemplado desde el inicio.** Todo desbloqueo, ajuste de frecuencia u overclock se verifica primero y tiene mecanismos de seguridad y recuperación. | Detección de CU, techo por calibración, guardia de arranque y vuelta atrás forman parte del núcleo, no son un añadido. |
| D-05 | **No fijar el regulador por suposición.** No se sustituye el regulador ni se adopta una versión nueva sin justificar su compatibilidad. | Ver H-02, R-03 y P-01. |
| D-06 | **No eliminar dependencias sin auditoría previa.** En particular, WebKit y Chromium siguen hasta que se apruebe la recomendación R-02. | Ninguna dependencia de rc23 se retira por ahora. |
| D-07 | **Idioma.** Código, nombres de variables, funciones y módulos, y comentarios técnicos: inglés. Documentación de usuario y manuales de instalación y configuración: español. Arquitectura técnica: preferentemente español, con los términos técnicos originales en inglés. | Este documento sigue ese criterio. |
| D-08 | **Nada se declara HARDWARE VERIFIED sin ejecutar su prueba en la BC-250.** | Sólo hay cuatro estados: `CODE TESTED`, `READY FOR HARDWARE TEST`, `OBSERVED ON BOARD` (dato visto, sin prueba formal) y `HARDWARE VERIFIED`. |
| D-09 | **Los datos de pantalla, conexión de vídeo y adaptadores** que no estén documentados quedan como pendientes. | Ver P-05 a P-07. |
| D-10 | **El repositorio anterior queda intacto.** No se empieza ninguna implementación que pueda comprometer funcionalidades existentes. | `01_STONE_OLD/` y `~/Downloads/stone-os/` se usan sólo para leer. |
| D-11 | **Si falta la auditoría, se genera una nueva sin inventar contenido.** | La v1.0 apareció (H-01). Se escribió además la v2.0 sobre rc23. |
| D-12 | (Sustituida por D-16 y D-17) **8 núcleos: verificar antes de tocar nada.** No se modifica la BIOS ni se aplica ningún desbloqueo por ahora. Primero se identifica cuántos núcleos están activos, qué método de desbloqueo hay y qué configuración tiene la placa. Si los 8 núcleos ya están activos, se documenta el procedimiento existente sin modificarlo. | P-03 se resuelve con el diagnóstico; P-04 queda sin acción hasta conocer el resultado. |
| D-13 | **La arquitectura STONE MACHINE se define antes de F0** y contempla todos los módulos del producto final. F0–F3 son etapas de construcción, no el producto. | `docs/ARQUITECTURA_STONE_MACHINE.md` v1.0, pendiente de aprobación. Los vacíos están marcados [P] o [V]. |
| D-14 | **Diagnóstico físico autorizado, sólo lectura.** Prohibido durante esa etapa: modificar BIOS o firmware, cambiar frecuencias o voltajes, activar o desactivar núcleos o CU, instalar o desinstalar paquetes, modificar servicios o configuraciones, y ejecutar pruebas de estrés. El procedimiento se aprueba antes de ejecutarlo. | `docs/diagnostico/PROCEDIMIENTO_DIAGNOSTICO_BC250.md` + `stone-diag-readonly.sh`, **aprobados el 2026-11-06**; pendientes de ejecución en la placa. |
| D-16 | **Configuración de hardware definitiva de STONE MACHINE: CPU con 8 núcleos desbloqueados y GPU con 40 CU habilitadas.** Lo confirma el propietario (2026-11-06) y es la referencia de diseño. La comprobación física queda diferida hasta que la consola vuelva a encenderse | STONE PERFORMANCE, STONE GRAPHICS y STONE OPTIMIZED se diseñan para 8 núcleos y 40 CU. Si STONE detecta otra configuración, lo muestra y funciona en modo conservador; nunca la da por buena (A3) |
| D-17 | **El desbloqueo de núcleos y CU no es una tarea pendiente.** No se investiga de nuevo ni se proponen cambios de BIOS o firmware para conseguirlo | Sustituye a D-12 y cierra P-04. El mecanismo de software de rc23 que la imagen necesita para arrancar con 40 CU (`amdgpu` con la opción `bc250_cc_write_mode`, guardia de arranque) se **conserva tal cual**, para no perder la configuración actual |
| D-18 | **No se inventan frecuencias máximas, voltajes ni límites térmicos.** Se determinan con documentación y validación posterior | Toda cifra del proyecto lleva su origen: leída del regulador, de fábrica, observada en placa o tomada de la documentación comunitaria. Ninguna es una constante de diseño de STONE |
| D-19 | **P-14 y la preparación de F0 siguen sin la consola encendida.** La validación física se programa para una fase posterior | Sustituye en parte a D-15: F0 se prepara y construye con verificación de software; su puerta de placa queda diferida y registrada (sección 6) |
| D-15 | **F0 no empieza** (sustituida en parte por D-19) hasta que P-14 esté resuelto documentalmente y el diagnóstico de hardware esté hecho, o hasta que las verificaciones físicas pendientes queden identificadas explícitamente. No se asume ninguna característica del hardware que no se haya comprobado. | Puerta previa a F0. |
| D-20 | **Autonomía total** (C-2, 2026-11-07). Claude avanza sin pedir aprobación tras cada módulo y se detiene sólo ante un bloqueo de acceso, hardware, autorización o información | Siguen vigentes los límites físicos: Claude no puede hacer push (el Mac no tiene credenciales de GitHub), no accede a la placa y no puede construir la imagen en el Mac. Cada decisión técnica tomada bajo esta autonomía se registra en este documento con su justificación |
| D-21 | **Sesión propia de STONE desde ya** (C-3). Steam Game Mode deja de ser la experiencia: STONE OS arranca en su propia sesión Gamescope con STONE Home al frente, y Steam corre como componente interno en segundo plano | Sustituye el principio A6. Steam Game Mode se conserva sólo como **ruta de recuperación** (nunca como experiencia normal). Diseño en ARQUITECTURA v1.2 (M24 STONE SESSION); las incógnitas técnicas se resuelven en F2 con pruebas en la placa (V-12 a V-16) |
| D-22 | **Generación de fotogramas permitida con condiciones** (C-7). Sustituye la regla de rc21 «nunca». Apagada por defecto; sólo se activa si la persona la elige o si una medición en esta consola muestra mejora; nunca en juegos online o con anti-cheat; los FPS generados se muestran aparte de los renderizados | STONE GRAPHICS y STONE OPTIMIZED |
| D-23 | **Vocabulario único de estados** (C-9): `CODE TESTED` → `READY FOR HARDWARE TEST` → `OBSERVED ON BOARD` → `HARDWARE VERIFIED`, más `EXPERIMENTAL` y `BLOCKED` para módulos, y `COMMUNITY REPORTED` sólo para perfiles de juego | Sustituye las listas de §22 y §30 del prompt maestro. Amplía D-08 |
| D-24 | **Recomendaciones aplicadas bajo D-20** a las contradicciones restantes del prompt maestro: C-1 (sólo se detecta y verifica el estado de núcleos y CU; D-17 sigue), C-4 (ventilador en sólo lectura; control por software sólo como módulo experimental con vuelta a la curva de la BIOS), C-5 (límite de potencia «no disponible» salvo que el diagnóstico encuentre interfaz), C-6 (CPU sólo detectada y monitorizada), C-8 (descargas a través del adaptador de Steam con capacidades detectadas; marcado «depende de Steam») | Decisiones conservadoras: no cambian nada de lo confirmado. Revisables por el propietario |
| D-26 | **Firma sin clave (keyless)** de las imágenes, decidida bajo D-20 (2026-11-07) a petición del propietario de no gestionar claves. Sustituye a F0-C: GitHub Actions firma con la identidad OIDC de `build-image.yml` a través de Sigstore y verifica la firma en el mismo flujo | Desaparecen cosign en el Mac, `cosign.key`, `cosign.pub` y `SIGNING_SECRET`. Efecto aceptado: la entrada pública de transparencia (Rekor) muestra el nombre del repositorio y del flujo. Verificación en `docs/FIRMA.md` |
| D-27 | **STONE DISPLAY y STONE OPTIMIZED se portan de rc23 junto con STONE Home en F2**, sin cambios, decidido bajo D-20 (2026-11-07). El host de Home los importa y la interfaz de rc23 llama a sus métodos; dejarlos para F4/F5 obligaría a recortar la interfaz y perder funciones existentes | F4 y F5 pasan a ser la revalidación en placa y la ampliación de esos módulos (IMAGE, generación de fotogramas según D-22, EXPERIENCE ENGINE), no su primera llegada. Sus suites de rc23 (D01–D24, G01–G22) corren en CI desde F2 |
| D-25 | **El prompt maestro es el objetivo de producto de STONE OS 1.0 RC.** Se integra en ARQUITECTURA v1.2 con los módulos nuevos M17–M24. Se mantiene la numeración F0–F9 ya en marcha, con la equivalencia de `REVISION_PROMPT_MAESTRO.md` §5 | La revisión completa queda en `STONE_MACHINE/REVISION_PROMPT_MAESTRO.md` |
| D-31 | **Una sola ISO 1.0.0-rc1 con todo el plan, instalada desde cero** (decisión del propietario, 2026-11-07). Los bloques 0.5 a 1.0 se construyen seguidos y se publican juntos como `1.0.0-rc1`, sin versiones intermedias | Para reducir errores en la consola: cada función comprueba si la consola puede hacerla y, si no, se muestra «no disponible» sin romper nada; lo arriesgado viene apagado de fábrica; una prueba de humo en CI arranca la imagen construida y comprueba paquetes, servicios y módulos; `stonectl doctor` se ejecuta en el primer arranque. La ISO borra el disco: el propietario lo asume (rc23 desaparece) |
| D-28 | **Todo el prompt maestro sin esperar a la placa** (decisión del propietario, 2026-11-07). F3 a F9 y el rediseño se construyen seguidos, sin parar por pruebas en hardware | Cada pieza termina en `CODE TESTED` o `READY FOR HARDWARE TEST`, nunca en `OBSERVED ON BOARD` sin la placa (D-23). Riesgo aceptado: si la placa contradice la sesión STONE, el mando o el foco de Gamescope, habrá que rehacer partes. La guía de la placa de 0.3.0-dev.1 sigue disponible para cuando se use. Plan en `docs/fases/PLAN_HASTA_1_0.md` |
| D-29 | **«Llegar y jugar» desde la próxima versión** (decisión del propietario, 2026-11-07). La imagen arranca directamente en la sesión STONE, sin comandos | La imagen trae la sesión STONE como sesión automática. Lo acompaña una guardia: si dos arranques seguidos en la sesión STONE no llegan a «Home operable» (BOOT TO READY), la consola vuelve sola al Game Mode de Bazzite en el siguiente arranque y Home explica por qué. `stone-session default off` sigue disponible. Sustituye «instalada pero no automática» de F2 |
| D-30 | **Rediseño de STONE a partir del sistema visual actual** (decisión del propietario, 2026-11-07): piedra, basalto, THE LINE, el arranque de Plymouth | Visión más artística y propia de la consola. Se presentaron tres direcciones (Monolito, Estratos, Forja) y el propietario eligió **B · Estratos** (2026-11-07): la pantalla en capas como roca en corte, etiquetas de muestra geológica en mono, una veta ámbar entre capas y el estado de la máquina siempre a la vista. La reconstrucción modular de Home (R-08) se hace con el lenguaje elegido, y todas las pantallas de F3 a F9 nacen con él |
| D-32 | **Troceado de la imagen con chunkah** (2026-11-08), a raíz de que la actualización de 1.0.0-rc1 a rc2 pesara ~7 GB en la consola. Sustituye a `rpm-ostree compose build-chunked-oci` | `build-chunked-oci` repartía los archivos en capas distintas en cada compilación, así que cambiar un archivo obligaba a descargar casi toda la imagen. chunkah (CoreOS, el que usa Bazzite) agrupa cada paquete en la misma capa compilación tras compilación: la consola solo descarga las capas que cambian. La imagen de chunkah va fijada por digest y se verifica su firma antes de usarla (`scripts/rechunk.sh`, también en la compilación local). Cada compilación dice en su resumen cuánto descargará una consola que esté en la versión anterior del mismo canal. La primera actualización a una imagen con chunkah sigue siendo completa, porque las capas cambian de forma; las siguientes son pequeñas |
| D-33 | **Experiencia de consola sin terminal y sin pantallas de Steam** (decisión del propietario, 2026-11-08). Auditoría completa en `docs/AUDITORIA_CONSOLA.md` | Configuración del primer encendido a pantalla completa; pantalla de carga propia al jugar; las preguntas de Steam se muestran y responden desde STONE; galería de capturas propia; nada en la interfaz manda a la terminal; HelixSR sale de la consola porque su instalador solo funciona en terminal; Escritorio pasa a Ajustes → Sistema. Quedan de Steam, por necesidad: el inicio de sesión (una vez), las compras y sus menús dentro del juego |
| D-34 | **STONE Home vuelve como interfaz de la consola, con Steam al frente para iniciar sesión y comprar** (decisión del propietario, 2026-11-10: «la experiencia debe ser 100 % de una consola»; última oportunidad para STONE OS). Sustituye a 2.0.0-rc1 (tema sobre el Modo Juego de Steam), que se abandona. Matiza D-33: el inicio de sesión y el pago siguen siendo pantallas de Steam, y ahora se pueden ver | Causa del fallo de rc5: Gamescope solo muestra ventanas con identificador de aplicación y las ventanas propias de Steam, con `steam -silent`, no lo tienen (`steamcompmgr.cpp`, lista de ventanas enfocables); la ventana de inicio de sesión existía y nunca estaba en pantalla. Solución: STONE Home pide la ventana de Steam con la propiedad `STONE_STEAM_FRONT` en la raíz de X; el supervisor de la sesión marca las ventanas de Steam (`STEAM_GAME=769`), nombra la que se muestra (`GAMESCOPECTRL_BASELAYER_WINDOW`) y devuelve la pantalla a Home con el botón guía, cuando Steam cierra su ventana, cuando empieza un juego o al terminar el inicio de sesión. Para la tienda se usa Big Picture. Plan B: el supervisor entrega la sesión a la interfaz de Modo Juego de Steam (la misma orden que la recuperación de D-21) y la recupera después. La biblioteca se vigila (la cuenta responde tarde, llegan juegos) y la última lista de la cuenta se guarda entre arranques. La tienda se lee de la API pública de Steam desde el host; STONE no maneja contraseñas ni pagos. Las carátulas que Steam no tiene en disco se descargan solo de `*.steamstatic.com`. Todo en CODE TESTED: pruebas de placa T-STEAM-11 a 14, T-LIB-11 a 13, T-STORE-01, T-EMU-02/03 y T-BOOT-10 |
| D-35 | **Diseño Cristal para STONE Home** (decisión del propietario, 2026-11-12: la interfaz se veía «apagada»; referencias Xbox, PS5, Apple TV y Liquid Glass; «un diseño que recuerde al diseño de la consola»; la tipografía de la marca). Se entrega como actualización en línea por el canal `rc` (3.1.0-rc1). Restyla Estratos (D-30) sin quitarle funciones | Capa visual propia (`dev/home/home_parts/cristal.css`, cargada después de Estratos) con los materiales de la STONE MACHINE: cristal negro brillante, banda de piedra facetada, panel blanco para lo elegido y la línea de luz. Liquid Glass con `backdrop-filter` y un filtro SVG de desplazamiento (`lens.html`); si Chromium no lo dibuja, queda el desenfoque. Tipografía: Jost 200/300/400 del logotipo, incluida en la imagen; IBM Plex Mono para cifras. Acento tomado del arte del juego en el propio Chromium (lienzo de 24×14). Carátulas de apartados dibujadas por la página (`covers.js`), sin imágenes. «Efectos ligeros» (preferencia `glass`) quita desenfoque y lente; sin GPU es obligatorio. Coste en GPU y legibilidad a distancia sin medir: T-HOME-03 a 05; la llegada por el canal, T-UPD-02. Todo en CODE TESTED |
| D-36 | **STONE habla con Steam con prueba de lo que pasó, Steam espera durante el primer encendido y las actualizaciones se buscan solas y a pedido** (a raíz de la consola con 3.0.0-rc1, 12-11-2026: juegos que no se instalaban, el inicio de sesión de Steam sobre la configuración inicial y «Comprobación automática: desactivada»; el propietario pide una ISO nueva). Versión 3.1.0-rc3 (3.1.0-rc2 se detuvo en CI y no se publicó) | Instalar: el asistente de Steam se sigue por su estado (`SteamClient.Installs.GetInstallManagerInfo`, `EInstallMgrState` de decky-frontend-lib) y solo se continúa en la carpeta y en la licencia gratuita pedida; contrato de licencia, clave, contraseña o disco vuelven a STONE sin aceptar nada; falta de espacio se dice con cifras; la instalación cuenta como empezada solo cuando aparece el `appmanifest` del juego (`storage.manifest_state`). Desinstalar espera a que desaparezca. Progreso en la ficha y en la pantalla de carga. Primer encendido: el supervisor no arranca Steam hasta el paso STEAM (`steam.wanted`) o el final; además, toda ventana de Steam no pedida pierde `STEAM_GAME` y se aparta a (-32000, -32000), con registro. Actualizaciones: la imagen activa `uupd.timer` (Bazzite deck lo deja apagado y espera a `steamos-update`, que la sesión STONE no muestra) y Ajustes ofrece Buscar actualizaciones, que arranca `uupd-manual.service` (la regla polkit de uupd lo permite). Todo en CODE TESTED: T-STEAM-15, T-STEAM-16, T-SETUP-02 y T-UPD-03 |
| D-37 | **Las llamadas a Steam se toman del código de su propia interfaz; descargas en vivo; contrato de licencia en STONE; fondos al doble de resolución** (a raíz de la consola con 3.1.0-rc3, 12-11-2026: «Steam no respondió» al instalar, carátulas transparentes y fondos pixelados; el propietario pide instalar sin entrar a Steam y una barra de descarga). Versión 3.1.0-rc4. Corrige D-36 | Fuente: el paquete público del cliente (`steam_client_ubuntu12` → `steamui_websrc_all.zip`, suma comprobada; se lee, nunca se ejecuta). De ahí: `OpenInstallWizard([appid], "0")` (el segundo dato es el cliente local; rc3 pasaba uno), la lista de juegos en `rgApps` (rc3 leía `rgAppIDs`), los pasos por `RegisterForShowInstallWizard`, `OpenUninstallWizard([appid], "0", true)`, el contrato con `Apps.LoadEula` y `Apps.MarkEulaAccepted`, y las descargas en `window.downloadsStore` (estado, bytes por etapa, velocidad, tiempo). El `appmanifest` decide siempre si la instalación empezó. El contrato se muestra en STONE (dirección y QR) con el foco en «No acepto»; solo la respuesta de la persona se pasa a Steam. Fondos: tipo de arte `hero2x` (`library_hero_2x.jpg`), pedido para el juego en foco; lo que aún se amplía mucho se suaviza (`--bg-blur`) y el arte claro recibe más sombra (`--bg-dim`). Carátulas sin instalar opacas. El código de instalación se ejecuta en las pruebas contra un Steam simulado (`tests/test_steam_install.py`). Todo en CODE TESTED: T-STEAM-15, T-STEAM-17, T-STEAM-18 y T-HOME-06 Abrir juegos (13-11-2026, Batman: Arkham City en «SIGUE CARGANDO»): el arranque se sigue con `Apps.RegisterForGameAction*` (oyente único en `window.__stoneGA`) y `GetActiveGameActions`; las preguntas (`ShowLaunchOption`, `ShowEula`, `SynchronizingCloud`, `RunningInstallScript`, `KickingOtherSession`, `ShowGameArgs`) se hacen en STONE y se responden con `ContinueGameAction`/`CancelGameAction` usando solo las respuestas de Steam; los errores `AppError_N` se dicen con sus textos. Steam Play para todos los títulos: `CompatToolMapping` "0" = `proton_experimental` en `config.vdf`, solo si no existe y con Steam cerrado (copia `config.vdf.stone-bak`). T-STEAM-19 |
| D-38 | **Todo lo que STONE le pide a Steam se comprueba contra el código de la propia interfaz de Steam** (el propietario, 13-11-2026: «lee el código de la propia Steam … para que stone os converse al 100% con steam os», y después: revisar el sistema, encontrar las fallas y arreglarlas). Versión 3.1.0-rc5, por actualización en línea. Amplía D-37 | Herramienta `dev/steam/steam_api.py` (`fetch` con suma SHA-256, `report`, `check`); foto sin código de Steam en `docs/steam/steam_api.json`, que `tests/test_steam_api.py` comprueba en cada compilación (llamadas, número de argumentos, campos, secciones de ajustes y páginas del navegador); guía `docs/steam/COMO_HABLA_STONE_CON_STEAM.md`. Fallos encontrados y corregidos: (1) la biblioteca leía `installed`, que en Steam es el del equipo de la cuenta que más tiene (puede ser otro PC): un juego instalado en el PC de la persona desaparecía de STONE; ahora se usa la entrada de esta consola (`per_client_data` con `clientid` "0", `local_per_client_data`) y se omite lo que la cuenta no posee (`BIsOwned`). (2) No había forma de cerrar un juego desde STONE: «Cerrar juego» en el menú rápido y en la ficha del juego abierto, con la pregunta de Steam («¿Salir del juego?», «Los datos no guardados podrían perderse.») y `Apps.TerminateApp(gameid, false)`. (3) Las descargas no se podían pausar: `Downloads.EnableAllDownloads(false, "0")` para pausar (Steam pausa sus descargas, no un juego) y `ResumeAppUpdate(appid, "0")` para reanudar o descargar ya uno en cola. (4) La resolución por juego se leía con `Apps.GetResolutionOverrideForApp`, que la interfaz de Steam nunca llama: ahora se lee de `RegisterForAppDetails` (`strResolutionOverride`), como Steam; la otra queda solo de respaldo. Confirmado sin cambios: abrir Ajustes y Descargas de Steam (`Navigator.Settings(sección)`, las 11 secciones de STONE son rutas de Steam). CODE TESTED: T-LIB-14, T-STEAM-20, T-STEAM-21, T-DISP-02 |

---

## 2. Hechos documentados (con evidencia)

| ID | Hecho | Evidencia |
| --- | --- | --- |
| H-01 | La auditoría v1.0 existe. Es del 23-10-2026, cubre el prototipo anterior a rc1 y propone el plan P0–P3. Estaba en `~/Downloads`; se copió a `02_AUDIT/` | SHA-256 `d1673fb8…385ea4`, idéntico en origen y copia |
| H-02 | **Versión del regulador durante rc14–rc16:** `cyan-skillfish-governor-smu` **`v0.4.14-1.20260619120402457887.update.deps.3.g14080b4.fc44`**. Es la misma en todas las releases publicadas de rc2 a rc16 | `02_AUDIT/evidencia/build-metadata/build-metadata-v0.1.0-rc{14,15,16}.json`, campo `STONE_GOVERNOR_VERSION` |
| H-03 | **rc23 trae otra versión del regulador:** `v0.4.15-1.…g14080b4.fc44`. No tiene validación ni nota en las release notes | `build-metadata-v0.1.0-rc23.json` |
| H-04 | Entorno de rc14–rc16: kernel `7.2.11-ogc4.1.fc44`, Bazzite `44.20261026.0`, base `sha256:278941ea…bdf4e`, Mesa `26.2.4-1.fc44`, Gamescope `terra-gamescope 3.17.0^1-1.fc44`, WebKitGTK `2.54.1`, Chromium `156.0.8078.73`, 40 CU `ok` (OGC `v7.2.11-ogc4`) | build-metadata rc14–rc16 |
| H-05 | Digests de imagen: rc14 `sha256:b10bb52c…2d17`, rc15 `sha256:a99b860d…3391`, rc16 `sha256:4974e3da…baa` | build-metadata |
| H-06 | Curva del regulador (rc14–rc23): `500@700, 1000@800, 1175@850, 1500@900, 1600@910, 1700@920, 1850@930, 2000@960` (MHz@mV); rango inicial 1000–1850; corte térmico 85 °C | build-metadata |
| H-07 | Observaciones en placa: con 40 CU, 1500→1950 MHz aprobados; **cuelgue total a 2000 MHz**; validado 1900 MHz; `pp_dpm_sclk` y `gpu_metrics` no fiables; el regulador no publica la frecuencia actual. Estado: `OBSERVED ON BOARD` | `STONE_PERFORMANCE.md` (rc14, rc15), RELEASE_NOTES rc16 |
| H-08 | Conexión de vídeo: DisplayPort → HDMI con un adaptador de unos 300 MHz de reloj de píxel. Con él, 4K60 no cabe; 1440p60 y 4K30 sí. Estado: `OBSERVED ON BOARD` (sin modelo de adaptador) | RELEASE_NOTES rc18 |
| H-09 | FIRMWARE.md descarta la BIOS MeiMeiDXE (desbloqueo a 8 núcleos) por ser la opción de mayor riesgo. RELEASE_NOTES rc8 dice que «el desbloqueo de 8 núcleos vive en el firmware». Ningún documento registra cuántos núcleos tiene esta placa | `docs/FIRMWARE.md`, RELEASE_NOTES rc8 |
| H-10 | Existe historial git completo (rc2→rc23) en `~/Downloads/stone-os` (remoto `irl1997/stone-os`) y 12 releases publicadas por CI | `git log`, API de releases |
| H-11 | El documento de arquitectura STONE MACHINE y los documentos de diseño originales no están en ninguna fuente disponible | `docs/AUDIT_STATUS.md` («fuera del repositorio») |

---

## 3. Recomendaciones técnicas

> **Estado: R-01 a R-12 APROBADAS por el propietario el 2026-11-06.** Desde esa fecha son de obligado cumplimiento, igual que las decisiones de la sección 1. Las condiciones que cada una lleva siguen vigentes: R-02 retira WebKit sólo después de la prueba 26; R-03 fija la versión del regulador sólo después de P-01.

### R-01. Base del sistema
Mantener la imagen bootc derivada de `bazzite-deck` (Fedora 44) con el patrón `ublue-os/image-template`. Fijar el digest de la base en cada release. Reutilizar el build de rc23, que instala y arranca en la placa (H-10, observaciones de rc1).

### R-02. Motor de STONE Home: auditoría WebKit / Chromium

**Quién usa cada motor en rc23**

| Componente | Motor | Dependencias | Papel |
| --- | --- | --- | --- |
| `stone_home/chromium.py` | Chromium (sistema, Fedora) | `chromium`; GTK 4 + Gdk **sólo para medir la pantalla** (`screen_size()`) | Motor por defecto desde rc9; GPU, kiosko, perfil propio, proxy nulo |
| `stone_home/server.py` | — (HTTP local) | stdlib | Transporte de Chromium y del servidor de desarrollo |
| `stone_home/app.py` | WebKitGTK 6 + GTK 4 | `webkitgtk6.0`, `gtk4`, `python3-gobject` | Respaldo sin GPU y `--selftest` |
| `/usr/libexec/stone-home` | Ambos | — | Elige motor; pasa a WebKit si Chromium falta o cae 3 veces al arrancar |
| `/usr/bin/stone-home` | WebKit | — | Fuerza dibujo por software (`GSK_RENDERER=cairo` …) para WebKit |
| `stone_home/host.py` | Ninguno | — | Tabla de métodos independiente del transporte |
| `build_files/build.sh` | Ambos | instala `webkitgtk6.0 gtk4 chromium`; **el build falla si falta cualquiera** | — |
| `tests/webkit_selftest.py` / `chromium_selftest.py` / `e2e_home.py` / `test_server.py` | Cada uno el suyo | Xvfb, WebKitGTK, Chromium, Playwright | Pruebas |
| `stone_home/session.py` (`diag`) | — | Imprime la versión de WebKitGTK | Diagnóstico |
| Interfaz de Steam (Game Mode) | CEF de Steam (propio de Steam, no el Chromium del sistema) | Steam | No es de STONE |

**Impacto de cada opción**

| Opción | Ventajas | Inconvenientes |
| --- | --- | --- |
| A. Mantener ambos (como rc23) | Siempre hay interfaz aunque Chromium falle | Dos motores que mantener, probar y actualizar; mayor tamaño de imagen; el respaldo dibuja por software, lento a 4K |
| B. Sólo Chromium | Un motor; GPU a resolución nativa; el mismo motor que Steam usa en el mismo Gamescope; menos superficie que mantener | Sin respaldo de STONE: si Chromium falla, se ve la interfaz de Steam (la consola sigue usable); GTK 4 sigue haciendo falta salvo que la medida de pantalla se haga con X11 (ya existe `stone_display/xwayland.py`) |
| C. Sólo WebKit | Menos memoria esperable | En la placa, el dibujo por GPU parpadeó y salió transparente (rc2); por software no es fluido a 4K. **No viable** |
| D. Interfaz nativa (Qt/QML u otra) | Posible menor consumo | Reescritura completa del diseño y del mando; sin datos; mayor riesgo |

**Recomendación:** objetivo **B (sólo Chromium)**, aplicado en dos pasos:

1. En F0–F2 se mantienen los dos motores tal como están (D-06).
2. WebKit se retira sólo cuando se cumplan las tres condiciones:
   - la prueba 26 (Home con GPU a 4K) pasa en la placa;
   - N arranques seguidos no activan el respaldo;
   - está validado que, si Chromium falla, la consola cae en la interfaz de Steam y sigue usable.

En ese momento, además, la medida de pantalla deja GTK y pasa a X11, para no arrastrar GTK 4. El consumo real de memoria y CPU de cada motor **está sin medir**: se medirá en la placa antes de decidir (P-10). No se elimina nada hasta aprobar esta recomendación.

### R-03. Regulador de frecuencia

- **Versión candidata para fijar:** `v0.4.14-1.20260619120402457887.update.deps.3.g14080b4.fc44` (H-02). Es la versión con la que se tomaron todas las mediciones de placa.
- No se fija mientras no se confirme en la placa que esa era la imagen instalada (P-01).
- **No adoptar v0.4.15** (H-03) sin prueba de contrato D-Bus (métodos, propiedades, curva) y sin repetir en placa las pruebas 0, 5 y 28.
- Conservar el RPM exacto de la versión validada, porque el COPR puede retirarla.

### R-04. Rendimiento con 40 CU
- 40 CU es la configuración de referencia (D-16).
- Techo por calibración propia de cada consola; nunca un número fijo.
- Los únicos datos de frecuencia disponibles son observaciones de rc15, no límites de diseño (D-18):
  - pasos aprobados hasta 1950 MHz;
  - cuelgue total en el paso de 2000 MHz;
  - máximo validado calculado: 1900 MHz.
- Mientras no haya una nueva calibración, se conserva la regla de rc16: no repetir el paso donde se colgó la placa.
- La validación definitiva del máximo requiere la calibración `standard` y una sesión larga de juego.
- La única acción automática permitida sobre 40 CU es la de seguridad: la guardia de arranque vuelve a 24 CU ante errores de GPU y lo informa. Activar 40 CU nunca es automático.

### R-05. Telemetría
- Declarar la fiabilidad medida de cada sensor en un perfil de placa (`hardware/bc250.yaml`).
- Mientras el regulador no publique la frecuencia real, usar la «velocidad real» de `stone-cu-verify` para la calibración y «—» en la interfaz.

### R-06. Integración con Steam
Crear un adaptador único con tres propiedades:
- detecta qué capacidades ofrece la versión instalada de Steam;
- tiene fallback (`steam://`, interfaz de Steam);
- se prueba con grabaciones tomadas de la Steam real de la placa.

Ningún módulo llama directamente a `SteamClient.*`. Hay que revisar también el riesgo del puerto CEF 127.0.0.1:8080.

### R-07. Contrato de API versionado
Definir `api/` con dos contratos: `stone-performance.v1` y `stone-home.v1`. De ellos salen la validación del host, el cliente JS y el *mock* del simulador. Así desaparecen las tres copias actuales de la misma API.

### R-08. Interfaz
Proyecto front-end modular con build reproducible. Conserva el diseño de rc23: THE LINE, navegación con mando, sonido. Sustituye la generación por anclas de texto.

### R-09. Seguridad
- Acotar la regla polkit al usuario de la consola, en lugar de todo `wheel`.
- Descargas de componentes de terceros desactivadas por defecto.
- Firma cosign obligatoria en las releases.

### R-10. Estructura del repositorio
```
image/        Containerfile, build_files/, config/, disk_config/
system/       rootfs (system_files)
services/     stoned/ y futuros servicios de sistema
apps/         stone-home/ (host + ui/)
modules/      display, graphics, optimized, connect, downloads, emulation, desktop, boot
api/          contratos versionados
hardware/     bc250.yaml, validation/ (matriz y resultados con fecha)
dev/          contenedor de desarrollo (Fedora 44), simulador, devserver
docs/         usuario (es), instalación (es), arquitectura (es + términos en inglés)
.github/
```

### R-11. Entorno de pruebas en macOS
Crear un contenedor Fedora 44 con PyGObject, dbus, Xvfb, Chromium, WebKitGTK y Node, para correr las mismas suites que CI. Además, migrar el runner propio a pytest conservando los identificadores de los casos (R01, P17, G22…).

### R-12. Copias de seguridad
Antes de la primera línea de código:
- copiar `01_STONE_OLD` y `~/Downloads/stone-os` (con `.git`) a `04_BACKUPS`, con su SHA-256;
- guardar allí también los metadatos de build y la auditoría v1.0.

---

## 4. Datos pendientes de verificación

| ID | Dato | Cómo se verifica | Requiere placa |
| --- | --- | --- | --- |
| P-01 | Que la placa ejecutó las imágenes rc14–rc16 publicadas (y por tanto el regulador v0.4.14) | En la placa: `rpm-ostree status` (digest) y `rpm -q cyan-skillfish-governor-smu` | Sí |
| P-02 | Compatibilidad del regulador v0.4.15 (D-Bus, propiedades, curva, `Enabled`) | Prueba de contrato + pruebas 0, 5 y 28 | Parcial (contrato en software, comportamiento en placa) |
| P-03 | **Confirmado por el propietario (D-16): 8 núcleos y 40 CU. Sólo queda la comprobación física diferida.** Antes: número de núcleos de CPU activos y BIOS instalada. Antecedentes: el prototipo asumía 6 núcleos y 24 CU; las notas de rc8 dicen que el desbloqueo vive en la BIOS; FIRMWARE.md descarta la BIOS MeiMeiDXE | Diagnóstico, secciones 02–03 (`lscpu`, `core_id`, `dmidecode -t processor`: Core Count frente a Core Enabled; versión de BIOS) | Sí |
| P-04 | **Cerrado (D-17).** No es una tarea pendiente. El diagnóstico diferido sólo registrará la versión de BIOS y la línea de arranque como dato informativo | — | — |
| P-05 | Modelo y capacidades de la pantalla (TV 4K, modelo, HDR, VRR, Hz) | `stonectl display diagnostics` (EDID sin número de serie) | Sí |
| P-06 | Modelo del adaptador DP→HDMI (pasivo/activo, reloj máximo) y cable | Etiqueta del producto + `stonectl display` | Sí |
| P-07 | Salida de vídeo usada en la placa (DP) y si existe alternativa | Inspección física | Sí |
| P-08 | Significado de la propiedad `Enabled=false` del regulador | Documentación del regulador + prueba | Sí |
| P-09 | Fuente fiable de frecuencia y carga de GPU (`fix-metrics`) | Prueba en placa | Sí |
| P-10 | Consumo real de memoria y CPU de Chromium y WebKit en Gamescope a 4K | Medición en placa (prueba 26 ampliada) | Sí |
| P-11 | Formato `reaper SteamLaunch AppId=` en la Steam actual | `ps -eo args \| grep SteamLaunch` | Sí |
| P-12 | Watchdog de hardware (`sp5100_tco`) | Prueba 15 | Sí |
| P-13 | Curva de ventilador de la BIOS (valores) y canal `fan2` | FIRMWARE.md + prueba 13 | Sí |
| P-14 | Documento de arquitectura STONE MACHINE con la definición de todos los módulos | **Resuelto documentalmente:** `ARQUITECTURA_STONE_MACHINE.md` v1.0, pendiente de aprobación; sus vacíos van de V-01 a V-11 | No |
| P-17 | Conectividad física (Ethernet, USB, Bluetooth, Wi-Fi) y almacenamiento | Diagnóstico, sección 10 | Sí |
| P-18 | Sesión de escritorio disponible en la imagen y mecanismo para cambiar a ella | Diagnóstico, sección 12 | Sí |
| P-15 | 1900 MHz con 40 CU en calibración `standard` y sesión larga | Prueba 28 | Sí |
| P-16 | Mando dentro de STONE Home, foco al volver de un juego | Prueba 17 | Sí |

---

## 5. Módulos de STONE OS y fases

Estado en rc23: **Existe** = hay código reutilizable · **Parcial** = existe una parte · **Nuevo** = no existe nada · **Sin especificar** = falta su definición (P-14).

| Módulo | Estado en rc23 | Qué hay | Fase propuesta |
| --- | --- | --- | --- |
| Imagen base (Bazzite bootc, sin reposo, kernel check) | Existe | `Containerfile`, `build.sh` | F0 |
| STONE BOOT ENGINE | Parcial | Plymouth, vídeo de arranque, `stoned-recover`, autoarranque de Home | F0 (base), F2 (Home) y ampliación posterior (sin especificar) |
| STONE PERFORMANCE (gestión de frecuencias, recuperación, Safe Mode, térmico) | Existe | `stoned` | F1 |
| Soporte 40 CU: configuración de referencia (D-16) | Existe | `stone_cu40.py`, `build_files/cu40` | F0 (módulo `amdgpu` con la opción, guardia de arranque y `stone-cu40 status`, para conservar los 40 CU actuales); F1 (detección en `stoned`); F3 (calibración y gestión desde STONE) |
| STONE HOME + integración Steam (biblioteca, JUGAR, instalar) | Existe | `stone_home/` | F2 |
| Performance Center + STONE CALIBRATION | Existe | `calibration.py`, UI | F3 |
| STONE DISPLAY | Existe | `stone_display/` | F4 |
| STONE GRAPHICS | Parcial | `stone_games/graphics.py` | F4 |
| STONE OPTIMIZED + STONE GAME PROFILE | Existe (sin mediciones) | `stone_games/` | F5 |
| STONE CONNECT (Bluetooth y mandos) | **Nuevo** (hoy lo hace Steam) | — | F6 |
| STONE DOWNLOADS (instalar y desinstalar) | Parcial | Asistente de instalación de Steam, `stone_games/install.py`, Flatpak de emuladores | F7 |
| STONE EMULATION | Parcial | `stone_home/emulators.py` (catálogo Flathub) | F8 |
| STONE DESKTOP | **Nuevo** (Bazzite trae modo escritorio KDE) | — | F9 |
| Otros módulos de la arquitectura STONE MACHINE | Sin especificar | — | Tras P-14 |

El orden de F6–F9 es una recomendación. **La primera imagen de validación** sería F0 + F1, sin cambiar el comportamiento de la placa respecto a rc16. Su objetivo: cerrar P-01, P-03 y las pruebas 0–2, 14 y 16.

Cada fase termina con una puerta: todas sus pruebas de software pasan en CI y todas sus pruebas de placa están ejecutadas y registradas.

---

## 6. Pruebas: qué se hace por software y qué exige la placa

Leyenda:
- **S**: software. Se hace en CI o en el contenedor, sin placa.
- **S+V**: se hace parcialmente en una máquina virtual o en otro PC, pero la validación definitiva sigue siendo en la placa.
- **P**: la placa física es obligatoria.

### 6.1 Pruebas automáticas existentes (todas S)

| Suite | Cubre |
| --- | --- |
| `scripts/validate.sh` | Estructura, shell, Python, XML/TOML/JSON, unidades, polkit, sin simulación en producción, workflows |
| `tests/run_tests.py` (88) | `stoned` contra regulador D-Bus y sysfs falsos |
| `tests/test_home.py` (26), `test_server.py` | Host, biblioteca, accesos directos, puente, transporte |
| `tests/test_display.py` (24) | EDID, conectores, política de pantalla, presupuesto del enlace |
| `tests/test_games.py` (22) | Perfiles de juego, rutas gráficas, métricas, puntuación |
| `tests/test_cu40.py`, `test_cu40_patch.py` | Opt-in de 40 CU, guardia, anclas del parche |
| `tests/chromium_selftest.py`, `webkit_selftest.py`, `e2e_home.py`, ESLint | Interfaz real en Xvfb (sin GPU real) |
| Build de imagen + `bootc container lint` + ISO | Workflows de GitHub |
| Prueba de contrato del regulador (nueva, R-03) | Interfaz D-Bus de cada versión del paquete |

### 6.2 Matriz de `HARDWARE_VALIDATION.md`

| Prueba | Tipo | Motivo |
| --- | --- | --- |
| 0 Inventario (ID PCI, D-Bus del regulador, sensores, permisos) | P | Sólo la placa tiene el hardware real |
| 1 BOOT ×5 | P | — |
| 2 IDLE | P | — |
| 3 Carga de prueba (vkmark headless) | P | GPU real |
| 4 GAME y detección de Steam | S+V | Formato del `reaper` se puede ver en otro PC con Steam; validación en placa |
| 5 PROFILE SWITCH | P | Regulador real |
| 6 OVERCLOCK | P | — |
| 7 THERMAL | P | — |
| 8 LONG SESSION | P | — |
| 9 REBOOT | P | — |
| 10 CRASH RECOVERY | S+V | Lógica cubierta en software; cuelgue real sólo en placa |
| 11 POWER LOSS | P | — |
| 12 SAFE MODE | S+V | Lógica en software; arranque con `stone.safe=1` en placa |
| 13 FAN READ | P | — |
| 14 SUSPEND | P | — |
| 15 HW WATCHDOG | P | — |
| 16 Instalador y primer arranque | S+V | ISO e instalación en VM; Game Mode y vídeo en placa |
| 17 STONE HOME en Game Mode | P | Gamescope + mando reales |
| 18 Perfil por juego | P | — |
| 19 Apagar / reiniciar | S+V | logind en VM; marca de apagado limpio en placa |
| 20 Apagar tras inactividad | S+V | — |
| 21 Actualización atómica | S+V | `bootc switch` en VM; en placa con la imagen real |
| 22 Rollback | S+V | Ídem |
| 23 Autoarranque que falla | P | Game Mode real |
| 24 Sin BC-250 | S+V | Otro PC o VM: todo debe quedar «no disponible» |
| 25 40 CU | P | — |
| 26 Home con GPU a 4K | P | Incluye P-10 |
| 27 STONE DISPLAY 4K | P | Pantalla y adaptador reales (P-05, P-06) |
| 28 PERFORMANCE 2.0 (calibración) | P | Incluye P-15 |
| 29 STONE OPTIMIZED (Cyberpunk) | P | — |

Ninguna fila de esta tabla se marca como validada sin haberla ejecutado en la BC-250 (D-08). Las observaciones previas (H-07, H-08) se registran como `OBSERVED ON BOARD`.

---

## 7. Próximos pasos (sin implementar todavía)

1. ~~El propietario aprueba o corrige las recomendaciones R-01 a R-12~~. Hecho: aprobadas el 2026-11-06.
2. Copia de seguridad (R-12). Ver `04_BACKUPS/MANIFIESTO.md`.
2b. Quedan abiertas tres decisiones del propietario: el método para llegar a 8 núcleos (P-04), el documento de arquitectura STONE MACHINE (P-14) y la confirmación del orden de F6–F9.
3. Se aporta el documento de arquitectura STONE MACHINE (P-14).
4. Sesión de inventario en placa, sólo lectura y sin riesgo: P-01, P-03, P-05 a P-08, P-11.
5. Con esos datos, empieza F0.

## Registro de cambios

| Versión | Fecha | Cambio |
| --- | --- | --- |
| 1 | 2026-11-06 | Primera versión: respuestas del propietario a las preguntas del inventario, hechos documentados, auditoría de motores y clasificación de pruebas |
| 2 | 2026-11-06 | R-01 a R-12 aprobadas por el propietario; copia de seguridad R-12 realizada |
| 20 | 2026-11-14 | D-38: revisión de todo lo que STONE le pide a Steam contra su código (`dev/steam/steam_api.py`, 144 llamadas comprobadas); biblioteca con el estado de esta consola; cerrar juego; pausar y reanudar descargas; resolución leída de los detalles del juego. Versión 3.1.0-rc5 |
| 19 | 2026-11-13 | D-37: instalación y desinstalación con las llamadas exactas de la interfaz de Steam; contrato de licencia aceptado desde STONE; barra de descarga en vivo; fondos `hero2x`, suavizado y sombra según el arte; carátulas sin instalar opacas. Versión 3.1.0-rc4 |
| 18 | 2026-11-12 | D-36: instalación y desinstalación comprobadas con los archivos de Steam y preguntas de Steam devueltas a STONE; Steam en espera durante el primer encendido y guardia contra ventanas de Steam no pedidas; comprobación diaria y Buscar actualizaciones. Versión 3.1.0-rc3 |
| 17 | 2026-11-12 | D-35: diseño Cristal de STONE Home (materiales de la consola, Liquid Glass, tipografía del logotipo, color del juego, carátulas de apartados, efectos ligeros), como actualización en línea. Versión 3.1.0-rc1 |
| 16 | 2026-11-11 | D-34: vuelve STONE Home; Steam al frente para iniciar sesión y comprar, con plan B; biblioteca vigilada y guardada entre arranques; tienda, código QR e instalación automática; emuladores de Switch y actualizador; arranque reordenado. Versión 3.0.0-rc1 |
| 15 | 2026-11-08 | D-32, corrección: chunkah conservaba `ostree.final-diffid` y `ostree.commit` de la imagen base; apuntaban a una capa inexistente y la ISO de 1.0.0-rc4 falló al instalar en la placa. Se quitan antes de trocear y cada compilación importa la imagen con ostree antes de publicarla. Versión 1.0.0-rc5 |
| 14 | 2026-11-08 | D-33: auditoría de experiencia de consola y 1.0.0-rc4 (configuración inicial, pantalla de carga, preguntas de Steam en STONE, capturas, sin terminal) |
| 13 | 2026-11-08 | D-32: troceado de la imagen con chunkah, para que las actualizaciones descarguen solo lo que cambia (rc1 → rc2 pesó ~7 GB). Versión 1.0.0-rc3 |
| 12 | 2026-11-07 | PR #6 fusionado; imagen F2 construida a partir de `a39ea65`. Fallo en la publicación: cada `podman push` volvía a generar el manifiesto, así que `dev` (`sha256:2156488e…`) y `dev-a39ea65` (`sha256:699a5d91…`, la firmada) tenían digests distintos y `dev` quedó sin firma. Lo mismo pasó en F1. Corregido: una sola subida, las otras etiquetas se copian por digest y el flujo comprueba que todas coinciden con el digest firmado. La imagen F2 no se instala hasta que se reconstruya con esta corrección |
| 11 | 2026-11-07 | Código de F2 completo en el PR #6, con CI en verde (run 21). Incluye: sesión STONE con supervisor; foco de Gamescope; botón guía como plan B de V-13; FIRST RUN; métricas de arranque; pantalla de actualizaciones para la sesión STONE; WebKit, Chromium y e2e en el CI. Abiertos V-18 y V-19. Todo en CODE TESTED: falta la placa (ver `docs/fases/F2_PLAN.md` §5) |
| 10 | 2026-11-07 | F1 fusionado en `main` (PR #5; CI en el contenedor: validación sin omisiones y suite de `stoned` 91/91); imagen F1 publicada. ISO de F0 construida (SHA-256 `f9d22f5b…cf88`). F2 iniciado: plan con la investigación de la sesión; D-27 |
| 9 | 2026-11-07 | F0 fusionado en `main` (PR #1, CI con 0 omisiones y 38 pruebas). F1 iniciado bajo D-20: `stoned` portado y configuración de referencia en `stoned` (ver `docs/fases/F1_PLAN.md`) |
| 8 | 2026-11-07 | D-26: firma sin clave; el flujo del instalador usa por defecto la etiqueta `dev` |
| 7 | 2026-11-07 | Prompt maestro revisado e integrado: D-20 (autonomía total), D-21 (sesión propia), D-22 (generación de fotogramas con condiciones), D-23 (vocabulario de estados), D-24 (recomendaciones aplicadas), D-25 (objetivo de producto). CI de F0 en verde en el Pull Request #1 |
| 6 | 2026-11-06 | Plan de F0 aprobado con F0-A (imagen `stone-os-rebuild`, canal `dev`), F0-B (F0 no se instala para uso diario; la primera imagen en la placa será F1), F0-C (firma obligatoria; el propietario crea `SIGNING_SECRET`) y F0-D (GitHub Actions) |
| 5 | 2026-11-06 | D-16 a D-19: configuración definitiva de 8 núcleos y 40 CU, desbloqueo fuera de alcance, sin cifras inventadas, F0 sin esperar a la consola; P-04 cerrado; R-04 reescrita sin límites de diseño; regulador v0.4.14 sigue en el COPR (build 11067195) |
| 4 | 2026-11-06 | Procedimiento de diagnóstico aprobado (D-14) |
| 3 | 2026-11-06 | D-12 a D-15 (8 núcleos, arquitectura antes de F0, diagnóstico sólo lectura, puerta de F0); P-14 resuelto documentalmente; nuevos P-17 y P-18 |
