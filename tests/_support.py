"""Shared helpers for the STONE OS (rebuild) tests.

Every test file runs under pytest (CI, dev container) and also as a plain script, so the parts
that need nothing beyond the standard library can run on any machine.

With STONE_REQUIRE_ALL=1 (CI and the dev container) a test that cannot run because a tool or
module is missing FAILS instead of being skipped.
"""

import os
import sys
import traceback

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Skip(Exception):
    pass


def need(condition, why):
    """Skip (or fail under STONE_REQUIRE_ALL=1) when a requirement is missing."""
    if condition:
        return
    if os.environ.get("STONE_REQUIRE_ALL") == "1":
        raise AssertionError(f"cannot run: {why} (STONE_REQUIRE_ALL=1)")
    try:
        import pytest
        pytest.skip(why)
    except ImportError:
        raise Skip(why) from None


def read_env_file(path):
    """KEY=VALUE lines of a shell env file (comments and blanks ignored, no expansion)."""
    out = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"')
    return out


def load_yaml(path):
    try:
        import yaml
    except ImportError:
        need(False, "PyYAML not installed")
    with open(path) as f:
        return yaml.safe_load(f)


def run_module(module_globals):
    """Plain-script runner: every test_* function of the module, PASS/SKIP/FAIL."""
    fails = 0
    for name, fn in sorted(module_globals.items()):
        if not (name.startswith("test_") and callable(fn)):
            continue
        try:
            fn()
            print(f"PASS  {name}")
        except Skip as e:
            print(f"SKIP  {name} ({e})")
        except Exception:
            fails += 1
            print(f"FAIL  {name}")
            traceback.print_exc()
    print("\nall passed" if not fails else f"\n{fails} failed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(0)
