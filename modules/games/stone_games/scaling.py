"""STONE SCALING (3.1.0-rc15): upscaling and frame generation in one simple choice per game.

Until rc14 a game's GRÁFICOS had four loose rows for this (Imagen, Ajuste de FSR, Fotogramas, Instalar
FSR): OptiScaler had to be installed by hand before it could be chosen, and frame generation only
worked if the person had also picked OptiScaler as the image. The owner (22-11-2026): "una manera fácil
e intuitiva" and "STONE OS tiene que asegurar que estas herramientas funcionen".

  UPSCALING          Automático · Nativo · FSR del juego · FSR 3.1 (OptiScaler) · HelixSR (if the person
                     installed it), with a quality (Calidad / Equilibrado / Rendimiento / Ultra rendimiento).
  FRAME GENERATION   Desactivada · FSR 3 (OptiScaler's own frame generation, framegen.py).

Each choice says in one line what it does and its state:
  ready      it can be used now
  manual     HelixSR: the person installs it with HelixSR Desktop (its setup downloads NVIDIA's and AMD's
             files after the person accepts their licenses; STONE never accepts a license for anyone),
             and STONE then switches it per launch like OptiScaler
  install    STONE downloads OptiScaler from its author's GitHub (SHA-256 checked, install.fetch) and
             installs it in the game when it is chosen: nothing to do by hand
  blocked    it cannot work in this game, and why (anti-cheat, online game, no DLSS/FSR 2/3/XeSS to
             replace, another upscaler already in the folder...)

WHAT STONE GUARANTEES (and what it cannot):
  - After every launch with OptiScaler, STONE looks inside the game's processes and checks that the
    file it installed (winmm.dll in the game's folder) is really loaded (optimizer.injected_probe).
    The result is kept per game: "funcionó" with the date, or "no se activó".
  - If it was not loaded, or the game closed right after starting, the next launch falls back on its
    own (optimizer.FALLBACK: OptiScaler -> FSR del juego -> Nativo) and STONE says so on screen.
  - Never in games with anti-cheat or online-only (an injected DLL can get an account banned).
  - Never in 32-bit games (rc16, detect.exe_bits): OptiScaler and HelixSR are 64-bit DLLs and are never
    loaded there (Batman Arkham City on the board, 22-11-2026).
  - It cannot make a tool work in a game that does not support it: that is why such a choice is shown
    as blocked with its reason instead of being offered.
Frame generation runs inside OptiScaler: it is verified as far as OptiScaler being loaded with
FGType=optifg in its ini; whether the game then gives it what it needs is up to the game, and the
person is told the FPS counter includes generated frames.
"""

import json
import os
import time

from . import framegen, graphics, install, schema

UPSCALERS = (
    ("auto", "Automático", "STONE elige lo mejor que midió para esta consola"),
    ("native", "Nativo", "Sin reescalar: la imagen más nítida, con menos FPS"),
    ("game_upscaler", "FSR del juego", "El FSR o XeSS que trae el juego; se activa en su menú de gráficos"),
    ("optiscaler", "FSR 3.1 (OptiScaler)", "Pone FSR 3.1 en juegos que traen DLSS, FSR 2 o XeSS: más FPS con buena imagen"),
    ("helixsr", "HelixSR", "FSR 4 y DLSS como sombreadores normales, hecho y probado en la BC-250"),
)
PRESETS = (("quality", "Calidad"), ("balanced", "Equilibrado"), ("performance", "Rendimiento"),
           ("ultra_performance", "Ultra rendimiento"))
FRAMEGEN = (
    ("off", "Desactivada", "Solo los fotogramas que dibuja el juego"),
    ("fsr3", "FSR 3 (OptiScaler)", "Genera un fotograma entre cada dos: más fluidez; el contador de FPS cuenta también los generados"),
)


