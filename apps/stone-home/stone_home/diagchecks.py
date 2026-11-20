"""What works and what does not, function by function, for the diagnostic report (3.1.0-rc8).

The first report from the console (14-11-2026) had every log in it and still did not say what the
person saw: the image looks ("filtros") doing nothing, and the home screen's colours washing out a few
seconds after the start. Logs say what a program did; they do not say whether a function a person uses
works. Each check here answers that for one function, from what STONE recorded (events.py), the
journal, Steam's own settings and the live state:

  FUNCIONA   there is evidence that it worked (the last time it was used)
  FALLA      there is evidence that it did not, and the reason found
  ATENCIÓN   it works, but something found here explains a problem a person would see
  SIN DATOS  it was not used since the start, or nothing can be read: how to get the data is said

The person can also say what they saw (the "¿Qué no funciona?" list before the report): each symptom
is tied to the checks that can explain it, and the summary puts those first.

Read-only, like the rest of the report: nothing is changed, nothing personal is kept (diagreport.redact
runs over everything after this).
"""

import json
import os
import re
import time

OK, FAIL, WARN, NODATA = "ok", "fail", "warn", "nodata"
LABEL = {OK: "FUNCIONA", FAIL: "FALLA", WARN: "ATENCIÓN", NODATA: "SIN DATOS"}

# what a person can tick before the report -> (Spanish text, the checks that can explain it)
SYMPTOMS = {
    "filters": ("Los filtros de imagen (Aspecto) no cambian nada", ("filters",)),
    "colors": ("Los colores se ven desvaídos o cambian solos", ("display",)),
    "game": ("Un juego no abre o se cierra solo", ("games", "filters")),
    "downloads": ("Las descargas o instalaciones no avanzan", ("steam", "network", "disk")),
    "sound": ("No hay sonido", ("sound",)),
    "controller": ("El mando no responde o no se detecta", ("controllers",)),
    "network": ("El Wi-Fi o internet fallan", ("network",)),
    "steam": ("Steam no abre, no deja volver o se queda en negro", ("steam",)),
    "emulators": ("Los emuladores o sus juegos no abren", ("emulators",)),
    "other": ("Otra cosa (explícala al enviar el informe)", ()),
}

_TS = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)")
_HDR = re.compile(r"HDR output (enabled|disabled)", re.I)
_SESSION_START = re.compile(r"gamescope version|Started .*Gamescope Session")
_JSEXC = re.compile(r"RaiseJSException: Method call failed: (\w+\.\w+)")
_HEALED_OLD = re.compile(r"'healed': 'look (\w+) turned off'")
_LAUNCH_ERR = re.compile(r"\[stone\] (?:launch (\d+):.*\berror\b.*|optimized: Steam did not start (\d+).*)")
_EMU_ERR = re.compile(r"\[stone\] emulators?:.*(error|fail|not found|no se)", re.I)
_PAD = re.compile(r"controller|gamepad|joystick|joy-con|xbox|dualsense|dualshock|wireless pad|8bitdo|pro controller", re.I)
_NOT_PAD = re.compile(r"motion sensors|touchpad|consumer control|keyboard|mouse", re.I)
LIB_DIRS = ("/usr/lib64", "/usr/lib", "/usr/lib/x86_64-linux-gnu", "/usr/lib32", "/usr/lib/i386-linux-gnu")


def _check(cid, name, status, detail, evidence=(), how=None):
    return {"id": cid, "name": name, "status": status, "label": LABEL[status], "detail": detail,
            "evidence": [str(e)[:300] for e in evidence][:12], "how": how}


