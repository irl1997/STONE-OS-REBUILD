"""Ask Steam's own interface to start a game, as Decky Loader does in Game Mode.

On the board (RC3, 25-10-2026) Steam logged `ExecuteSteamURL: "steam://rungameid/<id>"` for
every request with the right id and still never started the STONE shortcut: in Game Mode
steam://rungameid does not start non-Steam shortcuts. Steam's interface does, through
SteamClient.Apps.RunGame, reachable over Chromium's remote debugging protocol, which Steam
exposes on 127.0.0.1:8080 when `<Steam>/.cef-enable-remote-debugging` exists at its start.

Only the standard library is used: one HTTP GET for the list of pages and a minimal
WebSocket client for a single Runtime.evaluate call.
"""

import base64
import json
import os
import socket
import struct
import urllib.parse
import urllib.request

PORT = int(os.environ.get("STONE_STEAM_CEF_PORT", "8080"))
FLAG = ".cef-enable-remote-debugging"
# Pages of Steam's interface that carry the SteamClient object, most suitable first.
PREFERRED_TITLES = ("SharedJSContext", "Steam Shared Context presented by Valve™", "Steam Big Picture Mode", "Steam")


def enable(steam_root):
    """Create the flag file Steam reads at start. Returns True if it is there."""
    path = os.path.join(steam_root, FLAG)
    if os.path.exists(path):
        return True
    try:
        with open(path, "w"):
            pass
        return True
    except OSError:
        return False


def targets(port=PORT, timeout=2.0):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8", "replace"))
    return data if isinstance(data, list) else []


def candidates(pages):
    """Every page that may carry SteamClient, most suitable first (Steam names its pages by
    version, so a title alone cannot be relied on)."""
    usable = [p for p in pages if isinstance(p, dict) and p.get("webSocketDebuggerUrl")]
    out = []
    for title in PREFERRED_TITLES:
        out += [p for p in usable if p.get("title") == title and p not in out]
    out += [p for p in usable if "steamloopback.host" in str(p.get("url", "")) and p not in out]
    out += [p for p in usable if p not in out]
    return out


def pick(pages):
    """The page to run SteamClient calls in, or None."""
    usable = candidates(pages)
    for p in usable:
        if p.get("title") in PREFERRED_TITLES or "steamloopback.host" in str(p.get("url", "")):
            return p
    return None


def _recv_exact(s, n):
    buf = b""
    while len(buf) < n:
        chunk = s.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("connection closed")
        buf += chunk
    return buf


def _send_text(s, text):
    payload = text.encode("utf-8")
    mask = os.urandom(4)
    head = bytearray([0x81])
    n = len(payload)
    if n < 126:
        head.append(0x80 | n)
    elif n < 65536:
        head.append(0x80 | 126)
        head += struct.pack(">H", n)
    else:
        head.append(0x80 | 127)
        head += struct.pack(">Q", n)
    s.sendall(bytes(head) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))


def _recv_message(s):
    """One complete text message (fragments joined); control frames skipped."""
    parts = []
    while True:
        b0, b1 = _recv_exact(s, 2)
        n = b1 & 0x7F
        if n == 126:
            n = struct.unpack(">H", _recv_exact(s, 2))[0]
        elif n == 127:
            n = struct.unpack(">Q", _recv_exact(s, 8))[0]
        mask = _recv_exact(s, 4) if b1 & 0x80 else None
        data = _recv_exact(s, n)
        if mask:
            data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        op = b0 & 0x0F
        if op == 0x8:
            raise ConnectionError("closed by Steam")
        if op in (0x9, 0xA):          # ping / pong
            continue
        parts.append(data)
        if b0 & 0x80:
            return b"".join(parts).decode("utf-8", "replace")


