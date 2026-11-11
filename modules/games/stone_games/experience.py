"""STONE EXPERIENCE ENGINE (M23): deterministic rules and plain statistics over what STONE measures.
No generative AI (D-25). Each function works only when its data exists and says so when it does not.

  thermal_forecast   GPU temperature trend (least squares over the last minutes of stoned's readings):
                     minutes until the profile's limit at this pace
  stutter_verdict    MangoHud frametimes of a measurement: stutters per minute → fluido / tirones
  regression_guard   what changed since a game was measured (game build, Proton, GPU backend, CU,
                     calibration, display, STONE): the measurement may no longer hold
  confidence         how much STONE knows about a game (A11 states, number of clean measurements,
                     staleness, recent abnormal exits)
  report             all of the above for one game, in Spanish, for STONE Home's game page

Self-healing (non-destructive) lives where the event happens: optimizer.finish turns a game's
STONE IMAGE look off after an abnormal exit with that look on (look.py), and the existing safety
rules already launch the next start without what was blamed.
"""

STALE_LABELS = {"game_build": "el juego se actualizó", "proton": "cambió la versión de Proton",
                "injected": "cambió el escalador instalado", "gpu_backend": "cambió el regulador o las CU",
                "calibration": "cambió la calibración", "display": "cambió la pantalla",
                "engine": "cambió el motor de STONE", "stone_version": "cambió la versión de STONE OS"}
CONFIDENCE_TEXT = {"UNKNOWN": "Sin datos todavía", "AUTO_GENERATED": "Medido en esta consola",
                   "RECOMMENDED": "Recomendado por la base de datos de STONE", "USER_MODIFIED": "Tu configuración",
                   "HARDWARE_VERIFIED": "Verificado por ti en esta consola"}


def thermal_forecast(samples, limit_c, window_s=300, min_samples=6, min_span_s=60, min_slope=0.2):
    """samples: [(t_seconds, temp_c)]. Returns {"slope_c_per_min", "minutes_to_limit"} or None
    when there is not enough data, the temperature is not rising, or the limit is unknown."""
    if not limit_c or not samples:
        return None
    t_end = samples[-1][0]
    pts = [(t, c) for t, c in samples if c is not None and t_end - t <= window_s]
    if len(pts) < min_samples or pts[-1][0] - pts[0][0] < min_span_s:
        return None
    n = len(pts)
    mt = sum(t for t, _ in pts) / n
    mc = sum(c for _, c in pts) / n
    var = sum((t - mt) ** 2 for t, _ in pts)
    if var == 0:
        return None
    slope = sum((t - mt) * (c - mc) for t, c in pts) / var * 60.0          # °C per minute
    now_c = mc + slope / 60.0 * (t_end - mt)
    if slope < min_slope:
        return {"slope_c_per_min": round(slope, 2), "minutes_to_limit": None}
    left = (limit_c - now_c) / slope
    return {"slope_c_per_min": round(slope, 2), "minutes_to_limit": round(max(0.0, left), 1)}


def stutter_verdict(m):
    """m: metrics.summarize() of one measurement → (per_minute, verdict) or None."""
    if not m or m.get("error") or not m.get("seconds"):
        return None
    per_min = m.get("stutters", 0) / (m["seconds"] / 60.0)
    verdict = "fluido" if per_min < 1 else "algunos tirones" if per_min < 6 else "muchos tirones"
    return round(per_min, 1), verdict


def regression_guard(measured_env, env):
    """Spanish reasons why a measurement may no longer hold (empty: nothing changed or never measured)."""
    if not measured_env or not env:
        return []
    return [STALE_LABELS.get(k, k) for k in STALE_LABELS if measured_env.get(k) != env.get(k)]


def confidence(profile, env=None):
    """{"level": low|medium|high, "text": ...} from the profile's state and its measurements."""
    status = profile.get("status", "UNKNOWN")
    ms = [m for m in profile.get("measurements") or [] if not (m.get("metrics") or {}).get("error")]
    fails = sum((profile.get("failures") or {}).values())
    stale = regression_guard(profile.get("invalidation") if ms else None, env)
    text = CONFIDENCE_TEXT.get(status, status)
    if status == "HARDWARE_VERIFIED" and not stale:
        level = "high"
    elif ms and not stale and fails == 0:
        level = "high" if len(ms) >= 3 else "medium"
    elif ms or status == "RECOMMENDED":
        level = "medium"
    else:
        level = "low"
    if stale:
        level = "low" if level == "medium" else "medium" if level == "high" else level
    detail = [f"{len(ms)} medición{'es' if len(ms) != 1 else ''} limpia{'s' if len(ms) != 1 else ''}"]
    if fails:
        detail.append(f"{fails} cierre{'s' if fails != 1 else ''} anómalo{'s' if fails != 1 else ''}")
    if stale:
        detail.append("a revisar: " + ", ".join(stale))
    return {"level": level, "text": text, "detail": " · ".join(detail)}


def _best(ms, mode):
    scored = [m for m in ms if ((m.get("score") or {}).get(mode) or {}).get("score") is not None]
    return max(scored, key=lambda m: m["score"][mode]["score"]) if scored else None


def report(profile, env=None):
    """Everything STONE Home's game page shows under Experiencia."""
    ms = [m for m in profile.get("measurements") or [] if not (m.get("metrics") or {}).get("error")]
    last = ms[-1] if ms else None
    out = {"confidence": confidence(profile, env), "last": None, "regression": [], "autopilot": None}
    if last:
        m = last["metrics"]
        st = stutter_verdict(m)
        out["last"] = {"avg_fps": m.get("avg_fps"), "low1_fps": m.get("low1_fps"),
                       "stutters_per_min": st[0] if st else None, "verdict": st[1] if st else None,
                       "gpu_temp_max": m.get("gpu_temp_max"), "config": last.get("key")}
        out["regression"] = regression_guard(profile.get("invalidation"), env)
    # Performance Autopilot: the best measured configuration for each goal (QUALITY / BALANCED / FLUID)
    goals = {"quality": _best(ms, "quality"), "balanced": _best(ms, "recommended"), "fluid": _best(ms, "performance")}
    if any(goals.values()):
        out["autopilot"] = {k: (v.get("key") if v else None) for k, v in goals.items()}
    return out
