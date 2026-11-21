/* ---------- STONE CONNECT and SETTINGS (M12, M16): Bluetooth, audio, network ----------
   Read from the host (connect.py: bluetoothctl, wpctl, nmcli) when the category opens; every
   failure is a sentence, never a broken pane. */
const CX = {};
function cxLoad(key, fn, catName) {
  if (CX[key + '_loading']) return;
  CX[key + '_loading'] = true;
  fn().then(r => { CX[key] = r; }, e => { CX[key] = { error: (e && e.message) || 'no disponible' }; }).then(() => {
    CX[key + '_loading'] = false;
    if (S.screen === 'settings' && CATS[cat] === catName) enterSettings({ pane: !!NAV.pane, ri: NAV.pane ? NAV.c : 0 });
  });
}
const cxReset = (key, catName, ri) => { delete CX[key]; enterSettings({ pane: true, ri: ri || 0 }); };
function audioRows() {
  const A = CX.audio;
  if (!A) { cxLoad('audio', () => Bridge.call('audio.status'), 'Audio'); return [{ l: 'Leyendo…', s: 'Salidas de sonido', v: '' }]; }
  if (A.error) return [{ l: 'Audio no disponible', s: A.error, v: '' }];
  /* 3.1.0-rc12 (board, 20-11-2026): the only output was PipeWire's "Dummy Output", a sink that goes
     nowhere, shown as if it were the TV. It is said for what it is, with what to do. */
  const real = A.outputs.filter(o => !/^Dummy Output$/i.test(o.name));
  const none = !real.length ? [{ l: 'Sin salida de sonido', s: 'La TV no avisó a la consola que acepta sonido. Con la TV encendida y en la entrada de la consola, reinicia la consola; si sigue, vuelve a conectar el adaptador o el cable', v: 'Sin sonido', act: 'info', where: 'Reinicia con la TV encendida en la entrada de la consola' }] : [];
  return [...none,
    { l: 'Volumen', s: A.muted ? 'Silenciado' : 'Salida actual', v: A.volume == null ? '—' : `${Math.round(A.volume * 100)} %`, key: 'sysvol' },
    ...real.map(o => ({ l: o.name, s: o.default ? 'Salida en uso' : 'Otra salida disponible', v: o.default ? 'En uso' : 'Usar', act: o.default ? 'info' : 'audio-out', id: o.id, where: 'Ya es la salida en uso' }))];
}
function setSysVol(d, ri) {
  const A = CX.audio; if (!A || A.error || A.volume == null) return bump(d);
  const v = Math.max(0, Math.min(1, Math.round((A.volume + d * 0.05) * 100) / 100));
  A.volume = v; A.muted = false; play('nav');
  Bridge.call('audio.volume', v).catch(() => toast('No se pudo cambiar el volumen', false));
  enterSettings({ pane: true, ri });
}
/* Ajustes → Red, as SteamOS has it: Wi-Fi on or off, the network in use (DESCONECTAR / OLVIDAR),
   networks joined before join again without their password, whether there is internet. 3.1.0-rc5 on
   the board: after DESCONECTAR the old list still said "Conectada" and offered no way back. */
const NET_INTERNET = { full: ['Hay conexión a internet', 'Sí'], limited: ['La red no tiene salida a internet: revisa el router', 'No'],
  portal: ['La red pide iniciar sesión en una página web (hoteles, cafeterías): no se puede desde la consola', 'No'],
  none: ['Sin conexión', 'No'], unknown: ['Conectado; NetworkManager no comprobó internet', '—'] };
