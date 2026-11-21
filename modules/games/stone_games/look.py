"""STONE IMAGE (M17): a post-processing look per game, through the vkBasalt Vulkan layer.

  NATURAL    the game as it is, cleaner: light sharpening that does not sharpen grain, bands smoothed
  CLARITY    stronger detail for games that look soft (upscaled or with heavy TAA)
  CINEMA     film: S-curve, deeper blacks, teal shadows and warm highlights, a little less colour
  VIVID      more colour (above all where there was little) and more contrast
  RETRO      warm and faded, lifted blacks, for older and emulated games
  NEXT-GEN   (3.1.0-rc11) a newer-generation look: filmic highlights that roll off instead of clipping,
             deep but not crushed shadows, richer colour, edges smoothed (SMAA) and fine detail brought out
  REALISTA   (3.1.0-rc11) photographic: neutral filmic curve, over-saturated colours calmed (skin and
             nature stay), slightly cooler shadows, clean detail
  SIN GRANO  (3.1.0-rc11) for grainy or noisy pictures: denoise and debanding, colours untouched

Each look is a vkBasalt config in ~/.local/state/stone/looks/ (and a 33³ colour LUT, a .cube file, for the
ones that change colour). A game launched with a look gets ENABLE_VKBASALT=1 and VKBASALT_CONFIG_FILE in its
launch options, through the same crash-safe overrides as the graphics paths (graphics.Overrides). Off by
default for every game.

3.1.0-rc11, from the console (19-11-2026: "los filtros no se notan tanto" and "los juegos se ven un poco
granulados"): every look sharpened with CAS, which sharpens noise too (TAA and upscaler shimmer, film
grain); now DLS (vkBasalt's Denoised Luma Sharpening: dlsSharpness, dlsDenoise) with a denoise amount per
look, and deband where gradients matter. The colour changes are stronger than rc10's (mean change over the cube, rc10 -> rc11: cinema 0.035 -> 0.052,
vivid 0.029 -> 0.057, retro 0.069 -> 0.113; nextgen 0.061, realistic 0.056) and the
LUT went from 17³ to 33³ points (smoother gradients). Effects and options are vkBasalt 0.3.2.10's own
(src/basalt.cpp: cas, dls, fxaa, smaa, deband, lut; config/vkBasalt.conf), the version in the image.

Never applied: when vkBasalt is not installed (available() says why), to games with anti-cheat or
online-only games (a Vulkan layer can be flagged), or during a measurement (numbers stay clean). HDR tone
mapping is not offered: vkBasalt works on the game's SDR image (D-18: nothing claimed the layer cannot do).
"""

import json
import os

LOOKS = ("natural", "clarity", "cinema", "vivid", "retro", "nextgen", "realistic", "clean")
LABELS = {"natural": "NATURAL", "clarity": "CLARITY", "cinema": "CINEMA", "vivid": "VIVID", "retro": "RETRO",
          "nextgen": "NEXT-GEN", "realistic": "REALISTA", "clean": "SIN GRANO"}
DESCRIPTIONS = {"natural": "El juego tal cual, más limpio: nitidez sin realzar el grano",
                "clarity": "Más detalle para juegos que se ven blandos",
                "cinema": "Película: más contraste, negros profundos, sombras frías y luces cálidas",
                "vivid": "Mucho más color y más contraste",
                "retro": "Cálido y desvaído, para juegos antiguos y emuladores",
                "nextgen": "Aspecto de nueva generación: luces suaves, sombras profundas, color rico y bordes limpios",
                "realistic": "Fotográfico: colores naturales, contraste de cámara y detalle limpio",
                "clean": "Para juegos que se ven granulados: quita ruido y bandas, sin tocar el color"}
