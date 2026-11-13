/* ---------- STEAM IN FRONT (D-34) ----------
   Signing in and paying are done in Steam's own interface: STONE never sees a password or a card.
   In the STONE session Steam runs hidden, so STONE asks the session for Steam's window (steam.show):
   the session puts it in front and gives the screen back with the guide button, when Steam closes
   it or when the sign-in is done. While it is in front STONE ignores the controller (it is Steam's).
   If Steam shows no window, plan B hands the whole session to Steam's own Game Mode interface. */
const SF_TEXT = {
  login: ['INICIA SESIÓN EN STEAM', 'Steam muestra ahora su propia ventana. Escanea su código QR con la app de Steam del móvil, o escribe tu usuario con un teclado. STONE nunca ve tu contraseña.'],
  store: ['ABRIENDO LA TIENDA DE STEAM', 'La tienda y el pago son de Steam: se usan tu cuenta y tu forma de pago de Steam. Lo que compres aparece después en tu biblioteca de STONE.'],
  app: ['ABRIENDO EL JUEGO EN STEAM', 'La compra se hace en Steam, con tu cuenta y tu forma de pago. Al volver, STONE instala el juego en cuanto Steam lo añada a tu cuenta.'],
  install: ['STEAM PREGUNTA EN SU VENTANA', 'Responde en la ventana de Steam. Cuando termines, o para dejarlo para después, el botón guía del mando vuelve a STONE.']
};
let sfT = 0;
function sfVeil(what, title, text) {
  let v = $('#sfront');
  if (!v) {
    v = document.createElement('div'); v.id = 'sfront';
    v.innerHTML = '<div class="sf-box"><span class="st-cap">STEAM</span><h2></h2><p></p><div class="sf-foot"><span class="g">STONE</span>El botón guía del mando vuelve a STONE</div></div>';
    stage.appendChild(v);
  }
  if (!what) return v.classList.remove('on', 'now');
  v.querySelector('h2').textContent = title || SF_TEXT[what][0];
  v.querySelector('p').textContent = text || SF_TEXT[what][1];
  v.classList.add('on');
}
/* Steam is not up yet (the first start of a new console downloads Steam's own update, which takes minutes) */
const SF_WAIT = ['PREPARANDO STEAM', 'Steam todavía está arrancando. Si la consola acaba de instalarse, primero descarga su propia actualización: puede tardar unos minutos. Su ventana aparece aquí en cuanto esté lista.'];
async function steamOpen(what, appid) {
  if (S.steamFront) return;
  if (S.running !== null) { play('error'); return toast('Cierra antes el juego en curso: Steam ocuparía su lugar en la pantalla', false); }
  play('select');
  let r = null;
  try { r = await (appid && (what === 'app' || what === 'install') ? Sys.steamShow(what, appid) : Sys.steamShow(what)); }
  catch (e) { return steamNoWindow(what, appid); }
  if (!r.managed) {
    /* not the STONE session (Steam's own Game Mode, or development): Steam shows its pages itself */
    return toast(what === 'login' ? 'Steam muestra su inicio de sesión en su propia pantalla' : 'Steam abre su tienda en su propia pantalla', false);
  }
  S.steamFront = { what, appid: appid || null, t: Date.now() };
  line.classList.add('off'); $('#hints').classList.add('hide');
  sfVeil(what);
  clearInterval(sfT); sfT = setInterval(sfCheck, 5000);
}
/* The host says when Steam's window leaves the front and why: closed (guide button, Steam closed it,
   a game started), signed (the sign-in is done) or nowindow (Steam showed nothing). */
function sfEnd(why) {
  const fr = S.steamFront;
  if (!fr) return;
  S.steamFront = null; clearInterval(sfT); sfVeil(null);
  line.classList.remove('off'); applyFocus(); showHints(); armIdleOff();
  if (why === 'nowindow') return steamNoWindow(fr.what, fr.appid);
  if (why === 'signed') { play('notify'); longToast('Sesión iniciada en Steam. STONE está leyendo tu biblioteca…', 7000); }
  else toast(fr.what === 'login' ? 'De vuelta en STONE' : 'De vuelta en STONE. Lo que hayas comprado aparece en tu biblioteca', false);
  if (typeof SU !== 'undefined' && SU && SU.cur && SU.cur.key === 'steam') Sys.firstrunStatus().then(f => { SU.fr = f; if (SU && SU.cur && SU.cur.key === 'steam') SU_FN.steam(); }, () => {});
  S.steamAcct = undefined;
  reloadLibrary();
}
Bridge.on('steam', d => {
  if (!d) return;
  if (d.front === false) return sfEnd(d.why);
  if (S.steamFront && d.waiting) sfVeil(S.steamFront.what, SF_WAIT[0], SF_WAIT[1]);
  else if (S.steamFront && d.shown && !S.steamFront.full) sfVeil(S.steamFront.what);
});
/* If the event was lost (the host restarted), the lock never stays on: the host is asked. */
function sfCheck() {
  if (!S.steamFront) return clearInterval(sfT);
  Sys.steamStatus().then(st => { if (S.steamFront && st && st.front === false && Date.now() - S.steamFront.t > 4000) sfEnd('closed'); }, () => {});
}
function longToast(msg, ms) {
  toast(msg, false);
  clearTimeout(toastT); toastT = setTimeout(() => $('#toast').classList.remove('on'), ms);
}
/* What was under the dialog comes back as it was (dialogs here are opened over any screen). */
function dlgOver() {
  const scr = S.screen === 'dlg' && dlgPrev ? dlgPrev.screen : S.screen, nav = NAV;
  return () => { closeDlg(); S.screen = scr; NAV = nav; if (NAV) { line.classList.remove('off'); requestAnimationFrame(() => applyFocus()); } };
}
function steamNoWindow(what, appid) {
  const back = dlgOver();
  play('notify');
  const buy = what === 'app' && appid;
  openDlg(`<span class="st-cap">STEAM</span><h2>STEAM NO MOSTRÓ SU VENTANA</h2>
    <p>STONE pidió a Steam su ventana y no apareció. Si la consola acaba de encenderse, espera un minuto y vuelve a intentarlo.</p>
    <p>Hay otro camino: Steam ocupa toda la pantalla con su propia interfaz, hecha para el mando, y STONE vuelve después.</p>
    <div class="btns"><span class="txt-f" data-f data-b="full">STEAM COMPLETO</span>${buy ? '<span class="txt-f" data-f data-b="qr">CON EL MÓVIL</span>' : ''}<span class="txt-f" data-f data-b="no">VOLVER</span></div>`, {
    onA: el => {
      const b = el.dataset.b; play(b === 'no' ? 'back' : 'select'); back();
      if (b === 'full') return steamFullAsk(what === 'login' ? 'login' : 'store');
      if (b === 'qr') return storeQr(appid);
    }, onB: () => { play('back'); back(); } });
}
/* Plan B: Steam's own Game Mode interface takes the session (the session supervisor stops STONE Home
   and starts it again afterwards). */
