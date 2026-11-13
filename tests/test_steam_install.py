"""The JavaScript STONE runs inside Steam's interface to install a game (steamcef.install_expression,
accept_eula_expression, uninstall_expression) and to read its downloads (DOWNLOADS_EXPRESSION), run in
node against a stand-in of Steam's install manager.

The stand-in behaves as Steam's own interface code says the real one does (steamui/sp.js and
library.js of the client of 12-11-2026): OpenInstallWizard(appids, "0") starts the wizard, every step
is told to the callbacks of RegisterForShowInstallWizard, the wizard waits at "config" (7) for
ContinueInstall, a game with a licence agreement stops at "eula" (8) until MarkEulaAccepted, and after
"create-apps" (9) the wizard goes back to "none" (0). A call without the client id is ignored: that is
what STONE did in 3.1.0-rc3 and every install on the board ended in "Steam no respondió".
The real Steam is a board test (T-STEAM-15); this checks the logic of every path.

    python3 tests/test_steam_install.py     (or: pytest tests/test_steam_install.py)
"""

import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, need, run_module  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "apps", "stone-home"))
from stone_home import steamcef as CEF  # noqa: E402

# Timers run 25 times faster, the stand-in's and STONE's alike: a 30 s wait takes about a second.
HARNESS = """
const [opt, expressions] = JSON.parse(require('fs').readFileSync(0, 'utf8'));
globalThis.window = globalThis;
const realTimeout = setTimeout;
globalThis.setTimeout = (f, ms, ...a) => realTimeout(f, (ms || 0) / 25, ...a);
const M = { state: opt.state || 0, apps: opt.apps || [], cur: 0, folder: opt.folder === undefined ? -1 : opt.folder,
            cbs: [], calls: [], accepted: false, installed: false, unregistered: 0 };
const info = () => ({ eInstallState: M.state, rgApps: M.apps.map(a => ({ nAppID: a, lDiskSpaceRequiredBytes: 1 })), currentAppID: M.cur,
                      iInstallFolder: M.folder, nDiskSpaceRequired: opt.need || 1e9, nDiskSpaceAvailable: opt.free || 5e10,
                      eAppError: opt.err || 0, errorDetail: opt.err ? 'no connection' : '' });
const set = s => { M.state = s; if (!opt.nocallback) M.cbs.slice().forEach(f => f(info())); };
const end = () => { M.installed = !opt.fail; set(opt.fail ? 15 : opt.complete ? 14 : 0); };
const I = {
  RegisterForShowInstallWizard: f => { M.cbs.push(f); return { unregister() { M.cbs = M.cbs.filter(x => x !== f); M.unregistered++; } }; },
  OpenInstallWizard: (ids, client) => {
    M.calls.push(['open', ids, client === undefined ? null : client]);
    if (opt.dead || client !== '0' || !Array.isArray(ids)) return;            // without the client id Steam does nothing
    M.apps = ids; M.cur = 0; set(1);
    setTimeout(() => { set(opt.free_license ? 3 : 5); if (!opt.free_license) setTimeout(() => set(7), 150); }, 120);
  },
  SetInstallFolder: async i => { M.calls.push(['folder', i]); M.folder = i; return info(); },
  ContinueInstall: async () => {
    M.calls.push(['continue', M.state]);
    if (opt.hang) return new Promise(() => {});
    if (M.state === 3) { set(5); setTimeout(() => set(7), 100); }
    else if (M.state === 7) { M.cur = M.apps[0]; if (opt.eula && !M.accepted) set(8); else { set(9); setTimeout(end, 200); } }
    else if (M.state === 8 && M.accepted) { set(9); setTimeout(end, 200); }
    return info();
  },
  CancelInstall: () => { M.calls.push(['cancel', M.state]); set(16); setTimeout(() => set(0), 40); },
  OpenUninstallWizard: (ids, client, quiet) => { M.calls.push(['uninstall', ids, client, quiet]); },
};
if (!opt.nopoll) I.GetInstallManagerInfo = async () => info();
window.SteamClient = { Installs: I, Apps: {
  LoadEula: async id => (M.accepted ? [] : [{ id: id + '_eula_0', version: 3, url: 'http://store.steampowered.com/eula/' + id + '_eula_0' }]),
  MarkEulaAccepted: (id, eula, version) => { M.calls.push(['accept', id, eula, version]); M.accepted = true; } } };
if (opt.downloads) window.downloadsStore = { LocalDownloadOverview: opt.downloads.overview, m_DownloadItems: new Map([['0', opt.downloads.items || []]]) };
(async () => {
  const values = [];
  for (const e of expressions) values.push(await eval(e));
  process.stdout.write(JSON.stringify({ values, calls: M.calls, installed: M.installed, listeners: M.cbs.length, unregistered: M.unregistered }));
  process.exit(0);
})().catch(e => { process.stdout.write(JSON.stringify({ error: String(e && e.stack || e) })); process.exit(0); });
"""


