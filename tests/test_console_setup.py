"""stone-console-setup: what the first boot leaves in the user's home, and what later boots keep.
Fake home, image folder and commands; nothing outside a temporary folder is touched.

    python3 tests/test_console_setup.py     (or: pytest tests/test_console_setup.py)
"""

import hashlib
import json
import os
import shutil
import sys
import tempfile
from collections import namedtuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, run_module  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "system", "usr", "lib", "stone"))
import stone_console_setup as C  # noqa: E402

User = namedtuple("User", "pw_name pw_uid pw_gid pw_dir pw_shell")


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


class Box:
    def __init__(self, manifest=None):
        self.root = tempfile.mkdtemp(prefix="stone-setup-")
        self.console = os.path.join(self.root, "console")
        self.etc = os.path.join(self.root, "etc")
        self.homes = os.path.join(self.root, "home")
        self.home = os.path.join(self.homes, "ana")
        os.makedirs(self.home)
        os.makedirs(self.etc)
        self.calls = []
        self.user = User("ana", 1000, 1000, self.home, "/bin/bash")
        self.brew = os.path.join(self.home, "homebrew")
        C.CONSOLE, C.ETC, C.HOMES = self.console, self.etc, (self.homes,)
        C.DECK_LINK = os.path.join(self.homes, "deck")
        os.environ["STONE_SYSTEM_MOVIE_DIRS"] = os.path.join(self.root, "system-movies")
        self.image(manifest or {"decky": "v1", "css_loader": "1", "plugin": "2.0", "theme": "2.0"})

    def image(self, manifest, loader="loader-1", movie="stone-movie"):
        _write(os.path.join(self.console, "PluginLoader"), loader)
        _write(os.path.join(self.console, "stone-startup.webm"), movie)
        _write(os.path.join(self.console, "manifest.json"), json.dumps(manifest))
        _write(os.path.join(self.console, "plugins", "SDH-CssLoader", "plugin.json"), "css " + manifest["css_loader"])
        _write(os.path.join(self.console, "plugins", "STONE", "plugin.json"), "stone " + manifest["plugin"])
        _write(os.path.join(self.console, "themes", "STONE", "theme.json"), "theme " + manifest["theme"])

    def run(self, argv):
        self.calls.append(argv)
        return 0

    def setup(self):
        self.calls = []
        return C.setup(self.user, self.run)

    def read(self, *rel):
        with open(os.path.join(self.home, *rel)) as f:
            return f.read()

    def close(self):
        shutil.rmtree(self.root)


def _box(fn):
    def wrapped():
        b = Box()
        try:
            fn(b)
        finally:
            b.close()
    wrapped.__name__ = fn.__name__
    return wrapped


@_box
def test_first_boot_installs_everything(b):
    assert b.setup()
    assert b.read("homebrew", "services", "PluginLoader") == "loader-1"
    assert os.access(os.path.join(b.brew, "services", "PluginLoader"), os.X_OK)
    assert b.read("homebrew", "services", ".loader.version").strip() == "v1"
    assert b.read("homebrew", "plugins", "STONE", "plugin.json") == "stone 2.0"
    assert b.read("homebrew", "plugins", "SDH-CssLoader", "plugin.json") == "css 1"
    assert json.loads(b.read("homebrew", "themes", "STONE", "config_USER.json")) == {"active": True}
    assert os.path.exists(os.path.join(b.home, ".steam", "steam", ".cef-enable-remote-debugging"))
    assert os.path.realpath(os.path.join(b.home, ".steam", "steam")) == os.path.realpath(os.path.join(b.home, ".local", "share", "Steam"))
    assert b.read(".steam", "root", "config", "uioverrides", "movies", "deck_startup.webm") == "stone-movie"
    assert os.path.islink(C.DECK_LINK)
    with open(os.path.join(b.etc, "systemd", "system", "plugin_loader.service")) as f:
        unit = f.read()
    assert f"ExecStart={b.brew}/services/PluginLoader" in unit and "User=root" in unit
    assert ["systemctl", "daemon-reload"] in b.calls
    assert ["systemctl", "enable", "plugin_loader.service"] in b.calls
    assert ["systemctl", "start", "--no-block", "plugin_loader.service"] in b.calls
    assert ["chcon", "-t", "bin_t", os.path.join(b.brew, "services", "PluginLoader")] in b.calls


