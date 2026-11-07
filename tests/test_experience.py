"""STONE EXPERIENCE ENGINE (stone_games/experience.py): thermal forecast, stutters, regression guard,
confidence and the per-game report. Pure Python: runs anywhere.

    python3 tests/test_experience.py     (or: pytest tests/test_experience.py)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "modules", "games"))
from stone_games import experience as X  # noqa: E402


def test_thermal_forecast_only_with_enough_rising_data():
    rising = [(t, 60 + t / 60.0) for t in range(0, 181, 10)]          # +1 °C per minute, 3 min
    f = X.thermal_forecast(rising, 85)
    assert f["slope_c_per_min"] == 1.0 and 21.5 <= f["minutes_to_limit"] <= 22.5, f
    assert X.thermal_forecast(rising[:4], 85) is None                  # too few readings
    assert X.thermal_forecast([(t, 70) for t in range(0, 181, 10)], 85)["minutes_to_limit"] is None   # flat
    assert X.thermal_forecast(rising, None) is None                     # limit unknown
    hot = [(t, 84.5 + t / 60.0) for t in range(0, 181, 10)]
    assert X.thermal_forecast(hot, 85)["minutes_to_limit"] == 0.0       # already past it


def test_stutters_and_regression_and_confidence():
    assert X.stutter_verdict({"seconds": 120, "stutters": 1}) == (0.5, "fluido")
    assert X.stutter_verdict({"seconds": 60, "stutters": 10})[1] == "muchos tirones"
    assert X.stutter_verdict({"error": "x"}) is None and X.stutter_verdict(None) is None
    env = {"game_build": "1", "proton": "9.0", "gpu_backend": "gov/cu40=True", "stone_version": "1.0.0-rc1"}
    assert X.regression_guard(env, dict(env)) == []
    assert X.regression_guard(env, dict(env, proton="10.0")) == ["cambió la versión de Proton"]
    assert X.regression_guard(None, env) == []
    m = {"metrics": {"avg_fps": 60, "low1_fps": 45, "seconds": 120, "stutters": 0},
         "score": {"quality": {"score": 70}, "recommended": {"score": 80}, "performance": {"score": 75}}, "key": "k1"}
    p = {"status": "AUTO_GENERATED", "measurements": [m, dict(m, key="k2", score={"quality": {"score": 90}, "recommended": {"score": 60}, "performance": {"score": 50}})],
         "invalidation": env, "failures": {}}
    assert X.confidence(p, env)["level"] == "medium"
    assert X.confidence(p, dict(env, proton="10.0"))["level"] == "low" and "a revisar" in X.confidence(p, dict(env, proton="10.0"))["detail"]
    assert X.confidence({"status": "UNKNOWN"}, env)["level"] == "low"
    r = X.report(p, env)
    assert r["autopilot"] == {"quality": "k2", "balanced": "k1", "fluid": "k1"} and r["last"]["verdict"] == "fluido"
    assert X.report({"status": "UNKNOWN"}, env) == {"confidence": X.confidence({"status": "UNKNOWN"}, env), "last": None,
                                                   "regression": [], "autopilot": None}


if __name__ == "__main__":
    sys.exit(run_module(globals()))
