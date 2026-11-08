"""STONE plugin backend. Runs as root (`root` in plugin.json) so 40 CU, the profiles and reboot do
not depend on a polkit session that Game Mode does not have.

It only ever runs the fixed commands below, with values checked here: stoned, stone-cu40 and
systemd keep every limit and safety rule of their own. It never changes 40 CU by itself: each
change is one call from a dialog the person accepted in the plugin.
"""

import asyncio
import json
import os

import decky

BIN = os.environ.get("STONE_BIN_DIR", "/usr/bin")
RELEASE = os.environ.get("STONE_RELEASE_FILE", "/usr/lib/stone-release")
PROFILES = ("silent", "balanced", "performance")
TEST_MINUTES = 3
# Decky is a frozen Python: its libraries must not reach the system's programs.
DROP_ENV = ("LD_LIBRARY_PATH", "LD_PRELOAD", "PYTHONHOME", "PYTHONPATH", "PYTHONDONTWRITEBYTECODE")


def _env():
    env = {k: v for k, v in os.environ.items() if k not in DROP_ENV}
    env["PATH"] = f"{BIN}:/usr/sbin:/usr/bin:/sbin:/bin"
    return env


async def _run(*argv, timeout=30):
    """(returncode, stdout). returncode None: it could not run or took too long."""
    try:
        p = await asyncio.create_subprocess_exec(*argv, stdout=asyncio.subprocess.PIPE,
                                                 stderr=asyncio.subprocess.STDOUT, env=_env())
    except OSError as e:
        return None, str(e)
    try:
        out, _ = await asyncio.wait_for(p.communicate(), timeout)
    except asyncio.TimeoutError:
        p.kill()
        await p.wait()
        return None, "sin respuesta"
    return p.returncode, out.decode("utf-8", "replace")


async def _json(*argv, timeout=30):
    """The command's JSON, or {"error": text} if it failed or printed none."""
    rc, out = await _run(*argv, timeout=timeout)
    try:
        d = json.loads(out)
    except ValueError:
        return {"error": out.strip()[-300:] or "sin datos"}
    if rc != 0 and isinstance(d, dict):
        d.setdefault("error", "falló")
    return d


def _bin(name):
    return os.path.join(BIN, name)


def _version():
    try:
        with open(RELEASE) as f:
            for line in f:
                if line.startswith("STONE_VERSION="):
                    return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return None


class Plugin:
    test_task = None
    test_result = None

    async def ui_ready(self):
        """Steam's interface is up: stoned may apply the saved profile and count this boot as good."""
        return await _json(_bin("stonectl"), "ui-ready")

    async def state(self):
        st, metrics, cal, cu = await asyncio.gather(
            _json(_bin("stonectl"), "--json", "status"), _json(_bin("stonectl"), "--json", "metrics"),
            _json(_bin("stonectl"), "--json", "calibration"), _json(_bin("stone-cu40"), "status", "--json"))
        return {"version": _version(), "stoned": st, "metrics": metrics, "calibration": cal, "cu40": cu,
                "test": {"running": self.test_task is not None and not self.test_task.done(),
                         "result": self.test_result}}

    async def set_profile(self, profile):
        if profile not in PROFILES:
            return {"error": "perfil desconocido"}
        return await _json(_bin("stonectl"), "profile", profile)

    async def set_game_profile(self, appid, profile):
        if not str(appid).isdigit() or profile not in PROFILES + ("global",):
            return {"error": "valor no válido"}
        return await _json(_bin("stonectl"), "game-profile", str(appid), profile)

    async def set_safe_mode(self, on):
        rc, out = await _run(_bin("stonectl"), "safe-mode", "on" if on else "off")
        return {"ok": rc == 0, "error": None if rc == 0 else out.strip()}

    async def calibrate(self, level):
        if level not in ("quick", "standard"):
            return {"error": "nivel desconocido"}
        return await _json(_bin("stonectl"), "calibrate-start", level)

    async def calibrate_cancel(self):
        return await _json(_bin("stonectl"), "calibrate-cancel")

    async def cu40_enable(self):
        rc, out = await _run(_bin("stone-cu40"), "enable", "--yes", timeout=120)
        return {"ok": rc == 0, "error": None if rc == 0 else out.strip()[-300:]}

    async def cu40_disable(self):
        rc, out = await _run(_bin("stone-cu40"), "disable", "--yes", timeout=120)
        return {"ok": rc == 0, "error": None if rc == 0 else out.strip()[-300:]}

    async def cu40_test(self):
        """Starts stone-cu40's test and answers at once; state() reports when it ends."""
        if self.test_task is not None and not self.test_task.done():
            return {"ok": True}

        async def work():
            rc, out = await _run(_bin("stone-cu40"), "test", "--minutes", str(TEST_MINUTES),
                                 timeout=TEST_MINUTES * 60 + 120)
            self.test_result = {"ok": rc == 0, "output": out.strip()[-300:]}

        self.test_result = None
        self.test_task = asyncio.get_event_loop().create_task(work())
        return {"ok": True}

    async def doctor(self):
        return await _json(_bin("stone-doctor"), "--json", timeout=40)

    async def reboot(self):
        rc, out = await _run("systemctl", "reboot")
        return {"ok": rc == 0, "error": None if rc == 0 else out.strip()}

    async def _main(self):
        decky.logger.info("STONE plugin loaded")

    async def _unload(self):
        if self.test_task is not None:
            self.test_task.cancel()
