/* ---------- POWER ---------- */
let powerFrom = 'home';
function openPower() {
  powerFrom = S.screen === 'game' ? 'game' : S.screen;
  S.screen = 'power';
  const box = $('#power .box');
  box.innerHTML = `<div class="h">ENERGÍA</div>
    <div class="main txt-f" data-f data-act="off">APAGAR</div>
    <div class="txt-f" style="font-size:26px" data-f data-act="reboot">Reiniciar</div>
    ${S.running !== null && G[S.running] ? `<div class="warn">${esc(G[S.running].n)} se cerrará al apagar o reiniciar.</div>` : ''}`;
  $('#power').classList.add('on'); line.classList.remove('off');
  const items = [...box.querySelectorAll('[data-f]')];
  NAV = mkNav(items.map(e => [e]), { place: (el, b) => ({ x: b.x, y: b.y + b.h + 8, w: b.w }) });
  NAV.id = 'power';
  setTimeout(() => applyFocus(), S.rm ? 60 : 200);
  hints([['A', 'Elegir'], ['B', 'Cerrar']]);
}
function closePower() {
  play('back'); $('#power').classList.remove('on');
  if (powerFrom === 'game') { S.screen = 'game'; NAV = null; line.classList.add('off'); $('#hints').classList.add('hide'); return; }
  if (powerFrom === 'settings') return enterSettings();
  if (NAV) NAV.id = '';
  enterHome({ r: 1, c: 3 });
}
async function powerA(el) {
  const a = el.dataset.act; play('select');
  $('#power').classList.remove('on');
  if (a === 'off') return shutdown(false);
  if (a === 'reboot') return shutdown(true);
}
/* The animation plays, then logind powers off. stoned's clean-shutdown marker is written by
   systemd when its unit stops, whatever started the shutdown. */
async function shutdown(reboot) {
  S.screen = 'transition'; $('#hints').classList.add('hide'); play('stop');
  chrome(false, false);
  $('#black').classList.remove('fast'); $('#black').classList.add('on');
  setLine(720, 886, 480, { slow: true }); await wait(1000);
  setLine(960, 886, 0, { slow: true }); await wait(1300);
  line.classList.add('off');
  try {
    await Sys.power(reboot ? 'reboot' : 'off');
    setMetrics(false); NAV = null;
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('on')); setBg('', 'none');
    $('#offmsg').textContent = reboot ? 'Reiniciando…' : 'Apagando…'; $('#offmsg').classList.add('on');
  } catch (e) {
    $('#black').classList.remove('on'); line.classList.remove('off');
    S.section = 0; if (NAV) NAV.id = ''; enterHome({ r: 1, c: 3 });
    play('error'); toast(`No se pudo ${reboot ? 'reiniciar' : 'apagar'} (${ERR_TEXT[e.code] || e.message}). Usa el botón STEAM → Energía`, false);
  }
}
/* Apagar tras inactividad: only on STONE's own screens, never with a game open or a test running.
   A test or calibration started from a terminal (stonectl calibrate) counts too: stoned reports it
   in its state (board, rc16: the console powered off 30 min into `stonectl calibrate standard`). */
let idleOffT = 0;
function stonedBusy() {
  const st = S.st;
  return !!(st && (st.testing || (st.calibration && st.calibration.running)));
}
function armIdleOff() {
  clearTimeout(idleOffT);
  const min = IDLE_MIN[S.idle]; if (!min) return;
  idleOffT = setTimeout(() => {
    if (S.running !== null || S.game || testUI || stonedBusy() || ['game', 'quick', 'transition', 'dlg'].includes(S.screen)) return armIdleOff();
    shutdown(false);
  }, min * 60000);
}
let saveT = 0;
function savePrefs() {
  clearTimeout(saveT);
  saveT = setTimeout(() => Sys.prefsSet({ sound: S.sound, vol: S.vol, hc: S.hc, rm: S.rm, ts: S.ts, safe: S.safe, idle: S.idle,
    tech: S.tech, adv_ack: S.advAck, engine: S.render, favorites: [...favs] }).catch(() => {}), 400);
}
function loadPrefs(p) {
  if (!p) return;
  S.sound = p.sound; S.vol = p.vol; S.hc = p.hc; S.rm = p.rm || reduceOS; S.ts = p.ts; S.safe = p.safe; S.idle = p.idle;
  S.tech = p.tech; S.advAck = p.adv_ack; S.render = p.engine === 1 ? 1 : 0; favs.clear(); (p.favorites || []).forEach(a => favs.add(a));
  applyPrefs();
}

/* ---------- BOOT ----------
   Plymouth and Steam already showed the line while the machine started; this is STONE Home
   arriving. The animation runs while the library, settings and stoned answer, so it adds
   no waiting of its own; Home appears as soon as both are done. */
