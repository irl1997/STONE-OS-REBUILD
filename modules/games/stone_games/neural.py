"""STONE NEURAL RENDER (M18), EXPERIMENTAL: where neural image reconstruction backends plug in.

A backend is an object with `name`, `available() -> (bool, reason)` and `env_for(appid) -> dict`
(the launch variables that turn it on for one game, like look.py and graphics.py). None is registered:
no neural upscaler or frame generator runs today on the BC-250's GPU (GFX1013, RDNA 1 class, no
matrix/WMMA units) in a way STONE can measure on the board. A backend is added here only after a
measurement on the board shows it helps (D-18, D-23), and it starts as EXPERIMENTAL.

Looked at on 22-11-2026: Apex Neural Rendering (github.com/apex-compute/ANR). Only its frame generation
(ANR FG) exists, as a beta that plugs into OptiScaler and needs games with DLSS frame generation; its
upscaler (ANR SR) is not released, its source is "coming soon" and the BC-250 is not on its GPU list.
Not added (the owner chose to leave it out for now); FSR 3 frame generation through OptiScaler is
offered instead (scaling.py).
"""

BACKENDS = []


def register(backend):
    if not all(hasattr(backend, a) for a in ("name", "available", "env_for")):
        raise TypeError("a neural backend needs name, available() and env_for()")
    BACKENDS.append(backend)


def status():
    out = []
    for b in BACKENDS:
        ok, why = b.available()
        out.append({"name": b.name, "available": ok, "reason": why})
    return {"experimental": True, "backends": out,
            "summary": "Sin backends: ninguno funciona hoy de forma medible en la GPU de la BC-250" if not out else None}
