"""The JavaScript STONE runs inside Steam's interface to read the account's games and who is signed
in (steamcef.OWNED_EXPRESSION, LOGIN_EXPRESSION), run in node against stand-ins of Steam's objects.
The real objects of a given Steam build are a board test (T-LIB-11); this checks the logic: every
source is joined, tools and shortcuts are left out, and "not answering" differs from "empty".

    python3 tests/test_steam_expressions.py     (or: pytest tests/test_steam_expressions.py)
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

HARNESS = """
const [setup, expression] = JSON.parse(require('fs').readFileSync(0, 'utf8'));
globalThis.window = globalThis;
new Function(setup)();
Promise.resolve(eval(expression)).then(v => process.stdout.write(JSON.stringify({value: v === undefined ? null : v})),
                                       e => process.stdout.write(JSON.stringify({error: String(e)})));
"""

APP = "const app=(id,name,o)=>Object.assign({appid:id,display_name:name,app_type:1,BIsModOrShortcut:()=>false},o||{});"


def _run(setup, expression):
    need(shutil.which("node") is not None, "node not installed (dev container, CI)")
    r = subprocess.run(["node", "-e", HARNESS], input=json.dumps([APP + setup, expression]), capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert "error" not in out, out
    return out["value"]


def _owned(setup):
    raw = _run(setup, CEF.OWNED_EXPRESSION)
    old = CEF.ui_value
    CEF.ui_value = lambda expression, port=None: raw
    try:
        return raw, CEF.owned_games()
    finally:
        CEF.ui_value = old


def test_no_store_object_is_not_answering_and_empty_stores_are_an_empty_account():
    assert _owned("") == (None, None)
    assert _owned("window.appStore={allApps:[]};") == ("[]", [])
    assert _owned("window.collectionStore={};window.appStore={m_mapApps:new Map()};") == ("[]", [])


def test_hidden_steam_has_only_appstore_and_tools_and_shortcuts_are_left_out():
    raw, games = _owned("""
        window.appStore={m_mapApps:new Map([
          [620, app(620,'Portal 2',{per_client_data:[{clientid:'0',installed:true,bytes_downloaded:123}],minutes_playtime_forever:600,rt_last_time_played:1700000000})],
          [35140, app(35140,'Batman: Arkham Asylum',{installed:false,size_on_disk:'0'})],
          [228980, app(228980,'Steamworks Common Redistributables',{app_type:4})],
          [1493710, app(1493710,'Proton Experimental',{app_type:4})],
          [3000000000, app(3000000000,'Un emulador',{BIsModOrShortcut:()=>true,app_type:1073741824})],
          [9, null], [10, {display_name:'sin id', app_type:1}],
          [1245620, app(1245620,'Sin tipo',{app_type:undefined})]])};""")
    assert games == [(620, "Portal 2", True, 600, 1700000000, 123), (35140, "Batman: Arkham Asylum", False, 0, 0, 0),
                     (1245620, "Sin tipo", False, 0, 0, 0)], raw


def test_installed_means_on_this_console_and_games_not_owned_are_left_out():
    # Steam's entry per machine of the account: clientid "0" is this console; `installed` is the most
    # available machine's (the person's PC). Seen in Steam's code (SteamAppOverview, client 1792618285).
    _raw, games = _owned("""
        window.appStore={m_mapApps:new Map([
          [1174180, app(1174180,'Red Dead Redemption 2',{installed:true,
                    per_client_data:[{clientid:'0',installed:false},{clientid:'7656',installed:true,bytes_downloaded:9}]})],
          [570, app(570,'Dota 2',{per_client_data:[{clientid:'0',installed:true}],local_per_client_data:{clientid:'0',installed:true}})],
          [730, app(730,'Visto en la tienda',{BIsOwned:()=>false})],
          [1091500, app(1091500,'Cyberpunk 2077',{BIsOwned:()=>true,installed:true})]])};""")
    assert games == [(1174180, "Red Dead Redemption 2", False, 0, 0, 0), (570, "Dota 2", True, 0, 0, 0),
                     (1091500, "Cyberpunk 2077", True, 0, 0, 0)], games


def test_every_source_is_joined_without_repeating_a_game():
    _raw, games = _owned("""
        const portal=app(620,'Portal 2',{installed:true}), hades=app(1145360,'Hades'), celeste=app(504230,'Celeste');
        window.collectionStore={allGamesCollection:{allApps:[portal,hades]},
                                allAppsCollection:{allApps:[portal,app(431960,'Wallpaper Engine',{app_type:2})]}};
        window.appStore={allApps:[portal,celeste], m_mapApps:new Map([[620,portal],[1091500,app(1091500,'Cyberpunk 2077')]])};""")
    assert [g[0] for g in games] == [620, 1145360, 504230, 1091500]
    # a collection that exists and is still empty does not hide what appStore already has
    _raw, games = _owned("""
        window.collectionStore={allGamesCollection:{allApps:[]}};
        window.appStore={allApps:[app(620,'Portal 2')]};""")
    assert [g[0] for g in games] == [620]
    # a source that throws when read is skipped, the others still answer
    _raw, games = _owned("""
        window.collectionStore={get allGamesCollection(){return {get allApps(){throw new Error('boom');}};}};
        window.appStore={allApps:{values:()=>[app(730,'Counter-Strike 2')][Symbol.iterator]()}};""")
    assert [g[0] for g in games] == [730]


def test_who_is_signed_in():
    assert _run("", CEF.LOGIN_EXPRESSION) is None                                  # Steam's interface not loaded
    assert _run("window.App={};", CEF.LOGIN_EXPRESSION) is None                    # a build that does not say
    assert _run("window.App={m_CurrentUser:undefined};", CEF.LOGIN_EXPRESSION) == "out"
    assert _run("window.App={m_CurrentUser:{strSteamID:'0'}};", CEF.LOGIN_EXPRESSION) == "out"
    assert _run("window.App={m_CurrentUser:{strSteamID:''}};", CEF.LOGIN_EXPRESSION) == "out"
    assert _run("window.App={m_CurrentUser:{strSteamID:'76561198000000001'}};", CEF.LOGIN_EXPRESSION) == "in"
    assert _run("window.App={get m_CurrentUser(){throw new Error('x');}};", CEF.LOGIN_EXPRESSION) is None


STEAM_APPS = """
const calls=[];const det={620:{strResolutionOverride:'Default'},730:{strResolutionOverride:'1280x800'},570:{},440:null};
window.SteamClient={Apps:{
  RegisterForAppDetails:(id,cb)=>{calls.push(['details',id]);if(det[id]!==null)setTimeout(()=>cb(det[id]),5);return {unregister(){calls.push(['unregister',id]);}};},
  SetAppResolutionOverride:(id,v)=>calls.push(['set',id,v]),
  TerminateApp:(g,b)=>calls.push(['terminate',g,b])},
 Downloads:{EnableAllDownloads:(on,c)=>calls.push(['all',on,c]),ResumeAppUpdate:(id,c)=>calls.push(['resume',id,c])}};
