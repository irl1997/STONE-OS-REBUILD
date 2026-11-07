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
  return [
    { l: 'Volumen', s: A.muted ? 'Silenciado' : 'Salida actual', v: A.volume == null ? '—' : `${Math.round(A.volume * 100)} %`, key: 'sysvol' },
    ...A.outputs.map(o => ({ l: o.name, s: o.default ? 'Salida en uso' : 'Otra salida disponible', v: o.default ? 'En uso' : 'Usar', act: o.default ? 'info' : 'audio-out', id: o.id, where: 'Ya es la salida en uso' }))];
}
function setSysVol(d, ri) {
  const A = CX.audio; if (!A || A.error || A.volume == null) return bump(d);
  const v = Math.max(0, Math.min(1, Math.round((A.volume + d * 0.05) * 100) / 100));
  A.volume = v; A.muted = false; play('nav');
  Bridge.call('audio.volume', v).catch(() => toast('No se pudo cambiar el volumen', false));
  enterSettings({ pane: true, ri });
}
function netRows() {
  const N = CX.net, W = CX.wifi;
  if (!N) { cxLoad('net', () => Bridge.call('net.status'), 'Red'); return [{ l: 'Leyendo…', s: 'Cable y Wi-Fi', v: '' }]; }
  if (N.error) return [{ l: 'Red no disponible', s: N.error, v: '' }];
  const rows = N.devices.map(d => ({ l: d.type === 'wifi' ? 'Wi-Fi' : 'Cable', s: d.state === 'connected' ? `Conectado${d.connection ? ' · ' + d.connection : ''}` : d.state === 'unavailable' ? 'Sin cable o apagado' : 'Sin conectar',
    v: d.state === 'connected' ? 'Conectado' : '—', act: d.type === 'wifi' && d.state === 'connected' ? 'wifi-off' : 'info', dev: d.device, where: d.type === 'wifi' ? 'Elige una red de la lista' : 'Conecta un cable de red: se configura solo' }));
  if (N.devices.some(d => d.type === 'wifi')) {
    if (!W) { cxLoad('wifi', () => Bridge.call('net.wifiList'), 'Red'); rows.push({ l: 'Buscando redes Wi-Fi…', s: '', v: '' }); }
    else if (W.error) rows.push({ l: 'Wi-Fi', s: W.error, v: '' });
    else W.networks.slice(0, 12).forEach(n => rows.push({ l: n.ssid, s: `${n.secure ? 'Con contraseña' : 'Abierta'} · señal ${n.signal} %`, v: n.active ? 'Conectada' : 'Conectar', act: n.active ? 'info' : 'wifi', ssid: n.ssid, secure: n.secure, where: 'Ya conectada' }));
    rows.push({ l: 'Buscar de nuevo', s: 'Actualiza la lista de redes', v: '', act: 'wifi-scan' });
  }
  return rows;
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
  if (r.act === 'wifi-off') { play('select'); return run('net.wifiDisconnect', [r.dev], 'Wi-Fi desconectado', 'net', 'Red'); }
  if (r.act === 'wifi') {
    play('select');
    if (!r.secure) return run('net.wifiConnect', [r.ssid, null], `Conectado a ${r.ssid}`, 'net', 'Red').then(() => { delete CX.wifi; });
    return osk(`CONTRASEÑA DE ${r.ssid}`, pw => pw === null ? enterSettings({ pane: true, ri })
      : run('net.wifiConnect', [r.ssid, pw], `Conectado a ${r.ssid}`, 'net', 'Red').then(() => { delete CX.wifi; }), true);
  }
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
      <div class="btns"><span class="txt-f" data-f data-b="${d.connected ? 'disconnect' : 'connect'}">${d.connected ? 'DESCONECTAR' : 'CONECTAR'}</span><span class="txt-f" data-f data-b="forget">OLVIDAR</span><span class="txt-f" data-f data-b="no">VOLVER</span></div>`, {
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
      onB: () => { play('back'); text = text.slice(0, -1); const at = [NAV.r, NAV.c]; draw(); NAV.r = at[0]; NAV.c = Math.min(at[1], NAV.rows[NAV.r].length - 1); applyFocus(); } });
    const d = $('#dlg');
    NAV = mkNav([...d.querySelectorAll('.krow')].map(r => [...r.querySelectorAll('[data-f]')]), { place: (el, b) => ({ x: b.x, y: b.y + b.h + 4, w: b.w }) });
    NAV.id = 'dlg'; requestAnimationFrame(() => applyFocus());
    hints([['A', 'Escribir'], ['B', 'Borrar']]);
  };
  draw();
}
