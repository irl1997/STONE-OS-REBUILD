# Cómo habla STONE con Steam

**Regla:** STONE no deduce cómo funciona Steam. Lee el código de la propia interfaz de Steam, que Valve publica con cada versión del cliente, y hace exactamente lo que esa interfaz hace.

Esta regla nació de dos fallos vistos en la consola con 3.1.0-rc3 (12 y 13-11-2026):

- Al instalar, STONE pasaba un argumento menos que Steam (el equipo donde instalar) y buscaba el juego en un campo que la interfaz de Steam no usa. Resultado: «Steam no respondió».
- Al abrir un juego, las preguntas de Steam (opción de inicio, contrato de licencia, partidas de la nube) quedaban en ventanas ocultas. Resultado: Batman: Arkham City se quedaba en «SIGUE CARGANDO».

Las dos cosas estaban en el código de Steam desde el principio.

## De dónde sale el código de Steam

Valve publica los archivos de actualización del cliente en un servidor público, y todo cliente de Steam los descarga:

| Qué | Dónde |
| --- | --- |
| Manifiesto (versión, archivos, sumas SHA-256) | `https://client-update.steamstatic.com/steam_client_ubuntu12` |
| Interfaz de Steam (una aplicación web en JavaScript) | el archivo del paquete `steamui_websrc_all` que nombra el manifiesto |

Dentro del paquete, `steamui/sp.js` y `steamui/library.js` contienen lo que importa: cada llamada `SteamClient.<Área>.<Función>(…)`, los avisos a los que se suscribe la interfaz, los almacenes que guarda en `window` (`appStore`, `downloadsStore`, `collectionStore`…) y las enumeraciones con sus números (`k_EInstallMgrState…`, `k_EAppUpdateProgress…`). Los textos en español de Steam están en `steamui/localization/steamui_spanish-json.js`.

El código descargado **solo se lee como texto; nunca se ejecuta**. Se guarda fuera del repositorio.

## La herramienta

`dev/steam/steam_api.py`:

```bash
python3 dev/steam/steam_api.py fetch     # descarga la interfaz actual y comprueba su SHA-256
python3 dev/steam/steam_api.py report    # escribe docs/steam/STEAM_API.md y docs/steam/steam_api.json
python3 dev/steam/steam_api.py check     # compara cada llamada de STONE con el código de Steam
python3 dev/steam/steam_api.py check --snapshot    # lo mismo sin internet, contra docs/steam/steam_api.json
```

`check` genera todo el JavaScript que STONE ejecuta en la página de Steam (`stone_home/steamcef.py`), resuelve los alias (`const I=SteamClient.Installs` … `I.OpenInstallWizard`) y comprueba tres cosas:

1. Que la interfaz de Steam hace cada llamada.
2. Que la hace con el mismo número de argumentos.
3. Que cada campo que STONE lee (`display_name`, `strTaskName`, `update_appid`…) existe en el código de Steam.

`docs/steam/steam_api.json` es la foto que guarda el repositorio: solo nombres, número de argumentos, unos pocos ejemplos de argumentos, almacenes y enumeraciones. No contiene código de Steam. `tests/test_steam_api.py` corre la comparación contra esa foto en cada compilación: una llamada nueva de STONE que Steam no haga hace fallar las pruebas.

`docs/steam/STEAM_API.md` es la referencia legible: todas las funciones de `SteamClient` que usa la interfaz de Steam, cuántas veces y con qué argumentos.

## Cómo se trabaja un arreglo que toca Steam

1. `fetch`: la versión actual del cliente (la API cambia con Steam).
2. Buscar en `sp.js` cómo lo hace la interfaz de Steam: la llamada, sus argumentos, los avisos que escucha y qué responde. Por ejemplo, para instalar, buscar `Installs.OpenInstallWizard` y leer `OnShowInstallWizard`.
3. Hacer lo mismo en `steamcef.py`, con un comentario que diga de dónde salió.
4. Probarlo en node contra un Steam simulado que se comporte como dice ese código (`tests/test_steam_install.py`, `tests/test_steam_launch.py`).
5. `report` para actualizar la foto y la referencia; `check` sin errores.
6. Confirmarlo en la placa: el código de Steam dice qué llamar, pero solo la consola dice que funciona.

## Lo que STONE le pide a Steam hoy (cliente 1792618285)