window.calls=calls;"""


def test_game_resolution_is_read_from_the_games_details_as_steam_does():
    sys.path.insert(0, os.path.join(REPO, "modules", "display"))
    from stone_display import steam as D
    # Steam's interface reads strResolutionOverride from RegisterForAppDetails (absent: "Default");
    # 3.1.0-rc4 called GetResolutionOverrideForApp, which Steam's interface never calls.
    out = json.loads(_run(STEAM_APPS, D.ensure_native_expression([620, 730, 570, 440]).replace(
        "return JSON.stringify({changed:ch,kept:kept});", "return JSON.stringify({changed:ch,kept:kept,calls});")))
    assert out["changed"] == [570, 620] and out["kept"] == {"730": "1280x800"}, out          # 440: no details, left alone
    assert ["set", 620, "Native"] in out["calls"] and not [c for c in out["calls"] if c[0] == "set" and c[1] in (730, 440)]


def test_closing_a_game_and_pausing_downloads_use_steams_own_calls():
    js = STEAM_APPS + "window.downloadsStore={LocalDownloadOverview:{update_appid:620,paused:true}};"
    assert _run(js, CEF.terminate_expression(620) + "&&JSON.stringify(calls)") == '[["terminate","620",false]]'
    assert _run(js, CEF.download_control_expression(620, "pause") + "&&JSON.stringify(calls)") == '[["all",false,"0"]]'
    assert _run(js, CEF.download_control_expression(620, "resume") + "&&JSON.stringify(calls)") == '[["all",true,"0"],["resume",620,"0"]]'
    running = STEAM_APPS + "window.downloadsStore={LocalDownloadOverview:{update_appid:570,paused:false}};"
    assert _run(running, CEF.download_control_expression(620, "resume") + "&&JSON.stringify(calls)") == '[["resume",620,"0"]]'
    assert _run("", CEF.terminate_expression(620)) is None                          # Steam's interface not loaded
    for bad in (0, -1, 2**64):
        try:
            CEF.terminate_expression(bad)
            raise AssertionError(bad)
        except ValueError:
            pass


if __name__ == "__main__":
    sys.exit(run_module(globals()))
