/* ---------- INFORME DE DIAGNÓSTICO (Ajustes → Salud), 3.1.0-rc7 ----------
   Until now a failure on the console reached the developer as a photo of the TV. STONE gathers what is
   needed to find the cause (its logs, the session's, stoned's, Steam's, the previous boot's errors, and
   whether this Steam still has every function STONE uses) into one file, with nothing personal in it
   (diagreport.py), and the person takes it away with the phone (a QR code) or a USB drive. STONE never
   sends it anywhere by itself. */
async function diagStart(ri) {
  play('select');
  const back = () => { closeDlg(); Bridge.call('diag.close').catch(() => {}); play('back'); enterSettings({ pane: true, ri }); };
  openDlg(`<span class="st-cap">SALUD</span><h2>INFORME DE DIAGNÓSTICO</h2><p>Reuniendo los registros de STONE, de Steam y del sistema. Tarda unos segundos…</p>`, { onB: back }, true);
  let r = null;
  try { r = await Bridge.call('diag.build'); } catch (e) { closeDlg(); play('error'); toast('No se pudo hacer el informe: ' + ((e && e.message) || 'sin respuesta'), false); return enterSettings({ pane: true, ri }); }
  diagShow(r, ri, back);
}
function diagShow(r, ri, back) {
  const s = r.summary || {}, f = s.findings || [], sf = s.steam_functions || {};
  const kb = Math.max(1, Math.round(r.size / 1024));
  play(f.length ? 'notify' : 'select');
  openDlg(`<span class="st-cap">SALUD</span><h2>INFORME LISTO</h2>
    <div class="slist"><span class="sres">Versión<small>${esc(s.version || '—')}</small></span>
      <span class="sres">Errores de STONE en este arranque<small>${s.errors || 0}</small></span>
      <span class="sres">Funciones de Steam que STONE usa<small>${sf.missing === null || sf.missing === undefined ? 'Steam no respondió' : sf.missing.length ? `faltan ${sf.missing.length}` : 'todas presentes'}</small></span>
      <span class="sres">Hallazgos<small>${f.length ? f.length : 'ninguno'}</small></span></div>
    ${f.length ? `<p class="tech">${f.slice(0, 4).map(esc).join('<br>')}</p>` : ''}
    <p>Sin datos personales: se borran correos, cuentas, contraseñas e IP. Llévalo y envíalo a quien te ayuda (${kb} KB).</p>
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
