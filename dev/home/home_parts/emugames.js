/* ---------- GAMES FOR THE EMULATORS: FROM A USB DRIVE OR FROM THE PHONE (3.1.0-rc6) ----------
   The owner, 14-11-2026: games on a pendrive, or in iCloud or another cloud. A USB drive with games is
   noticed when it is plugged in and its games are copied to the console (usbgames.py): like installing
   from a disc, they keep working without the drive. The cloud is reached through the phone, already
   signed in: a QR code opens a page served by the console on the home Wi-Fi and the phone's own picker
   (on an iPhone «Archivos», with iCloud Drive) sends the files (phonedrop.py). Both add the games to
   the library by themselves. */
const EG = { usb: null, seen: new Set(), copy: null, t: 0, drop: null };
const egGB = b => b >= 2 ** 30 ? `${(b / 2 ** 30).toFixed(1).replace('.', ',')} GB` : `${Math.max(1, Math.round(b / 2 ** 20))} MB`;
const egSys = d => Object.entries(d.systems).map(([k, n]) => `${n} de ${k}`).join(', ');
function egRows() {
  const rows = [];
  if (EG.copy) rows.push({ l: `Copiando juegos del USB · ${EG.copy.total ? Math.floor(EG.copy.done * 100 / EG.copy.total) : 0} %`, s: EG.copy.name || 'Preparando…', v: 'Cancelar', act: 'usb-cancel' });
  else if (EG.usb && EG.usb.length) EG.usb.forEach(d => rows.push({ l: `USB «${d.label}»: ${d.count} juego${d.count === 1 ? '' : 's'}`, s: d.new ? `${d.new} nuevo${d.new === 1 ? '' : 's'} · ${egGB(d.new_bytes)} · ${egSys(d)}` : 'Ya están todos en la consola',
    v: d.new ? 'Copiar' : 'Listo', act: d.new ? 'usb' : 'info', drive: d, where: 'Ya están todos en la consola' }));
  else rows.push({ l: 'Juegos desde un USB', s: 'Conecta un pendrive con carpetas por consola (ps2, gba, switch…): STONE copia los juegos y los añade', v: EG.usb === null ? '…' : 'Buscar', act: 'usb-scan' });
  rows.push({ l: 'Juegos desde el móvil', s: 'iCloud Drive, Google Drive o el móvil: escanea un código y elige los archivos', v: 'Abrir', act: 'drop' });
  return rows;
}
async function egScan(quiet) {
  const r = await Bridge.call('usb.scan').catch(() => null);
  if (!r) return;
  EG.usb = r.drives || [];
  if (S.screen === 'settings' && CATS[cat] === 'Emuladores') enterSettings({ pane: !!(NAV && NAV.pane), ri: NAV && NAV.pane ? NAV.c : 0 });
  /* a drive that just appeared with new games: STONE offers to copy them, as a console offers a disc */
  const fresh = EG.usb.filter(d => d.new && !EG.seen.has(d.path));
  EG.usb.forEach(d => EG.seen.add(d.path));
  if (quiet !== true && fresh.length && !EG.copy && ['home', 'library', 'settings'].includes(S.screen)) egAsk(fresh[0]);
}
function egAsk(d) {
  const back = dlgOver();
  play('notify');
  openDlg(`<span class="st-cap">USB</span><h2>JUEGOS EN «${esc(d.label.toUpperCase())}»</h2><p>${d.new} juego${d.new === 1 ? '' : 's'} nuevo${d.new === 1 ? '' : 's'}: ${esc(egSys(d))}. Ocupan ${egGB(d.new_bytes)}.</p>
    <p>STONE los copia a la consola y los añade a tu biblioteca: después siguen funcionando sin el USB.</p>
    <div class="btns"><span class="txt-f" data-f data-b="go">COPIAR A LA CONSOLA</span><span class="txt-f" data-f data-b="no">AHORA NO</span></div>`, {
    onA: el => { back(); if (el.dataset.b === 'go') egCopy(d); else play('back'); }, onB: () => { play('back'); back(); } });
}
function egCopy(d) {
  play('select');
  Bridge.call('usb.copy', d.path).then(() => { EG.copy = { done: 0, total: d.new_bytes, name: '' }; toast(`Copiando ${d.new} juegos del USB…`, false); egRefresh(); },
    e => { play('error'); toast((e && e.message) || 'No se pudo copiar', false); });
}
const egRefresh = () => { if (S.screen === 'settings' && CATS[cat] === 'Emuladores') enterSettings({ pane: !!(NAV && NAV.pane), ri: NAV && NAV.pane ? NAV.c : 0 }); };
Bridge.on('usb', d => {
  if (!d) return;
  if (d.state === 'copying') { EG.copy = d; return egRefresh(); }
  if (d.state !== 'done') return;
  EG.copy = null; delete CX.roms;
  if (d.error) { play('error'); toast(d.error, false); }
  else if (d.canceled) toast(`Copia cancelada: ${d.copied} juego${d.copied === 1 ? '' : 's'} copiado${d.copied === 1 ? '' : 's'}`, false);
  else { play('notify'); longToast(`${d.copied} juego${d.copied === 1 ? '' : 's'} copiado${d.copied === 1 ? '' : 's'} y añadido${d.copied === 1 ? '' : 's'} a tu biblioteca. Ya puedes quitar el USB`, 7000); }
  egScan(true); reloadLibrary();
});
/* «Juegos desde el móvil»: the QR code, what arrives, CERRAR adds them to the library */
async function egDrop() {
  play('select');
  let r = null;
  try { r = await Bridge.call('drop.start'); } catch (e) { play('error'); return toast((e && e.message) || 'No se pudo abrir', false); }
  EG.drop = { got: [], now: null };
  const back = dlgOver();
  openDlg(`<span class="st-cap">DESDE EL MÓVIL</span><h2>ENVÍA TUS JUEGOS</h2>
    <div class="qrrow">${qrSvg(r.url, 240)}<div><p>Escanea el código con el móvil, conectado al mismo Wi-Fi, y elige los juegos. En iPhone, «Archivos» incluye iCloud Drive.</p><p class="url">${esc(r.url.replace(/^http:\/\//, ''))}</p></div></div>
    <p id="egdrop" class="tech">Esperando archivos… (abierto 30 minutos)</p>
    <div class="btns"><span class="txt-f" data-f data-b="end">TERMINAR</span></div>`, {
    onA: () => egDropEnd(back), onB: () => egDropEnd(back) });
}
function egDropLine() {
  const e = $('#egdrop'); if (!e || !EG.drop) return;
  const n = EG.drop.now, got = EG.drop.got;
  e.textContent = (n ? `Recibiendo ${n.name} · ${n.total ? Math.floor(n.done * 100 / n.total) : 0} %` : 'Esperando archivos…')
    + (got.length ? ` · Recibidos: ${got.map(g => `${g.name} (${g.system})`).slice(-4).join(', ')}${got.length > 4 ? ` y ${got.length - 4} más` : ''}` : '');
}
Bridge.on('drop', d => {
  if (!d || !EG.drop) return;
  if (d.state === 'receiving') EG.drop.now = d;
  if (d.state === 'received') { EG.drop.now = null; EG.drop.got.push(d); play('notify'); }
  egDropLine();
});
function egDropEnd(back) {
  play('back'); back();
  const n = EG.drop ? EG.drop.got.length : 0; EG.drop = null;
  Bridge.call('drop.stop').then(() => { delete CX.roms; egRefresh(); if (n) { longToast(`${n} juego${n === 1 ? '' : 's'} recibido${n === 1 ? '' : 's'} y añadido${n === 1 ? '' : 's'} a tu biblioteca`, 6000); reloadLibrary(); } }, () => {});
}
function egAct(r, ri) {
  if (r.act === 'usb') { egAsk(r.drive); return; }
  if (r.act === 'usb-scan') { play('select'); toast('Buscando juegos en los USB conectados…', false); EG.seen.clear(); return egScan(); }
  if (r.act === 'usb-cancel') { play('select'); return Bridge.call('usb.cancel').catch(() => {}); }
  if (r.act === 'drop') return egDrop();
}
/* a drive plugged in is noticed within 10 s, outside games */
setInterval(() => { if (['home', 'library', 'settings'].includes(S.screen) && !S.steamFront) egScan(); }, 10000);
setTimeout(() => egScan(true), 4000);
