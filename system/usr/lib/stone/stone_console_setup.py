"""STONE console setup: Decky Loader, CSS Loader, the STONE theme and the STONE plugin, no terminal.

Decky Loader lives in the user's home (~/homebrew), which a bootc image cannot ship, and the user
only exists once the installer has created it. So the image carries everything in
/usr/share/stone/console and this runs as root at every boot, before the display manager
(stone-console-setup.service). It repeats what Decky's official installer does:

  ~/homebrew/services/PluginLoader   the loader, with SELinux type bin_t
  /etc/systemd/system/plugin_loader.service
  <Steam>/.cef-enable-remote-debugging

and adds STONE's own pieces. A piece is copied only when the image carries a version this console
has not installed yet (recorded in ~/homebrew/.stone-installed.json), so something updated from
Decky's store stays until the image brings a newer one, and an option the user changed
(the theme off, their own startup movie) is never reverted.

It never stops the boot: a failed step is logged and the next one still runs.
"""

import hashlib
import json
import os
import pwd
import shutil
import subprocess
import sys

CONSOLE = os.environ.get("STONE_CONSOLE_DIR", "/usr/share/stone/console")
ETC = os.environ.get("STONE_ETC_DIR", "/etc")
HOMES = tuple(os.environ.get("STONE_HOME_DIRS", "/home:/var/home").split(":"))
DECK_LINK = os.environ.get("STONE_DECK_LINK", "/home/deck")
STALE_SESSION = "sddm.conf.d/zz-stone-session.conf"   # STONE 1.0's automatic session, now gone
THEME_ON = {"active": True}
BOOT_MOVIE = "deck_startup.webm"

UNIT = """[Unit]
Description=SteamDeck Plugin Loader
After=network.target
[Service]
Type=simple
User=root
Restart=always
KillMode=process
TimeoutStopSec=15
ExecStart={home}/services/PluginLoader
WorkingDirectory={home}/services
Environment=UNPRIVILEGED_PATH={home}
Environment=PRIVILEGED_PATH={home}
Environment=LOG_LEVEL=INFO
[Install]
WantedBy=multi-user.target
"""


def log(msg):
    print(f"stone-console-setup: {msg}", flush=True)


def console_user(users=None):
    """The person's account: the lowest ordinary uid with a real home. None before installation."""
    best = None
    for u in (pwd.getpwall() if users is None else users):
        if not 1000 <= u.pw_uid < 60000 or u.pw_shell.endswith(("nologin", "false")):
            continue
        if not u.pw_dir.startswith(tuple(h + "/" for h in HOMES)) or not os.path.isdir(u.pw_dir):
            continue
        if best is None or u.pw_uid < best.pw_uid:
            best = u
    return best


def _chown(path, user):
    """Give a tree to the user. Not root in the tests: then there is nothing to change."""
    if os.geteuid() != 0:
        return
    os.chown(path, user.pw_uid, user.pw_gid)
    for top, dirs, files in os.walk(path):
        for n in dirs + files:
            os.chown(os.path.join(top, n), user.pw_uid, user.pw_gid, follow_symlinks=False)


def _mkdirs(path, user, stop):
    """mkdir -p owned by the user, from `stop` down (nothing above it changes owner)."""
    todo = []
    while not os.path.isdir(path) and path != stop:
        todo.append(path)
        path = os.path.dirname(path)
    for p in reversed(todo):
        os.mkdir(p)
        if os.geteuid() == 0:
            os.chown(p, user.pw_uid, user.pw_gid)


def _replace_tree(src, dest, keep=()):
    """Copy src over dest; only names in `keep` survive from what was there."""
    kept = {}
    for name in keep:
        p = os.path.join(dest, name)
        if os.path.isfile(p):
            with open(p, "rb") as f:
                kept[name] = f.read()
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    shutil.copytree(src, dest, symlinks=True)
    for name, data in kept.items():
        with open(os.path.join(dest, name), "wb") as f:
            f.write(data)


def _load(path):
    try:
        with open(path) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _give_to_user(home, user):
    """The user's tree, except the loader, which runs as root: root's, as Decky's installer leaves it."""
    _chown(home, user)
    loader = os.path.join(home, "services", "PluginLoader")
    if os.geteuid() == 0 and os.path.exists(loader):
        os.chown(loader, 0, 0)


def install_loader(home, want, run):
    services = os.path.join(home, "services")
    os.makedirs(services, exist_ok=True)
    tmp = os.path.join(services, ".PluginLoader.stone-tmp")
    shutil.copyfile(os.path.join(CONSOLE, "PluginLoader"), tmp)
    os.chmod(tmp, 0o755)
    os.replace(tmp, os.path.join(services, "PluginLoader"))
    with open(os.path.join(services, ".loader.version"), "w") as f:
        f.write(want + "\n")


def relabel_loader(home, run):
    """Bazzite enforces SELinux; a binary in a home directory may not run as a service otherwise."""
    if run(["selinuxenabled"]) == 0:
        run(["chcon", "-t", "bin_t", os.path.join(home, "services", "PluginLoader")])


def install_unit(home, run):
    path = os.path.join(ETC, "systemd", "system", "plugin_loader.service")
    want = UNIT.format(home=home)
    try:
        with open(path) as f:
            same = f.read() == want
    except OSError:
        same = False
    if not same:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(want)
        run(["systemctl", "daemon-reload"])
    run(["systemctl", "enable", "plugin_loader.service"])
    run(["systemctl", "start", "--no-block", "plugin_loader.service"])


