/* ---------- INFORME DE DIAGNÓSTICO (Ajustes → Salud), 3.1.0-rc7; «¿Qué no funciona?» in rc8 ----------
   Until now a failure on the console reached the developer as a photo of the TV. STONE gathers what is
   needed to find the cause (its logs, the session's, stoned's, Steam's, the previous boot's errors, and
   whether this Steam still has every function STONE uses) into one file, with nothing personal in it
   (diagreport.py), and the person takes it away with the phone (a QR code) or a USB drive. STONE never
   sends it anywhere by itself.
   rc8: first the person ticks what they saw go wrong; the report then checks every function STONE has
   (diagchecks.py: FUNCIONA / FALLA / ATENCIÓN / SIN DATOS, with the reason) and puts the ticked ones first. */
const DIAG_SYMPTOMS = [['filters', 'Filtros de imagen'], ['colors', 'Colores desvaídos'], ['picture', 'Imagen borrosa o con grano'], ['game', 'Un juego no abre'],
  ['downloads', 'Descargas'], ['sound', 'Sonido'], ['controller', 'Mando'], ['network', 'Wi-Fi o internet'],
  ['steam', 'Steam'], ['emulators', 'Emuladores'], ['other', 'Otra cosa']];
const DIAG_MARK = { ok: 'FUNCIONA', fail: 'FALLA', warn: 'ATENCIÓN', nodata: 'SIN DATOS' };
function diagStart(ri, picked = new Set(), at = 0) {
  play('select');
  const back = () => { closeDlg(); play('back'); enterSettings({ pane: true, ri }); };
  const cell = ([k, l]) => `<span class="txt-f sres" data-f data-k="${k}">${esc(l)}<small>${picked.has(k) ? '✓ Falla' : ''}</small></span>`;
  openDlg(`<span class="st-cap">SALUD · INFORME DE DIAGNÓSTICO</span><h2>¿QUÉ NO FUNCIONA?</h2>
    <p>Marca lo que has visto fallar (o nada) y STONE comprobará cada función.</p>
    <div class="slist two">${DIAG_SYMPTOMS.map(cell).join('')}</div>
    <div class="btns"><span class="txt-f" data-f data-b="go">HACER INFORME</span><span class="txt-f" data-f data-b="no">VOLVER</span></div>`, {
    onA: el => {
      if (el.dataset.b === 'no') return back();
      if (el.dataset.b === 'go') return diagBuild(ri, [...picked]);
      const k = el.dataset.k, r = NAV.r, c = NAV.c;
      if (picked.has(k)) picked.delete(k); else picked.add(k);
      diagStart(ri, picked, r * 2 + c);
    }, onB: back });
  const d = $('#dlg'), cells = [...d.querySelectorAll('.slist [data-f]')], rows = [];
  for (let i = 0; i < cells.length; i += 2) rows.push(cells.slice(i, i + 2));
  NAV = mkNav(rows.concat([[...d.querySelectorAll('.btns [data-f]')]]), { r: Math.floor(at / 2), c: at % 2, place: (el, b) => ({ x: b.x, y: b.y + b.h + 4, w: b.w }) });
  NAV.id = 'dlg'; requestAnimationFrame(() => applyFocus());
}
async function diagBuild(ri, symptoms) {
  play('select');
  const back = () => { closeDlg(); Bridge.call('diag.close').catch(() => {}); play('back'); enterSettings({ pane: true, ri }); };
  openDlg(`<span class="st-cap">SALUD</span><h2>INFORME DE DIAGNÓSTICO</h2><p><i class="spin" aria-hidden="true"></i>Comprobando cada función y reuniendo los registros de STONE, de Steam y del sistema. Tarda unos segundos…</p>`, { onB: back }, true);
  let r = null;
  busy('diag', 'Haciendo el informe');
  try { r = await Bridge.call('diag.build', symptoms); } catch (e) { busy('diag'); closeDlg(); play('error'); toast('No se pudo hacer el informe: ' + ((e && e.message) || 'sin respuesta'), false); return enterSettings({ pane: true, ri }); }
  busy('diag');
  diagShow(r, ri, back);
}
function diagShow(r, ri, back) {
  const s = r.summary || {}, checks = s.checks || [], kb = Math.max(1, Math.round(r.size / 1024));
  const order = { fail: 0, warn: 1, nodata: 2, ok: 3 };
  const top = checks.filter(c => (c.symptom && c.symptom.length) || c.status !== 'ok')
    .sort((a, b) => ((b.symptom || []).length > 0) - ((a.symptom || []).length > 0) || order[a.status] - order[b.status]).slice(0, 5);
  const bad = checks.filter(c => c.status === 'fail');
  play(bad.length ? 'notify' : 'select');
  openDlg(`<span class="st-cap">SALUD</span><h2>INFORME LISTO</h2>
    <div class="slist">${top.length ? top.map(c => `<span class="sres">${esc(c.name)}<small>${DIAG_MARK[c.status] || ''}</small></span>`).join('')
      : `<span class="sres">Todo lo comprobado<small>FUNCIONA</small></span>`}
      <span class="sres">Versión · errores de STONE<small>${esc(s.version || '—')} · ${s.errors || 0}</small></span></div>
    ${bad.length ? `<p class="tech">${bad.slice(0, 2).map(c => esc(c.detail.length > 170 ? c.detail.slice(0, 167) + '…' : c.detail)).join('<br>')}</p>` : ''}
    <p>Sin datos personales: se borran correos, cuentas, contraseñas e IP. Envíalo a quien te ayuda (${kb} KB).</p>
    <div class="btns"><span class="txt-f" data-f data-b="phone">AL MÓVIL</span><span class="txt-f" data-f data-b="usb">A UN USB</span><span class="txt-f" data-f data-b="no">VOLVER</span></div>`, {
    onA: el => {
      const b = el.dataset.b;
      if (b === 'no') return back();
      if (b === 'usb') return diagUsb(r, ri, back);
      return diagPhone(r, ri, back);
    }, onB: back });
}
async function diagPhone(r, ri, back) {
  play('select');
  let x = null;
  try { x = await Bridge.call('diag.phone'); } catch (e) { play('error'); return toast((e && e.message) || 'No se pudo abrir', false); }
  openDlg(`<span class="st-cap">SALUD</span><h2>LLÉVATELO AL MÓVIL</h2>
    <div class="qrrow">${qrSvg(x.download, 240)}<div><p>Escanea el código con el móvil conectado al mismo Wi-Fi: se descarga «${esc(r.name)}». Después envíalo como archivo adjunto.</p>
    <p class="url">${esc(x.download.replace(/^http:\/\//, ''))}</p></div></div>
    <div class="btns"><span class="txt-f" data-f data-b="ok">LISTO</span><span class="txt-f" data-f data-b="no">VOLVER</span></div>`, {
    onA: el => el.dataset.b === 'no' ? diagShow(r, ri, back) : back(), onB: () => diagShow(r, ri, back) });
}
async function diagUsb(r, ri, back) {
  play('select'); toast('Copiando el informe al USB…', false);
  const x = await Bridge.call('diag.usb').catch(e => ({ error: (e && e.message) || 'No se pudo copiar' }));
  if (x.error) { play('error'); return toast(x.error === 'No hay ningún USB conectado' ? 'Conecta un pendrive y vuelve a pulsar «A UN USB»' : x.error, false); }
  play('notify'); toast(`Informe guardado en el USB «${x.drive}». Ya puedes quitarlo`, false);
}
/* A look STONE turned off (optimizer.finish, rc8: only after two early ends in a row) is said, never silent. */
Bridge.on('game', d => {
  const e = d && d.ended;
  if (!e || !e.healed) return;
  const g = G.find(x => String(x.appid) === String(e.appid));
  toast(`STONE quitó el aspecto de ${g ? g.n : 'un juego'}: se cerró dos veces nada más empezar. Puedes volver a elegirlo en su página`, false);
});