function steamFullAsk(why) {
  if (S.running !== null) { play('error'); return toast('Cierra antes el juego en curso: al cambiar a Steam se cerraría sin guardar', false); }
  const back = dlgOver();
  openDlg(`<span class="st-cap">STEAM COMPLETO</span><h2>STEAM OCUPA LA PANTALLA</h2>
    <p>STONE se cierra un momento y Steam abre su propia interfaz, con su tienda y su inicio de sesión.</p>
    <p>${why === 'login' ? 'Cuando inicies sesión, STONE vuelve sola. Para volver antes,' : 'Para volver a STONE,'} mantén pulsado el botón guía del mando 3 segundos; reiniciar la consola también vuelve a STONE.</p>
    <div class="btns"><span class="txt-f" data-f data-b="no">CANCELAR</span><span class="txt-f" data-f data-b="yes">ABRIR STEAM</span></div>`, {
    onA: el => {
      if (el.dataset.b !== 'yes') { play('back'); return back(); }
      play('select'); back();
      Sys.steamFull(why).then(() => {
        S.steamFront = { what: why, appid: null, t: Date.now(), full: true };
        line.classList.add('off'); $('#hints').classList.add('hide');
        /* STONE Home is stopped within a second: the veil is whole at once, not caught half-way
           through its fade with the page showing through (board, 3.1.0-rc3) */
        sfVeil(why, 'CAMBIANDO A STEAM', 'Steam abre su propia interfaz. Para volver a STONE: mantén pulsado el botón guía 3 segundos.');
        $('#sfront').classList.add('now');
        /* the supervisor stops STONE Home in about a second; if it does not, the lock is released */
        setTimeout(() => { if (S.steamFront && S.steamFront.full) { S.steamFront = null; sfVeil(null); line.classList.remove('off'); applyFocus(); toast('Steam no tomó la pantalla. Reinicia la consola e inténtalo de nuevo', false); } }, 20000);
      }, e => { play('error'); toast(e && e.code === 'Unsupported' ? 'Solo disponible en la sesión STONE de la consola' : 'No se pudo cambiar a Steam', false); });
    }, onB: () => { play('back'); back(); } });
}
/* What STONE knows about Steam, said on the console itself (Ajustes → Steam → Estado de Steam). */
async function steamStatusDlg() {
  const back = dlgOver();
  const st = await Sys.steamStatus().catch(() => null);
  const kv = (k, v) => `<span class="sres">${k}<small>${esc(v)}</small></span>`;
  const rows = !st ? '<p>No se pudo leer el estado.</p>' : `<div class="slist">
    ${kv('Carpeta de Steam', st.root_found ? 'Encontrada' : 'No encontrada: Steam no ha arrancado nunca')}
    ${kv('Interfaz de Steam', st.interface === true ? 'Responde' : st.interface === false ? 'No responde (Steam está arrancando o cerrado)' : 'Sin dato')}
    ${kv('Cuenta en esta consola', st.account ? 'Sí' : 'Ninguna: falta iniciar sesión')}
    ${kv('Sesión de Steam', st.logged === 'in' ? 'Iniciada' : st.logged === 'out' ? 'Sin iniciar' : 'Steam todavía no lo ha dicho')}
    ${kv('Juegos de la cuenta', st.owned_known ? 'Leídos de Steam ahora' : st.owned_cached ? 'Los que Steam dio la última vez' : 'Todavía sin leer: solo los instalados')}
    ${kv('Sesión de la consola', st.session === 'stone' ? 'STONE' : 'Otra (Steam o escritorio)')}</div>`;
  openDlg(`<span class="st-cap">DIAGNÓSTICO</span><h2>ESTADO DE STEAM</h2>${rows}
    <div class="btns"><span class="txt-f" data-f data-b="no">VOLVER</span></div>`, { onA: () => { play('back'); back(); }, onB: () => { play('back'); back(); } });
}
