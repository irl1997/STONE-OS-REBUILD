"""STONE NEURAL RENDER (stone_games/neural.py): the registry, empty on purpose (M18, EXPERIMENTAL)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "modules", "games"))
from stone_games import neural as N  # noqa: E402


def test_no_backend_by_default_and_backends_must_be_complete():
    assert N.status()["backends"] == [] and N.status()["experimental"] is True and N.status()["summary"]

    class B:
        name = "x"

        def available(self):
            return False, "needs measurement"

        def env_for(self, appid):
            return {}
    N.register(B())
    try:
        assert N.status()["backends"] == [{"name": "x", "available": False, "reason": "needs measurement"}]
        try:
            N.register(object())
            raise AssertionError("incomplete backend accepted")
        except TypeError:
            pass
    finally:
        N.BACKENDS.clear()


if __name__ == "__main__":
    sys.exit(run_module(globals()))