function netRows() {
  const N = CX.net, W = CX.wifi;
  if (!N) { cxLoad('net', () => Bridge.call('net.status'), 'Red'); return [{ l: 'Leyendo…', s: 'Cable y Wi-Fi', v: '' }]; }
  if (N.error) return [{ l: 'Red no disponible', s: N.error, v: '' }];
  const wifi = N.devices.find(d => d.type === 'wifi'), cable = N.devices.find(d => d.type === 'ethernet'), rows = [];
  if (wifi) {
    const on = N.radio !== false && wifi.state !== 'unavailable';
    rows.push({ l: 'Wi-Fi', s: wifi.state === 'connected' ? `Conectado a ${N.ssid || wifi.connection || 'una red'}${N.signal != null ? ` · señal ${N.signal} %` : ''}`
      : on ? (wifi.state === 'connecting' ? 'Conectando…' : 'Sin conectar: elige una red de la lista') : 'Apagado', v: on ? 'Activado' : 'Desactivado', act: 'wifi-radio', on });
  }
  if (cable) rows.push({ l: 'Cable de red', s: cable.state === 'connected' ? 'Conectado: se configura solo' : 'Sin cable conectado', v: cable.state === 'connected' ? 'Conectado' : '—', act: 'info', where: 'Conecta un cable de red: se configura solo' });
  const it = NET_INTERNET[N.online ? N.internet || 'unknown' : 'none'] || NET_INTERNET.unknown;
  rows.push({ l: 'Internet', s: it[0], v: it[1], act: 'info', where: it[0] });
  if (wifi && N.radio !== false && wifi.state !== 'unavailable') {
    if (!W) { cxLoad('wifi', () => Bridge.call('net.wifiList'), 'Red'); rows.push({ l: 'Buscando redes Wi-Fi…', s: '', v: '' }); }
    else if (W.error) rows.push({ l: 'Redes Wi-Fi', s: W.error, v: '' });
    else {
      if (!W.networks.length) rows.push({ l: 'Ninguna red a la vista', s: 'Acerca la consola al router o busca de nuevo', v: '' });
      W.networks.slice(0, 12).forEach(n => rows.push({ l: n.ssid, s: `${n.active ? 'En uso' : n.known ? 'Guardada' : n.secure ? 'Con contraseña' : 'Abierta'} · señal ${n.signal} %`,
        v: n.active ? 'Conectada' : 'Conectar', act: n.active ? 'wifi-net' : 'wifi', ssid: n.ssid, secure: n.secure, known: n.known, dev: wifi.device }));
    }
    rows.push({ l: 'Buscar de nuevo', s: 'Actualiza la lista de redes', v: '', act: 'wifi-scan' });
  }
  return rows;
}
/* Every network change: the status, the list and the status icon are read again. */
function netRun(method, args, ok, ri, onError) {
  toast('Un momento…', false);
  busy('net', method === 'net.wifiConnect' ? `Conectando a ${args[0]}` : 'Cambiando la red');
  return Bridge.call(method, ...args).finally(() => busy('net')).then(() => { if (ok) toast(ok, false); return true; },
    e => { const m = (e && e.message) || 'No se pudo'; if (onError && onError(m)) return false; play('error'); toast(m, false); return false; })
    .then(r => { delete CX.net; delete CX.wifi; netIconKick(); if (S.screen !== 'game' && S.screen !== 'off' && !$('#dlg').classList.contains('on')) enterSettings({ pane: true, ri }); return r; });
}
function wifiJoin(r, ri) {
  const ask = () => osk(`CONTRASEÑA DE ${r.ssid}`, pw => pw === null ? enterSettings({ pane: true, ri }) : netRun('net.wifiConnect', [r.ssid, pw], `Conectado a ${r.ssid}`, ri), true);
  if (r.secure && !r.known) return ask();
  /* open networks and networks joined before: no password; if it is asked after all, the keyboard */
  return netRun('net.wifiConnect', [r.ssid, null], `Conectado a ${r.ssid}`, ri, m => /contraseña/i.test(m) ? (ask(), true) : false);
}
function wifiNetDlg(r, ri) {
  const back = () => { closeDlg(); play('back'); enterSettings({ pane: true, ri }); };
  openDlg(`<span class="st-cap">WI-FI</span><h2>${esc(r.ssid)}</h2><p>Conectada · ${esc(r.s.split(' · ').pop())}</p><p>«Olvidar» borra también la contraseña guardada.</p>
    <div class="btns"><span class="txt-f" data-f data-b="no">VOLVER</span><span class="txt-f" data-f data-b="off">DESCONECTAR</span><span class="txt-f" data-f data-b="forget">OLVIDAR</span></div>`, {
    onA: el => {
      const b = el.dataset.b; if (b === 'no') return back();
      closeDlg(); play('select');
      if (b === 'off') return netRun('net.wifiDisconnect', [r.dev], 'Wi-Fi desconectado. Elige una red para volver a conectar', ri);
      return netRun('net.wifiDisconnect', [r.dev], null, ri).then(() => netRun('net.wifiForget', [r.ssid], `${r.ssid}: olvidada`, ri));
    }, onB: back });
}
function btRows() {
  const B = CX.bt;
  if (!B) { cxLoad('bt', () => Bridge.call('bt.devices'), 'Bluetooth'); return [{ l: 'Leyendo…', s: 'Mandos, auriculares y teclados', v: '' }]; }
  if (B.error) return [{ l: 'Bluetooth no disponible', s: B.error, v: '' }];
  const rows = B.devices.map(d => ({ l: d.name, s: `${d.connected ? 'Conectado' : d.paired ? 'Emparejado' : 'Visible, sin emparejar'}${d.battery != null ? ` · batería ${d.battery} %` : ''}`,
    v: d.connected ? 'Conectado' : d.paired ? 'Conectar' : 'Emparejar', act: 'bt', mac: d.mac, dev: d }));
  rows.push({ l: CX.btScanning ? 'Buscando… (8 s)' : 'Buscar dispositivos', s: 'Pon el mando o los auriculares en modo emparejamiento', v: '', act: 'bt-scan' });
  return rows;
}
async function cxAct(r, ri) {
  const run = (method, args, ok, key, catName) => { toast('Un momento…', false);
    return Bridge.call(method, ...args).then(() => { if (ok) toast(ok, false); cxReset(key, catName, ri); }, e => { play('error'); toast((e && e.message) || 'No se pudo', false); cxReset(key, catName, ri); }); };
  if (r.act === 'audio-out') { play('select'); return run('audio.default', [r.id], `Sonido por: ${r.l}`, 'audio', 'Audio'); }
  if (r.act === 'wifi-scan') { play('select'); delete CX.wifi; return enterSettings({ pane: true, ri }); }
  if (r.act === 'wifi-radio') { play('select'); return netRun('net.wifiRadio', [!r.on], r.on ? 'Wi-Fi desactivado' : 'Wi-Fi activado: buscando redes…', ri); }
  if (r.act === 'wifi-net') { play('select'); return wifiNetDlg(r, ri); }
  if (r.act === 'wifi') { play('select'); return wifiJoin(r, ri); }
  if (r.act === 'bt-scan') {
    play('select'); CX.btScanning = true; enterSettings({ pane: true, ri });
    return Bridge.call('bt.scan').then(x => { CX.bt = x; }, e => { toast((e && e.message) || 'No se pudo buscar', false); }).then(() => { CX.btScanning = false; if (S.screen === 'settings') enterSettings({ pane: true, ri }); });
  }
  if (r.act === 'bt') {
    play('select');
    const d = r.dev;
    if (!d.paired) return run('bt.action', ['pair', d.mac], `${d.name}: emparejado`, 'bt', 'Bluetooth');
    const back = () => { closeDlg(); play('back'); enterSettings({ pane: true, ri }); };
    return openDlg(`<h2>${esc(d.name)}</h2><p>${d.connected ? 'Conectado' : 'Emparejado, sin conectar'}${d.battery != null ? ` · batería ${d.battery} %` : ''}</p>
      <div class="btns"><span class="txt-f" data-f data-b="${d.connected ? 'disconnect' : 'connect'}">${d.connected ? 'DESCONECTAR' : 'CONECTAR'}</span><span class="txt-f" data-f data-b="forget">OLVIDAR</span><span class="txt-f" data-f data-def data-b="no">VOLVER</span></div>`, {
      onA: el => { if (el.dataset.b === 'no') return back(); closeDlg(); play('select'); run('bt.action', [el.dataset.b, d.mac], el.dataset.b === 'forget' ? `${d.name}: olvidado` : null, 'bt', 'Bluetooth'); }, onB: back });
  }
}
/* On-screen keyboard (Wi-Fi passwords, later names): the controller moves over the keys, A types,
   B deletes; LISTO returns the text, CANCELAR returns null. A physical keyboard also types. */
