/* ---------- INSTALL, UNINSTALL AND DOWNLOADS ----------
   Games are downloaded and installed from STONE, without going into Steam's own interface. The host
   drives Steam's install wizard as Steam's interface does and proves the result with Steam's own files
   (host.m_install); what Steam asks comes back here: a licence agreement is shown by STONE (its
   address as a QR code for the phone) and the person's acceptance is passed on to Steam.
   The bar: Steam's live downloads (host.m_downloads) on the game's page, on its cover in Home and in
   the Library, and in the status at the top right. 3.1.0-rc4, after the board of 12-11-2026. */
const DL = { at: {}, t: 0, want: 0, busy: new Set(), live: false, seen: new Set(), lastLaunch: '' };
const DL_STAGE = { download: 'Descargando', prealloc: 'Reservando espacio en disco', install: 'Instalando', verify: 'Verificando archivos',
  queued: 'En cola', paused: 'En pausa' };
const dlGB = b => b >= 2 ** 30 ? `${(b / 2 ** 30).toFixed(1).replace('.', ',')} GB` : `${Math.max(1, Math.round(b / 2 ** 20))} MB`;
const dlPct = d => d && d.progress != null ? `${Math.min(100, Math.floor(d.progress * 100))} %` : '';
const dlRate = r => r >= 2 ** 20 ? `${(r / 2 ** 20).toFixed(1).replace('.', ',')} MB/s` : r > 0 ? `${Math.max(1, Math.round(r / 1024))} kB/s` : '';
function dlEta(s) {
  if (s == null || s < 0) return '';
  if (s < 90) return 'falta 1 min';
  if (s < 3600) return `faltan ${Math.round(s / 60)} min`;
  const h = Math.floor(s / 3600), m = Math.round((s % 3600) / 60);
  return `faltan ${h} h${m ? ' ' + m + ' min' : ''}`;
}
/* One line that says how far a download is: "12,4 de 54,0 GB · 35,2 MB/s · faltan 20 min" */
function dlLine(d) {
  const a = [];
  if (d.total && (d.stage === 'download' || d.stage === 'paused' || d.stage === 'queued')) a.push(`${dlGB(d.downloaded)} de ${dlGB(d.total)}`);
  if (d.stage === 'download') { const r = dlRate(d.rate), e = dlEta(d.eta); if (r) a.push(r); if (e) a.push(e); }
  if (d.stage === 'install' || d.stage === 'verify' || d.stage === 'prealloc') a.push('Steam prepara los archivos del juego');
  if (d.stage === 'queued') a.push('empieza cuando termine la descarga en curso');
  return a.join(' · ');
}
/* Look at Steam's downloads now (an install was asked, a game is opening). */
function dlKick(ms = 0) {
  DL.want = Math.max(DL.want, Date.now() + ms);
  clearTimeout(DL.t); DL.t = setTimeout(dlTick, 900);
}
async function dlTick() {
  DL.t = 0;
  if (!S.dormant && S.screen !== 'off' && S.screen !== 'asleep') {
    const r = await Sys.downloads().catch(() => null);
    if (r && Array.isArray(r.downloads)) {
      const now = {};
      r.downloads.forEach(d => { now[d.appid] = d; });
      const ended = [...DL.seen].filter(id => !now[id]);
      DL.at = now; DL.live = !!r.live; DL.seen = new Set(Object.keys(now));
      dlShow();
      if (ended.length) dlEnded(ended);
    }
  }
  clearTimeout(DL.t);
  DL.t = setTimeout(dlTick, Object.keys(DL.at).length || Date.now() < DL.want ? 2500 : 20000);
}
/* A download left Steam's list: the library says whether the game is ready now */
async function dlEnded(ids) {
  await reloadLibrary();
  ids.forEach(id => {
    const g = G.find(x => x.appid === id);
    if (g && g.inst && !g.upd) { play('notify'); longToast(`${g.n} está listo para jugar`, 7000); }
  });
  dlShow();
}
function dlBarHTML() {
  return '<div class="dl" id="ddl"><div class="dl-top"><b id="ddl-ph"></b><span id="ddl-pc"></span></div><div class="dl-bar" id="ddl-bar"><i></i></div><div class="dl-sub" id="ddl-sub"></div></div>';
}
function dlShow() {
  /* the game's page */
  if (S.screen === 'detail' && G[curG]) {
    const g = G[curG], d = DL.at[g.appid], el = $('#dprim'), box = $('#ddl'), st = $('#dstate');
    const canPlay = g.inst || g.src === 'shortcut';
    if (box) {
      box.classList.toggle('on', !!d);
      if (d) {
        $('#ddl-ph').textContent = (g.inst && d.stage === 'download' ? 'Actualizando' : DL_STAGE[d.stage] || 'Descargando');
        $('#ddl-pc').textContent = dlPct(d);
        const bar = $('#ddl-bar'); bar.classList.toggle('wait', d.progress == null || d.stage === 'queued');
        bar.firstChild.style.width = d.progress == null ? '' : `${Math.max(1, Math.min(100, d.progress * 100)).toFixed(1)}%`;
        $('#ddl-sub').textContent = dlLine(d);
      }
    }
    if (el && S.running !== g.i && !DL.busy.has(g.appid)) {
      if (d) {
        el.textContent = g.inst ? 'ACTUALIZANDO' : d.stage === 'queued' ? 'EN COLA' : d.stage === 'paused' ? 'EN PAUSA' : 'INSTALANDO';
        if (st) st.textContent = `${g.inst ? 'Actualizando' : DL_STAGE[d.stage] || 'Descargando'}${dlPct(d) ? ' · ' + dlPct(d) : ''}`;
      } else if (/^(INSTALANDO|ACTUALIZANDO|EN COLA|EN PAUSA)/.test(el.textContent)) {
        /* the download ended: the page says what the game is now */
        el.textContent = canPlay ? 'JUGAR' : g.upd ? 'INSTALANDO…' : 'INSTALAR';
        if (st) st.textContent = g.upd ? (g.inst ? 'Actualizando en Steam' : 'Instalándose') : g.inst ? 'Instalado' : 'En tu cuenta · sin instalar';
      }
    }
  }
  /* the covers of Home and of the Library */
  document.querySelectorAll('#home .card[data-g], #library .card[data-g]').forEach(c => {
    const g = G[+c.dataset.g], d = g && DL.at[g.appid];
    let b = c.querySelector('.cdl');
    if (!d) { if (b) b.remove(); return; }
    if (!b) { b = document.createElement('span'); b.className = 'cdl'; b.innerHTML = '<em></em><span><i></i></span>'; c.appendChild(b); }
    b.firstChild.textContent = d.stage === 'queued' ? 'En cola' : d.stage === 'paused' ? 'En pausa' : dlPct(d) || 'Descargando';
    b.lastChild.classList.toggle('wait', d.progress == null || d.stage === 'queued');
    b.lastChild.firstChild.style.width = d.progress == null ? '' : `${Math.max(2, Math.min(100, d.progress * 100)).toFixed(1)}%`;
  });
  /* the status at the top right: the download in progress, whatever screen is open */
  const act = Object.values(DL.at).find(d => d.stage !== 'queued' && d.stage !== 'paused') || Object.values(DL.at)[0];
  let chip = $('#dlst');
  if (!chip && act && $('#status')) { chip = document.createElement('span'); chip.id = 'dlst'; $('#status').insertBefore(chip, $('#clock')); }
  if (chip) { chip.hidden = !act; if (act) chip.textContent = `↓ ${dlPct(act) || (DL_STAGE[act.stage] || '').toLowerCase()}`; }
  /* a game that Steam updates before opening it */
  if (S.launching !== null && G[S.launching]) {
    const g = G[S.launching], d = DL.at[g.appid], gm = $('#game');
    if (d && gm && gm.querySelector('.ld-step')) {
      ldT.forEach(clearTimeout); ldT = [];
      gm.querySelector('.ld-step').textContent = `STEAM ACTUALIZA EL JUEGO${dlPct(d) ? ' · ' + dlPct(d) : ''}`;
      gm.querySelector('.ld-note').textContent = `${dlLine(d) || 'Descargando la actualización'}. El juego se abre solo al terminar; B vuelve al inicio y la descarga sigue.`;
      const key = `${d.downloaded}|${d.progress}`;
      if (key !== DL.lastLaunch) { DL.lastLaunch = key; clearTimeout(launchT); launchT = setTimeout(() => launchStalled(g), 90000); }
    }
  }
}
/* Screens are redrawn whole: the bars go back on their covers at once, not at the next reading */
const dlShowScreen = showScreen;
showScreen = function (...a) { const r = dlShowScreen(...a); if (Object.keys(DL.at).length) setTimeout(dlShow, 0); return r; };
setTimeout(() => dlKick(), 9000);

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
/* What Steam's wizard did, step by step: in a photo of the message it says where Steam stopped */
const installTrace = r => r && r.trace && r.trace.length ? `Detalle técnico: Steam ${r.trace.join(' › ')}${r.detail ? ' · ' + r.detail : ''}` : (r && r.detail ? `Detalle técnico: ${r.detail}` : '');
function installAnswer(r, appid, name, opts) {
  const again = () => installGame(appid, name, opts);
  const inSteam = () => steamOpen('install', appid);
  switch (r.state) {
    case 'queued':
      steamWatch(20000); dlKick(180000); play('notify');
      longToast(`${name}: descarga en marcha. El avance se ve en su ficha y en su carátula`, 7000);
      return true;
    case 'unconfirmed':
      steamWatch(30000); dlKick(180000);
      longToast(`${name}: Steam aceptó la instalación. La descarga aparece en cuanto empiece`, 8000);
      return true;
    case 'steam-dialog':
      longToast('Steam pide confirmar la instalación en su propia ventana', 6000);
      steamOpen('install');
      return true;
    case 'eula':
      eulaDlg(appid, name, r.eulas || [], opts, 0);
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
      installDlg(name, 'Steam no pudo instalarlo. Suele ser la conexión o un servidor de Steam ocupado.',
        [['REINTENTAR', again], ['VER EN STEAM', inSteam], ['CERRAR', null]], installTrace(r));
      return false;
    default:
      installDlg(name, 'Steam no empezó la instalación. Si la consola acaba de encenderse, Steam puede estar arrancando o actualizándose: espera un momento y vuelve a intentarlo.',
        [['REINTENTAR', again], ['VER EN STEAM', inSteam], ['CERRAR', null]], installTrace(r));
      return false;
  }
}
function installDlg(name, text, buttons, tech) {
  const back = dlgOver();
  play('notify');
  openDlg(`<span class="st-cap">INSTALAR</span><h2>${esc(name.toUpperCase())}</h2><p>${esc(text)}</p>${tech ? `<p class="tech">${esc(tech)}</p>` : ''}
    <div class="btns">${buttons.map(([l], i) => `<span class="txt-f" data-f data-i="${i}">${l}</span>`).join('')}</div>`, {
    onA: el => { const fn = buttons[+el.dataset.i][1]; play('select'); back(); if (fn) fn(); },
    onB: () => { play('back'); back(); } });
}
/* A licence agreement (EULA): the person reads it on the phone and answers here; STONE tells Steam.
   Nothing is accepted for them: the answer in focus is "no". */