# vkBasalt effects per look, in the order they run: (name, {option: value}). DLS sharpens luma only and
# holds back where the picture is noisy (dlsDenoise); deband smooths 8-bit steps in skies and fog.
# 3.1.0-rc12 (board, 20-11-2026: "las imágenes se ven granuladas", Batman Arkham Asylum with NEXT-GEN):
# vkBasalt's deband ends with an ordered dither and samples at random angles (src/shader/deband.frag.glsl);
# running first, that pattern was then sharpened by DLS and stretched by the colour curve into visible grain.
# Deband now runs LAST, on the finished picture, so nothing after it enlarges its dither; and NEXT-GEN
# sharpens less and holds back more on noise.
FX = {
    "natural": [("dls", {"dlsSharpness": 0.35, "dlsDenoise": 0.30}), ("deband", {})],
    "clarity": [("dls", {"dlsSharpness": 0.70, "dlsDenoise": 0.25})],
    "cinema": [("dls", {"dlsSharpness": 0.25, "dlsDenoise": 0.35}), ("lut", {}), ("deband", {})],
    "vivid": [("dls", {"dlsSharpness": 0.40, "dlsDenoise": 0.25}), ("lut", {})],
    "retro": [("lut", {})],
    "nextgen": [("smaa", {"smaaEdgeDetection": "luma", "smaaThreshold": 0.05, "smaaMaxSearchSteps": 24,
                          "smaaMaxSearchStepsDiag": 8, "smaaCornerRounding": 25}),
                ("dls", {"dlsSharpness": 0.42, "dlsDenoise": 0.45}), ("lut", {}), ("deband", {})],
    "realistic": [("dls", {"dlsSharpness": 0.30, "dlsDenoise": 0.40}), ("lut", {}), ("deband", {})],
    "clean": [("dls", {"dlsSharpness": 0.10, "dlsDenoise": 1.0}),
              ("deband", {"debandAvgdiff": 3.4, "debandMaxdiff": 6.8, "debandMiddiff": 3.3, "debandRange": 16.0,
                          "debandIterations": 4})],
}
LAYER_JSONS = ("/usr/share/vulkan/implicit_layer.d/vkBasalt.json", "/usr/share/vulkan/implicit_layer.d/vkBasalt.x86_64.json",
               "/etc/vulkan/implicit_layer.d/vkBasalt.json")
LUT_SIZE = 33


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


# Colour per look (rc11). sat: saturation; vib: vibrance (more where colour is low); calm: lowers only the
# most saturated colours (photographic); curve: S-curve amount; toe/shoulder: filmic roll-off of shadows and
# highlights; black/white: output levels; warm: white balance (+ warmer); shadows/highlights: split toning.
GRADE = {
    "cinema": {"sat": 0.78, "curve": 0.50, "black": 0.045, "warm": 0.035, "shadows": (-0.05, 0.0, 0.06), "highlights": (0.06, 0.025, -0.05)},
    "vivid": {"sat": 1.35, "vib": 0.45, "curve": 0.30},
    "retro": {"sat": 0.68, "curve": -0.10, "black": -0.07, "white": 0.93, "warm": 0.07, "highlights": (0.04, 0.02, -0.05)},
    "nextgen": {"sat": 1.16, "vib": 0.35, "toe": 0.40, "shoulder": 0.45, "curve": 0.28, "black": 0.025,
                "shadows": (-0.03, 0.0, 0.04), "highlights": (0.03, 0.012, -0.02)},
    "realistic": {"sat": 0.96, "calm": 0.30, "curve": 0.22, "shoulder": 0.30, "black": 0.015, "warm": -0.012,
                  "shadows": (-0.02, 0.0, 0.025)},
}


def _s(x, k):
    """S-curve around mid grey (k > 0 more contrast, k < 0 less), fixed at 0 and 1."""
    return x + k * (x - 0.5) * (1 - abs(2 * x - 1))


def _filmic(x, toe, shoulder):
    """Shadows pressed down (toe: a power curve below mid grey) and highlights rolled off instead of
    clipped (shoulder: a soft knee above it). Both keep 0, 0.5 and 1 where they are."""
    if x < 0.5 and toe:
        x = 0.5 * (2 * x) ** (1 + toe)
    elif x > 0.5 and shoulder:
        t = (x - 0.5) * 2
        x = 0.5 + 0.5 * (t * (1 + shoulder) / (1 + shoulder * t))
    return x