def _when(line):
    m = _TS.match(line)
    if not m:
        return None
    try:
        return time.mktime(time.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S"))
    except ValueError:
        return None


def _json(path):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _game(names, appid):
    n = (names or {}).get(str(appid))
    return f"{n} ({appid})" if n else str(appid)


# ---- image looks (vkBasalt) ------------------------------------------------------------------
def layer_state(root="/", layer_jsons=None):
    """(installed, library found, evidence) for the vkBasalt layer of this image."""
    from_look = ("/usr/share/vulkan/implicit_layer.d/vkBasalt.json", "/usr/share/vulkan/implicit_layer.d/vkBasalt.x86_64.json",
                 "/etc/vulkan/implicit_layer.d/vkBasalt.json")
    ev, found, lib_ok = [], False, False
    for j in layer_jsons or from_look:
        p = os.path.join(root, j.lstrip("/"))
        if not os.path.isfile(p):
            continue
        found = True
        lib = (_json(p).get("layer") or {}).get("library_path") or ""
        # "$LIB" is the dynamic loader's own token (lib64 on Fedora for 64-bit programs): Fedora's
        # vkBasalt declares /usr/$LIB/vkbasalt/libvkbasalt.so (the console's report, 15-11-2026)
        libs = [lib.replace("$LIB", d) for d in ("lib64", "lib", "lib/x86_64-linux-gnu", "lib32")] if "$LIB" in lib else [lib]
        if lib.startswith("/"):
            ok = any(os.path.exists(os.path.join(root, x.lstrip("/"))) for x in libs)
        else:
            ok = bool(lib) and any(os.path.exists(os.path.join(root, d.lstrip("/"), lib)) for d in LIB_DIRS)
        lib_ok = lib_ok or ok
        ev.append(f"{j}: biblioteca {lib or '—'} {'encontrada' if ok else 'NO encontrada'}")
    return found, lib_ok, ev


def check_filters(ev, logs, home, prefs, names, root="/"):
    name = "Filtros de imagen (Aspecto, vkBasalt)"
    looks = _json(os.path.join(home, ".config", "stone", "looks.json"))
    installed, lib_ok, evidence = layer_state(root)
    evidence = list(evidence)
    if looks:
        evidence.append("Aspectos elegidos: " + ", ".join(f"{_game(names, a)} → {v}" for a, v in looks.items()))
    if not installed:
        return _check("filters", name, FAIL, "vkBasalt no está instalado en esta imagen: ningún aspecto puede aplicarse.", evidence)
    if not lib_ok:
        return _check("filters", name, FAIL, "La capa de vkBasalt está declarada pero su biblioteca no existe: los juegos no la cargan.", evidence)
    if prefs.get("optimized", 1) == 0:
        return _check("filters", name, FAIL, "STONE OPTIMIZED está desactivado: JUGAR lanza el juego tal cual y los aspectos no se aplican.", evidence)
    # a look turned off counts only if that game was not played with a look since (rc11: the fourth report
    # still warned about one turned off four days earlier by rc9's rule)
    last_fx = {}
    for e in ev:
        if e.get("kind") == "game_effects" and e.get("look"):
            last_fx[e.get("appid")] = e.get("t") or 0
    healed = [e for e in ev if e.get("kind") == "game_end" and e.get("healed") and (e.get("t") or 0) >= last_fx.get(e.get("appid"), 0)]
    healed_old = [m.group(1) for m in _HEALED_OLD.finditer(logs)]
    for e in healed:
        evidence.append(f"STONE apagó el aspecto {e.get('look')} de {_game(names, e.get('appid'))} tras cerrarse el juego a los {e.get('seconds')} s")
    for lk in healed_old:
        evidence.append(f"STONE apagó el aspecto {lk} sin avisar (regla de 3.1.0-rc7: juego cerrado antes de 60 s)")
    effects = [e for e in ev if e.get("kind") == "game_effects" and e.get("look")]
    prepared = [e for e in ev if e.get("kind") == "game_prepare"]
    for e in prepared[-4:]:
        evidence.append(f"JUGAR {_game(names, e.get('appid'))}: aspecto {e.get('look') or 'ninguno'}, opciones de lanzamiento "
                        f"{'aplicadas' if e.get('graphics_applied') else 'NO aplicadas: ' + str(e.get('graphics_error'))}")
    if effects:
        e = effects[-1]
        g = _game(names, e.get("appid"))
        env = e.get("env") or {}
        evidence.append(f"Dentro de {g}: {e.get('processes', 0)} procesos ({', '.join(e.get('names') or [])}); variables {env or 'ninguna'}; "
                        f"Vulkan {'sí' if e.get('vulkan_loaded') else 'no'}, vkBasalt {'cargado' if e.get('vkbasalt_loaded') else 'NO cargado'}")
        if e.get("error"):
            return _check("filters", name, NODATA, f"No se pudo mirar dentro de {g}: {e['error']}", evidence)
        if not e.get("processes"):
            return _check("filters", name, NODATA, f"No se encontraron los procesos de {g} para comprobarlo.", evidence,
                          "Juega un minuto con el aspecto puesto y haz el informe con el juego abierto (botón guía → Ajustes → Salud).")
        if env.get("ENABLE_VKBASALT") != "1":
            return _check("filters", name, FAIL, f"El aspecto no llegó a {g}: Steam lo lanzó sin la variable ENABLE_VKBASALT "
                          "(¿lanzado desde Steam en vez de JUGAR de STONE, o Steam no usó las opciones de lanzamiento?).", evidence)
        if not e.get("vulkan_loaded"):
            return _check("filters", name, FAIL, f"{g} no dibuja con Vulkan (OpenGL o 2D): vkBasalt solo actúa sobre juegos Vulkan "
                          "(los de Windows con Proton lo son casi siempre).", evidence)
        if not e.get("vkbasalt_loaded"):
            return _check("filters", name, FAIL, f"{g} recibió el aspecto pero vkBasalt no se cargó dentro del juego "
                          "(la capa no llegó al contenedor de Steam o el juego la rechazó). Mira juegos/vkbasalt-*.txt.", evidence)
        if healed or healed_old:
            return _check("filters", name, WARN, f"vkBasalt se cargó en {g}, pero STONE apagó un aspecto después: por eso parecía no funcionar.", evidence)
        return _check("filters", name, OK, f"vkBasalt cargado dentro de {g} con el aspecto {e.get('look')}.", evidence)
    if healed or healed_old:
        return _check("filters", name, FAIL, "STONE apagó aspectos tras cerrarse los juegos: por eso no se notan. Vuelve a elegirlos "
                      "(desde 3.1.0-rc8 solo se apagan tras dos cierres seguidos en los primeros 20 s, y avisa).", evidence)
    if not looks:
        return _check("filters", name, NODATA, "Ningún juego tiene un aspecto elegido ahora mismo.", evidence,
                      "En la página del juego elige «Aspecto», pulsa JUGAR, juega un minuto y haz el informe.")
    return _check("filters", name, NODATA, "Hay aspectos elegidos, pero ningún juego se ha jugado con uno desde que se registra.", evidence,
                  "Pulsa JUGAR en un juego con aspecto, juega un minuto y vuelve a hacer el informe.")


# ---- screen colours / HDR ---------------------------------------------------------------------
def hdr_timeline(journal):
    """[(seconds after the session started or None, "enabled"|"disabled", line)] of this boot."""
    lines = journal.splitlines()
    first = next((ln for ln in lines if "gamescope version" in ln), None) or next((ln for ln in lines if _SESSION_START.search(ln)), None)
    start, out = (_when(first) if first else None), []
    for ln in lines:
        m = _HDR.search(ln)
        if m:
            t = _when(ln)
            out.append((round(t - start) if t is not None and start is not None else None, m.group(1).lower(), ln.strip()[-160:]))
    return out


def check_display(journal, live):
    name = "Colores de la pantalla (HDR / SDR)"
    tl = hdr_timeline(journal)
    steam_hdr = (live.get("steam_display") or {}).get("gamescope_hdr_enabled")
    atoms = live.get("gamescope_atoms") or {}
    evidence = [f"{'a los ' + str(s) + ' s del inicio de la sesión' if s is not None else 'hora desconocida'}: HDR {st}" for s, st, _ in tl[-6:]]
    if steam_hdr is not None:
        evidence.append(f"Ajuste de Steam «Activar HDR» (gamescope_hdr_enabled): {'activado' if steam_hdr else 'desactivado'}")
    hdr_atoms = {k: v for k, v in atoms.items() if "HDR" in k or "SDR" in k or "COLOR" in k}
    if hdr_atoms:
        evidence.append("Gamescope: " + ", ".join(f"{k}={v}" for k, v in sorted(hdr_atoms.items())[:10]))
    disp = live.get("display") or {}
    if disp.get("summary"):
        evidence.append(f"Pantalla: {disp['summary']}")
    # what gamescope says NOW wins over the journal (the third report, 15-11-2026: HDR on at 8 s, off,
    # on again at 219 s in the journal, while gamescope's own feedback said SDR and Steam's switch was off)
    fb = atoms.get("GAMESCOPE_HDR_OUTPUT_FEEDBACK")
    live = bool(fb[0]) if isinstance(fb, list) and fb else None
    on = live if live is not None else (tl[-1][1] == "enabled" if tl else bool(steam_hdr))
    if not tl and steam_hdr is None and live is None:
        return _check("display", name, NODATA, "No hay registro de gamescope sobre HDR ni respuesta de Steam.", evidence,
                      "Haz el informe con la consola recién encendida, sin reiniciar la sesión.")
    if on:
        when = "" if live is not None and tl and tl[-1][1] != "enabled" else next((f" a los {s} s de empezar la sesión" for s, st, _ in tl if st == "enabled" and s is not None), "")
        return _check("display", name, WARN, f"La salida de vídeo pasó a HDR{when}, cuando Steam arrancó con «Activar HDR». La pantalla de "
                      "inicio de STONE está hecha en SDR: en una salida HDR gamescope la convierte y los colores pueden verse desvaídos. "
                      "Coincide con «los colores se deslavan al pasar unos segundos».", evidence,
                      "Para probarlo: Ajustes → Steam → «HDR en la salida de vídeo» en No, y mira si los colores dejan de cambiar.")
    return _check("display", name, OK, "La salida está en SDR ahora mismo (lo dice gamescope)" if live is not None
                  else "La salida está en SDR: la interfaz se ve con sus colores.", evidence)


# ---- games ----------------------------------------------------------------------------------------
def check_games(ev, logs, names):
    name = "Abrir juegos (JUGAR)"
    started = [e for e in ev if e.get("kind") == "game_started"]
    ends = [e for e in ev if e.get("kind") == "game_end"]
    # a launch that "never started" because the console was turned off or asleep in between is not a
    # failure: only a launch STONE saw time out (START_TIMEOUT_S, 3 min) while the console was on
    prep = {}
    not_started = []
    for e in ev:
        if e.get("kind") == "game_prepare":
            prep[e.get("appid")] = e.get("t")
        elif e.get("kind") == "game_end" and e.get("reason") == "not started":
            t0 = prep.get(e.get("appid"))
            if t0 is None or e.get("t") is None or e.get("t") - t0 < 600:
                not_started.append(e)
    # Steam retried and the game opened within two minutes: not a failure (fourth report, Arkham Knight)
    not_started = [e for e in not_started if not any(x.get("kind") == "game_started" and x.get("appid") == e.get("appid")
                                                     and x.get("t") is not None and e.get("t") is not None and 0 < x["t"] - e["t"] < 120
                                                     for x in ev)]
    early = [e for e in ends if e.get("abnormal") and e.get("reason") == "exit"]
    errs = [m.group(0) for m in _LAUNCH_ERR.finditer(logs)]
    evidence = [f"{_game(names, e.get('appid'))}: {e.get('reason')} a los {e.get('seconds')} s" for e in ends[-6:]] + errs[-4:]
    if not_started or errs:
        g = _game(names, (not_started[-1] if not_started else {}).get("appid") or "")
        return _check("games", name, FAIL, f"Steam no llegó a abrir {g or 'un juego'} después de JUGAR." if not_started
                      else "Steam devolvió un error al abrir un juego.", evidence)
    if early:
        e = early[-1]
        return _check("games", name, WARN, f"{_game(names, e.get('appid'))} se cerró a los {e.get('seconds')} s de abrirse.", evidence)
    if started:
        return _check("games", name, OK, f"{len(started)} juegos abiertos sin fallo desde que se registra.", evidence)
    return _check("games", name, NODATA, "No se ha abierto ningún juego desde STONE.", evidence, "Abre un juego con JUGAR y vuelve a hacer el informe.")


# ---- Steam's interface ---------------------------------------------------------------------------
def check_steam(live, logs, ev):
    name = "Steam (su interfaz, la tienda y volver a STONE)"
    sf = live.get("steam_functions") or {}
    exc = {}
    for m in _JSEXC.finditer(logs):
        exc[m.group(1)] = exc.get(m.group(1), 0) + 1
    fronts = [e for e in ev if e.get("kind") == "steam_front"]
    evidence = [f"Funciones de Steam que STONE usa: {sf.get('have', 0)} presentes"
                + (f", faltan {', '.join(sf['missing'])}" if sf.get("missing") else "")]
    if exc:
        evidence.append("Steam rechazó llamadas: " + ", ".join(f"{k} ×{v}" for k, v in sorted(exc.items(), key=lambda x: -x[1])[:8]))
    for e in fronts[-5:]:
        evidence.append(f"Steam delante ({e.get('page')}): {e.get('state')}")
    if not live.get("steam_reachable"):
        return _check("steam", name, FAIL, "La interfaz de Steam no respondió al hacer el informe.", evidence)
    if sf.get("missing"):
        return _check("steam", name, FAIL, f"Este Steam no tiene {len(sf['missing'])} funciones que STONE usa.", evidence)
    bad = [e for e in fronts if e.get("state") in ("navfail", "not shown")]
    if bad:
        return _check("steam", name, FAIL, f"Abrir Steam ({bad[-1].get('page')}) falló: {bad[-1].get('state')}.", evidence)
    if exc:
        return _check("steam", name, WARN, f"Steam respondió, pero rechazó {sum(exc.values())} llamadas (lista abajo).", evidence)
    return _check("steam", name, OK, "Steam responde y tiene todas las funciones que STONE usa.", evidence)


# ---- sound, controllers, network, disk, emulators -----------------------------------------------
def _elds(root):
    """[(card file, monitor_present, eld_valid, monitor_name)] from /proc/asound/card*/eld#*: what the
    display told the graphics card about its sound (HDMI/DisplayPort audio)."""
    out = []
    base = os.path.join(root, "proc", "asound")
    try:
        cards = sorted(n for n in os.listdir(base) if n.startswith("card"))
    except OSError:
        return out
    for c in cards:
        try:
            names = sorted(n for n in os.listdir(os.path.join(base, c)) if n.startswith("eld#"))
        except OSError:
            continue
        for n in names:
            try:
                with open(os.path.join(base, c, n), encoding="utf-8", errors="replace") as f:
                    text = f.read(4096)
            except OSError:
                continue
            kv = dict(re.findall(r"^(\w+)\s+(.*)$", text, re.M))
            out.append((f"{c}/{n}", kv.get("monitor_present", "?").strip(), kv.get("eld_valid", "?").strip(), kv.get("monitor_name", "").strip()))
    return out


def check_sound(run, root="/", live=None):
    """3.1.0-rc12 (board, 20-11-2026: no sound, and the report said FUNCIONA): the default output was
    PipeWire's "Dummy Output", a sink that goes nowhere, at 100 %. With no real output the check fails and
    says why: the display did not tell the console it takes sound (ELD), which comes with an identification
    of the TV without its HDMI part (the same report had lost HDR too)."""
    name = "Sonido"
    vol = run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"], 5)
    st = run(["wpctl", "status"], 5)
    sinks = re.search(r"Sinks:\n(.*?)\n\s*│?\s*\n", st, re.S)
    lines = [ln.strip(" │├└─") for ln in sinks.group(1).splitlines()] if sinks else []
    evidence = [vol.strip()[:120]] + lines[:6]
    real = [ln for ln in lines if ln and "Dummy Output" not in ln]
    elds = _elds(root)
    evidence += [f"{c}: pantalla presente {p}, datos de sonido válidos {v}{(' · ' + n) if n else ''}" for c, p, v, n in elds[:4]]
    disp = ((live or {}).get("display") or {}).get("summary")
    if disp:
        evidence.append(f"Pantalla: {disp}")
    if sinks is not None and not real and "Audio" in st:
        told = any(p == "1" and v == "1" for _c, p, v, _n in elds)
        why = ("La pantalla sí dice que acepta sonido, pero no hay salida para ella: reinicia la consola."
               if told else
               "La TV no le dijo a la consola que acepta sonido (por HDMI/DisplayPort no llegó la información de audio). "
               "Suele pasar cuando la consola arranca con la TV apagada o en otra entrada, o con el adaptador "
               "DisplayPort→HDMI mal conectado.")
        return _check("sound", name, FAIL, "No hay ninguna salida de sonido real: solo la salida vacía («Dummy Output»). " + why, evidence,
                      "Con la TV encendida y en la entrada de la consola, reinicia la consola. Si sigue sin sonido, desconecta "
                      "y vuelve a conectar el adaptador o el cable, y en la TV revisa que esa entrada HDMI tenga activada la "
                      "señal mejorada (HDMI UHD Color, Enhanced o similar).")
    m = re.search(r"Volume:\s*([\d.]+)(.*MUTED)?", vol)
    if not m:
        return _check("sound", name, FAIL if "wpctl" not in vol.lower() else NODATA, "No hay salida de sonido por defecto (PipeWire no da ninguna).", evidence)
    if m.group(2):
        return _check("sound", name, WARN, "La salida de sonido está silenciada.", evidence)
    if float(m.group(1)) == 0:
        return _check("sound", name, WARN, "El volumen está a 0.", evidence)
    return _check("sound", name, OK, f"Salida de sonido al {round(float(m.group(1)) * 100)} %.", evidence)


def check_controllers(root="/"):
    name = "Mandos"
    try:
        with open(os.path.join(root, "proc/bus/input/devices"), encoding="utf-8", errors="replace") as f:
            blocks = f.read().split("\n\n")
    except OSError:
        return _check("controllers", name, NODATA, "No se pudo leer la lista de dispositivos de entrada.")
    pads = []
    for b in blocks:
        n = re.search(r'N: Name="([^"]*)"', b)
        h = re.search(r"H: Handlers=(.*)", b)
        if n and h and (re.search(r"\bjs\d+", h.group(1)) or _PAD.search(n.group(1))) and not _NOT_PAD.search(n.group(1)):
            pads.append(n.group(1))
    if not pads:
        return _check("controllers", name, WARN, "No hay ningún mando conectado ahora mismo.", [],
                      "Conecta o enciende el mando y vuelve a hacer el informe.")
    return _check("controllers", name, OK, f"{len(pads)} mando(s) conectado(s).", pads)


def check_network(live):
    name = "Wi-Fi e internet"
    n = live.get("net") or {}
    if n.get("error"):
        return _check("network", name, NODATA, f"No se pudo leer la red: {n['error']}")
    ev = [f"{k}: {n.get(k)}" for k in ("online", "radio", "ssid", "signal", "internet") if k in n]
    if n.get("internet") == "full":
        return _check("network", name, OK, "Conectado y con internet.", ev)
    if n.get("online") or n.get("ssid"):
        return _check("network", name, FAIL, "Conectado a la red, pero sin internet.", ev)
    return _check("network", name, FAIL, "Sin conexión de red.", ev)


def check_disk(live):
    name = "Espacio en disco"
    rows = [c for c in (live.get("health") or []) if isinstance(c, (list, tuple)) and len(c) >= 3 and str(c[1]).startswith("Disco")]
    if not rows:
        return _check("disk", name, NODATA, "Sin datos del disco.")
    low = [r for r in rows if r[0] != "ok"]
    return _check("disk", name, WARN if low else OK, "Queda poco espacio." if low else "Hay espacio libre.", [f"{r[1]}: {r[2]}" for r in rows])


def check_emulators(logs, live):
    name = "Emuladores"
    errs = [m.group(0) for m in _EMU_ERR.finditer(logs)]
    emu = live.get("emulators")
    ev = ([f"Instalados: {', '.join(emu)}"] if emu else []) + errs[-6:]
    if errs:
        return _check("emulators", name, FAIL, "STONE registró errores con los emuladores.", ev)
    if not emu:
        return _check("emulators", name, NODATA, "No hay emuladores instalados o no se pudieron leer.", ev)
    return _check("emulators", name, OK, f"{len(emu)} emuladores instalados, sin errores registrados.", ev)


# ---- boot and game start times (rc12) -------------------------------------------------------------
def check_boot(home, run, blame=None):
    name = "Tiempo de encendido"
    recs = []
    try:
        with open(os.path.join(home, ".local", "state", "stone", "boot-metrics.jsonl"), encoding="utf-8") as f:
            for ln in f:
                try:
                    recs.append(json.loads(ln))
                except ValueError:
                    pass
    except OSError:
        pass
    text = blame if blame is not None else run(["systemd-analyze", "blame", "--no-pager"], 30)
    blame = [ln.strip() for ln in text.splitlines()[:6] if ln.strip()]
    if not recs:
        return _check("boot", name, NODATA, "Aún no hay arranques medidos.", blame)
    r = recs[-1]
    sd = r.get("systemd") or {}
    fw = (sd.get("firmware") or 0) + (sd.get("loader") or 0)
    ev = [f"Pantalla de STONE a los {r.get('visual_s', '—')} s del kernel; lista a los {r.get('ready_s', '—')} s"]
    if sd:
        ev.append("systemd: " + ", ".join(f"{k} {v} s" for k, v in sd.items() if v))
    ev += [f"Más lentos: {b}" for b in blame[:5]]
    total = (r.get("ready_s") or r.get("visual_s") or 0) + fw
    st = WARN if (r.get("ready_s") or 0) > 45 else OK
    return _check("boot", name, st, f"De encendido a STONE listo: unos {round(total)} s" + (" (más BIOS/firmware no medido)" if not fw else "")
                  + (". Hay servicios del sistema que retrasan el arranque (ver arranque.txt)" if st == WARN else "."), ev)


def check_launch_times(ev, names):
    name = "Tiempo para abrir un juego"
    prep = {}
    waits = []
    for e in ev:
        if e.get("kind") == "game_prepare":
            prep[e.get("appid")] = e.get("t")
        elif e.get("kind") == "game_started" and prep.get(e.get("appid")) and e.get("t"):
            waits.append((e.get("appid"), round(e["t"] - prep.pop(e.get("appid")))))
    stone = [e for e in ev if e.get("kind") == "launch_timing"]
    evidence = [f"{_game(names, a)}: {s} s de JUGAR al juego" for a, s in waits[-6:]]
    evidence += [f"STONE antes de pedirlo a Steam: {e.get('env_ms', 0) + e.get('prepare_ms', 0)} ms ({_game(names, e.get('appid'))})" for e in stone[-3:]]
    if not waits:
        return _check("launch", name, NODATA, "No se ha abierto ningún juego desde que se registra.", evidence)
    slow_stone = [e for e in stone[-5:] if e.get("env_ms", 0) + e.get("prepare_ms", 0) > 2500]
    med = sorted(s for _a, s in waits)[len(waits) // 2]
    if slow_stone:
        return _check("launch", name, WARN, f"STONE tarda más de 2,5 s en preparar el juego antes de pedírselo a Steam (mediana de JUGAR al juego: {med} s).", evidence)
    return _check("launch", name, OK, f"Mediana de JUGAR al juego: {med} s (la mayor parte es Steam y el propio juego).", evidence)


# ---- all of it --------------------------------------------------------------------------------------
def run_checks(live, journal, logs, home, run, symptoms=(), events=None, root="/", names=None, blame=None):
    """[check] (most useful first: those tied to the person's symptoms), plus the symptoms' text."""
    from . import events as E
    ev = events if events is not None else E.read()
    prefs = _json(os.path.join(home, ".config", "stone", "home.json"))
    checks = []
    for fn in (lambda: check_filters(ev, logs, home, prefs, names, root), lambda: check_display(journal, live),
               lambda: check_games(ev, logs, names), lambda: check_steam(live, logs, ev), lambda: check_sound(run, root, live),
               lambda: check_controllers(root), lambda: check_network(live), lambda: check_disk(live),
               lambda: check_emulators(logs, live), lambda: check_boot(home, run, blame), lambda: check_launch_times(ev, names)):
        try:
            checks.append(fn())
        except Exception as e:  # noqa: BLE001  (one check that breaks never stops the report)
            checks.append(_check("error", "Comprobación", NODATA, f"Una comprobación falló: {e!r}"))
    wanted = [s for s in symptoms if s in SYMPTOMS]
    first = [c for s in wanted for c in SYMPTOMS[s][1]]
    rank = {cid: i for i, cid in enumerate(dict.fromkeys(first))}
    order = {FAIL: 0, WARN: 1, NODATA: 2, OK: 3}
    checks.sort(key=lambda c: (rank.get(c["id"], 99), order[c["status"]]))
    for c in checks:
        c["symptom"] = [SYMPTOMS[s][0] for s in wanted if c["id"] in SYMPTOMS[s][1]]
    return checks


def text(checks, symptoms=()):
    """comprobaciones.txt: one block per function."""
    out = ["COMPROBACIONES DE STONE OS (qué funciona y qué no)", ""]
    if symptoms:
        out += ["LO QUE MARCASTE:"] + [f"- {SYMPTOMS[s][0]}" for s in symptoms if s in SYMPTOMS] + [""]
    for c in checks:
        out.append(f"[{c['label']}] {c['name']}" + (f"   ← {'; '.join(c['symptom'])}" if c.get("symptom") else ""))
        out.append(f"    {c['detail']}")
        out += [f"    · {e}" for e in c["evidence"]]
        if c.get("how"):
            out.append(f"    {'Qué hacer' if c['status'] in (FAIL, WARN) else 'Para tener datos'}: {c['how']}")
        out.append("")
    return "\n".join(out)