function eulaDlg(appid, name, eulas, opts, k) {
  const e = eulas[k], back = dlgOver(), qr = e ? qrSvg(e.url, 260) : '';
  play('notify');
  if (!e) {
    return installDlg(name, 'Este juego tiene un contrato de licencia y Steam no entregó su dirección. Steam lo muestra en su propia ventana.',
      [['VER EN STEAM', () => steamOpen('install')], ['AHORA NO', () => Sys.installCancel().catch(() => {})]]);
  }
  openDlg(`<span class="st-cap">CONTRATO DE LICENCIA${eulas.length > 1 ? ` · ${k + 1} DE ${eulas.length}` : ''}</span><h2>${esc(name.toUpperCase())}</h2>
    <div class="qrrow">${qr}<div><p>Este juego pide aceptar su contrato de licencia antes de instalarse. Léelo en el móvil${qr ? ' con este código' : ''}.</p>
    <p>Si lo aceptas, STONE se lo comunica a Steam y la instalación sigue sola.</p><p class="url">${esc(e.url.slice(8))}</p></div></div>
    <div class="btns"><span class="txt-f" data-f data-b="no">NO ACEPTO</span><span class="txt-f" data-f data-b="yes">ACEPTO E INSTALAR</span></div>`, {
    onA: el => {
      play('select'); back();
      if (el.dataset.b !== 'yes') { toast(`${name}: no se instala sin aceptar su contrato`, false); return Sys.installCancel().catch(() => {}); }
      if (k + 1 < eulas.length) return eulaDlg(appid, name, eulas, opts, k + 1);
      eulaAccept(appid, name, opts);
    },
    onB: () => { play('back'); back(); Sys.installCancel().catch(() => {}); } });
}
async function eulaAccept(appid, name, opts) {
  DL.busy.add(appid);
  toast(`${name}: comunicando tu aceptación a Steam…`, false);
  let r = null;
  try { r = await Sys.installAcceptEula(appid); }
  catch (e) { DL.busy.delete(appid); play('error'); toast(ERR_TEXT[e.code] || e.message, false); return false; }
  DL.busy.delete(appid);
  const ok = installAnswer(r || {}, appid, name, opts);
  if (S.screen === 'detail') dlShow();
  return ok;
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