def evaluate(ws_url, expression, timeout=5.0):
    """Runtime.evaluate in one page; returns the result value (or raises)."""
    u = urllib.parse.urlparse(ws_url)
    if u.scheme != "ws" or u.hostname not in ("127.0.0.1", "localhost"):
        raise ValueError(f"refusing non-local debugger url {ws_url}")
    s = socket.create_connection((u.hostname, u.port or 80), timeout=timeout)
    try:
        key = base64.b64encode(os.urandom(16)).decode()
        s.sendall((f"GET {u.path} HTTP/1.1\r\nHost: {u.hostname}:{u.port}\r\nUpgrade: websocket\r\n"
                   f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = s.recv(1024)
            if not chunk:
                raise ConnectionError("no handshake answer")
            head += chunk
        if b" 101 " not in head.split(b"\r\n", 1)[0]:
            raise ConnectionError(head.split(b"\r\n", 1)[0].decode(errors="replace"))
        _send_text(s, json.dumps({"id": 1, "method": "Runtime.evaluate",
                                  "params": {"expression": expression, "awaitPromise": True, "returnByValue": True}}))
        while True:
            msg = json.loads(_recv_message(s))
            if msg.get("id") == 1:
                if "error" in msg:
                    raise RuntimeError(msg["error"].get("message", "error"))
                res = msg.get("result", {})
                if res.get("exceptionDetails"):
                    raise RuntimeError(res["exceptionDetails"].get("text", "exception"))
                return res.get("result", {}).get("value")
    finally:
        s.close()


def run_game_expression(game_id):
    gid = str(int(game_id))           # digits only: nothing else reaches Steam's interface
    return ("(async()=>{if(!window.SteamClient||!SteamClient.Apps||!SteamClient.Apps.RunGame)"
            "return 'no SteamClient';"
            f"SteamClient.Apps.RunGame('{gid}','',-1,100);return 'ok';}})()")


def ui_eval(expression, port=PORT):
    """Run one fixed expression in Steam's interface. Returns a short status, never raises."""
    try:
        pages = targets(port)
        page = pick(pages) or (candidates(pages) or [None])[0]
    except (OSError, ValueError) as e:
        return f"cef unavailable ({e.__class__.__name__})"
    if not page:
        return "cef: no Steam page yet"
    try:
        return f"cef[{page.get('title', '?')}]: {evaluate(page['webSocketDebuggerUrl'], expression)}"
    except (OSError, ValueError, RuntimeError) as e:
        return f"cef error: {e}"


def run_game(game_id, port=PORT):
    """Ask Steam's interface to start game_id (a Steam app id or a shortcut's 64-bit game id)."""
    return ui_eval(run_game_expression(game_id), port)


# Sections of Steam's own settings (SettingsSection_t in decky-frontend-lib) STONE may open.
SETTINGS_SECTIONS = ("Display", "Audio", "Controller", "Internet", "Bluetooth", "Storage", "System",
                     "Power", "Accessibility", "Keyboard", "Downloads")
PAGES = ("Downloads",)

# Steam's interface: the focused window (or the Game Mode main window) and its navigator.
# The main menu is opened first so Steam's interface comes over the running app (STONE is
# itself the "game" Steam is showing), then menus are closed after navigating, as Decky does.
_NAV = ("const S=window.SteamUIStore;if(!S)return 'no SteamUIStore';let w=null;"
        "try{w=S.GetFocusedWindowInstance();}catch(e){}"
        "const main=S.WindowStore&&S.WindowStore.GamepadUIMainWindowInstance;"
        "if(!w||!(w.Navigator||w.m_Navigator))w=main||w;"
        "const n=w&&(w.Navigator||w.m_Navigator);if(!n)return 'no Navigator';"
        "const m=w.MenuStore;try{m&&m.OpenMainMenu&&m.OpenMainMenu();}catch(e){}")


def open_settings_expression(section):
    if section not in SETTINGS_SECTIONS:
        raise ValueError("unknown settings section")
    return ("(async()=>{" + _NAV + f"if(!n.Settings)return 'no Settings';n.Settings('{section}');"
            "await new Promise(r=>setTimeout(r,150));try{m&&m.CloseSideMenus&&m.CloseSideMenus();}catch(e){}"
            "return 'ok';})()")


def open_page_expression(page):
    if page not in PAGES:
        raise ValueError("unknown page")
    return ("(async()=>{" + _NAV + f"if(!n.{page})return 'no {page}';n.{page}();"
            "await new Promise(r=>setTimeout(r,150));try{m&&m.CloseSideMenus&&m.CloseSideMenus();}catch(e){}"
            "return 'ok';})()")


def open_settings(section, port=PORT):
    return ui_eval(open_settings_expression(section), port)


def open_page(page, port=PORT):
    return ui_eval(open_page_expression(page), port)


def ui_value(expression, port=PORT, timeout=10.0):
    """Like ui_eval, but returns the value itself; None if no Steam page answers. Pages are
    tried in order of suitability, because the page that carries SteamClient is not always the
    one Steam lists first."""
    for _title, value, err in ui_values(expression, port, timeout=timeout):
        if err is None and value is not None:
            return value
    return None


def ui_values(expression, port=PORT, limit=8, timeout=10.0):
    """[(page title, value or None, error or None)] running the expression in each candidate page,
    stopping at the first page that returns a value. Never raises."""
    try:
        pages = candidates(targets(port))[:limit]
    except (OSError, ValueError) as e:
        return [("-", None, f"cef unavailable ({e.__class__.__name__})")]
    if not pages:
        return [("-", None, "no Steam page yet")]
    out = []
    for page in pages:
        try:
            v = evaluate(page["webSocketDebuggerUrl"], expression, timeout=timeout)
            out.append((page.get("title", "?"), v, None))
            if v is not None:
                break
        except (OSError, ValueError, RuntimeError) as e:
            out.append((page.get("title", "?"), None, f"{e.__class__.__name__}: {e}"))
    return out


# Names (never values) of what this Steam build offers, for STONE's Steam settings layer.
API_PROBE = (
    "(()=>{const o={has:!!window.SteamClient,tree:{}};if(!o.has)return JSON.stringify(o);let n=0;"
    "const names=x=>{const s=new Set();try{for(const k of Object.keys(x))s.add(k);let p=Object.getPrototypeOf(x);"
    "while(p&&p!==Object.prototype){for(const k of Object.getOwnPropertyNames(p))if(k!=='constructor')s.add(k);p=Object.getPrototypeOf(p);}}catch(e){}"
    "return [...s].sort();};"
    "const walk=(x,d)=>{const r={};for(const k of names(x)){if(n++>4000)break;let v;try{v=x[k];}catch(e){continue;}"
    "if(typeof v==='function')r[k]='f'+v.length;else if(v&&typeof v==='object'&&d>0)r[k]=walk(v,d-1);}return r;};"
    "o.tree=walk(window.SteamClient,3);return JSON.stringify(o);})()")


def probe(port=PORT):
    """Run API_PROBE in every candidate page: [{title, url, has_steamclient, tree, error}]."""
    try:
        pages = candidates(targets(port))[:12]
    except (OSError, ValueError) as e:
        return [{"title": "-", "error": f"cef unavailable ({e.__class__.__name__})"}]
    out = []
    for page in pages:
        row = {"title": page.get("title", "?"), "url": str(page.get("url", ""))[:120]}
        try:
            raw = evaluate(page["webSocketDebuggerUrl"], API_PROBE, timeout=10.0)
            d = json.loads(raw) if isinstance(raw, str) else {}
            row["has_steamclient"] = bool(d.get("has"))
            row["tree"] = d.get("tree") or {}
        except (OSError, ValueError, RuntimeError) as e:
            row["error"] = f"{e.__class__.__name__}: {e}"
        out.append(row)
    return out


# Every game in the Steam account, installed or not (the library on disk only has installed
# ones). Fields: appid, name, installed, minutes played, last played (unix), size on disk.
# Every source this Steam build has is read and joined: Big Picture's collectionStore (all games,
# all apps) and appStore, which the client also loads when Steam runs hidden (-silent, the STONE
# session) and collectionStore may not exist (rc1 on the board: games of the account missing from
# the library). appStore also holds tools and DLC: games only. Returns null when Steam has no
# store object yet (not answering), "[]" when it has them and they are empty (loading, signed out).
# Installed means installed on THIS console: Steam keeps one entry per machine of the account in
# per_client_data, "0" being the local one (its own getter local_per_client_data); its `installed` is
# the most available machine's, which may be another PC (3.1.0-rc4: a game installed on the person's
# PC was neither installed nor "in the account" here, so it vanished from the library). Apps the
# account does not own (BIsOwned: visible_in_game_list && subscribed_to) are not listed, as in Steam.
OWNED_EXPRESSION = (
    "(async()=>{const cs=window.collectionStore,A=window.appStore;if(!cs&&!A)return null;"
    "const lists=[];const add=f=>{try{const x=f();if(!x)return;"
    "const a=Array.isArray(x)?x:(typeof x.values==='function'?[...x.values()]:[...x]);"
    "if(a&&a.length)lists.push(a);}catch(e){}};"
    "if(cs){add(()=>cs.allGamesCollection.allApps);add(()=>cs.allAppsCollection.allApps);}"
    "if(A){add(()=>A.allApps);add(()=>A.m_mapApps);}"
    "const seen=new Set(),o=[];"
    "for(const src of lists)for(const a of src){if(!a||typeof a.appid!=='number'||seen.has(a.appid))continue;"
    "if(!(a.app_type===1||a.app_type===undefined))continue;"
    "try{if(a.BIsModOrShortcut&&a.BIsModOrShortcut())continue;}catch(e){}"
    "try{if(a.BIsOwned&&!a.BIsOwned())continue;}catch(e){}"
    "seen.add(a.appid);let lp=null;try{lp=a.local_per_client_data||null;}catch(e){}"
    "if(!lp&&Array.isArray(a.per_client_data))lp=a.per_client_data.find(c=>c&&String(c.clientid)==='0')||null;"
    "o.push([a.appid,String(a.display_name||''),!!(lp?lp.installed:(a.per_client_data?false:a.installed)),"
    "a.minutes_playtime_forever||0,a.rt_last_time_played||0,Number(a.size_on_disk||(lp&&lp.bytes_downloaded)||0)]);}"
    "return JSON.stringify(o);})()")

# Whether someone is signed in to Steam: "in", "out", or null when this Steam build does not say.
LOGIN_EXPRESSION = (
    "(()=>{try{const A=window.App;if(!A||!('m_CurrentUser' in A))return null;const u=A.m_CurrentUser;"
    "const id=u?String(u.strSteamID||''):'';return /^[1-9][0-9]{4,19}$/.test(id)?'in':'out';}catch(e){return null;}})()")


def login_state(port=PORT):
    """"in", "out" or None (Steam's interface does not answer, or does not say)."""
    v = ui_value(LOGIN_EXPRESSION, port)
    return v if v in ("in", "out") else None


def owned_games(port=PORT):
    """[(appid, name, installed, minutes, last_played, size)] or None if Steam does not answer."""
    raw = ui_value(OWNED_EXPRESSION, port)
    if not isinstance(raw, str):
        return None
    try:
        rows = json.loads(raw)
    except ValueError:
        return None
    out = []
    for r in rows if isinstance(rows, list) else []:
        if (isinstance(r, list) and len(r) == 6 and isinstance(r[0], int) and 0 < r[0] < 0x80000000
                and isinstance(r[1], str)):
            out.append((r[0], r[1][:200], bool(r[2]), int(r[3] or 0), int(r[4] or 0), int(r[5] or 0)))
    return out


# Steam's install wizard, step by step. Everything here is what Steam's own interface does, read from
# its code (steamui/sp.js and library.js of the client package of 12-11-2026, client-update.steamstatic.com):
#   SteamClient.Installs.OpenInstallWizard([appid], "0")     "0" is the local client: Steam can also
#                                                            install on another of the person's machines
#   SteamClient.Installs.RegisterForShowInstallWizard(cb)    cb(info) at every step; info.eInstallState,
#                                                            info.rgApps [{nAppID}], disk space, folder
#   SetInstallFolder(i) / ContinueInstall() / CancelInstall()
#   SteamClient.Apps.LoadEula(appid) -> [{id, version, url}] and MarkEulaAccepted(appid, id, version)
#   SteamClient.Installs.OpenUninstallWizard([appid], "0", true)
# 3.1.0-rc3 called OpenInstallWizard with one argument and looked for the app in "rgAppIDs", which does
# not exist: on the board (12-11-2026) every install ended in "Steam no respondió".
INSTALL_STATES = {0: "none", 1: "setup", 2: "wait-license", 3: "free-license", 4: "cd-key", 5: "wait-appinfo",
                  6: "password", 7: "config", 8: "eula", 9: "create-apps", 10: "read-media", 11: "change-media",
                  12: "wait-legacy-keys", 13: "signup", 14: "complete", 15: "failed", 16: "canceled"}
INSTALL_ANSWERS = ("started", "gone", "failed", "canceled", "eula", "asks", "space", "timeout", "nowizard", "error")
LOCAL_CLIENT = "0"

# Shared by the install and by the licence acceptance: the wizard's steps are noted as Steam tells them
# (the callback) and, where this build still has it, asked for (GetInstallManagerInfo). No call can hang
# the answer: each one races a timer. `out` always gives the steps seen (tr), for the console's own log.
_WIZARD = (
    "const I=window.SteamClient&&SteamClient.Installs;"
    "if(!I||!I.OpenInstallWizard||!I.ContinueInstall)return null;"
    "const z=ms=>new Promise(r=>setTimeout(r,ms));const tr=[];let last=null,reg=null;"
    "const note=d=>{if(!d||typeof d.eInstallState!=='number')return;last=d;"
    "if(tr[tr.length-1]!==d.eInstallState)tr.push(d.eInstallState);};"
    "try{if(I.RegisterForShowInstallWizard)reg=I.RegisterForShowInstallWizard(note);}catch(e){}"
    "const poll=async()=>{if(!I.GetInstallManagerInfo)return;"
    "try{note(await Promise.race([I.GetInstallManagerInfo(),z(1500)]));}catch(e){}};"
    "const out=(s,x)=>{try{reg&&reg.unregister&&reg.unregister();}catch(e){}"
    "return JSON.stringify(Object.assign({s:s,st:last?last.eInstallState:null,tr:tr.slice(-16),"
    "need:last?Number(last.nDiskSpaceRequired)||0:0,free:last?Number(last.nDiskSpaceAvailable)||0:0},x||{}));};"
    # follow(A, pushed, grace): until Steam has started the install, or asks what only the person can
    # answer. A finished state only counts after a live one was seen: the wizard keeps its last state.
    "const follow=async(A,pushed,grace)=>{let folder=false,live=pushed>0;"
    "for(let i=0;i<110;i++){await z(250);if(i%4===0||!last)await poll();const d=last;if(!d)continue;"
    "const st=d.eInstallState;if(st>0&&st<14)live=true;"
    "if(st===14&&live)return out('started');"
    "if(st===15&&live)return out('failed',{err:Number(d.eAppError)||0,detail:String(d.errorDetail||'').slice(0,160)});"
    "if(st===16&&live)return out('canceled');"
    "if(st===0&&pushed>0&&i>=grace)return out('gone');"
    "if(st===8){if(i<grace)continue;let eu=[];"
    "try{const v=await Promise.race([SteamClient.Apps.LoadEula(A),z(4000)]);"
    "eu=[...(v||[])].slice(0,6).map(x=>({id:String(x.id==null?'':x.id).slice(0,64),version:Number(x.version)||0,"
    "url:String(x.url||'').slice(0,300)}));}catch(e){}"
    "return out('eula',{eulas:eu});}"
    "if(st===4||st===6||st===11||st===12||st===13)return out('asks');"
    "if(st===7){const apps=[...(d.rgApps||d.rgAppIDs||[])].map(x=>x&&x.nAppID);"
    "if(apps.length&&apps.indexOf(A)<0&&d.currentAppID!==A)return out('error',{detail:'another install is open in Steam'});"
    "if(d.nDiskSpaceRequired>0&&d.nDiskSpaceAvailable>0&&d.nDiskSpaceRequired>d.nDiskSpaceAvailable)"
    "{try{I.CancelInstall();}catch(e){}return out('space');}"
    "if(!folder){folder=true;if(!(d.iInstallFolder>=0)){try{note(await Promise.race([I.SetInstallFolder(0),z(1500)]));}catch(e){}}}"
    "if(pushed<4){pushed++;try{note(await Promise.race([I.ContinueInstall(),z(1500)]));}"
    "catch(e){return out('error',{detail:String(e).slice(0,160)});}await z(500);}}"
    "else if(st===3&&pushed<4){pushed++;try{note(await Promise.race([I.ContinueInstall(),z(1500)]));}catch(e){}await z(500);}}"
    "return out(tr.length?'timeout':'nowizard');};")


def _appid(appid):
    a = int(appid)
    if not 0 < a < 0x80000000:
        raise ValueError("not a Steam app id")
    return a


def install_expression(appid):
    """Install without showing Steam's dialog: in the STONE session Steam's interface is hidden behind
    STONE Home. Steam's install wizard is opened as Steam's own interface opens it and followed until
    Steam has started the install or asks something only the person can answer: a licence agreement
    (its address comes back, STONE shows it and passes the acceptance on: accept_eula_expression), a
    key, a password, a disc. A full disk comes back with its figures. Only two steps are taken for the
    person, the ones Steam's own interface takes by itself on a console: the install folder and the
    free licence of the free game they asked for. Returns null where this page has no SteamClient (the
    next page is tried), else a JSON answer with the steps seen."""
    a = _appid(appid)
    return ("(async()=>{" + _WIZARD +
            # a wizard left open by an earlier request (or by Steam itself) would swallow this one
            "await poll();if(last&&last.eInstallState>0&&last.eInstallState<14){try{I.CancelInstall();}catch(e){}await z(500);}"
            "tr.length=0;last=null;"
            f"try{{I.OpenInstallWizard([{a}],'{LOCAL_CLIENT}');}}catch(e){{return out('error',{{detail:String(e).slice(0,160)}});}}"
            f"return await follow({a},0,0);}})()")


def accept_eula_expression(appid):
    """The person read the game's licence agreement in STONE and accepted it: every agreement Steam
    lists for the game is marked accepted, as Steam's own dialog does, and the waiting wizard goes on."""
    a = _appid(appid)
    return ("(async()=>{" + _WIZARD +
            "await poll();let v=[];"
            f"try{{v=[...(await Promise.race([SteamClient.Apps.LoadEula({a}),z(4000)])||[])];}}catch(e){{}}"
            f"for(const x of v){{try{{SteamClient.Apps.MarkEulaAccepted({a},x.id,x.version);}}"
            "catch(e){return out('error',{detail:String(e).slice(0,160)});}}"
            "await z(300);try{note(await Promise.race([I.ContinueInstall(),z(1500)]));}"
            "catch(e){return out('error',{detail:String(e).slice(0,160)});}"
            f"return await follow({a},1,8);}})()")


def _eulas(rows):
    out = []
    for r in rows if isinstance(rows, list) else []:
        if not isinstance(r, dict) or not isinstance(r.get("url"), str):
            continue
        url = r["url"].replace("http://", "https://", 1)
        if not url.startswith("https://") or len(url) > 300 or any(c in url for c in " \"'<>\\\n\r"):
            continue
        out.append({"id": str(r.get("id") or "")[:64], "version": int(r.get("version") or 0), "url": url})
    return out[:6]


def parse_install(raw):
    """Steam's answer to install_expression as a dict, or None (no page with SteamClient answered).
    "trace": the wizard's steps by name, e.g. ["setup", "wait-appinfo", "config"]."""
    try:
        d = json.loads(raw) if isinstance(raw, str) else None
    except ValueError:
        return None
    if not isinstance(d, dict) or d.get("s") not in INSTALL_ANSWERS:
        return None
    st = d.get("st")
    out = {"answer": d["s"], "state": INSTALL_STATES.get(st) if isinstance(st, int) else None,
           "trace": [INSTALL_STATES.get(x, str(x)) for x in (d.get("tr") or []) if isinstance(x, int)][:16]}
    for k in ("need", "free", "err"):
        if isinstance(d.get(k), (int, float)) and d[k] >= 0:
            out[k] = int(d[k])
    if isinstance(d.get("detail"), str) and d["detail"]:
        out["detail"] = d["detail"][:160]
    if d["s"] == "eula":
        out["eulas"] = _eulas(d.get("eulas"))
    return out


def install(appid, port=PORT):
    """Steam's answer ({"answer": started|gone|failed|canceled|eula|asks|space|timeout|nowizard|error,
    "trace": [...], ...}) or None when Steam's interface does not answer (not up, or its remote
    debugging is off)."""
    return parse_install(ui_value(install_expression(appid), port, timeout=45.0))


def accept_eula(appid, port=PORT):
    return parse_install(ui_value(accept_eula_expression(appid), port, timeout=45.0))


CANCEL_INSTALL_EXPRESSION = ("(()=>{const I=window.SteamClient&&SteamClient.Installs;"
                             "if(!I||!I.CancelInstall)return null;I.CancelInstall();return 'ok';})()")


def cancel_install(port=PORT):
    """Close Steam's install wizard (the person said no to what it asked). True if Steam answered."""
    return ui_value(CANCEL_INSTALL_EXPRESSION, port) == "ok"


def uninstall_expression(appid):
    """Uninstall without Steam's dialog (STONE asked first); Steam keeps cloud saves as always.
    Three arguments, as Steam's interface calls it: the games, the local client, "do not ask"."""
    a = _appid(appid)
    return ("(async()=>{const I=window.SteamClient&&SteamClient.Installs;"
            "if(!I||!I.OpenUninstallWizard)return null;"
            f"I.OpenUninstallWizard([{a}],'{LOCAL_CLIENT}',true);return 'ok';}})()")


def uninstall(appid, port=PORT):
    """True when Steam took the request (the files are then removed by Steam), None if its
    interface does not answer."""
    return True if ui_value(uninstall_expression(appid), port) == "ok" else None


# ---- Steam's downloads, live (the bar in STONE Home) ------------------------------------------
# Steam's interface keeps what it is downloading in window.downloadsStore: the overview of the local
# client ("0") with the app being updated, its state ("Downloading", "Preallocating", "Unpacking",
# "None"), the bytes of each stage (EAppUpdateProgress: 0 verifying installed files, 1 preallocating,
# 2 download, 3 staging, 4 verifying staged files, 5 copying, 6 committing), the speed and the time
# left; and the queue. The appmanifest on disk has the same bytes, but written only now and then.
STAGES = ("verify", "prealloc", "download", "install", "verify", "install", "install")
DOWNLOADS_EXPRESSION = (
    "(()=>{const S=window.downloadsStore;if(!S)return null;let o=null,q=[];"
    "try{o=S.LocalDownloadOverview||null;}catch(e){}"
    f"try{{if(!o&&S.m_DownloadOverview&&S.m_DownloadOverview.get)o=S.m_DownloadOverview.get('{LOCAL_CLIENT}')||null;}}catch(e){{}}"
    f"try{{const m=S.m_DownloadItems,a=m&&m.get?m.get('{LOCAL_CLIENT}'):null;"
    "if(a)q=[...a].slice(0,40).map(x=>[x.appid|0,x.active?1:0,x.completed?1:0,x.paused?1:0,Number(x.queue_index)||0]);}catch(e){}"
    "const p=o&&o.progress?[...o.progress].slice(0,7).map(x=>[Number(x.bytes_in_progress)||0,Number(x.bytes_total)||0]):[];"
    "return JSON.stringify({a:o?o.update_appid|0:0,s:o?String(o.update_state||''):'',pa:!!(o&&o.paused),"
    "r:o?Number(o.update_network_bytes_per_second)||0:0,eta:o?Number(o.overall_estimated_time_remaining_sec):-1,"
    "pct:o?Number(o.overall_percent_complete)||0:0,p:p,q:q});})()")


def parse_downloads(raw):
    """Steam's live downloads as {"appid", "state", "paused", "rate", "eta", "percent", "progress",
    "queue"} or None. "progress": [[bytes done, bytes total] per stage]; "queue": [{"appid", "active",
    "completed", "paused", "index"}]."""
    try:
        d = json.loads(raw) if isinstance(raw, str) else None
    except ValueError:
        return None
    if not isinstance(d, dict):
        return None

    def num(v, lo=0, hi=2**53):
        return int(v) if isinstance(v, (int, float)) and lo <= v <= hi else 0
    prog = [[num(x[0]), num(x[1])] for x in (d.get("p") or []) if isinstance(x, list) and len(x) == 2][:7]
    queue = [{"appid": num(x[0], 1, 0x7FFFFFFF), "active": bool(x[1]), "completed": bool(x[2]), "paused": bool(x[3]),
              "index": num(x[4])} for x in (d.get("q") or []) if isinstance(x, list) and len(x) == 5][:40]
    eta = d.get("eta")
    pct = d.get("pct")
    return {"appid": num(d.get("a"), 0, 0x7FFFFFFF), "state": str(d.get("s") or "")[:24], "paused": bool(d.get("pa")),
            "rate": num(d.get("r")), "eta": int(eta) if isinstance(eta, (int, float)) and 0 <= eta < 10**7 else None,
            "percent": float(pct) if isinstance(pct, (int, float)) and 0 <= pct <= 100 else 0.0,
            "progress": prog, "queue": [q for q in queue if q["appid"]]}


def downloads_state(port=PORT):
    """What Steam is downloading now, live, or None (its interface does not answer)."""
    return parse_downloads(ui_value(DOWNLOADS_EXPRESSION, port, timeout=4.0))


def stage_of(live):
    """The stage of the app Steam is updating, in STONE's words: "prealloc", "download", "install",
    "verify", or None (nothing in progress). Steam's state names first, then the stage with bytes left."""
    if not live or not live.get("appid"):
        return None
    state = live.get("state")
    if state == "Preallocating":
        return "prealloc"
    if state == "Unpacking":
        return "install"
    prog = live.get("progress") or []
    for i in (2, 3, 5, 6, 4, 0, 1):
        if i < len(prog) and prog[i][1] > 0 and prog[i][0] < prog[i][1]:
            return STAGES[i]
    return "download" if state == "Downloading" else "install"


# ---- Starting a game, followed step by step ----------------------------------------------------
# Steam starts a game as a "game action" and tells every step to its interface (its own code, client
# package of 12-11-2026): RegisterForGameAction{Start,TaskChange,UserRequest,ShowError,End}, with
# (actionID, gameid, "LaunchApp", task|request|error, details). Some steps wait for the person
# (UserRequest): a launch option, a licence agreement, saves in the cloud that do not match, an install
# script that failed, another session playing... Steam's interface answers with
# SteamClient.Apps.ContinueGameAction(actionID, answer) or CancelGameAction(actionID). In the STONE
# session those questions open in Steam's hidden windows, so the game waited for ever (board,
# 13-11-2026: Batman: Arkham City "SIGUE CARGANDO"). STONE listens to the same steps (one listener,
# kept on window.__stoneGA in Steam's page), says them on the loading screen, asks the questions itself
# and passes the person's answer on.
LAUNCH_ANSWERS = {          # request -> answers STONE may pass on (Steam's own words, from its code)
    "ShowEula": ("ShowEula",), "ShowLaunchOption": None,             # None: a launch option index
    "SynchronizingCloud": ("KeepLocal", "KeepRemote", "IgnoreCloud", "IgnorePendingCloudSessions"),
    "SynchronizingControllerConfig": ("KeepLocal", "KeepRemote", "IgnoreCloud"),
    "RunningInstallScript": ("IgnoreInstallError",), "KickingOtherSession": ("KickOtherSession",),
    "ProcessingShaderCache": ("SkipShaders",), "ShowCDKey": ("",), "ShowDurationControl": ("",),
    "ShowInterstitials": ("ShowInterstitials",), "ShowGameArgs": ("ShowGameArgs",), "CreatingProcess": ("CreatingProcess",),
    "ShowVROculusOnly": ("1",)}
_GA = (
    "const A=window.SteamClient&&SteamClient.Apps;if(!A||!A.RunGame)return null;"
    "const z=ms=>new Promise(r=>setTimeout(r,ms));"
    "if(!window.__stoneGA){const W=window.__stoneGA={g:{}};"
    "const at=(gid,id)=>{gid=String(gid);let e=W.g[gid];if(!e||(id&&e.act&&e.act!==id&&e.done))"
    "e=W.g[gid]={act:id||0,tr:[],req:null,det:'',err:null,errd:'',done:false,t:Date.now()};if(id&&!e.act)e.act=id;return e;};"
    "W.at=at;const on=(f,cb)=>{try{if(A[f])A[f](cb);}catch(e){}};"
    "on('RegisterForGameActionStart',(id,gid,n)=>{if(n==='LaunchApp')at(gid,id);});"
    "on('RegisterForGameActionTaskChange',(id,gid,n,t,d)=>{if(n!=='LaunchApp')return;const e=at(gid,id);"
    "if(e.tr[e.tr.length-1]!==t)e.tr.push(String(t).slice(0,40));if(e.tr.length>24)e.tr.shift();e.det=String(d||'').slice(0,160);"
    "if(e.req&&t!==e.req)e.req=null;});"
    "on('RegisterForGameActionUserRequest',(id,gid,n,r,d)=>{if(n!=='LaunchApp')return;const e=at(gid,id);"
    "e.req=String(r).slice(0,40);e.det=String(d||'').slice(0,160);e.tr.push('ask:'+e.req);});"
    "on('RegisterForGameActionShowError',(id,gid,n,er,d)=>{if(n!=='LaunchApp')return;const e=at(gid,id);"
    "e.err=String(er).slice(0,40);e.errd=String(d||'').slice(0,160);e.tr.push('error:'+e.err);});"
    "on('RegisterForGameActionEnd',id=>{for(const k in W.g){if(W.g[k].act===id){W.g[k].done=true;W.g[k].req=null;}}});}"
    "const W=window.__stoneGA;"
    # what Steam says now about this game's action (also when STONE Home was restarted meanwhile)
    "const state=async G=>{const e=W.at(G);try{const acts=await Promise.race([A.GetActiveGameActions(),z(1500)])||[];"
    "const a=acts.find(x=>String(x.gameid)===G&&x.strActionName==='LaunchApp');"
    "if(a){e.act=a.nGameActionID;if(a.strTaskName&&e.tr.indexOf(String(a.strTaskName))<0)e.tr.push(String(a.strTaskName).slice(0,40));"
    "if(a.bWaitingForUI&&!e.req){e.req=String(a.strTaskName).slice(0,40);e.det=String(a.strTaskDetails||'').slice(0,160);}"
    "e.num=Number(a.strNumDone)||0;e.tot=Number(a.strNumTotal)||0;}else if(e.act&&!e.done&&acts.length>=0&&Date.now()-e.t>3000)e.done=true;}catch(x){}"
    "let opts=null,eulas=null;const appid=Number(G)<2**32?Number(G):0;"
    "if(e.req==='ShowLaunchOption'&&appid){try{opts=[...(await Promise.race([A.GetLaunchOptionsForApp(appid),z(2000)])||[])].slice(0,8)"
    ".map(o=>({i:Number(o.nIndex)||0,d:String(o.strDescription||o.strGameName||'').slice(0,80)}));}catch(x){}}"
    "if(e.req==='ShowEula'&&appid){try{eulas=[...(await Promise.race([A.LoadEula(appid),z(4000)])||[])].slice(0,6)"
    ".map(x=>({id:String(x.id==null?'':x.id).slice(0,64),version:Number(x.version)||0,url:String(x.url||'').slice(0,300)}));}catch(x){}}"
    "return JSON.stringify({act:e.act,tr:e.tr.slice(-12),req:e.req,det:e.det,err:e.err,errd:e.errd,done:e.done,num:e.num||0,tot:e.tot||0,opts:opts,eulas:eulas});};")


def _gid(game_id):
    g = int(game_id)
    if not 0 < g < 2**64:
        raise ValueError("not a game id")
    return str(g)


def launch_expression(game_id):
    """Start a game as Steam's interface does (RunGame(gameid, "", -1, source)) with the listener in
    place first, so no step is missed; the state after a few seconds is the answer."""
    g = _gid(game_id)
    return ("(async()=>{" + _GA +
            f"const G='{g}';const old=W.g[G];if(old&&(old.done||old.err))delete W.g[G];W.at(G);"
            f"try{{A.RunGame(G,'',-1,100);}}catch(x){{return JSON.stringify({{act:0,tr:[],err:'RunGame',errd:String(x).slice(0,160)}});}}"
            "for(let i=0;i<16;i++){await z(250);const e=W.g[G];if(e&&(e.req||e.err))break;}"
            "return await state(G);})()")


def launch_state_expression(game_id):
    g = _gid(game_id)
    return "(async()=>{" + _GA + f"return await state('{g}');}})()"


def launch_answer_expression(game_id, answer):
    """Pass the person's answer to the question Steam is asking about this game. "ShowEula": every
    agreement Steam lists is marked accepted first, as Steam's own dialog does. "cancel": the start is
    cancelled. Answers are only Steam's own words for that question (LAUNCH_ANSWERS) or a launch option."""
    g = _gid(game_id)
    if not isinstance(answer, str) or not (answer == "cancel" or answer.isdigit() and len(answer) <= 2
                                           or any(answer in (v or ()) for v in LAUNCH_ANSWERS.values())):
        raise ValueError("answer")
    appid = int(g) if int(g) < 2**32 else 0
    eula = (f"if(a==='ShowEula'){{let v=[];try{{v=[...(await Promise.race([A.LoadEula({appid}),z(4000)])||[])];}}catch(x){{}}"
            f"for(const x of v){{try{{A.MarkEulaAccepted({appid},x.id,x.version);}}catch(x){{}}}}await z(300);}}") if appid else ""
    return ("(async()=>{" + _GA + f"const G='{g}',a={json.dumps(answer)};await state(G);const e=W.g[G];"
            "if(!e||!e.act)return JSON.stringify({ok:false,why:'no action'});"
            "e.req=null;e.tr.push('answer:'+(a||'-'));"
            "try{if(a==='cancel'){A.CancelGameAction(e.act);e.done=true;}else{" + eula +
            "A.ContinueGameAction(e.act,a);}}catch(x){return JSON.stringify({ok:false,why:String(x).slice(0,160)});}"
            "return JSON.stringify({ok:true});})()")


def parse_launch(raw):
    """{"action", "trace", "request", "details", "error", "error_details", "done", "done_n", "total",
    "options", "eulas"} or None."""
    try:
        d = json.loads(raw) if isinstance(raw, str) else None
    except ValueError:
        return None
    if not isinstance(d, dict):
        return None

    def s(v, n):
        return str(v)[:n] if isinstance(v, (str, int)) and v != "" else None
    opts = [{"index": int(o.get("i") or 0), "label": str(o.get("d") or "")[:80]} for o in (d.get("opts") or [])
            if isinstance(o, dict)][:8] or None
    return {"action": int(d.get("act") or 0) if str(d.get("act") or "0").isdigit() else 0,
            "trace": [str(t)[:40] for t in (d.get("tr") or []) if isinstance(t, str)][:12],
            "request": s(d.get("req"), 40), "details": s(d.get("det"), 160) or "", "error": s(d.get("err"), 40),
            "error_details": s(d.get("errd"), 160) or "", "done": bool(d.get("done")),
            "progress": [int(d.get("num") or 0), int(d.get("tot") or 0)], "options": opts,
            "eulas": _eulas(d.get("eulas")) if d.get("eulas") else None}


def launch(game_id, port=PORT):
    """Steam's state of the start (parse_launch), or None when its interface does not answer."""
    return parse_launch(ui_value(launch_expression(game_id), port, timeout=15.0))


def launch_state(game_id, port=PORT):
    return parse_launch(ui_value(launch_state_expression(game_id), port, timeout=12.0))


def launch_answer(game_id, answer, port=PORT):
    raw = ui_value(launch_answer_expression(game_id, answer), port, timeout=12.0)
    try:
        return bool(json.loads(raw).get("ok")) if isinstance(raw, str) else None
    except ValueError:
        return None


# ---- Steam asking the person something, answered from STONE Home -----------------------------
# A cloud-save conflict, a choice of launch options, a licence or a first-launch question: Steam
# shows it in its own interface, which the STONE session keeps hidden. STONE Home reads the topmost
# dialog of Steam's interface as text and buttons, asks the same with its own screen and presses the
# button the person chose. Only reading and one click; nothing is typed into Steam. [VERIFICAR EN PLACA]
_DIALOG_FIND = (
    "const vis=e=>{const r=e.getBoundingClientRect();return r.width>1&&r.height>1;};"
    "const ms=[...document.querySelectorAll('[class*=\"ModalPosition\"],[role=\"dialog\"],[class*=\"DialogContent\"]')]"
    ".filter(vis).filter((m,i,a)=>!a.some(o=>o!==m&&m.contains(o)));"
    "const m=ms[ms.length-1];"
    "const btns=m?[...m.querySelectorAll('button,[class*=\"DialogButton\"]')].filter(vis)"
    ".filter((b,i,a)=>!a.some(o=>o!==b&&o.contains(b))).filter(b=>(b.innerText||'').trim()).slice(0,4):[];")
DIALOG_EXPRESSION = (
    "(()=>{" + _DIALOG_FIND + "if(!m||!btns.length)return null;"
    "const t=e=>(e&&e.innerText||'').replace(/\\s+/g,' ').trim();"
    "const head=m.querySelector('[class*=\"DialogHeader\"],[class*=\"Title\"],h1,h2');"
    "const body=m.querySelector('[class*=\"DialogBodyText\"],[class*=\"DialogBody\"]')||m;"
    "let text=t(body);for(const b of btns)text=text.split(t(b)).join(' ');if(head)text=text.split(t(head)).join(' ');"
    "return JSON.stringify({title:t(head).slice(0,120),text:text.replace(/\\s+/g,' ').trim().slice(0,600),"
    "buttons:btns.map(t).map(x=>x.slice(0,40))});})()")


def answer_expression(index, label):
    """Press button `index` of Steam's topmost dialog, only if it still reads `label`."""
    if not isinstance(index, int) or not 0 <= index < 4 or not isinstance(label, str) or not 0 < len(label) <= 40:
        raise ValueError("dialog button")
    want = json.dumps(label)               # ASCII-only JSON string: a safe JavaScript literal
    return ("(()=>{" + _DIALOG_FIND + f"const b=btns[{index}];"
            "if(!b)return null;if((b.innerText||'').replace(/\\s+/g,' ').trim().slice(0,40)!==" + want + ")return 'changed';"
            "b.click();return 'ok';})()")


def parse_dialog(raw):
    """The dialog as {"title", "text", "buttons"} or None (nothing asked, or not readable)."""
    try:
        d = json.loads(raw) if isinstance(raw, str) else None
    except ValueError:
        return None
    if not isinstance(d, dict) or not isinstance(d.get("buttons"), list):
        return None
    buttons = [b for b in d["buttons"] if isinstance(b, str) and b.strip()][:4]
    if not buttons:
        return None
    return {"title": str(d.get("title") or "")[:120], "text": str(d.get("text") or "")[:600], "buttons": buttons}


def dialog(port=PORT):
    return parse_dialog(ui_value(DIALOG_EXPRESSION, port))


def answer_dialog(index, label, port=PORT):
    """'ok' (pressed), 'changed' (another dialog is there now) or 'gone'."""
    v = ui_value(answer_expression(index, label), port)
    return v if v in ("ok", "changed") else "gone"


def reachable(port=PORT):
    """True when Steam's interface answers on the remote debugging port (STONE needs it for the
    library of the account, installing, Steam's settings and adding shortcuts)."""
    try:
        return bool(candidates(targets(port, timeout=1.5)))
    except (OSError, ValueError):
        return False


def add_shortcut_expression(name, exe, start_dir, launch_options):
    for v in (name, exe, start_dir, launch_options):
        if not isinstance(v, str) or any(c in v for c in "'\\\n\r\"`$"):
            raise ValueError("unsafe shortcut field")
    return ("(async()=>{if(!window.SteamClient||!SteamClient.Apps||!SteamClient.Apps.AddShortcut)return 'no SteamClient';"
            f"const id=await SteamClient.Apps.AddShortcut('{name}','{exe}','{start_dir}','{launch_options}');"
            f"try{{SteamClient.Apps.SetShortcutName(id,'{name}');}}catch(e){{}}"
            "return 'ok '+id;})()")


def add_shortcut(name, exe, start_dir, launch_options, port=PORT):
    """Adds a non-Steam shortcut while Steam runs. Returns its app id, or None."""
    v = ui_value(add_shortcut_expression(name, exe, start_dir, launch_options), port)
    if isinstance(v, str) and v.startswith("ok ") and v[3:].isdigit():
        return int(v[3:])
    return None


# ---- Closing a game and pausing a download, as Steam's own buttons do ---------------------------
# Steam's "Exit game" (its dialog "¿Salir del juego?" / "Los datos no guardados podrían perderse.",
# and B on the running game's panel) calls SteamClient.Apps.TerminateApp(gameid, false). The actions
# of a game in the library: pause is Downloads.EnableAllDownloads(false, client) (Steam pauses its
# downloads, not one game), resume / update now is Downloads.ResumeAppUpdate(appid, client), and a
# paused download list is let go again with EnableAllDownloads(true, client). Client "0": this console.
# (Steam's code, client 1792618285: the app action switch and the exit-game dialog.)
def terminate_expression(game_id):
    g = _gid(game_id)
    return ("(()=>{const A=window.SteamClient&&SteamClient.Apps;if(!A||!A.TerminateApp)return null;"
            f"A.TerminateApp('{g}',false);return 'ok';}})()")


def terminate(game_id, port=PORT):
    """Close a running game the way Steam's "Exit game" does. True, or None if Steam does not answer."""
    return True if ui_value(terminate_expression(game_id), port, timeout=6.0) == "ok" else None


DOWNLOAD_ACTIONS = ("pause", "resume")


def download_control_expression(appid, action):
    a = _appid(appid)
    if action not in DOWNLOAD_ACTIONS:
        raise ValueError("download action")
    c = LOCAL_CLIENT
    if action == "pause":
        body = f"D.EnableAllDownloads(false,'{c}');"
    else:
        body = (f"let o=null;try{{const S=window.downloadsStore;o=S&&(S.LocalDownloadOverview||(S.m_DownloadOverview&&S.m_DownloadOverview.get('{c}')));}}catch(e){{}}"
                f"if(!o||o.paused)D.EnableAllDownloads(true,'{c}');D.ResumeAppUpdate({a},'{c}');")
    return ("(()=>{const D=window.SteamClient&&SteamClient.Downloads;if(!D||!D.EnableAllDownloads||!D.ResumeAppUpdate)return null;"
            + body + "return 'ok';})()")


def download_control(appid, action, port=PORT):
    """Pause Steam's downloads or let this game's download go on. True, or None if Steam does not answer."""
    return True if ui_value(download_control_expression(appid, action), port, timeout=6.0) == "ok" else None
