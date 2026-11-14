"""Games for the emulators sent from the phone (3.1.0-rc6).

The owner, 14-11-2026, asked for games from a USB drive "o que también se pueda conectar a un iCloud o
alguna nube". STONE never signs in to anything with the person's password (D-34), so the cloud is
reached through the phone, which is already signed in: STONE shows a QR code; the phone opens a page
served by the console on the home network, and the person picks files in the phone's own picker (on an
iPhone, «Archivos» includes iCloud Drive and other clouds; on Android, the Files app and Drive). Each
file is sent straight to ~/Emulation/roms/<system>/.

What keeps this safe:
  - it runs only while that screen is open in STONE Home, 30 minutes at most;
  - every address carries a random key, shown only in the QR code and on the TV;
  - only files with an extension of a system (roms.SYSTEMS) are taken, written under that system's
    folder with their bare file name, and only while 2 GB stay free;
  - nothing received is ever run; the page loads nothing from the internet.
"""

import json
import os
import secrets
import shutil
import socket
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import roms

OPEN_S = 30 * 60
MAX_FILE = 64 * 2**30
KEEP_FREE = 2 * 2**30
CHUNK = 1 * 2**20


def lan_address():
    """This console's address on the home network (no packet is sent), or None."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.0.2.1", 9))                 # TEST-NET-1: only chooses the route
        ip = s.getsockname()[0]
        return None if ip.startswith("127.") else ip
    except OSError:
        return None
    finally:
        s.close()


def system_for(filename, wanted=None):
    """The system a file goes to: the one asked for if its extension fits it, else the only system
    whose extensions include it. None if it is not a game file."""
    ext = os.path.splitext(filename)[1].lower()
    if wanted in roms.SYSTEMS and ext in roms.SYSTEMS[wanted][3]:
        return wanted
    fits = [k for k, v in roms.SYSTEMS.items() if ext in v[3]]
    return fits[0] if len(fits) == 1 else None


def safe_name(name):
    n = os.path.basename(str(name or "").replace("\\", "/")).replace("\x00", "").strip()
    return n if n and not n.startswith(".") and len(n.encode()) <= 200 else None


PAGE = """<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>STONE · Enviar juegos</title><style>
body{margin:0;font:16px/1.45 -apple-system,system-ui,sans-serif;background:#0b0b0d;color:#ece9e2;padding:22px 18px 40px}
h1{font-weight:300;letter-spacing:.3em;font-size:20px;margin:0 0 4px}p{color:#a8a59d;margin:6px 0 18px}
label,select,button{display:block;width:100%;box-sizing:border-box;font:inherit}select{margin:6px 0 16px;padding:12px;border-radius:12px;background:#1b1c20;color:#ece9e2;border:1px solid #333}
.pick{padding:18px;border-radius:16px;background:#ece9e2;color:#0b0b0d;text-align:center;font-weight:600}
input[type=file]{display:none}ul{list-style:none;padding:0;margin:18px 0 0}li{padding:12px 14px;border-radius:12px;background:#17181b;margin:8px 0}
li b{display:block;font-weight:500;word-break:break-word}li small{color:#a8a59d}.bar{height:4px;border-radius:2px;background:#2a2b30;margin-top:8px}.bar i{display:block;height:100%;width:0;border-radius:2px;background:#ece9e2}
.ok{color:#9fd49a}.err{color:#f0a07a}
</style><h1>STONE</h1><p>Elige juegos en tu móvil: en iPhone, «Archivos» incluye iCloud Drive. Se envían a la consola por tu Wi-Fi. Deja esta página abierta hasta que terminen.</p>
<label>Consola de los juegos<select id="sys"><option value="">Según el tipo de archivo</option>__OPTIONS__</select></label>
<label class="pick" for="f">ELEGIR JUEGOS</label><input id="f" type="file" multiple>
<ul id="l"></ul><script>
const B=location.pathname.replace(/\\/$/,''),l=document.getElementById('l');let q=Promise.resolve();
const gb=b=>b>=1073741824?(b/1073741824).toFixed(1)+' GB':Math.max(1,Math.round(b/1048576))+' MB';
document.getElementById('f').onchange=e=>{for(const f of e.target.files){const li=document.createElement('li');li.innerHTML='<b></b><small>En espera · '+gb(f.size)+'</small><div class=bar><i></i></div>';li.querySelector('b').textContent=f.name;l.appendChild(li);
q=q.then(()=>new Promise(ok=>{const x=new XMLHttpRequest(),s=li.querySelector('small'),i=li.querySelector('i');
x.open('PUT',B+'/up?name='+encodeURIComponent(f.name)+'&system='+encodeURIComponent(document.getElementById('sys').value));
x.upload.onprogress=p=>{if(p.lengthComputable){i.style.width=(p.loaded*100/p.total)+'%';s.textContent='Enviando · '+Math.floor(p.loaded*100/p.total)+' %'}};
x.onload=()=>{let r={};try{r=JSON.parse(x.responseText)}catch(e){}if(x.status==200){s.textContent='En la consola: '+(r.system||'');s.className='ok';i.style.width='100%'}else{s.textContent=r.error||'No se pudo enviar';s.className='err'}ok()};
x.onerror=()=>{s.textContent='Se cortó la conexión: vuelve a elegirlo';s.className='err';ok()};x.send(f)}))}};
</script></html>"""


class Drop:
    """One open session of «Juegos desde el móvil». on_event(name, data) is called from the server's
    threads: ("drop", {"state": "receiving", "name", "done", "total"}) and ({"state": "received", ...})."""

    def __init__(self, on_event, base=None, clock=time.monotonic):
        self.on_event, self.base, self.clock = on_event, base, clock
        self.server = self.thread = None
        self.token, self.until, self.received = None, 0.0, []

    def start(self, host=None, port=0):
        if self.server:
            return self.info()
        ip = host or lan_address()
        if not ip:
            raise OSError("La consola no está conectada a una red")
        self.base = roms.folders(self.base)
        self.token, self.until, self.received = secrets.token_urlsafe(12), self.clock() + OPEN_S, []
        drop = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _ok_path(self):
                u = urllib.parse.urlparse(self.path)
                parts = u.path.strip("/").split("/")
                if not parts or not secrets.compare_digest(parts[0], drop.token) or drop.clock() > drop.until:
                    self._send(404, {"error": "Esta dirección ya no está abierta: vuelve a escanear el código"})
                    return None
                return parts[1:], urllib.parse.parse_qs(u.query)

            def _send(self, code, obj, ctype="application/json"):
                body = obj.encode() if isinstance(obj, str) else json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text/") else ""))
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                p = self._ok_path()
                if p is None:
                    return
                if p[0] not in ([], [""]):
                    return self._send(404, {"error": "no"})
                opts = "".join(f'<option value="{k}">{v[1]}</option>' for k, v in roms.SYSTEMS.items())
                self._send(200, PAGE.replace("__OPTIONS__", opts), "text/html")

            def do_PUT(self):
                p = self._ok_path()
                if p is None:
                    return
                rest, qs = p
                if rest != ["up"]:
                    return self._send(404, {"error": "no"})
                name = safe_name((qs.get("name") or [""])[0])
                system = system_for(name or "", (qs.get("system") or [""])[0] or None)
                try:
                    size = int(self.headers.get("Content-Length") or -1)
                except ValueError:
                    size = -1
                if not name or not system:
                    return self._send(400, {"error": "No es un archivo de juego que STONE conozca"})
                if not 0 < size <= MAX_FILE:
                    return self._send(400, {"error": "Tamaño no válido"})
                d = os.path.join(drop.base, "roms", roms.SYSTEMS[system][0])
                if size > shutil.disk_usage(d).free - KEEP_FREE:
                    return self._send(507, {"error": "No hay espacio en la consola"})
                dst, part, done, last = os.path.join(d, name), os.path.join(d, name + ".stone-part"), 0, 0.0
                try:
                    with open(part, "wb") as f:
                        while done < size:
                            b = self.rfile.read(min(CHUNK, size - done))
                            if not b:
                                raise OSError("connection closed")
                            f.write(b)
                            done += len(b)
                            if drop.clock() - last >= 0.5:
                                last = drop.clock()
                                drop.on_event("drop", {"state": "receiving", "name": name, "done": done, "total": size})
                    os.replace(part, dst)
                except OSError:
                    try:
                        os.remove(part)
                    except OSError:
                        pass
                    return self._send(500, {"error": "Se cortó el envío"})
                drop.received.append({"name": name, "system": roms.SYSTEMS[system][1], "size": size})
                drop.on_event("drop", {"state": "received", "name": name, "system": roms.SYSTEMS[system][1], "size": size})
                self._send(200, {"ok": True, "system": roms.SYSTEMS[system][1]})

        self.server = ThreadingHTTPServer((ip, port), H)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.ip = ip
        return self.info()

    def info(self):
        if not self.server:
            return {"open": False}
        return {"open": True, "url": f"http://{self.ip}:{self.server.server_address[1]}/{self.token}/",
                "seconds": max(0, int(self.until - self.clock())), "received": list(self.received)}

    def stop(self):
        srv, self.server = self.server, None
        if srv:
            srv.shutdown()
            srv.server_close()
        return {"received": list(self.received)}