function osk(title, done, secret) {
  let text = '', shift = false, sym = false;
  const L1 = 'qwertyuiop', L2 = 'asdfghjklñ', L3 = 'zxcvbnm', N = '1234567890', SY = '!@#$%&*-_+=?/.,:;()[]';
  const draw = () => {
    const tr = s => shift ? s.toUpperCase() : s;
    const rows = sym ? [SY.slice(0, 10), SY.slice(10, 21), N] : [N, tr(L1), tr(L2), tr(L3)];
    const keys = rows.map(r => `<div class="krow">${[...r].map(c => `<span class="txt-f key" data-f data-k="${esc(c)}">${esc(c)}</span>`).join('')}</div>`).join('');
    const shown = secret ? '•'.repeat(Math.max(0, text.length - 1)) + text.slice(-1) : esc(text);
    openDlg(`<h2>${esc(title)}</h2><p class="okbox">${shown || '<span style="color:var(--slate)">escribe…</span>'}</p>${keys}
      <div class="krow"><span class="txt-f key wide" data-f data-k="⇧">${shift ? 'abc' : 'MAYÚS'}</span><span class="txt-f key wide" data-f data-k="#">${sym ? 'ABC' : '#+='}</span><span class="txt-f key wide" data-f data-k=" ">ESPACIO</span><span class="txt-f key wide" data-f data-k="⌫">BORRAR</span><span class="txt-f key wide" data-f data-k="✓">LISTO</span><span class="txt-f key wide" data-f data-k="✕">CANCELAR</span></div>`, {
      onA: el => { const k = el.dataset.k; play('select');
        if (k === '✓') { closeDlg(); return done(text); } if (k === '✕') { closeDlg(); return done(null); }
        if (k === '⌫') text = text.slice(0, -1); else if (k === '⇧') shift = !shift; else if (k === '#') sym = !sym; else if (text.length < 63) text += k;
        const at = [NAV.r, NAV.c]; draw(); NAV.r = Math.min(at[0], NAV.rows.length - 1); NAV.c = Math.min(at[1], NAV.rows[NAV.r].length - 1); applyFocus(); },
      /* B erases; with nothing written it closes, like the consoles' keyboards (3.1.0-rc12: it did
         nothing, and the search could only be left with ✕ on the keyboard's last row) */
      onB: () => { play('back'); if (!text) { closeDlg(); return done(null); } text = text.slice(0, -1); const at = [NAV.r, NAV.c]; draw(); NAV.r = at[0]; NAV.c = Math.min(at[1], NAV.rows[NAV.r].length - 1); applyFocus(); } });
    const d = $('#dlg');
    NAV = mkNav([...d.querySelectorAll('.krow')].map(r => [...r.querySelectorAll('[data-f]')]), { place: (el, b) => ({ x: b.x, y: b.y + b.h + 4, w: b.w }) });
    NAV.id = 'dlg'; requestAnimationFrame(() => applyFocus());
    hints([['A', 'Escribir'], ['B', text ? 'Borrar' : 'Salir']]);
  };
  draw();
}

