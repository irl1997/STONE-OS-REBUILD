"""STONE IMAGE (M17): a light post-processing look per game, through the vkBasalt Vulkan layer.

  NATURAL   a touch of contrast-adaptive sharpening (AMD CAS), nothing else
  CLARITY   stronger sharpening, for games that look soft (upscaled or TAA)
  CINEMA    soft S-curve, slightly warmer and less saturated, deeper blacks; light sharpening
  VIVID     more colour and a little more contrast; light sharpening
  RETRO     warm and slightly faded, for older and emulated games; no sharpening

Each look is a vkBasalt config (CAS sharpening and/or a colour LUT written here as a .cube file)
in ~/.local/state/stone/looks/. A game launched with a look gets ENABLE_VKBASALT=1 and
VKBASALT_CONFIG_FILE=<that file> in its launch options, through the same crash-safe overrides as
the graphics paths (graphics.Overrides). Off by default for every game.

Never applied: when vkBasalt is not installed (available() says why), to games with anti-cheat or
online-only games (a Vulkan layer can be flagged), or during a measurement (numbers stay clean).
Debanding and HDR tone mapping are not offered: vkBasalt has no such effect (D-18: nothing is
claimed that the layer cannot do).
"""

import json
import os

LOOKS = ("natural", "clarity", "cinema", "vivid", "retro")
LABELS = {"natural": "NATURAL", "clarity": "CLARITY", "cinema": "CINEMA", "vivid": "VIVID", "retro": "RETRO"}
DESCRIPTIONS = {"natural": "Un poco más de nitidez, nada más",
                "clarity": "Más nitidez para juegos que se ven blandos",
                "cinema": "Contraste suave, tono cálido, negros más profundos",
                "vivid": "Más color y algo más de contraste",
                "retro": "Cálido y algo desvaído, para juegos antiguos y emuladores"}
CAS = {"natural": 0.35, "clarity": 0.75, "cinema": 0.25, "vivid": 0.35, "retro": None}
LAYER_JSONS = ("/usr/share/vulkan/implicit_layer.d/vkBasalt.json", "/usr/share/vulkan/implicit_layer.d/vkBasalt.x86_64.json",
               "/etc/vulkan/implicit_layer.d/vkBasalt.json")
LUT_SIZE = 17


def state_dir():
    return os.path.join(os.environ.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state"), "stone", "looks")


def prefs_path():
    return os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config"), "stone", "looks.json")


def available(layer_jsons=None):
    """(True, None) or (False, reason)."""
    for p in (layer_jsons or ([os.environ["STONE_VKBASALT_LAYER"]] if os.environ.get("STONE_VKBASALT_LAYER") else LAYER_JSONS)):
        if os.path.exists(p):
            return True, None
    return False, "vkBasalt no está instalado en esta imagen"


# ---- colour LUTs (pure functions: tested without a GPU) ----------------------------------------
def _clamp(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def _grade(look, r, g, b):
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    if look == "cinema":
        def s(x):                                  # gentle S-curve around mid grey
            return x + 0.18 * (x - 0.5) * (1 - abs(2 * x - 1))
        r, g, b = (lum + 0.85 * (c - lum) for c in (r, g, b))       # 15 % less saturation
        r, g, b = s(r) * 1.02, s(g), s(b) * 0.96                    # slightly warmer
        r, g, b = (max(0.0, c - 0.02) / 0.98 for c in (r, g, b))     # deeper blacks
    elif look == "vivid":
        r, g, b = (lum + 1.2 * (c - lum) for c in (r, g, b))        # 20 % more saturation
        r, g, b = (0.5 + 1.06 * (c - 0.5) for c in (r, g, b))       # a little more contrast
    elif look == "retro":
        r, g, b = (lum + 0.75 * (c - lum) for c in (r, g, b))
        r, g, b = r * 1.04 + 0.02, g * 1.0 + 0.015, b * 0.92 + 0.01  # warm, lifted blacks
    return _clamp(r), _clamp(g), _clamp(b)


def cube(look, size=LUT_SIZE):
    """The .cube LUT text of a look (Adobe/Resolve format, red changing fastest)."""
    lines = [f'TITLE "STONE {LABELS[look]}"', f"LUT_3D_SIZE {size}"]
    n = size - 1
    for bi in range(size):
        for gi in range(size):
            for ri in range(size):
                r, g, b = _grade(look, ri / n, gi / n, bi / n)
                lines.append(f"{r:.6f} {g:.6f} {b:.6f}")
    return "\n".join(lines) + "\n"


def conf(look, lut_path=None):
    """The vkBasalt config text of a look."""
    effects, lines = [], []
    if CAS[look] is not None:
        effects.append("cas")
        lines.append(f"casSharpness = {CAS[look]}")
    if lut_path:
        effects.append("lut")
        lines.append(f"lutFile = {lut_path}")
    head = [f"# STONE IMAGE · {LABELS[look]} (written by STONE; edits are replaced)", f"effects = {':'.join(effects)}",
            "reshadeTexturePath = /dev/null", "reshadeIncludePath = /dev/null", "toggleKey = Home"]
    return "\n".join(head + lines) + "\n"


def write(look, directory=None):
    """Write (or refresh) a look's files; returns the config path."""
    if look not in LOOKS:
        raise ValueError("look")
    d = directory or state_dir()
    os.makedirs(d, exist_ok=True)
    lut = None
    if look in ("cinema", "vivid", "retro"):
        lut = os.path.join(d, f"{look}.cube")
        with open(lut, "w") as f:
            f.write(cube(look))
    path = os.path.join(d, f"{look}.conf")
    with open(path, "w") as f:
        f.write(conf(look, lut))
    return path


# ---- the person's choice per game --------------------------------------------------------------
def load_prefs():
    try:
        with open(prefs_path()) as f:
            d = json.load(f)
        return {k: v for k, v in d.items() if isinstance(k, str) and k.isdigit() and v in LOOKS} if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def set_look(appid, look):
    appid = str(appid)
    if not appid.isdigit() or (look is not None and look not in LOOKS):
        raise ValueError("look")
    prefs = load_prefs()
    if look is None:
        prefs.pop(appid, None)
    else:
        prefs[appid] = look
    os.makedirs(os.path.dirname(prefs_path()), exist_ok=True)
    tmp = prefs_path() + ".tmp"
    with open(tmp, "w") as f:
        json.dump(prefs, f)
    os.replace(tmp, prefs_path())
    return {"ok": True, "look": look}


def options(appid, facts, game):
    """What Home shows on a game's page: the looks, the chosen one, and why none can be used."""
    ok, why = available()
    if ok and (facts.get("anti_cheat") or game.get("anti_cheat") or game.get("online_only")):
        ok, why = False, "No se aplica a juegos con anti-cheat ni a juegos en línea"
    return {"available": ok, "reason": why, "chosen": load_prefs().get(str(appid)),
            "looks": [{"key": k, "label": LABELS[k], "description": DESCRIPTIONS[k]} for k in LOOKS]}


def env_for_game(appid, facts, game, measuring=False):
    """The launch variables of the chosen look, or {} (none chosen, not available, or measuring)."""
    look = load_prefs().get(str(appid))
    if not look or measuring or not options(appid, facts, game)["available"]:
        return {}
    return {"ENABLE_VKBASALT": "1", "VKBASALT_CONFIG_FILE": write(look), "STONE_LOOK": look}