def _grade(look, r, g, b):
    p = GRADE.get(look)
    if not p:
        return r, g, b
    w = p.get("warm", 0.0)
    r, g, b = r * (1 + w), g, b * (1 - w)
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    chroma = max(r, g, b) - min(r, g, b)
    k = p.get("sat", 1.0) * (1 + p.get("vib", 0.0) * (1 - min(1.0, chroma * 2))) * (1 - p.get("calm", 0.0) * chroma)
    r, g, b = (lum + k * (c - lum) for c in (r, g, b))
    r, g, b = (_filmic(_clamp(c), p.get("toe", 0.0), p.get("shoulder", 0.0)) for c in (r, g, b))
    r, g, b = (_s(_clamp(c), p.get("curve", 0.0)) for c in (r, g, b))
    lum = _clamp(0.2126 * r + 0.7152 * g + 0.0722 * b)
    sh, hi = p.get("shadows", (0, 0, 0)), p.get("highlights", (0, 0, 0))
    ws, wh = (1 - lum) ** 2, lum ** 2
    r, g, b = (c + sh[i] * ws + hi[i] * wh for i, c in enumerate((r, g, b)))
    lo, top = p.get("black", 0.0), p.get("white", 1.0)
    r, g, b = ((c - lo) / (1 - lo) * top if lo >= 0 else (-lo) + c * (top + lo) for c in (r, g, b))
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
    for name, opts in FX[look]:
        if name == "lut":
            if not lut_path:
                continue
            opts = {"lutFile": lut_path}
        effects.append(name)
        lines += [f"{k} = {v}" for k, v in opts.items()]
    head = [f"# STONE IMAGE · {LABELS[look]} (written by STONE; edits are replaced)", f"effects = {':'.join(effects)}",
            "reshadeTexturePath = /dev/null", "reshadeIncludePath = /dev/null", "toggleKey = Home", "enableOnLaunch = True"]
    return "\n".join(head + lines) + "\n"


def _key(look, lut_path):
    """What a look's files depend on: when it is the same, the files written before are used as they are."""
    import hashlib
    return hashlib.sha1(repr((look, LUT_SIZE, GRADE.get(look), FX[look], lut_path)).encode()).hexdigest()[:16]


def write(look, directory=None):
    """Write (or refresh) a look's files; returns the config path. rc12: the 33³ LUT (a third of a second of
    Python on the console) is computed only when the look itself changed (a new STONE version), not for
    every launch: its key is the config's first line."""
    if look not in LOOKS:
        raise ValueError("look")
    d = directory or state_dir()
    os.makedirs(d, exist_ok=True)
    lut = os.path.join(d, f"{look}.cube") if any(name == "lut" for name, _o in FX[look]) else None
    path = os.path.join(d, f"{look}.conf")
    key = f"# key {_key(look, lut)}"
    try:
        with open(path) as f:
            same = f.readline().strip() == key
        if same and (lut is None or os.path.getsize(lut) > 0):
            return path
    except OSError:
        pass
    if lut:
        with open(lut + ".tmp", "w") as f:
            f.write(cube(look))
        os.replace(lut + ".tmp", lut)
    with open(path + ".tmp", "w") as f:
        f.write(key + "\n" + conf(look, lut))
    os.replace(path + ".tmp", path)
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
    # vkBasalt's own log (its README: VKBASALT_LOG_FILE / VKBASALT_LOG_LEVEL), one file per game, so the
    # diagnostic report can say whether the layer started in the game and which effects it loaded.
    return {"ENABLE_VKBASALT": "1", "VKBASALT_CONFIG_FILE": write(look), "STONE_LOOK": look,
            "VKBASALT_LOG_LEVEL": "info", "VKBASALT_LOG_FILE": log_path(appid)}


def log_path(appid):
    return os.path.join(state_dir(), f"vkbasalt-{int(appid)}.log")