/* ---------- STONE STORAGE and DOWNLOADS (storage.py) ---------- */
const GB = b => b == null ? '—' : b >= 2 ** 30 ? `${(b / 2 ** 30).toFixed(b >= 10 * 2 ** 30 ? 0 : 1).replace('.', ',')} GB` : `${Math.max(1, Math.round(b / 2 ** 20))} MB`;
function storageRows() {
  const T = CX.storage;
  if (!T) { cxLoad('storage', () => Bridge.call('storage.status'), 'Almacenamiento'); return [{ l: 'Leyendo…', s: 'Discos, juegos y descargas', v: '' }]; }
  if (T.error) return [{ l: 'No se pudo leer el almacenamiento', s: T.error, v: '' }];
  /* the disk by what it is for the person (the console's own disk, a card, an external disk), not by its Linux path */
  const disk = (l, k) => /\/run\/media\/|\/media\//.test(l.path) ? `Disco externo ${T.libraries.length > 2 ? k : ''}`.trim() : /\/mnt\//.test(l.path) ? 'Otro disco' : 'Disco de la consola';
  const rows = T.libraries.map((l, k) => ({ l: disk(l, k), s: `${GB(l.free)} libres de ${GB(l.total)}${l.low ? ' · queda poco espacio: borra algún juego que no uses' : ''}`, v: l.low ? 'Poco espacio' : 'Bien', act: 'info', where: `Biblioteca de Steam en ${l.path}` }));
  T.downloads.forEach(d => rows.push({ l: `Descargando · ${d.name}`, s: d.progress == null ? 'En cola o preparando' : `${GB(d.downloaded)} de ${GB(d.total)}`, v: d.progress == null ? '—' : `${Math.round(d.progress * 100)} %`, act: 'steam-dl', appid: d.appid }));
  T.games.slice(0, 20).forEach(g => rows.push({ l: g.name, s: `Juego ${GB(g.size)} · caché de sombreadores ${GB(g.shader_cache)} · Proton ${GB(g.prefix)}`, v: GB((g.size || 0) + (g.shader_cache || 0) + (g.prefix || 0)), act: 'game-store', game: g }));
  rows.push({ l: 'Volver a leer', s: 'Actualiza tamaños y descargas', v: '', act: 'storage-again' });
  return rows;
}
function storeAct(r, ri) {
  if (r.act === 'storage-again') { play('select'); return cxReset('storage', 'Almacenamiento', ri); }
  if (r.act === 'steam-dl') {
    /* the game's page: its bar, PAUSAR / REANUDAR (rc5 said "también con la consola en reposo": this console has no standby) */
    play('select'); const i = G.findIndex(g => g.appid === String(r.appid));
    return i >= 0 ? enterDetail(i) : toast('La descarga sigue mientras la consola esté encendida. Al terminar, el juego aparece listo para jugar', false);
  }
  const g = r.game, back = () => { closeDlg(); play('back'); enterSettings({ pane: true, ri }); };
  play('select');
  openDlg(`<h2>${esc(g.name)}</h2><p>Juego: <b>${GB(g.size)}</b> · caché de sombreadores: <b>${GB(g.shader_cache)}</b> · datos de Proton: <b>${GB(g.prefix)}</b></p>
    <p>La caché de sombreadores se vuelve a crear sola la próxima vez que juegues (el primer arranque irá algo más lento).</p>
    <div class="btns"><span class="txt-f" data-f data-b="cache">LIMPIAR CACHÉ</span><span class="txt-f" data-f data-b="uninstall">DESINSTALAR</span><span class="txt-f" data-f data-def data-b="no">VOLVER</span></div>`, {
    onA: el => {
      if (el.dataset.b === 'no') return back();
      closeDlg(); play('select');
      const m = el.dataset.b === 'cache' ? Bridge.call('storage.clearShaderCache', g.appid).then(x => toast(`Caché limpiada: ${GB(x.freed)} libres`, false))
        : uninstallGame(g.appid, g.name);
      m.catch(e => { play('error'); toast((e && e.message) || 'No se pudo', false); }).then(() => cxReset('storage', 'Almacenamiento', ri));
    }, onB: back });
}