def install_theme(home, user):
    dest = os.path.join(home, "themes", "STONE")
    _replace_tree(os.path.join(CONSOLE, "themes", "STONE"), dest, keep=("config_USER.json", "config_ROOT.json"))
    # CSS Loader picks the file by the user it runs as; on by default, off stays off once chosen.
    for name in ("config_USER.json", "config_ROOT.json"):
        p = os.path.join(dest, name)
        if not os.path.exists(p):
            with open(p, "w") as f:
                json.dump(THEME_ON, f)


def steam_root(user):
    """Steam's folder, made now if Steam has not run yet: the two files below must be there before
    its first start. ~/.steam/{steam,root} are the links Steam itself makes to this folder."""
    root = os.path.join(user.pw_dir, ".local", "share", "Steam")
    dot = os.path.join(user.pw_dir, ".steam")
    _mkdirs(root, user, user.pw_dir)
    _mkdirs(dot, user, user.pw_dir)
    for name in ("steam", "root"):
        link = os.path.join(dot, name)
        if not os.path.lexists(link):
            os.symlink(root, link)
            if os.geteuid() == 0:
                os.chown(link, user.pw_uid, user.pw_gid, follow_symlinks=False)
    return os.path.realpath(os.path.join(dot, "steam"))


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def install_movie(root, user):
    """Steam's startup movie becomes STONE's. One that is not STONE's and that the user may have put
    there is never replaced, unless it is a copy of a movie the image ships (Bazzite has its own)."""
    src = os.path.join(CONSOLE, "stone-startup.webm")
    movies = os.path.join(root, "config", "uioverrides", "movies")
    dest = os.path.join(movies, BOOT_MOVIE)
    marker = dest + ".stone"
    want = _sha256(src)
    if os.path.exists(dest):
        have = _sha256(dest)
        try:
            with open(marker) as f:
                mine = f.read().strip()
        except OSError:
            mine = None
        if have == want:
            return "unchanged"
        if mine != have and not _is_system_movie(dest, have):
            return "kept: the user's own movie"
    _mkdirs(movies, user, root)
    tmp = dest + ".stone-tmp"
    shutil.copyfile(src, tmp)
    os.replace(tmp, dest)
    with open(marker, "w") as f:
        f.write(want + "\n")
    if os.geteuid() == 0:
        for p in (dest, marker):
            os.chown(p, user.pw_uid, user.pw_gid)
    return "installed"


def _is_system_movie(path, digest, dirs=None):
    size = os.path.getsize(path)
    for top in dirs or os.environ.get("STONE_SYSTEM_MOVIE_DIRS", "/usr/share:/etc/skel").split(":"):
        for d, _sub, files in os.walk(top):
            for n in files:
                f = os.path.join(d, n)
                if n.endswith(".webm") and not f.startswith(CONSOLE) and os.path.getsize(f) == size \
                        and _sha256(f) == digest:
                    return True
    return False


def _step(name, fn, *args):
    try:
        out = fn(*args)
        log(f"{name}: {out if isinstance(out, str) else 'ok'}")
        return True
    except Exception as e:  # noqa: BLE001  a failed step never stops the boot
        log(f"{name}: FAILED: {type(e).__name__}: {e}")
        return False


def _run(argv):
    try:
        return subprocess.run(argv, check=False, timeout=60).returncode
    except (OSError, subprocess.SubprocessError) as e:
        log(f"{argv[0]}: {e}")
        return None


def setup(user, run=_run):
    manifest = _load(os.path.join(CONSOLE, "manifest.json"))
    home = os.path.join(user.pw_dir, "homebrew")
    record_path = os.path.join(home, ".stone-installed.json")
    _mkdirs(os.path.join(home, "plugins"), user, user.pw_dir)
    _mkdirs(os.path.join(home, "themes"), user, user.pw_dir)
    done = _load(record_path)
    ok = True
    changed = False

    def piece(key, fn, *args):
        nonlocal ok, changed
        if done.get(key) == manifest.get(key):
            return
        changed = True
        if _step(key, fn, *args):
            done[key] = manifest.get(key)
        else:
            ok = False

    piece("decky", install_loader, home, manifest.get("decky", ""), run)
    piece("css_loader", _replace_tree, os.path.join(CONSOLE, "plugins", "SDH-CssLoader"),
          os.path.join(home, "plugins", "SDH-CssLoader"))
    piece("plugin", _replace_tree, os.path.join(CONSOLE, "plugins", "STONE"), os.path.join(home, "plugins", "STONE"))
    piece("theme", install_theme, home, user)
    if changed:
        with open(record_path, "w") as f:
            json.dump(done, f)
        ok = _step("ownership", _give_to_user, home, user) and ok
    ok = _step("selinux", relabel_loader, home, run) and ok

    def link_deck():
        # As Bazzite's own `ujust setup-decky`: some plugins assume this path.
        if not os.path.lexists(DECK_LINK):
            os.symlink(user.pw_dir, DECK_LINK)
    ok = _step("/home/deck", link_deck) and ok
    ok = _step("service", install_unit, home, run) and ok

    def steam():
        root = steam_root(user)
        flag = os.path.join(root, ".cef-enable-remote-debugging")
        if not os.path.exists(flag):
            open(flag, "a").close()
            if os.geteuid() == 0:
                os.chown(flag, user.pw_uid, user.pw_gid)
        return install_movie(root, user)
    ok = _step("steam", steam) and ok

    def stale_session():
        p = os.path.join(ETC, STALE_SESSION)
        if os.path.exists(p):
            os.remove(p)
            return "removed STONE 1.0's automatic session"
        return "none"
    return _step("old session", stale_session) and ok


def main(argv=None):
    user = console_user()
    if user is None:
        log("no console user yet; nothing to do")
        return 0
    log(f"setting up for {user.pw_name}")
    if not setup(user):
        log("finished with failures; Steam still starts")
    return 0                                     # never stop the boot


if __name__ == "__main__":
    sys.exit(main())