@_box
def test_second_boot_reinstalls_nothing_and_respects_store_updates(b):
    assert b.setup()
    _write(os.path.join(b.brew, "services", "PluginLoader"), "updated from decky")
    _write(os.path.join(b.brew, "plugins", "SDH-CssLoader", "plugin.json"), "updated from the store")
    assert b.setup()
    assert b.read("homebrew", "services", "PluginLoader") == "updated from decky"
    assert b.read("homebrew", "plugins", "SDH-CssLoader", "plugin.json") == "updated from the store"
    assert ["systemctl", "daemon-reload"] not in b.calls


@_box
def test_new_image_updates_only_what_changed_and_keeps_the_theme_off(b):
    assert b.setup()
    _write(os.path.join(b.brew, "themes", "STONE", "config_USER.json"), json.dumps({"active": False}))
    _write(os.path.join(b.brew, "plugins", "SDH-CssLoader", "plugin.json"), "updated from the store")
    b.image({"decky": "v1", "css_loader": "1", "plugin": "2.1", "theme": "2.1"})
    assert b.setup()
    assert b.read("homebrew", "plugins", "STONE", "plugin.json") == "stone 2.1"
    assert b.read("homebrew", "themes", "STONE", "theme.json") == "theme 2.1"
    assert json.loads(b.read("homebrew", "themes", "STONE", "config_USER.json")) == {"active": False}
    assert b.read("homebrew", "plugins", "SDH-CssLoader", "plugin.json") == "updated from the store"


@_box
def test_movie_of_the_user_is_kept_and_bazzites_is_replaced(b):
    movies = os.path.join(b.home, ".local", "share", "Steam", "config", "uioverrides", "movies")
    _write(os.path.join(movies, "deck_startup.webm"), "my own movie")
    assert b.setup()
    assert b.read(".local", "share", "Steam", "config", "uioverrides", "movies", "deck_startup.webm") == "my own movie"

    _write(os.path.join(os.environ["STONE_SYSTEM_MOVIE_DIRS"], "bazzite.webm"), "bazzite movie")
    _write(os.path.join(movies, "deck_startup.webm"), "bazzite movie")
    assert b.setup()
    assert b.read(".local", "share", "Steam", "config", "uioverrides", "movies", "deck_startup.webm") == "stone-movie"
    with open(os.path.join(movies, "deck_startup.webm.stone")) as f:
        assert f.read().strip() == hashlib.sha256(b"stone-movie").hexdigest()


@_box
def test_old_stone_session_is_removed(b):
    stale = os.path.join(b.etc, "sddm.conf.d", "zz-stone-session.conf")
    _write(stale, "[Autologin]\nSession=gamescope-session-stone.desktop\n")
    keep = os.path.join(b.etc, "sddm.conf.d", "zz-holo-autologin.conf")
    _write(keep, "x")
    assert b.setup()
    assert not os.path.exists(stale) and os.path.exists(keep)


@_box
def test_a_failed_piece_is_retried_and_the_rest_still_runs(b):
    shutil.rmtree(os.path.join(b.console, "plugins", "STONE"))
    assert not b.setup()
    assert b.read("homebrew", "services", "PluginLoader") == "loader-1"
    assert ["systemctl", "enable", "plugin_loader.service"] in b.calls
    b.image({"decky": "v1", "css_loader": "1", "plugin": "2.0", "theme": "2.0"})
    assert b.setup()
    assert b.read("homebrew", "plugins", "STONE", "plugin.json") == "stone 2.0"


@_box
def test_console_user_is_the_lowest_ordinary_account_with_a_home(b):
    other = os.path.join(b.homes, "otra")
    os.makedirs(other)
    users = [User("root", 0, 0, "/root", "/bin/bash"), User("stoned", 900, 900, "/", "/sbin/nologin"),
             User("nobody", 65534, 65534, b.home, "/sbin/nologin"), User("sin", 999, 999, b.home, "/bin/bash"),
             User("otra", 1001, 1001, other, "/bin/bash"), b.user]
    assert C.console_user(users).pw_name == "ana"
    assert C.console_user(users[:4]) is None


if __name__ == "__main__":
    sys.exit(run_module(globals()))