async function boot() {
  S.screen = 'transition';
  $('#black').classList.add('on'); line.classList.add('boot');
  Sys.bootMark('visual').catch(() => {});          /* BOOT TO VISUAL: STONE Home's first frame */
  const first = Sys.firstrunStatus().catch(() => ({ done: true }));
  const prefs = Sys.prefsGet().then(loadPrefs).catch(() => {});
  const prep = Promise.all([prefs, refreshCaps(), Sys.info().then(i => { S.info = i; }).catch(() => {}), prefs.then(loadLibrary)]);
  /* Home is about to be on screen: only now may stoned apply the saved profile (factory or validated) */
  const home = prep.then(() => PerfAPI.homeReady()).then(st => { adopt(st); return st; })
    .catch(e => { if (e && e.code === 'ServiceUnavailable') S.actual = { error: 'ServiceUnavailable' }; return null; });
  /* The frame before this one (Plymouth, then STONE's Steam startup movie) is black with the full
     line at 82 % of the height and 25 % of the width: STONE Home starts on that same frame. */
  setLine(720, 886, 480); line.classList.remove('off');
  play('start');
  await wait(1000);
  $('#bootword').classList.add('on');
  await Promise.race([prep, new Promise(r => setTimeout(r, 8000))]).then(() => wait(700));
  $('#bootword').classList.remove('on');
  await wait(300);
  $('#black').classList.remove('on');
  S.section = 0; if (NAV) NAV.id = ''; NAV = null;
  const fr = await Promise.race([first, wait(3000).then(() => ({ done: true }))]);
  if (S.running !== null && S.game) { showGame(G[S.running], true); }
  else if (!fr.done) { await home; Sys.bootMark('ready').catch(() => {}); return firstRun(fr); }
  else enterHome({ r: 0, c: 0, slow: true });
  Sys.bootMark('ready').catch(() => {});           /* BOOT TO READY: Home answers the controller */
  setTimeout(() => line.classList.remove('boot'), 1300);
  armIdleOff();
  home.then(st => { if (st) setTimeout(() => bootNotices(st), 1400); });
}

/* ---------- FIRST RUN (M22) ----------
   Shown once on a new installation. It only reads what the console has (configuration, health,
   display, Steam account) and leaves the profile at BALANCED, the factory one: no overclock,
   calibration or experimental function on the first start (A2). Connectivity and audio come with
   STONE CONNECT and SETTINGS (F6). */
function frStep(html, buttons) {
  return new Promise(res => {
    const b = buttons.map(([k, t]) => `<span class="txt-f" data-f data-b="${k}">${t}</span>`).join('');
    openDlg(`${html}<div class="btns">${b}</div>`, { onA: el => { play('select'); closeDlg(); S.screen = 'transition'; res(el.dataset.b); } }, false, true);
  });
}
function frConfigText() {
  const c = S.caps, cfg = c && c.configuration;
  if (!c) return ['<p>El servicio de rendimiento no responde: STONE no puede leer la configuración. Home funciona; Rendimiento quedará en valores de fábrica.</p>', false];
  const d = (cfg && cfg.detected) || {}, r = (cfg && cfg.reference) || {};
  const row = (label, have, want, unit) => `<p>${label}: <b>${have === null || have === undefined ? 'no se pudo leer' : have + unit}</b>${want ? ` · referencia ${want}${unit}` : ''}</p>`;
  const ok = c.board && cfg && cfg.matches !== false;
  return [`<p>Placa BC-250: <b>${c.board ? 'detectada' : 'no detectada'}</b></p>${row('Núcleos de CPU', d.cpu_cores, r.cpu_cores, '')}${row('GPU', d.gpu_cu, r.gpu_cu, ' CU')}
    ${cfg && cfg.matches === false ? `<p>Esta configuración no es la de referencia (${esc(cfg.reasons.join('; '))}). Los perfiles de fábrica funcionan; CUSTOM, pruebas y calibración quedan bloqueados.</p>` : ''}
    ${S.safeMode ? '<p>STONE arrancó en Safe Mode: valores de fábrica.</p>' : ''}`, ok];
}
async function firstRun(fr) {
  S.screen = 'transition';
  setTimeout(() => line.classList.remove('boot'), 1300);
  const [cfgHtml] = frConfigText();
  await frStep(`<div class="brand" style="font-size:40px">STONE</div><h2>BIENVENIDO</h2><p>Primer encendido de STONE MACHINE. Si has llegado aquí con el botón A, el mando funciona.</p>${cfgHtml}`, [['next', 'CONTINUAR']]);
  const dsp = await Sys.display(true).catch(() => null);
  await frStep(`<h2>PANTALLA</h2>${dsp && dsp.connected
    ? `<p>${esc(dsp.name || 'Pantalla')}${dsp.connection ? ' · ' + esc(dsp.connection) : ''}</p><p>Resolución nativa: <b>${resTxt(dsp.native)}</b></p><p>Salida actual: <b>${resTxt(dsp.output)}</b>${dsp.max_hz ? ` · hasta ${dsp.max_hz} Hz` : ''}</p>`
    : '<p>STONE no pudo leer la pantalla. Puedes revisarla después en Ajustes → Pantalla.</p>'}<p>Se cambia en Ajustes → Pantalla.</p>`, [['next', 'CONTINUAR']]);
  if (!fr.steam_account) {
    const b = await frStep('<h2>STEAM</h2><p>Para jugar, inicia sesión en Steam una vez. Es la única pantalla de Steam que verás.</p>', [['login', 'INICIAR SESIÓN'], ['later', 'MÁS TARDE']]);
    if (b === 'login') await Sys.openSteam('store').catch(() => {});
  } else await frStep('<h2>STEAM</h2><p>Cuenta de Steam: <b>conectada</b>.</p>', [['next', 'CONTINUAR']]);
  await frStep(`<h2>RENDIMIENTO</h2><p>STONE empieza en <b>${profOf(S.prof || 'balanced').n}</b>, los valores de fábrica.</p><p>El primer encendido nunca sube frecuencias ni calibra. Eso se hace cuando quieras en Ajustes → Rendimiento.</p>`, [['go', 'EMPEZAR']]);
  await Sys.firstrunComplete().catch(() => {});
  if (NAV) NAV.id = ''; NAV = null;
  enterHome({ r: 0, c: 0, slow: true });
  armIdleOff();
}