def human(reason):
    """An availability reason (graphics.availability, install_plan) in words for the screen."""
    r = (reason or "").lower()
    if not r:
        return None
    if "32-bit" in r:
        return "Juego de 32 bits: FSR 3.1 (OptiScaler) y HelixSR solo funcionan en juegos de 64 bits"
    if "anti-cheat" in r:
        return "No se usa en juegos con anti-cheat (una DLL inyectada puede costar la cuenta)"
    if "online" in r:
        return "No se usa en juegos en línea"
    if "no dlss/fsr/xess" in r or "no upscaler of the game" in r or "no_upscaler" in r:
        return "El juego no trae DLSS, FSR 2/3 ni XeSS: no hay nada que reemplazar"
    if "launch options" in r:
        return "Tus opciones de lanzamiento de Steam ya cargan otra DLL (WINEDLLOVERRIDES)"
    if "installed instead" in r or "already installed" in r:
        return "Ya hay otro reescalador instalado en la carpeta del juego"
    if "always loaded" in r:
        return "Instalado como dxgi.dll: siempre se carga; reinstálalo como winmm.dll"
    if "not installed" in r and "game" in r:
        return "El juego no está instalado"
    if "executable" in r:
        return "No se encontró el ejecutable del juego"
    if "same name" in r:
        return "En la carpeta del juego ya hay archivos con los mismos nombres"
    return reason


# ---- what STONE saw in the last launches ------------------------------------------------------------
def _verify_path():
    return os.path.join(graphics.state_dir(), "scaling-verify.json")


def _verify_all():
    try:
        with open(_verify_path()) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def verified(appid):
    """{tool: {"ok": bool, "at": epoch, "why": str|None}} for one game."""
    v = _verify_all().get(str(appid))
    return v if isinstance(v, dict) else {}


def record(appid, tool, ok, why=None, now=None):
    d = _verify_all()
    g = d.setdefault(str(appid), {})
    g[tool] = {"ok": bool(ok), "at": int(now or time.time()), "why": why}
    os.makedirs(os.path.dirname(_verify_path()), exist_ok=True)
    tmp = _verify_path() + ".tmp"
    with open(tmp, "w") as f:
        json.dump(d, f)
    os.replace(tmp, _verify_path())
    return g[tool]


def _check_text(v):
    if not v:
        return None
    day = time.strftime("%d-%m", time.localtime(v.get("at") or 0))
    return f"Funcionó en la última partida ({day})" if v.get("ok") else f"No se activó en la última partida ({day}): {v.get('why') or 'STONE volvió a una opción segura'}"


# ---- the choices --------------------------------------------------------------------------------------
def optiscaler_state(appid, facts, game, avail):
    """("ready" | "install" | "blocked", reason) for FSR 3.1 through OptiScaler in this game."""
    a = avail.get("optiscaler") or {}
    if a.get("available"):
        return "ready", None
    if facts.get("exe_bits") == 32:
        return "blocked", human("32-bit")
    if install.installed_by_stone(appid):                # installed by STONE but not usable now
        return "blocked", human(a.get("reason"))
    why = graphics.safe_reason(game, facts)
    if why:
        return "blocked", human(why)
    if not facts.get("installed") or not facts.get("install_dir"):
        return "blocked", "El juego no está instalado"
    if facts.get("exe_bits") == 32:
        return "blocked", human("32-bit")
    if (facts.get("injected") or {}).get("kind"):
        return "blocked", human("installed instead")
    if not (game.get("native_upscalers") or install.game_upscalers(facts["install_dir"])):
        return "blocked", human("no_upscaler")
    return "install", "Se descarga del autor y se instala al elegirla (un minuto)"


HELIXSR_HOW = ("HelixSR se instala con HelixSR Desktop, la app de su autor (github.com/lonewolf0622/HelixSR): la primera vez descarga archivos de NVIDIA y AMD y te pide aceptar sus licencias, por eso lo instalas tú, en el Modo escritorio, eligiendo este juego y «HelixSR Scaler». Si queda como dxgi.dll se carga en cada partida; para que STONE pueda activarlo y quitarlo cuando elijas, en la carpeta del juego cambia el nombre de dxgi.dll a winmm.dll (la guía de HelixSR lo permite). Al volver, HelixSR aparece aquí listo para elegir.")


def helixsr_state(facts, game):
    """HelixSR when it is not installed in the game: the person installs it (its setup asks to accept NVIDIA's
    and AMD's licenses, which STONE never does for anyone), unless it could never work here."""
    if facts.get("exe_bits") == 32:
        return "blocked", human("32-bit")
    why = graphics.safe_reason(game, facts)
    if why:
        return "blocked", human(why)
    if (facts.get("injected") or {}).get("kind") == "optiscaler":
        return "manual", "Instálalo tú con HelixSR Desktop (reemplaza el OptiScaler de este juego). Elige para ver cómo"
    return "manual", "Lo instalas tú con HelixSR Desktop (pide aceptar licencias de NVIDIA y AMD). Elige para ver cómo"


