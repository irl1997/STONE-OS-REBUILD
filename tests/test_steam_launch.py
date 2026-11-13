"""Starting a game through Steam's interface, followed step by step (steamcef.launch_expression,
launch_state_expression, launch_answer_expression), run in node against a stand-in of Steam's game
actions as Steam's own interface code describes them (client of 12-11-2026): RunGame(gameid, "", -1,
source) starts an action, its steps arrive through RegisterForGameAction{Start,TaskChange,
UserRequest,ShowError,End}, a question waits until ContinueGameAction(id, answer) or
CancelGameAction(id). Board, 13-11-2026: Batman: Arkham City stayed on "SIGUE CARGANDO" because those
questions opened in Steam's hidden windows. The real Steam is a board test (T-STEAM-19).

    python3 tests/test_steam_launch.py     (or: pytest tests/test_steam_launch.py)
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _support import REPO, need, run_module  # noqa: E402

sys.path.insert(0, os.path.join(REPO, "apps", "stone-home"))
from stone_home import shortcuts as SC  # noqa: E402
from stone_home import steamcef as CEF  # noqa: E402
from stone_home import vdf  # noqa: E402

HARNESS = """
const [opt, steps] = JSON.parse(require('fs').readFileSync(0, 'utf8'));
globalThis.window = globalThis;
const realTimeout = setTimeout;
globalThis.setTimeout = (f, ms, ...a) => realTimeout(f, (ms || 0) / 20, ...a);
const cb = {}, calls = []; let act = null;
const reg = n => f => { (cb[n] = cb[n] || []).push(f); return { unregister() {} }; };
const fire = (n, ...a) => (cb[n] || []).forEach(f => f(...a));
const later = (ms, f) => setTimeout(f, ms);
window.SteamClient = { Apps: {
  RegisterForGameActionStart: reg('start'), RegisterForGameActionTaskChange: reg('task'), RegisterForGameActionUserRequest: reg('ask'),
  RegisterForGameActionShowError: reg('error'), RegisterForGameActionEnd: reg('end'),
  RunGame: (gid, a, b, src) => { calls.push(['run', gid, a, b]); act = { id: 41, gid: String(gid), task: 'UpdatingAppInfo', wait: false };
    fire('start', 41, gid, 'LaunchApp', src); fire('task', 41, gid, 'LaunchApp', 'UpdatingAppInfo', '');
    later(60, () => { if (opt.ask) { act.task = opt.ask; act.wait = true; fire('ask', 41, gid, 'LaunchApp', opt.ask, opt.details || ''); }
      else if (opt.error) fire('error', 41, gid, 'LaunchApp', opt.error, 'proton');
      else { fire('task', 41, gid, 'LaunchApp', 'CreatingProcess', ''); fire('task', 41, gid, 'LaunchApp', 'Completed', ''); fire('end', 41); act = null; } }); },
  GetActiveGameActions: async () => act ? [{ nGameActionID: act.id, gameid: act.gid, strActionName: 'LaunchApp', strTaskName: act.task,
    strTaskDetails: '', bWaitingForUI: act.wait, strNumDone: '0', strNumTotal: '0' }] : [],
  GetLaunchOptionsForApp: async () => [{ nIndex: 0, strDescription: 'Jugar' }, { nIndex: 1, strDescription: 'Jugar en DirectX 11' }],
  LoadEula: async id => [{ id: id + '_eula', version: 1, url: 'http://store.steampowered.com/eula/' + id + '_eula' }],
  MarkEulaAccepted: (...a) => calls.push(['accept', ...a]),
  ContinueGameAction: (id, a) => { calls.push(['continue', id, a]); if (act) { act.wait = false; fire('task', id, act.gid, 'LaunchApp', 'CreatingProcess', ''); } },
  CancelGameAction: id => { calls.push(['cancel', id]); fire('end', id); act = null; } } };