def _run(opt, *expressions):
    need(shutil.which("node") is not None, "node not installed (dev container, CI)")
    r = subprocess.run(["node", "-e", HARNESS], input=json.dumps([opt, list(expressions)]), capture_output=True, text=True, timeout=120)
    assert r.returncode == 0 and r.stdout, r.stderr
    out = json.loads(r.stdout)
    assert "error" not in out, out["error"]
    out["answers"] = [CEF.parse_install(v) if isinstance(v, str) else v for v in out["values"]]
    return out


def _calls(out, name):
    return [c for c in out["calls"] if c[0] == name]


def test_a_game_is_installed_the_way_steams_own_interface_does_it():
    out = _run({}, CEF.install_expression(200260))
    a = out["answers"][0]
    assert _calls(out, "open") == [["open", [200260], "0"]], out["calls"]          # the games and the local client
    assert _calls(out, "folder") == [["folder", 0]] and _calls(out, "continue") == [["continue", 7]]
    assert a["answer"] == "gone" and out["installed"] is True, a                   # the wizard closed after being continued
    assert a["trace"] == ["setup", "wait-appinfo", "config", "create-apps", "none"], a
    assert not _calls(out, "accept") and out["listeners"] == 0 and out["unregistered"] == 1   # nothing accepted, nothing left behind
    done = _run({"complete": True}, CEF.install_expression(200260))["answers"][0]
    assert done["answer"] == "started" and done["state"] == "complete", done


def test_the_callback_alone_or_the_question_alone_is_enough():
    for opt in ({"nopoll": True}, {"nocallback": True}):                 # a build without GetInstallManagerInfo; callbacks not arriving
        out = _run(opt, CEF.install_expression(620))
        assert out["answers"][0]["answer"] == "gone" and out["installed"], (opt, out["answers"], out["calls"])


def test_the_last_install_left_in_the_wizard_is_not_taken_for_this_one():
    out = _run({"state": 14, "apps": [10]}, CEF.install_expression(620))          # "complete" from an earlier game
    assert out["answers"][0]["answer"] == "gone" and _calls(out, "continue") == [["continue", 7]] and out["installed"]
    out = _run({"state": 7, "apps": [10], "folder": 0}, CEF.install_expression(620))   # a wizard left open on another game
    assert out["calls"][0] == ["cancel", 7] and out["answers"][0]["answer"] == "gone" and _calls(out, "open") == [["open", [620], "0"]]


