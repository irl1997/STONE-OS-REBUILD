/* ---------- POWER ---------- */
let powerFrom = 'home';
function openPower() {
  powerFrom = S.screen === 'game' ? 'game' : S.screen;
  S.screen = 'power';
  const box = $('#power .box');
  box.innerHTML = `<div class="h">ENERGÍA</div>
    <div class="main txt-f" data-f data-act="off">APAGAR</div>
    <div class="txt-f" style="font-size:26px" data-f data-act="reboot">Reiniciar</div>
    <div class="txt-f" style="font-size:26px" data-f data-act="bootopts">Opciones de arranque</div>
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
  if (a === 'desktop') return toDesktop();
  if (a === 'bootopts') return bootOptions();
}
/* M02: what the boot menu offers, reachable with the controller. Each option says what happens
   and asks before restarting. */
function bootOptions() {
  const dep = S.info && S.info.deployments, prev = dep && dep.rollback;
  const back = () => { closeDlg(); play('back'); S.section = 0; if (NAV) NAV.id = ''; enterHome({ r: 1, c: 3 }); };
  openDlg(`<h2>OPCIONES DE ARRANQUE</h2>
    <p><b>Safe Mode</b>: STONE arranca con los valores de fábrica, sin perfiles CUSTOM ni perfiles por juego.</p>
    <p><b>Versión anterior</b>: ${prev ? `el próximo arranque usa ${esc(prev.version || 'la versión anterior')}. Puedes volver a la actual de la misma forma.` : 'no hay una versión anterior guardada todavía.'}</p>
    <div class="btns"><span class="txt-f" data-f data-b="safe">SAFE MODE</span>${prev ? '<span class="txt-f" data-f data-b="prev">VERSIÓN ANTERIOR</span>' : ''}<span class="txt-f" data-f data-b="no">VOLVER</span></div>`, {
    onA: async el => {
      const b = el.dataset.b; if (b === 'no') return back();
      closeDlg(); play('select');
      if (b === 'safe') { const st = await api('enterSafeMode'); if (st) return rebootDlg('Safe Mode queda activo: STONE usará los valores de fábrica.', back); return back(); }
      try { await Sys.bootRollback(); rebootDlg('El próximo arranque usará la versión anterior de STONE OS.', back); }
      catch (e) { play('error'); toast(e.code === 'PermissionDenied' ? 'Hace falta ser el administrador de la consola' : `No se pudo: ${e.message}`, false); back(); }
    }, onB: back });
}
function desktopDlg(ri) {
  const back = () => { closeDlg(); play('back'); enterSettings({ pane: true, ri }); };
  openDlg(`<h2>MODO ESCRITORIO</h2><p>Sales de la consola al escritorio de Linux, para usuarios avanzados. Los juegos y STONE se cierran.</p><p>Para volver: «Volver a STONE» en el escritorio, o reinicia la consola.</p>
    <div class="btns"><span class="txt-f" data-f data-b="no">CANCELAR</span><span class="txt-f" data-f data-b="yes">ABRIR EL ESCRITORIO</span></div>`, {
    onA: el => { if (el.dataset.b !== 'yes') return back(); closeDlg(); play('select'); toDesktop(); }, onB: back });
}
/* M15: Bazzite's desktop for this login only; "Volver a STONE" on the desktop (or a reboot) comes back. */
async function toDesktop() {
  S.screen = 'transition'; $('#hints').classList.add('hide'); play('stop');
  $('#black').classList.remove('fast'); $('#black').classList.add('on');
  setLine(960, 886, 0, { slow: true }); await wait(900);
  try {
    await Sys.sessionDesktop();
    $('#offmsg').textContent = 'Abriendo el escritorio… Para volver: «Volver a STONE» en el escritorio, o reiniciar.'; $('#offmsg').classList.add('on');
  } catch (e) {
    $('#black').classList.remove('on'); line.classList.remove('off');
    S.section = 0; if (NAV) NAV.id = ''; enterHome({ r: 1, c: 3 });
    play('error'); toast(`No se pudo abrir el escritorio (${ERR_TEXT[e.code] || e.message})`, false);
  }
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
    tech: S.tech, adv_ack: S.advAck, engine: S.render, favorites: [...favs], frame: FRAME }).catch(() => {}), 400);
}
function loadPrefs(p) {
  if (!p) return;
  S.sound = p.sound; S.vol = p.vol; S.hc = p.hc; S.rm = p.rm || reduceOS; S.ts = p.ts; S.safe = p.safe; S.idle = p.idle;
  S.tech = p.tech; S.advAck = p.adv_ack; S.render = p.engine === 1 ? 1 : 0; favs.clear(); (p.favorites || []).forEach(a => favs.add(a));
  FRAME = p.frame > 0 && p.frame <= 6 ? p.frame : 0; fit();
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

/* ---------- SETUP: the first start (M22) ----------
   A full-screen setup like a console's: controller, internet, screen and framing, sound,
   performance, Steam account. It only reads and offers; nothing changes without the person's A.
   The profile stays BALANCED, the factory one: no overclock, calibration or experiment (A2).
   The right side is a core sample of the setup: one stratum per step, the vein on the current one. */
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
const SU_STEPS = [['hola', 'INICIO'], ['mando', 'MANDO'], ['red', 'INTERNET'], ['pantalla', 'PANTALLA'], ['sonido', 'SONIDO'],
  ['rend', 'RENDIMIENTO'], ['steam', 'STEAM'], ['listo', 'LISTO']];
let SU = null;
function suEl() {
  let el = $('#setup');
  if (!el) {
    stage.insertAdjacentHTML('beforeend', `<section id="setup"><div class="su-head"><div class="brand">STONE</div><div class="su-count"></div></div>
      <div class="su-body"><div class="su-kick"></div><h1 class="su-title"></h1><p class="su-lead"></p><div class="su-rows"></div><div class="su-btns"></div></div><div class="su-core"></div><div class="su-frame"><i></i><i></i><i></i><i></i></div></section>`);
    el = $('#setup');
  }
  return el;
}
/* One step on screen. rows: [{l, v, k, lr}] (k = what A does, lr = LEFT/RIGHT change it); buttons: [[k, label]] */
function suDraw(st) {
  const el = suEl(), i = SU_STEPS.findIndex(x => x[0] === st.key);
  SU.cur = st;
  el.querySelector('.su-count').textContent = `PASO ${String(i + 1).padStart(2, '0')} DE ${String(SU_STEPS.length).padStart(2, '0')}`;
  el.querySelector('.su-kick').innerHTML = `ESTRATO ${String(i + 1).padStart(2, '0')} · <b>${SU_STEPS[i][1]}</b>`;
  el.querySelector('.su-title').textContent = st.title;
  el.querySelector('.su-lead').innerHTML = st.lead || '';
  el.querySelector('.su-rows').innerHTML = (st.rows || []).map((r, k) => `<div class="su-row${r.k ? ' txt-f' : ''}${r.lr ? ' lr' : ''}"${r.k ? ` data-f data-r="${k}"` : ''}><span>${esc(r.l)}</span><b>${r.lr ? '◀ ' : ''}${esc(r.v || '')}${r.lr ? ' ▶' : ''}</b></div>`).join('');
  el.querySelector('.su-btns').innerHTML = st.buttons.map(([k, t]) => `<span class="txt-f" data-f data-b="${k}">${t}</span>`).join('');
  el.querySelector('.su-core').innerHTML = SU_STEPS.map(([k, n], j) => `<div class="${j < i ? 'done' : j === i ? 'cur' : ''}"><span>${String(j + 1).padStart(2, '0')}</span>${n}</div>`).join('');
  el.classList.toggle('framing', st.key === 'pantalla');
  const body = el.querySelector('.su-body'); body.classList.remove('in'); void body.offsetWidth; body.classList.add('in');
  S.screen = 'dlg';
  DLG = { onA: suA, onLR: suLR, onB: i > 0 ? () => { play('back'); suGo(SU.i - 1); } : null };
  const rows = [...el.querySelectorAll('.su-rows [data-f]')].map(e => [e]);
  NAV = mkNav(rows.concat([[...el.querySelectorAll('.su-btns [data-f]')]]), { r: st.r == null ? rows.length : Math.min(st.r, rows.length), place: (e, b) => ({ x: b.x, y: b.y + b.h + 6, w: b.w }) });
  NAV.id = 'setup';
  requestAnimationFrame(() => { line.classList.remove('off'); applyFocus(); });
  hints([['A', 'Elegir'], ...(st.rows || []).some(r => r.lr) ? [['◀ ▶', 'Ajustar']] : [], ...(i > 0 ? [['B', 'Atrás']] : [])]);
}
function suA(el) {
  SU.at = NAV.r;                      /* a step drawn again keeps the focus where it was */
  if (el.dataset.b) { play('select'); return SU.cur.onButton(el.dataset.b); }
  const r = SU.cur.rows[+el.dataset.r];
  if (r && r.k) { play('select'); return SU.cur.onRow(r, +el.dataset.r); }
}
function suLR(d, el) {
  const r = el && el.dataset.r !== undefined ? SU.cur.rows[+el.dataset.r] : null;
  if (!r || !r.lr) return false;
  SU.at = NAV.r; SU.cur.onLR(r, d, +el.dataset.r); return true;
}
function suGo(i) { SU.at = null; SU.i = Math.max(0, Math.min(SU_STEPS.length - 1, i)); return SU_FN[SU_STEPS[SU.i][0]](); }
const suNext = () => suGo(SU.i + 1);
const SU_FN = {
  hola() {
    const [cfgHtml] = frConfigText(), hl = S.health;
    const bad = hl ? hl.checks.filter(c => c[0] === 'fail') : [];
    const tmp = document.createElement('div'); tmp.innerHTML = cfgHtml;
    const rows = [...tmp.querySelectorAll('p')].map(p => { const [l, v] = p.textContent.split(/: (.*)/s); return { l, v: v || '' }; }).filter(r => r.v);
    rows.push({ l: 'Comprobación del sistema', v: !hl ? 'en Ajustes → Salud' : bad.length ? `${bad.length} aviso${bad.length > 1 ? 's' : ''} · Ajustes → Salud` : 'todo bien' });
    suDraw({ key: 'hola', title: 'HOLA.', lead: 'Vamos a dejar lista tu STONE MACHINE. Son unos minutos y todo se puede cambiar después en Ajustes.', rows,
      buttons: [['go', 'EMPEZAR']], onButton: suNext });
  },
  async mando() {
    const draw = (list, note) => suDraw({ key: 'mando', title: 'MANDO', r: SU.at,
      lead: 'Si has llegado aquí con el botón A, tu mando ya funciona. Para añadir un mando Bluetooth, ponlo en modo de emparejamiento y búscalo.',
      rows: [...(list || []).filter(d => /input-gaming|joystick|gamepad/i.test(d.icon || '') || /mando|controller|pad/i.test(d.name || ''))
        .map(d => ({ l: d.name, v: d.connected ? `conectado${d.battery != null ? ' · ' + d.battery + ' %' : ''}` : d.paired ? 'emparejado' : 'EMPAREJAR', k: d.paired ? null : 'pair', mac: d.mac })),
        { l: 'Buscar mandos Bluetooth', v: note || '', k: 'scan' }],
      buttons: [['next', 'CONTINUAR']], onButton: suNext,
      onRow: async r => {
        if (r.k === 'scan') { draw(list, 'buscando…'); const x = await Bridge.call('bt.scan').catch(() => null); return draw(x && x.devices, x ? '' : 'Bluetooth no responde'); }
        draw(list, 'emparejando…');
        const x = await Bridge.call('bt.action', 'pair', r.mac).catch(e => ({ error: (e && e.message) || 'no se pudo' }));
        toast(x && x.error ? `${r.l}: ${x.error}` : `${r.l}: emparejado`, false);
        const y = await Bridge.call('bt.devices').catch(() => null); draw(y && y.devices, '');
      } });
    draw(null, 'leyendo…');
    const x = await Bridge.call('bt.devices').catch(() => null);
    if (SU.cur.key === 'mando') draw(x && x.devices, x ? '' : 'Bluetooth no responde');
  },
  async red() {
    let net = null, wifi = null, note = '';
    const draw = () => {
      const online = net && net.online, cable = net && net.devices.find(d => d.type === 'ethernet' && d.state === 'connected');
      const rows = [{ l: 'Estado', v: !net ? 'leyendo…' : online ? (cable ? 'conectado por cable' : 'conectado') : 'sin conexión' }];
      (wifi || []).slice(0, 6).forEach(w => rows.push({ l: w.ssid, v: w.active ? 'conectado' : `${w.secure ? 'con contraseña' : 'abierta'} · señal ${w.signal} %`, k: w.active ? null : 'wifi', w }));
      rows.push({ l: 'Buscar redes Wi-Fi', v: note, k: 'scan' });
      suDraw({ key: 'red', title: 'INTERNET', r: SU.at, rows,
        lead: 'STONE necesita internet para Steam, las descargas y las actualizaciones. Con cable ya está; si no, elige tu Wi-Fi.',
        buttons: online ? [['next', 'CONTINUAR']] : [['next', 'OMITIR POR AHORA']], onButton: suNext,
        onRow: async r => {
          if (r.k === 'scan') { note = 'buscando…'; draw(); wifi = ((await Bridge.call('net.wifiList').catch(() => null)) || {}).networks || []; note = wifi.length ? '' : 'ninguna red'; return draw(); }
          const go = async pw => {            /* pw null: an open network */
            note = `conectando a ${r.w.ssid}…`; draw();
            const x = await Bridge.call('net.wifiConnect', r.w.ssid, pw).catch(e => ({ error: (e && e.message) || 'no se pudo' }));
            note = x && x.error ? x.error : ''; if (!(x && x.error)) toast(`Conectado a ${r.w.ssid}`, false);
            net = await Bridge.call('net.status').catch(() => net); wifi = ((await Bridge.call('net.wifiList').catch(() => null)) || {}).networks || wifi; draw();
          };
          if (!r.w.secure) return go(null);
          osk(`Contraseña de ${r.w.ssid}`, pw => (pw === null ? draw() : go(pw)), true);
        } });
    };
    draw();
    net = await Bridge.call('net.status').catch(() => ({ devices: [], online: false }));
    if (SU.cur.key !== 'red') return;
    if (!net.online) { wifi = ((await Bridge.call('net.wifiList').catch(() => null)) || {}).networks || []; }
    if (SU.cur.key === 'red') draw();
  },
  async pantalla() {
    const draw = d => suDraw({ key: 'pantalla', title: 'PANTALLA', r: SU.at,
      lead: 'Ajusta el encuadre hasta que las cuatro esquinas ámbar se vean enteras en tu televisor. Si ya se ven, déjalo en 0 %.',
      rows: [{ l: 'Televisor', v: d ? (d.connected ? (d.name || 'conectado') : 'no se pudo leer') : 'leyendo…' },
        { l: 'Resolución', v: d && d.connected ? resTxt(d.output) : '—' },
        { l: 'Encuadre', v: `${FRAME} %`, k: 'frame', lr: true }],
      buttons: [['next', 'CONTINUAR']], onButton: suNext,
      onRow: () => toast('Usa ◀ ▶ para ajustar el encuadre', false),
      onLR: (r, dd, k) => { const n = Math.max(0, Math.min(6, FRAME + dd)); if (n === FRAME) return bump(dd); FRAME = n; fit(); play('nav'); savePrefs(); draw(d); } });
    draw(null);
    const d = await Sys.display(true).catch(() => ({ connected: false }));
    if (SU.cur.key === 'pantalla') draw(d);
  },
  async sonido() {
    let A = null;
    const draw = () => suDraw({ key: 'sonido', title: 'SONIDO', r: SU.at,
      lead: 'Elige por dónde suena la consola. Al elegir una salida suena una nota de prueba.',
      rows: [...(A ? A.outputs : []).map(o => ({ l: o.name, v: o.default ? 'en uso' : 'usar', k: 'out', o })),
        ...(A ? [{ l: 'Volumen', v: `${Math.round(A.volume * 100)} %`, k: 'vol', lr: true }] : [{ l: 'Salidas', v: 'leyendo…' }])],
      buttons: [['next', 'CONTINUAR']], onButton: suNext,
      onRow: async (r, k) => { if (r.k !== 'out') return; await Bridge.call('audio.default', r.o.id).catch(() => {}); A = await Bridge.call('audio.status').catch(() => A); draw(); setTimeout(() => play('notify'), 250); },
      onLR: (r, d, k) => { A.volume = Math.max(0, Math.min(1, Math.round((A.volume + d * 0.05) * 20) / 20)); Bridge.call('audio.volume', A.volume).catch(() => {}); play('nav'); draw(); } });
    draw();
    A = await Bridge.call('audio.status').catch(() => null);
    if (SU.cur.key === 'sonido') draw();
  },
  rend() {
    const c40 = S.caps && S.caps.board && S.caps.cu40, offer = c40 && c40.available && !c40.active && !SU.reboot;
    suDraw({ key: 'rend', title: 'RENDIMIENTO',
      lead: `STONE empieza en <b>${profOf(S.prof || 'balanced').n}</b>, los valores de fábrica. El primer encendido nunca sube frecuencias ni calibra: eso se hace cuando quieras en Ajustes → Rendimiento.`
        + (offer ? '<br><br>Tu GPU usa 24 de sus 40 unidades de cálculo. Con 40 rinde más, consume unos 30 W más y se calienta más. Es un cambio de la comunidad: si aparecen errores de GPU, STONE vuelve sola a 24 CU.' : ''),
      rows: [{ l: 'Perfil', v: profOf(S.prof || 'balanced').n }, { l: 'GPU', v: c40 ? (c40.active || SU.reboot ? '40 CU' + (SU.reboot ? ' al reiniciar' : '') : '24 CU') : '—' }],
      buttons: offer ? [['next', 'AHORA NO'], ['cu', 'ACTIVAR 40 CU']] : [['next', 'CONTINUAR']],   /* the safe answer has the focus */
      onButton: async b => {
        if (b !== 'cu') return suNext();
        toast('Cambiando el arranque…', false);
        const r = await Sys.cu40('enable').catch(e => ({ ok: false, text: e.message }));
        SU.reboot = !!(r && r.ok);
        toast(SU.reboot ? '40 CU se usará desde el próximo arranque' : 'No se pudo ahora: Ajustes → Rendimiento', false);
        SU_FN.rend();
      } });
  },
  steam() {
    const has = SU.fr.steam_account;
    suDraw({ key: 'steam', title: 'STEAM',
      lead: has ? 'Tu cuenta de Steam ya está en esta consola: tu biblioteca aparece en STONE.'
        : 'Tus juegos vienen de tu cuenta de Steam. Steam muestra su propia pantalla de inicio de sesión una sola vez (puedes usar el código QR con la app de Steam del móvil); después todo sigue en STONE.',
      rows: [{ l: 'Cuenta', v: has ? 'conectada' : 'sin iniciar sesión' }],
      buttons: has ? [['next', 'CONTINUAR']] : [['login', 'INICIAR SESIÓN'], ['next', 'MÁS TARDE']],
      onButton: async b => {
        if (b === 'login') { await Sys.openSteam('store').catch(() => {}); SU.fr = await Sys.firstrunStatus().catch(() => SU.fr); }
        suNext();
      } });
  },
  listo() {
    suDraw({ key: 'listo', title: 'TODO LISTO.', lead: 'Tu STONE MACHINE está preparada. Pulsa Y en Inicio para buscar un juego, y el botón STONE para volver aquí desde cualquier juego.',
      rows: [{ l: 'Encuadre', v: `${FRAME} %` }, { l: 'Rendimiento', v: profOf(S.prof || 'balanced').n + (SU.reboot ? ' · 40 CU al reiniciar' : '') },
        { l: 'Steam', v: SU.fr.steam_account ? 'conectado' : 'pendiente: Ajustes → Steam' }],
      buttons: [['go', 'EMPEZAR A JUGAR']], onButton: suFinish });
  }
};
async function firstRun(fr) {
  setTimeout(() => line.classList.remove('boot'), 1300);
  SU = { i: 0, fr, reboot: false, at: null };
  S.health = await Promise.race([Sys.health().catch(() => null), wait(5000).then(() => null)]);
  chrome(false, false); showScreen('');
  suEl().classList.add('on');
  suGo(0);
}
async function suFinish() {
  S.screen = 'transition';
  await Sys.firstrunComplete().catch(() => {});
  const el = $('#setup'); el.classList.add('out');
  await wait(700);
  el.classList.remove('on', 'out', 'framing');
  DLG = null; if (NAV) NAV.id = ''; NAV = null;
  enterHome({ r: 0, c: 0, slow: true });
  armIdleOff();
  if (SU.reboot) setTimeout(() => rebootDlg('40 CU se usará desde el próximo arranque.', () => enterHome({ r: 0, c: 0 })), 900);
}