(async () => {
  const out = [];
  for (const e of steps) out.push(await eval(e));
  process.stdout.write(JSON.stringify({ out, calls })); process.exit(0);
})().catch(e => { process.stdout.write(JSON.stringify({ error: String(e && e.stack || e) })); process.exit(0); });
"""


def _run(opt, *steps):
    need(shutil.which("node") is not None, "node not installed (dev container, CI)")
    r = subprocess.run(["node", "-e", HARNESS], input=json.dumps([opt, list(steps)]), capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and r.stdout, r.stderr
    d = json.loads(r.stdout)
    assert "error" not in d, d["error"]
    return [CEF.parse_launch(v) if isinstance(v, str) and v.startswith('{"act') else v for v in d["out"]], d["calls"]


def test_a_game_that_needs_nothing_starts_and_its_steps_are_known():
    (st,), calls = _run({}, CEF.launch_expression(200260))
    assert calls == [["run", "200260", "", -1]], calls             # as Steam's interface calls it
    assert st["trace"] == ["UpdatingAppInfo", "CreatingProcess", "Completed"] and st["done"] and not st["request"], st


def test_a_question_comes_back_and_the_persons_answer_is_passed_on():
    (st, after, ans, later), calls = _run({"ask": "SynchronizingCloud", "details": "cloudconflict"},
                                         CEF.launch_expression(200260), CEF.launch_state_expression(200260),
                                         CEF.launch_answer_expression(200260, "KeepRemote"), CEF.launch_state_expression(200260))
    assert st["request"] == "SynchronizingCloud" and st["details"] == "cloudconflict" and st["action"] == 41, st
    assert after["request"] == "SynchronizingCloud"                 # still asked until someone answers
    assert json.loads(ans) == {"ok": True} and ["continue", 41, "KeepRemote"] in calls
    assert not later["request"] and later["trace"][-1] == "CreatingProcess", later


def test_launch_options_and_licence_and_cancel():
    (st,), _ = _run({"ask": "ShowLaunchOption"}, CEF.launch_expression(200260))
    assert st["options"] == [{"index": 0, "label": "Jugar"}, {"index": 1, "label": "Jugar en DirectX 11"}], st
    (st, ans), calls = _run({"ask": "ShowEula"}, CEF.launch_expression(200260), CEF.launch_answer_expression(200260, "ShowEula"))
    assert st["eulas"][0]["url"] == "https://store.steampowered.com/eula/200260_eula"
    assert ["accept", 200260, "200260_eula", 1] in calls and ["continue", 41, "ShowEula"] in calls
    (_st, ans), calls = _run({"ask": "RunningInstallScript"}, CEF.launch_expression(200260), CEF.launch_answer_expression(200260, "cancel"))
    assert ["cancel", 41] in calls and not any(c[0] == "continue" for c in calls)


def test_an_error_comes_back_with_steams_reason():
    (st,), _ = _run({"error": "AppError_51"}, CEF.launch_expression(200260))
    assert st["error"] == "AppError_51" and st["error_details"] == "proton" and st["trace"][-1] == "error:AppError_51", st


def test_only_steams_own_answers_reach_steam():
    for ok in ("cancel", "0", "3", "KeepLocal", "IgnoreInstallError", "ShowEula", "SkipShaders", ""):
        CEF.launch_answer_expression(620, ok)
    for bad in ("x');alert(1);('", "123", "IgnoreAll", None, 5):
        try:
            CEF.launch_answer_expression(620, bad)
            raise AssertionError(bad)
        except ValueError:
            pass
    assert CEF.launch(620, port=1) is None and CEF.launch_state(620, port=1) is None and CEF.launch_answer(620, "0", port=1) is None


def test_steam_play_for_windows_games_is_turned_on_once_and_a_persons_choice_stays():
    d = tempfile.mkdtemp(prefix="stone-steamplay-")
    try:
        os.makedirs(os.path.join(d, "config"))
        p = os.path.join(d, "config", "config.vdf")
        assert SC.ensure_steam_play(d) == "no config.vdf yet"
        with open(p, "w") as f:
            f.write('"InstallConfigStore"\n{\n\t"Software"\n\t{\n\t\t"Valve"\n\t\t{\n\t\t\t"Steam"\n\t\t\t{\n\t\t\t\t"Kept"\t\t"1"\n\t\t\t}\n\t\t}\n\t}\n}\n')
        assert SC.ensure_steam_play(d) == "turned on" and os.path.exists(p + ".stone-bak")
        steam = vdf.get_ci(vdf.load_file(p), "InstallConfigStore", "Software", "Valve", "Steam")
        assert steam["CompatToolMapping"]["0"]["name"] == SC.COMPAT_TOOL and steam["Kept"] == "1"
        assert SC.ensure_steam_play(d) == "already set"
        with open(p, "w") as f:                                   # the person chose another Proton in Steam
            f.write('"InstallConfigStore"{"Software"{"Valve"{"Steam"{"CompatToolMapping"{"0"{"name" "proton_9" "config" "" "priority" "75"}}}}}}')
        assert SC.ensure_steam_play(d) == "already set" and "proton_9" in open(p).read()
        with open(p, "w") as f:
            f.write("broken {")
        assert SC.ensure_steam_play(d).startswith("not read") and open(p).read() == "broken {"
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    run_module(globals())
