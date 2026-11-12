/* ---------- INSTALL, UNINSTALL AND DOWNLOADS (3.1.0-rc2) ----------
   The host follows Steam's install wizard and proves the result with Steam's own files (host.m_install):
   STONE says what really happened, in its own words, instead of "instalando" whatever Steam did
   (board, 12-11-2026: games that never installed and nothing said why). The download's progress is
   shown on the game's page and on the loading screen when Steam updates a game before opening it. */
const DL = { at: {}, t: 0, want: 0, busy: new Set() };
const dlPct = d => d && d.progress != null ? `${Math.round(d.progress * 100)} %` : '';
const dlGB = b => b >= 2 ** 30 ? `${(b / 2 ** 30).toFixed(1).replace('.', ',')} GB` : `${Math.max(1, Math.round(b / 2 ** 20))} MB`;
/* Look at Steam's downloads for a while (an install was asked, a game page or a loading screen is open). */
function dlKick(ms = 0) {
  DL.want = Math.max(DL.want, Date.now() + ms);
  if (!DL.t) DL.t = setTimeout(dlTick, 1200);
}
function dlFocus() {
  if (S.launching !== null && G[S.launching]) return G[S.launching];
  return S.screen === 'detail' ? G[curG] : null;
}
async function dlTick() {
  DL.t = 0;
  const g = dlFocus();
  const watch = Date.now() < DL.want || (g && (g.upd || !g.inst || DL.at[g.appid]));
  if (!watch) return;
  if (!S.dormant) {
    const r = await Sys.downloads().catch(() => null);
    if (r && Array.isArray(r.downloads)) { DL.at = {}; r.downloads.forEach(d => { DL.at[d.appid] = d; }); dlShow(); }
  }
  DL.t = setTimeout(dlTick, 3000);
}
function dlShow() {
  if (S.screen === 'detail' && G[curG]) {
    const g = G[curG], d = DL.at[g.appid], el = $('#dprim');
    if (el && S.running !== g.i && !DL.busy.has(g.appid)) {
      const st = $('#dstate'), canPlay = g.inst || g.src === 'shortcut';
      if (d) {
        el.textContent = g.inst ? `ACTUALIZANDO${dlPct(d) ? ' · ' + dlPct(d) : '…'}` : `INSTALANDO${dlPct(d) ? ' · ' + dlPct(d) : '…'}`;
        if (st) st.textContent = `${g.inst ? 'Actualizando' : 'Descargando'} en Steam${d.total ? ` · ${dlGB(d.downloaded)} de ${dlGB(d.total)}` : ''}`;
      } else if (/^(INSTALANDO|ACTUALIZANDO)/.test(el.textContent)) {
        /* the download ended: the page says what the game is now */
        el.textContent = canPlay ? 'JUGAR' : g.upd ? 'INSTALANDO…' : 'INSTALAR';
        if (st) st.textContent = g.upd ? (g.inst ? 'Actualizando en Steam' : 'Instalándose') : g.inst ? 'Instalado' : 'En tu cuenta · sin instalar';
      }
    }
  }
  if (S.launching !== null && G[S.launching]) {
    const g = G[S.launching], d = DL.at[g.appid], gm = $('#game');
    if (d && gm && gm.querySelector('.ld-step')) {
      /* Steam updates the game before opening it: say so, and do not call it stalled while it advances */
      ldT.forEach(clearTimeout); ldT = [];
      gm.querySelector('.ld-step').textContent = `STEAM ACTUALIZA EL JUEGO${dlPct(d) ? ' · ' + dlPct(d) : ''}`;
      gm.querySelector('.ld-note').textContent = d.total ? `${dlGB(d.downloaded)} de ${dlGB(d.total)}. El juego se abre solo al terminar; B vuelve al inicio y la descarga sigue.` : 'El juego se abre solo al terminar; B vuelve al inicio y la descarga sigue.';
      const key = `${d.downloaded}`;
      if (key !== DL.lastLaunch) { DL.lastLaunch = key; clearTimeout(launchT); launchT = setTimeout(() => launchStalled(g), 90000); }
    }
  }
}
/* INSTALAR: Steam's answer, said by STONE. Returns true when the install is under way. */
async function installGame(appid, name, opts = {}) {
  if (DL.busy.has(appid)) { play('error'); toast('Esperando la respuesta de Steam…', false); return false; }
  DL.busy.add(appid);
  if (!opts.quiet) toast(`${name}: pidiendo la instalación a Steam…`, false);
  let r = null;
  try { r = await Sys.install(appid); }
  catch (e) { DL.busy.delete(appid); play('error'); toast(ERR_TEXT[e.code] || e.message, false); return false; }
  DL.busy.delete(appid);
  return installAnswer(r || {}, appid, name, opts);
}
function installAnswer(r, appid, name, opts) {
  const again = () => installGame(appid, name, opts);
  switch (r.state) {
    case 'queued':
      steamWatch(20000); dlKick(120000); play('notify');
      longToast(`${name}: Steam lo está instalando. El avance se ve en su ficha y en Ajustes → Almacenamiento`, 7000);
      return true;
    case 'unconfirmed':
      steamWatch(30000); dlKick(120000);
      longToast(`${name}: Steam aceptó la instalación. La descarga aparece en cuanto empiece`, 8000);
      return true;
    case 'steam-dialog':
      longToast('Steam pide confirmar la instalación en su propia ventana', 6000);
      steamOpen('install');
      return true;
    case 'eula':
      installDlg(name, 'Este juego tiene un contrato de licencia (EULA) que debes leer y aceptar tú. Steam lo muestra en su propia ventana; al aceptarlo, la instalación sigue sola.',
        [['VER EN STEAM', () => steamOpen('install')], ['AHORA NO', () => Sys.installCancel().catch(() => {})]]);
      return false;
    case 'asks':
      installDlg(name, 'Steam necesita un dato que solo tú puedes darle (una clave del producto o una contraseña). Lo pide en su propia ventana.',
        [['VER EN STEAM', () => steamOpen('install')], ['AHORA NO', () => Sys.installCancel().catch(() => {})]]);
      return false;
    case 'space':
      installDlg(name, `No cabe: necesita ${dlGB(r.need || 0)} y quedan ${dlGB(r.free || 0)} libres. Libera espacio en Ajustes → Almacenamiento y vuelve a intentarlo.`,
        [['ENTENDIDO', null]]);
      return false;
    case 'canceled':
      toast(`${name}: Steam canceló la instalación`, false);
      return false;
    case 'failed':
      installDlg(name, `Steam no pudo instalarlo${r.detail ? ` (${r.detail})` : ''}. Suele ser la conexión o un servidor de Steam ocupado.`,
        [['REINTENTAR', again], ['VER EN STEAM', () => steamOpen('install')], ['CERRAR', null]]);
      return false;
    default:
      installDlg(name, 'Steam no respondió. Si la consola acaba de encenderse, Steam puede estar arrancando o actualizándose: espera un momento y vuelve a intentarlo.',
        [['REINTENTAR', again], ['VER EN STEAM', () => steamOpen('install')], ['CERRAR', null]]);
      return false;
  }
}
function installDlg(name, text, buttons) {
  const back = dlgOver();
  play('notify');
  openDlg(`<span class="st-cap">INSTALAR</span><h2>${esc(name.toUpperCase())}</h2><p>${esc(text)}</p>
    <div class="btns">${buttons.map(([l], i) => `<span class="txt-f" data-f data-i="${i}">${l}</span>`).join('')}</div>`, {
    onA: el => { const fn = buttons[+el.dataset.i][1]; play('select'); back(); if (fn) fn(); },
    onB: () => { play('back'); back(); } });
}
/* DESINSTALAR: done by Steam without its dialog; STONE waits until Steam's files say it is gone. */
function uninstallGame(appid, name) {
  toast(`${name}: desinstalando…`, false);
  return Bridge.call('storage.uninstall', appid).then(r => {
    if (r && r.state === 'steam-dialog') { longToast('Steam pide confirmar en su propia ventana', 6000); return steamOpen('install'); }
    steamWatch(15000);
    toast(r && r.state === 'removed' ? `${name} se desinstaló` : `${name}: Steam lo sigue desinstalando`, false);
  }, e => { play('error'); toast((e && e.message) || 'No se pudo desinstalar', false); });
}