def options(appid, img, facts, game, avail, fg):
    """Everything the GRÁFICOS pickers show. img: Engine.image_options; fg: framegen.status."""
    seen = verified(appid)
    by_key = {c["key"]: c for c in img["choices"]}
    ups = []
    for key, label, desc in UPSCALERS:
        if key == "optiscaler":
            state, why = optiscaler_state(appid, facts, game, avail)
        elif key == "auto":
            state, why = "ready", None
        else:
            c = by_key.get(key)
            if c is None and key == "helixsr":
                state, why = helixsr_state(facts, game)
            elif c is None:
                continue
            else:
                state, why = ("ready", None) if c["available"] else ("blocked", human(c.get("reason")))
        sel = (img["mode"] != "custom") if key == "auto" else (img["mode"] == "custom" and img["path"] == key)
        ups.append({"key": key, "label": label, "description": desc, "state": state, "reason": why, "selected": sel,
                    "check": _check_text(seen.get(key)), "check_ok": (seen.get(key) or {}).get("ok")})
    cur = next((u for u in ups if u["selected"]), ups[0])
    fg_on = bool(fg.get("on"))
    o = next(u for u in ups if u["key"] == "optiscaler")
    fgs = []
    for key, label, desc in FRAMEGEN:
        if key == "off":
            fgs.append({"key": key, "label": label, "description": desc, "state": "ready", "reason": None, "selected": not fg_on})
            continue
        blocked = framegen.blocked(facts, game)
        state, why = ("blocked", blocked) if blocked else (o["state"], o["reason"])
        if state == "ready" and cur["key"] != "optiscaler":
            why = "Al elegirla, el reescalado pasa a FSR 3.1 (OptiScaler), que la hace funcionar"
        fgs.append({"key": key, "label": label, "description": desc, "state": state, "reason": why, "selected": fg_on,
                    "check": _check_text(seen.get("framegen")), "check_ok": (seen.get("framegen") or {}).get("ok")})
    return {"upscaler": cur["key"], "upscalers": ups, "helixsr_how": HELIXSR_HOW,
            "preset": img.get("preset"), "presets": [{"key": k, "label": lbl} for k, lbl in PRESETS],
            "preset_applies": cur["key"] not in ("auto", "native"),
            "framegen": "fsr3" if fg_on else "off", "framegens": fgs,
            "summary": summary(cur, img.get("preset"), fg_on)}


def summary(cur, preset, fg_on):
    p = dict(PRESETS).get(preset) if cur["key"] not in ("auto", "native") else None
    return " · ".join(x for x in (cur["label"], p, "fotogramas generados" if fg_on else None) if x)


def ensure_optiscaler(appid, facts, game, log=print):
    """OptiScaler in this game, downloaded and installed by STONE if needed. Raises ProfileError with
    words for the screen when it cannot be done."""
    if install.installed_by_stone(appid):
        return False
    plan = install.install_plan(appid, facts, game)
    if plan.get("needs_download"):
        try:
            install.fetch("optiscaler", log=log)
        except install.InstallError as e:
            raise schema.ProfileError(f"No se pudo descargar OptiScaler: {e}") from e
        except OSError as e:
            raise schema.ProfileError("No se pudo descargar OptiScaler: ¿hay conexión a internet?") from e
        plan = install.install_plan(appid, facts, game)
    if not plan.get("ok"):
        raise schema.ProfileError(human(plan.get("error")) or "No se pudo preparar OptiScaler")
    if plan.get("no_upscaler") and not game.get("native_upscalers"):     # nothing for OptiScaler to replace
        raise schema.ProfileError(human("no_upscaler"))
    r = install.install_optiscaler(appid, facts, game)
    if not r.get("ok"):
        raise schema.ProfileError(human(r.get("error")) or "No se pudo instalar OptiScaler")
    log(f"[stone] scaling: OptiScaler {r.get('installed')} installed in {appid} ({r.get('folder')})")
    return True