/* ---------- STONE EMULATION: your games for other consoles (roms.py) ---------- */
function romRows() {
  const R = CX.roms;
  if (!R) { cxLoad('roms', () => Bridge.call('roms.scan'), 'Emuladores'); return [{ l: 'Buscando tus juegos…', s: '~/Emulation/roms', v: '' }]; }
  if (R.error) return [{ l: 'Tus juegos', s: R.error, v: '' }];
  const found = R.systems.filter(s => s.games.length);
  const rows = egRows();
  found.forEach(s => rows.push({ l: `${s.name}: ${s.games.length} juego${s.games.length === 1 ? '' : 's'}`, s: s.installed ? `Se abren con ${s.emulator}` : `Falta instalar ${s.emulator} (arriba)`, v: s.installed ? 'Listo' : 'Falta emulador', act: 'info', where: s.games.slice(0, 5).map(g => g.name).join(', ') }));
  if (found.length) rows.push({ l: 'Añadir juegos a la biblioteca', s: 'Los juegos con su emulador instalado aparecen en STONE como cualquier juego', v: 'Añadir', act: 'roms-add' });
  rows.push({ l: 'Carpeta de tus juegos', s: `${R.base}/roms/<consola> · BIOS en ${R.base}/bios`, v: 'Preparar', act: 'roms-folders' });
  return rows;
}
function romAct(r, ri) {
  play('select');
  if (r.act === 'roms-folders') return Bridge.call('roms.folders').then(x => toast(`Carpetas listas en ${x.base}/roms`, false), e => toast((e && e.message) || 'No se pudo', false)).then(() => cxReset('roms', 'Emuladores', ri));
  toast('Añadiendo…', false);
  return Bridge.call('roms.add').then(x => toast(x.new === 0 ? 'Ya estaban todos en la biblioteca' : x.queued ? `${x.added} añadidos ahora; ${x.queued} aparecerán al reiniciar la consola` : `${x.added} juegos añadidos a la biblioteca`, false),
    e => toast((e && e.message) || 'No se pudo', false)).then(() => { cxReset('roms', 'Emuladores', ri); loadLibrary(); });
}
/* At start, once: a console with no real sound output says so, instead of being silent (3.1.0-rc12; board,
   20-11-2026: only "Dummy Output", and nothing on screen said why the TV was mute). */
setTimeout(() => Bridge.call('audio.status').then(A => {
  if (!A || A.error || !Array.isArray(A.outputs) || A.outputs.some(o => !/^Dummy Output$/i.test(o.name))) return;
  if (S.screen === 'game' || S.screen === 'off') return;
  play('error'); toast('Sin sonido: la TV no avisó que acepta sonido. Ajustes → Audio', false);
}).catch(() => {}), 12000);