| Para qué | Cómo lo hace la interfaz de Steam (y STONE) |
| --- | --- |
| Instalar | `Installs.OpenInstallWizard([appid], "0")` («0» = este equipo); los pasos llegan por `Installs.RegisterForShowInstallWizard(cb)` con `eInstallState` y `rgApps`; en el paso 7 (configuración), `SetInstallFolder(i)` y `ContinueInstall()`; en el 8, el contrato. La prueba de que empezó es el `appmanifest` del juego en disco. |
| Contrato de licencia | `Apps.LoadEula(appid)` da `[{id, version, url}]`; aceptar es `Apps.MarkEulaAccepted(appid, id, version)` y seguir. STONE muestra la dirección (QR) y solo pasa la respuesta de la persona. |
| Desinstalar | `Installs.OpenUninstallWizard([appid], "0", true)`. |
| Descargas en vivo | `window.downloadsStore`: `LocalDownloadOverview` (o `m_DownloadOverview.get("0")`) con `update_appid`, `update_state` (`Downloading`, `Preallocating`, `Unpacking`, `None`), `progress[k_EAppUpdateProgress_*]` (bytes por etapa), `update_network_bytes_per_second`, `overall_estimated_time_remaining_sec`; la cola en `m_DownloadItems.get("0")`. |
| Abrir un juego | `Apps.RunGame(gameid, "", -1, origen)`; los pasos por `Apps.RegisterForGameAction{Start,TaskChange,UserRequest,ShowError,End}` y `Apps.GetActiveGameActions()`; las respuestas con `Apps.ContinueGameAction(id, respuesta)` o `Apps.CancelGameAction(id)`. Respuestas de Steam: `ShowEula`, índice de opción de inicio, `KeepLocal`/`KeepRemote`/`IgnoreCloud`/`IgnorePendingCloudSessions`, `IgnoreInstallError`, `KickOtherSession`, `SkipShaders`. Errores: `AppError_N`, con los textos `Steam_AppUpdateError_N`. |
| Juegos de la cuenta | `window.appStore` (`m_mapApps`, `allApps`) y `window.collectionStore` (`allGamesCollection.allApps`): `appid`, `display_name`, `app_type`, `minutes_playtime_forever`, `rt_last_time_played`, `size_on_disk`. Instalado **en esta consola**: `local_per_client_data` (la entrada de `per_client_data` con `clientid` «0»); el `installed` de Steam es el del equipo de la cuenta que más tiene, que puede ser otro PC. Solo lo que la cuenta posee (`BIsOwned()`). |
| Cerrar un juego | `Apps.TerminateApp(gameid, false)`, tras la pregunta de Steam «¿Salir del juego?» / «Los datos no guardados podrían perderse.» |
| Pausar y reanudar descargas | Pausar: `Downloads.EnableAllDownloads(false, "0")` (Steam pausa sus descargas, no un juego). Reanudar o descargar ya uno en cola: `Downloads.ResumeAppUpdate(appid, "0")`, y antes `EnableAllDownloads(true, "0")` si estaban en pausa. |
| Resolución por juego | Se lee de `Apps.RegisterForAppDetails(appid, cb)` → `strResolutionOverride` (si falta, «Default») y se cambia con `Apps.SetAppResolutionOverride(appid, valor)`. `GetResolutionOverrideForApp` solo de respaldo. |
| Quién inició sesión | `window.App.m_CurrentUser.strSteamID`. |
| Abrir los ajustes o las descargas de Steam | `window.SteamUIStore.GetFocusedWindowInstance()` (o `WindowStore.GamepadUIMainWindowInstance`) → `.Navigator`; `MenuStore.OpenMainMenu()` para traer la interfaz de Steam sobre STONE; `Navigator.Settings("System")`, que en el modo consola va a la ruta `Settings[sección]` (las secciones de STONE son claves de esa tabla de rutas, y `check` lo comprueba), o `Navigator.Downloads()`; después, `MenuStore.CloseSideMenus()`. |
| Accesos directos | `Apps.AddShortcut(nombre, exe, carpeta, opciones)` y `Apps.SetShortcutName(id, nombre)`. |
| Steam Play para juegos de Windows | `CompatToolMapping` «0» en `config/config.vdf` (lo que Steam escribe al activar «Steam Play para todos los títulos»), solo si no existe y con Steam cerrado. |

Hay dos funciones que STONE usa y la interfaz de Steam no. Las dos se usan solo si existen y como respaldo:

- `Installs.GetInstallManagerInfo`: encuentra un asistente de instalación que quedó abierto antes de que STONE pidiera otro. Los pasos los da el aviso, como en Steam.
- `Apps.GetResolutionOverrideForApp`: lee la resolución de un juego cuyos detalles no llegan.

`check` también revisa el código de pantalla (`stone_display/steam.py`) y de gráficos (`stone_games/graphics.py`). Los ajustes de Steam (`steamsettings.py`) se descubren en cada versión, leyendo los nombres que ofrece `SteamClient`, y no se fijan de antemano.