def test_a_licence_agreement_comes_back_and_only_the_persons_acceptance_goes_on():
    out = _run({"eula": True}, CEF.install_expression(1174180))
    a = out["answers"][0]
    assert a["answer"] == "eula" and a["trace"][-1] == "eula" and not out["installed"], a
    assert a["eulas"] == [{"id": "1174180_eula_0", "version": 3, "url": "https://store.steampowered.com/eula/1174180_eula_0"}]
    assert not _calls(out, "accept") and _calls(out, "continue") == [["continue", 7]]        # stopped at the agreement
    both = _run({"eula": True}, CEF.install_expression(1174180), CEF.accept_eula_expression(1174180))
    assert both["answers"][0]["answer"] == "eula" and both["answers"][1]["answer"] == "gone", both["answers"]
    assert _calls(both, "accept") == [["accept", 1174180, "1174180_eula_0", 3]] and both["installed"] is True
    assert _calls(both, "continue") == [["continue", 7], ["continue", 8]] and len(_calls(both, "open")) == 1


def test_a_full_disk_a_failure_a_free_licence_and_a_steam_that_does_nothing():
    out = _run({"need": 80e9, "free": 12e9}, CEF.install_expression(620))
    a = out["answers"][0]
    assert a["answer"] == "space" and a["need"] == 80e9 and a["free"] == 12e9 and not _calls(out, "continue")
    assert _calls(out, "cancel") and not out["installed"]
    fail = _run({"fail": True, "err": 3}, CEF.install_expression(620))["answers"][0]
    assert fail["answer"] == "failed" and fail["err"] == 3 and fail["detail"] == "no connection", fail
    free = _run({"free_license": True}, CEF.install_expression(570))
    assert free["answers"][0]["answer"] == "gone" and _calls(free, "continue") == [["continue", 3], ["continue", 7]]
    dead = _run({"dead": True}, CEF.install_expression(620))["answers"][0]            # Steam ignores the request
    assert dead["answer"] in ("timeout", "nowizard") and dead["trace"] in ([], ["none"]), dead
    hang = _run({"hang": True}, CEF.install_expression(620))["answers"][0]            # a call that never answers
    assert hang["answer"] == "timeout" and hang["trace"][-1] == "config", hang


def test_without_steamclient_the_next_page_is_tried_and_uninstall_takes_three_arguments():
    need(shutil.which("node") is not None, "node not installed (dev container, CI)")
    r = subprocess.run(["node", "-e", "globalThis.window=globalThis;Promise.resolve(eval(require('fs').readFileSync(0,'utf8')))"
                        ".then(v=>process.stdout.write(JSON.stringify(v)))"], input=CEF.install_expression(620),
                       capture_output=True, text=True, timeout=30)
    assert r.stdout == "null", (r.stdout, r.stderr)
    out = _run({}, CEF.uninstall_expression(620))
    assert out["values"] == ["ok"] and _calls(out, "uninstall") == [["uninstall", [620], "0", True]]


def test_live_downloads_are_read_from_steams_own_store():
    overview = {"update_appid": 200260, "update_state": "Downloading", "paused": False, "update_network_bytes_per_second": 38000000,
                "overall_estimated_time_remaining_sec": 1260, "overall_percent_complete": 14.5,
                "progress": [{"bytes_in_progress": 0, "bytes_total": 0}, {"bytes_in_progress": 0, "bytes_total": 0},
                             {"bytes_in_progress": 2500, "bytes_total": 17000}, {"bytes_in_progress": 100, "bytes_total": 19000}]}
    items = [{"appid": 200260, "active": True, "completed": False, "queue_index": 0}, {"appid": 620, "active": False, "completed": False, "queue_index": 1}]
    out = _run({"downloads": {"overview": overview, "items": items}}, CEF.DOWNLOADS_EXPRESSION)
    live = CEF.parse_downloads(out["values"][0])
    assert live["appid"] == 200260 and live["state"] == "Downloading" and live["rate"] == 38000000 and live["eta"] == 1260
    assert live["percent"] == 14.5 and live["progress"][2] == [2500, 17000] and CEF.stage_of(live) == "download"
    assert [(q["appid"], q["active"], q["index"]) for q in live["queue"]] == [(200260, True, 0), (620, False, 1)]
    assert _run({}, CEF.DOWNLOADS_EXPRESSION)["values"] == [None]                    # this page has no downloads store


if __name__ == "__main__":
    run_module(globals())
