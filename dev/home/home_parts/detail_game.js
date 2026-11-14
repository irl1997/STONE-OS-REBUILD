/* ---------- DETAIL ---------- */
let curG = 0;
function enterDetail(i, opts = {}) {
  curG = i; const g = G[i], running = S.running === i;
  S.screen = 'detail';
  const canPlay = g.inst || g.src === 'shortcut';
  const prim = running ? 'REANUDAR' : canPlay ? 'JUGAR' : g.upd ? 'INSTALANDO' : 'INSTALAR';
  /* Five actions at most on one line (they always fit the 1920 stage); the image options live in GRÁFICOS. */
  const sec = [[g.fav ? 'Quitar de favoritos' : 'Favorito', 'fav'], [`Rendimiento: ${g.perf ? profOf(g.perf).n : 'Global'}`, 'perf'], ['Propiedades', 'opt']];
  if (g.src === 'steam' && g.inst) sec.splice(2, 0, ['Gráficos', 'gfx'], ['Experiencia', 'xp']);
  if (running) sec[1] = ['Cerrar juego', 'close'];          /* the profile applies at start; while playing it is in the quick menu */
  $('#detail').innerHTML = `
    <div class="col"><div class="origin">${esc(g.o)}</div><h1${g.n.length > 22 ? ' class="long"' : ''}>${esc(g.n)}</h1>
      <div class="stats">${playText(g)} · Última sesión: ${running ? 'ahora' : g.last}</div>
      <div class="stats exp" id="dexp" style="margin-top:.35em;opacity:.85"></div></div>
    <div class="primary txt-f" data-f data-act="primary" id="dprim">${prim}</div>
    <div class="second">${sec.map(([s, a]) => `<span class="txt-f" data-f data-act="${a}">${s}</span>`).join('')}</div>
    ${dlBarHTML()}
    <div class="info"><div><span>Tamaño</span><b>${g.sz}</b></div><div><span>Origen</span><b>${esc(g.o)}</b></div><div><span>Estado</span><b id="dstate">${g.upd ? (g.inst ? 'Actualizando en Steam' : 'Instalándose') : g.inst ? 'Instalado' : 'En tu cuenta · sin instalar'}</b></div><div><span>Al iniciarse</span><b>${g.perf ? profOf(g.perf).n : 'Perfil global'}${S.safeMode && g.perf ? ' (en pausa: Safe Mode)' : ''}</b></div></div>`;
  showScreen('detail'); chrome(true, false);
  bgGame(g, true, 'side');
  dlShow(); if (!canPlay || g.upd) dlKick();
  const d = $('#detail');
  NAV = mkNav([[d.querySelector('#dprim')], [...d.querySelectorAll('.second [data-f]')]], {
    r: opts.r || 0, c: opts.c || 0,
    place: (el, b, r) => ({ x: b.x, y: b.y + b.h + (r === 0 ? 16 : 12), w: b.w })
  });
  NAV.id = 'detail';
  requestAnimationFrame(() => applyFocus());
  hints([['A', DL.at[g.appid] && !canPlay ? 'Opciones de la descarga' : prim.charAt(0) + prim.slice(1).toLowerCase()], ['B', 'Volver']]);
  if (g.src === 'steam' && g.inst) { experience(g, i); imgLoad(g, i); }
  if (g.src === 'steam' && !g.art.hero) Sys.artWant(g.appid).catch(() => {});      /* its big picture, if Steam had not cached it */
}
/* Image enhancement: the person's own explicit choice (Nativo / FSR del juego / FSR de pantalla / HelixSR),
   from the host (stone_games). Only what is available is offered; STONE decides again with "STONE decide". */
const PRESET_TXT = { quality: 'Calidad', balanced: 'Equilibrado', performance: 'Rendimiento', ultra_performance: 'Ultra rendimiento' };
const imgSel = g => g.img && g.img.choices.find(c => c.selected);
const imgLabel = g => 'Imagen: ' + (g.img ? (imgSel(g) ? imgSel(g).label : 'STONE decide') : '…');
/* STONE IMAGE (look.py): a look per game through vkBasalt; Original = none. */
const lookLabel = g => 'Aspecto: ' + (g.look ? (g.look.chosen ? g.look.looks.find(l => l.key === g.look.chosen).label : 'Original') : '…');
/* D-22 frame generation (framegen.py): EXPERIMENTAL, only with OptiScaler installed by STONE. */
const fgLabel = g => 'Fotogramas: ' + (g.fg ? (g.fg.on ? 'generados (exp.)' : 'normales') : '…');
const optzLabel = g => 'Optimizar' + (g.opz ? ` (${g.opz.done}/${g.opz.total})` : '');
const optLabel = g => g.img && g.img.by_stone ? 'Quitar FSR (OptiScaler)' : 'Instalar FSR (OptiScaler)';
const preLabel = g => 'Calidad: ' + (g.img && g.img.preset ? PRESET_TXT[g.img.preset] || g.img.preset : 'según el juego');
function imgRefresh(g) {
  const d = $('#detail'); if (!d) return;
  const a = d.querySelector('[data-act="img"]'), b = d.querySelector('[data-act="pre"]');
  if (a) a.textContent = imgLabel(g);
  if (b) b.textContent = preLabel(g);
  const fgEl = d.querySelector('[data-act="fg"]');
  if (fgEl) fgEl.textContent = fgLabel(g);
  const lk = d.querySelector('[data-act="look"]');
  if (lk) lk.textContent = lookLabel(g);
  const z = d.querySelector('[data-act="opz"]');
  if (z) z.textContent = optzLabel(g);
  const c = d.querySelector('[data-act="ins"]');
  if (c) c.textContent = optLabel(g);
}
async function imgLoad(g, i) {
  try { g.img = await Sys.gameImage(g.appid); } catch (e) { return; }
  try { g.opz = await Sys.gameOptStatus(g.appid); } catch (e) { g.opz = null; }
  try { g.look = await Sys.gameLook(g.appid); } catch (e) { g.look = null; }
  try { g.fg = await Sys.gameFrameGen(g.appid); } catch (e) { g.fg = null; }
  if (curG === i && S.screen === 'detail') imgRefresh(g);
}
async function imgSet(g, key, preset) {
  try { await Sys.gameSetImage(g.appid, key, preset); } catch (e) { play('error'); return toast('No se pudo cambiar: ' + ((e && e.message) || 'sin respuesta'), false); }
  await imgLoad(g, curG); experience(g, curG);
  const c = g.img && imgSel(g);
  toast(c ? `${g.n}: ${c.label}${g.img.preset && c.key !== 'native' ? ' · ' + (PRESET_TXT[g.img.preset] || g.img.preset) : ''}` : `${g.n}: STONE decide`, false);
}
/* OPTIMIZAR: STONE launches the next combination of the measurement matrix; the person runs the game's
   own benchmark (or plays ~3 min) and quits; MangoHud's numbers become the measurement. Two presses. */
async function optimizar(g, i) {
  if (!g.opz) await imgLoad(g, i);
  const o = g.opz;
  if (!o) { play('error'); return toast('No se pudo leer el estado de la optimización', false); }
  if (!o.next) return toast(`${g.n}: ya está medido (${o.done} de ${o.total}). Mejor para esta consola: ${o.recommended}`, false);
  if (!insConfirmed('z' + g.appid)) return toast(`Prueba ${o.done + 1} de ${o.total}: ${o.next}. ` + (o.benchmark ? `Dentro del juego: ${o.benchmark}, déjalo ~2 min y sal. ` : 'Juega ~3 min y sal. ') + 'Pulsa otra vez para empezar', false);
  let r = null;
  try { r = await Sys.gameOptStart(g.appid); } catch (e) { play('error'); return toast('No se pudo empezar: ' + ((e && e.message) || 'sin respuesta'), false); }
  if (!r || !r.ok) { play('error'); return toast((r && r.error) || 'No se pudo empezar', false); }
  toast(`Midiendo: ${r.summary}`, false);
  return launch(g, () => Promise.resolve(true));
}
/* Install FSR (OptiScaler) / HelixSR: only on the person's request. First press says what will happen,
   the second one (within 10 s) does it. Nothing for games with anti-cheat or online-only (the host refuses). */
let insAsk = null;
const insConfirmed = key => { const ok = insAsk && insAsk.key === key && Date.now() - insAsk.t < 10000; insAsk = ok ? null : { key, t: Date.now() }; return ok; };
async function insOpti(g, i) {
  const key = 'o' + g.appid;
  try {
    if (g.img && g.img.by_stone) {
      if (!insConfirmed(key)) return toast('Pulsa otra vez para quitar OptiScaler de este juego', false);
      const r = await Sys.gameUninstall(g.appid); await imgLoad(g, i); experience(g, i);
      return toast(r && r.ok ? 'OptiScaler quitado de este juego' : ((r && r.error) || 'No se pudo quitar'), false);
    }
    let plan = await Sys.gamePlan(g.appid, 'optiscaler');
    if (plan && plan.needs_download) {
      toast('Descargando OptiScaler del autor (GitHub)… puede tardar', false);
      await Sys.components('optiscaler');
      plan = await Sys.gamePlan(g.appid, 'optiscaler');
    }
    if (!plan || !plan.ok) { play('error'); return toast(((plan && plan.error) || 'No se pudo preparar') + '', false); }
    if (!insConfirmed(key)) return toast(`OptiScaler ${plan.component.tag} → ${plan.folder} (${plan.files} archivos). Pulsa otra vez para instalar`, false);
    const r = await Sys.gameInstall(g.appid); await imgLoad(g, i); experience(g, i);
    toast(r && r.ok ? 'FSR (OptiScaler) instalado. Elige «Imagen: OptiScaler» para usarlo' : ((r && r.error) || 'No se pudo instalar'), false);
  } catch (e) { play('error'); toast('No se pudo: ' + ((e && e.message) || 'sin respuesta') + '. Si fue la descarga, revisa internet y vuelve a pulsar', false); }
}
/* STONE OPTIMIZED: GAME -> STONE RECOMMENDED -> PLAY. The host says what JUGAR will use and why;
   nothing is shown that was not measured or is not in the profile database. */
async function experience(g, i) {
  let r = null;
  try { r = await Sys.gameRecommended(g.appid); } catch (e) { return; }
  const el = $('#dexp');
  if (!r || !el || curG !== i || S.screen !== 'detail') return;
  g.exp = r;
  el.textContent = `${r.label} · ${r.summary} · ${r.status_text}`;
  el.title = r.settings || '';
}
function detailA(el) {
  const g = G[curG], a = el.dataset.act;
  if (a === 'primary') {
    play('select');
    if (S.running === g.i) return resumeGame();
    if (!g.inst && g.src !== 'shortcut') {
      if (g.upd || DL.at[g.appid]) return downloadDlg(g);
      const pe = $('#dprim'); if (pe) pe.textContent = 'PIDIENDO A STEAM';
      return installGame(g.appid, g.n).then(ok => { const e2 = $('#dprim'); if (e2 && G[curG] === g && /^PIDIENDO/.test(e2.textContent)) e2.textContent = ok ? 'INSTALANDO' : 'INSTALAR'; if (S.screen === 'detail') dlShow(); });
    }
    return launch(g);
  }
  if (a === 'opt') { play('select'); return propsDlg(g); }
  if (a === 'close') { play('select'); return closeGameAsk('detail'); }
  if (a === 'fav') {
    play('select'); g.fav = !g.fav; if (g.fav) favs.add(g.appid); else favs.delete(g.appid); savePrefs();
    enterDetail(curG, { r: 1, c: 0 }); return toast(g.fav ? 'Añadido a favoritos' : 'Quitado de favoritos', false);
  }
  if (a === 'opz') { play('select'); return optimizar(g, curG); }
  if (a === 'ins') { play('select'); return insOpti(g, curG); }
  if (a === 'gfx') { play('select'); return gfxPanel(g); }
  if (a === 'xp') { play('select'); return xpDlg(g); }
  if (a === 'fg') {
    if (!g.fg) { play('error'); return toast('Leyendo…', false); }
    if (!g.fg.available) { play('error'); return toast(g.fg.reason, false); }
    play('nav');
    return Sys.gameSetFrameGen(g.appid, !g.fg.on).then(r => {
      g.fg.on = r.on; imgRefresh(g);
      toast(r.on ? 'Generación de fotogramas activada (experimental): más fluidez, algo más de latencia. El contador de FPS incluye los fotogramas generados' : 'Generación de fotogramas desactivada', false);
    }, e => { play('error'); toast('No se pudo: ' + ((e && e.message) || 'sin respuesta'), false); });
  }
  if (a === 'look') {
    if (!g.look) { play('error'); return toast('Leyendo los aspectos…', false); }
    if (!g.look.available) { play('error'); return toast(g.look.reason || 'No disponible', false); }
    play('nav');
    const keys = [null, ...g.look.looks.map(l => l.key)], next = keys[(keys.indexOf(g.look.chosen ?? null) + 1) % keys.length];
    return Sys.gameSetLook(g.appid, next).then(() => {
      g.look.chosen = next; imgRefresh(g);
      const l = g.look.looks.find(x => x.key === next);
      toast(l ? `${l.label}: ${l.description}. Se aplica al jugar` : 'Original: sin cambios de aspecto', false);
    }, e => { play('error'); toast('No se pudo cambiar: ' + ((e && e.message) || 'sin respuesta'), false); });
  }
  if (a === 'img' || a === 'pre') {
    if (!g.img) { play('error'); return toast('Leyendo las opciones de imagen…', false); }
    play('nav');
    if (a === 'img') {
      const ok = g.img.choices.filter(c => c.available), k = ok.findIndex(c => c.selected);
      const next = ok[(k + 1) % ok.length];
      return imgSet(g, next.key, g.img.preset && next.key !== 'native' ? g.img.preset : undefined);
    }
    const c = imgSel(g);
    if (!c || c.key === 'native') return toast('Elige primero una mejora de imagen (FSR o HelixSR)', false);
    const k = g.img.presets.indexOf(g.img.preset);
    return imgSet(g, c.key, g.img.presets[(k + 1) % g.img.presets.length]);
  }
  if (a === 'perf') {
    play('nav'); const list = [null, ...usable()], k = list.indexOf(g.perf || null), next = list[(k + 1) % list.length];
    return api('setGameProfile', g.appid, next || 'global').then(st => {
      if (S.screen === 'detail') enterDetail(curG, { r: 1, c: 1 });
      if (st) toast(g.perf ? `${g.n} usará ${profOf(g.perf).n} al iniciarse` : `${g.n} usará el perfil global`, false);
    });
  }
}

/* ---------- GAME ----------
   Steam starts the game; Gamescope puts it in front of STONE Home. stoned sees the session through
   Steam's reaper process and reports it in its state, which is what this screen follows: when the
   game ends, Home comes back. */
let tagT = 0, launchT = 0, ldT = [];
/* The launch sound: the line rising into the game (the same voice as the start of the console). */
SND.launch = () => { tone(220, 1.6, .05, { glide: 440, attack: .05, lp: 1400, wet: .5 }); tone(660, 1.8, .018, { attack: .2, delay: .35, lp: 3000, wet: .8 }); };
async function launch(g, starter) {
  if (S.launching !== null) return;
  const ok = await (starter ? starter() : sys('launch', g.appid));
  if (!ok) return;
  S.launching = g.i; S.running = g.i; S.screen = 'transition';
  recent = [g.i, ...recent.filter(i => i !== g.i)].slice(0, 6);
  const el = focusEl(), b = el ? stageBox(el) : { x: 960, y: 540, w: 0, h: 0 };
  chrome(false, false); $('#hints').classList.add('hide');
  play('launch');
  /* The focus line leaves the card and becomes the loading vein of the game's own screen. */
  $('#black').classList.remove('fast'); $('#black').classList.add('on');
  setLine(b.x + b.w / 2, b.y + b.h + 16, 0, { slow: true });
  await wait(700);
  showGame(g, true);
  steamWatch(95000); DL.lastLaunch = ''; dlKick(95000);
  LW.step = ''; lwStart(g, ok && ok.launch);            /* Steam's steps and questions (launchwatch.js) */
  /* stoned may have seen the game before STONE started waiting for it */
  if (S.game && S.game.appid === g.appid) launchFound(g.i);
  /* Steam updating the game first, a long first start or a game that never opens: after 90 s STONE asks. */
  clearTimeout(launchT); launchT = setTimeout(() => launchStalled(g), 90000);
}
const LD_STEPS = [[0, 'PREPARANDO', ''], [1400, 'STEAM ABRE EL JUEGO', ''],
  [7000, 'CARGANDO', 'La primera vez que juegas, el juego prepara sus sombreadores: puede tardar unos minutos.'],
  [40000, 'SIGUE CARGANDO', 'B vuelve al inicio; el juego seguirá abriéndose.']];
function loadingOn(g) {
  const gm = $('#game');
  if (!gm.querySelector('.ld')) gm.insertAdjacentHTML('beforeend', '<div class="ld"><div class="col"><div class="ld-kick"></div><div class="ld-title"></div><div class="ld-sub"></div><div class="ld-bar"><i></i></div><div class="ld-step"></div><div class="ld-note"></div></div><div class="ld-foot"><span class="g">B</span>INICIO</div></div>');
  const set = (k, v) => { gm.querySelector('.ld-' + k).textContent = v; };
  set('kick', `${g.o} · ${profOf(g.perf || effective()).n}`);
  set('title', g.n);
  gm.querySelector('.ld-title').classList.toggle('long', g.n.length > 22);
  set('sub', g.exp && g.exp.settings && g.exp.status !== 'UNKNOWN' ? g.exp.settings : '');
  ldT.forEach(clearTimeout);
  ldT = LD_STEPS.map(([t, step, note]) => setTimeout(() => { set('step', step); set('note', note); }, t));
  const tag = gm.querySelector('.tag'); tag.textContent = `${g.n} · en curso. A: volver al juego · ☰: menú de STONE · B: inicio`; tag.classList.add('gone');
  gm.classList.add('loading');
}
function loadingOff() {
  ldT.forEach(clearTimeout); ldT = [];
  $('#game').classList.remove('loading');
}
function launchStalled(g) {
  if (S.launching !== g.i) return;
  if (S.screen === 'dlg') { launchT = setTimeout(() => launchStalled(g), 15000); return; }
  play('notify');
  const dl = DL.at[g.appid], st = LW.last, shaders = st && (st.trace || []).slice(-1)[0] === 'ask:ProcessingShaderCache' || st && st.request === 'ProcessingShaderCache';
  openDlg(`<h2>${esc(g.n.toUpperCase())}</h2><p>${dl ? `Steam sigue actualizando el juego (${dlPct(dl) || 'en cola'}). Se abre solo al terminar.`
    : shaders ? 'Steam sigue preparando los sombreadores del juego. Puedes omitirlo: el juego se abre antes, pero puede ir a tirones al principio.'
    : 'El juego todavía no se ha abierto.'}</p>${lwTech(st) ? `<p class="tech">${esc(lwTech(st))}</p>` : ''}
    <div class="btns"><span class="txt-f" data-f data-b="wait">ESPERAR</span>${shaders ? '<span class="txt-f" data-f data-b="skip">OMITIR</span>' : ''}<span class="txt-f" data-f data-b="cancel">CANCELAR</span></div>`, {
    onA: el => {
      closeDlg(); play('select');
      if (el.dataset.b === 'skip') { Bridge.call('launch.answer', g.appid, 'SkipShaders').catch(() => {}); }
      if (el.dataset.b !== 'cancel') { S.screen = 'game'; NAV = null; line.classList.add('off'); $('#hints').classList.add('hide'); steamWatch(95000); launchT = setTimeout(() => launchStalled(g), 90000); return; }
      Bridge.call('launch.answer', g.appid, 'cancel').catch(() => {});
      S.launching = null; S.running = null; loadingOff(); returnHome();
    } });
}
function launchFound(i) {
  S.launching = null; clearTimeout(launchT); sessionStart();
  setTimeout(() => { if (S.dormant) return; loadingOff(); if (S.running === i) showTag(G[i]); }, 1500);
}
/* Called from adopt(): stoned's view of the running game is the truth. */
function gameSync(st, before) {
  const appid = st.game ? st.game.appid : null;
  const i = appid ? G.findIndex(g => g.appid === appid) : -1;
  if (appid) {
    if (i >= 0) { S.running = i; sessionStart(); if (S.launching === i) launchFound(i); }
    return;
  }
  if (S.running !== null && S.launching === null) gameEnded(before);
}
function gameEnded(before) {
  const g = G[S.running]; S.running = null; setMetrics(false);
  const k = before ? slots.findIndex((sl, i) => sl && sl.state === 'validated' && before[i] !== 'validated') : -1;
  const back = ['game', 'quick'].includes(S.screen) || (S.screen === 'power' && powerFrom === 'game');
  if (back) {
    $('#quick').classList.remove('on'); $('#power').classList.remove('on');
    returnHome();
  }
  if (k >= 0) setTimeout(() => toast(`${g ? g.n + ' terminó. ' : ''}CUSTOM 0${k + 1} validado: la partida terminó sin errores de GPU`), back ? 1200 : 0);
  else sessionReport(g);
  loadLibrary().then(() => { if (S.screen === 'home') enterHome(); });     /* play time and order changed */
}
function returnHome() {
  closeQuick(true); loadingOff();
  $('#black').classList.add('fast', 'on');
  setTimeout(() => {
    S.section = 0; if (NAV) NAV.id = ''; NAV = null;
    if (AC && AC.state !== 'running' && S.sound) AC.resume();
    enterHome({ r: 0, c: 0 }); $('#black').classList.remove('on');
  }, S.rm ? 120 : 450);
}
/* GAME MODE RESOURCE STATE: menu screens are unmounted, full-screen backgrounds released,
   the blur cache emptied, input polling slowed and metrics only if the overlay is on. */
function gameMode() {
  ['home', 'library', 'detail', 'settings', 'perf', 'tuning'].forEach(id => { $('#' + id).innerHTML = ''; });
  spreadEls = [];
  setBg('', 'none'); $('#bgA').style.backgroundImage = 'none'; $('#bgB').style.backgroundImage = 'none'; bgCur = '';
  trimArt();
  setTimeout(() => { if (S.screen === 'game') audioSleep(); }, 2500);
}
function showGame(g, fresh) {
  S.screen = 'game'; NAV = null;
  const gm = $('#game'), hu = heroUrl(g);
  gm.querySelector('.art').style.backgroundImage = hu ? `url("${hu}")` : neutralBg;
  if (S.launching === g.i) loadingOn(g); else { loadingOff(); showTag(g); }
  showScreen('game'); setBg('', 'none'); chrome(false, false);
  $('#hints').classList.add('hide');
  line.classList.add('off');
  setTimeout(() => $('#black').classList.remove('on'), fresh ? 200 : 0);
  setMetrics(S.tech);
  gameMode();
}
function showTag(g) {
  const tag = $('#game .tag'); tag.textContent = `${g.n} · en curso. A: volver al juego · ☰: menú de STONE · B: inicio`;
  tag.classList.remove('gone'); clearTimeout(tagT); tagT = setTimeout(() => tag.classList.add('gone'), 6000);
}
/* In the STONE session the session puts the game back in front (guide button, plan B of V-13);
   elsewhere Steam does it when it is asked to start the game again. [VERIFICAR EN PLACA] */
function resumeGame() {
  closeQuick(true);
  const g = G[S.running]; if (!g) return returnHome();
  if (S.info && S.info.session === 'stone') Sys.sessionResume().catch(() => sys('launch', g.appid));
  else sys('launch', g.appid);
  $('#black').classList.add('fast', 'on');
  setTimeout(() => showGame(g, true), S.rm ? 120 : 450);
}
function metricsTick() {
  if (!S.tech || $('#metrics').hidden) return;
  const id = effective(), m = S.metrics;
  const lim = S.actual && !S.actual.error ? `Límite ${S.actual.max} MHz · ${S.actual.temp} °C (regulador)` : noLimitText();
  $('#metrics').textContent = `STONE ${profOf(id).n}\n${lim}\n` + (m ? `GPU ${nv(m.gpu_temp_c, ' °C')}   ${nv(m.gpu_clock_mhz, ' MHz')}   uso ${nv(m.gpu_busy_pct, ' %')}\nCPU ${nv(m.cpu_temp_c, ' °C')}   uso ${nv(m.cpu_pct, ' %')}   GPU ${nv(m.gpu_power_w, ' W')}\nVentilador ${nv(m.fan_rpm, ' RPM')} · curva de la BIOS\n` : 'Leyendo…\n')
    + 'FPS y frametime: botón ··· → Rendimiento (Steam)';
}
function setMetrics(on) {
  $('#metrics').hidden = !on;
  if (on) metricsTick();
  telemetrySync();        /* the overlay subscribes at 0.5 s; closed, nothing is read */
}

/* EXPERIENCE ENGINE (experience.py): what STONE knows about this game, from its own measurements. */
const CONF_TXT = { high: 'Alta', medium: 'Media', low: 'Baja' };
const GOAL_TXT = { quality: 'CALIDAD', balanced: 'EQUILIBRIO', fluid: 'FLUIDEZ' };
async function xpDlg(g) {
  let r;
  try { r = await Sys.gameExperience(g.appid); } catch (e) { play('error'); return toast('No se pudo leer la experiencia de este juego', false); }
  const back = () => { closeDlg(); play('back'); enterDetail(curG, { r: 1, c: 0 }); };
  const L = r.last, c = r.confidence;
  const rows = [`<p>Confianza: <b>${CONF_TXT[c.level] || c.level}</b> · ${esc(c.text)} · ${esc(c.detail)}</p>`];
  rows.push(L ? `<p>Última medición: <b>${L.avg_fps} FPS</b> de media · 1 % más lento ${L.low1_fps} FPS · ${L.verdict ? esc(L.verdict) + ` (${L.stutters_per_min} tirones/min)` : 'tirones sin datos'}${L.gpu_temp_max ? ` · GPU hasta ${L.gpu_temp_max} °C` : ''}</p>`
    : '<p>Todavía no hay mediciones de este juego. «Optimizar» mide cada combinación con MangoHud.</p>');
  if (r.regression.length) rows.push(`<p>Desde la última medición ${esc(r.regression.join(', '))}: conviene volver a medir.</p>`);
  if (r.autopilot) rows.push(`<p>Mejor medido: ${Object.entries(r.autopilot).filter(([, v]) => v).map(([k]) => GOAL_TXT[k]).join(' · ') || '—'}. STONE RECOMMENDED usa el de EQUILIBRIO.</p>`);
  openDlg(`<h2>EXPERIENCIA</h2>${rows.join('')}<div class="btns"><span class="txt-f" data-f data-b="ok">VOLVER</span></div>`, { onA: back, onB: back });
}

/* GRÁFICOS: the image options of one game in a list, each line with its value; A changes it in place. */
const GFX = [['img', g => imgLabel(g)], ['pre', g => preLabel(g)], ['look', g => lookLabel(g)], ['fg', g => fgLabel(g)], ['ins', g => optLabel(g)], ['opz', g => optzLabel(g)]];
function gfxPanel(g, at = 0) {
  const row = ([k, f]) => { const [l, v] = f(g).split(/: (.*)/s); return `<span class="txt-f sres" data-f data-act="${k}">${esc(l)}<small>${esc(v || '')}</small></span>`; };
  const back = () => { closeDlg(); play('back'); enterDetail(curG, { r: 1, c: 2 }); };
  openDlg(`<h2>GRÁFICOS</h2><p>${esc(g.n)} · cada cambio se aplica la próxima vez que juegues.</p><div class="slist">${GFX.map(row).join('')}</div>
    <div class="btns"><span class="txt-f" data-f data-b="no">VOLVER</span></div>`, {
    onA: el => {
      if (el.dataset.b === 'no') return back();
      const k = el.dataset.act, r = NAV.r;
      if (k === 'opz') { closeDlg(); enterDetail(curG, { r: 1, c: 2 }); return detailA({ dataset: { act: 'opz' } }); }
      Promise.resolve(detailA({ dataset: { act: k } })).then(() => { if (S.screen === 'dlg' && $('#dlg h2') && $('#dlg h2').textContent === 'GRÁFICOS') gfxPanel(g, r); });
    }, onB: back });
  const d = $('#dlg');
  NAV = mkNav([...d.querySelectorAll('.slist [data-f]')].map(e => [e]).concat([[...d.querySelectorAll('.btns [data-f]')]]), { r: at, place: (el, b) => ({ x: b.x, y: b.y + b.h + 4, w: b.w }) });
  NAV.id = 'dlg'; requestAnimationFrame(() => applyFocus());
  if (!g.img) imgLoad(g, curG).then(() => { if (S.screen === 'dlg' && $('#dlg h2') && $('#dlg h2').textContent === 'GRÁFICOS') gfxPanel(g, NAV ? NAV.r : 0); });
}
/* PROPIEDADES: what STONE knows of the game, and uninstalling it (asked twice, done without Steam's dialog). */
function propsDlg(g) {
  const back = () => { closeDlg(); play('back'); enterDetail(curG, { r: 1, c: [...$('#detail').querySelectorAll('.second [data-f]')].length - 1 }); };
  const kv = (k, v) => `<span class="sres">${k}<small>${esc(v)}</small></span>`;
  const canRemove = g.src === 'steam' && g.inst && S.running !== g.i;
  openDlg(`<h2>PROPIEDADES</h2><div class="slist">${kv('Origen', g.o)}${kv('Tamaño', g.sz || '—')}${kv('Tiempo jugado', playText(g))}${kv('Última sesión', g.last || '—')}${kv('Al iniciarse', g.perf ? profOf(g.perf).n : 'Perfil global')}${g.src === 'steam' ? kv('Steam App ID', g.appid) : ''}</div>
    <div class="btns">${canRemove ? '<span class="txt-f" data-f data-b="rm">DESINSTALAR</span>' : ''}<span class="txt-f" data-f data-b="no">VOLVER</span></div>`, {
    onA: el => {
      if (el.dataset.b === 'no') return back();
      play('select');
      openDlg(`<h2>DESINSTALAR</h2><p>Se borra ${esc(g.n)} de la consola (${esc(g.sz || 'su tamaño en disco')}). Tus partidas en la nube de Steam se conservan. Puedes volver a instalarlo cuando quieras.</p>
        <div class="btns"><span class="txt-f" data-f data-b="no">CANCELAR</span><span class="txt-f" data-f data-b="yes">DESINSTALAR</span></div>`, {
        onA: e2 => {
          if (e2.dataset.b !== 'yes') { closeDlg(); play('back'); return propsDlg(g); }
          closeDlg(); play('select');
          S.section = 0; if (NAV) NAV.id = ''; enterHome({ r: 0, c: 0 });
          uninstallGame(g.appid, g.n).then(() => loadLibrary()).then(() => { if (S.screen === 'home') enterHome({ r: 0, c: 0 }); });
        }, onB: () => { closeDlg(); play('back'); propsDlg(g); } });
    }, onB: back });
}

/* ---------- STEAM ASKS, STONE ANSWERS ----------
   Steam sometimes stops to ask (saves in the cloud that do not match, which way to start a game,
   a licence, a first-launch question). Its interface is hidden in the STONE session, so STONE reads
   the question (steamcef.dialog) and asks it with its own screen; the answer presses Steam's button.
   Watched while a game starts, installs or uninstalls. [VERIFICAR EN PLACA] */
let swT = 0, swUntil = 0, swBusy = false, swSkip = { key: '', until: 0 };
function steamWatch(ms) {
  swUntil = Math.max(swUntil, Date.now() + ms);
  if (!swT) swT = setTimeout(swTick, 1200);
}
async function swTick() {
  swT = 0;
  if (Date.now() > swUntil) return;
  if (!swBusy && !S.dormant && !['dlg', 'power', 'quick'].includes(S.screen)) {
    swBusy = true;
    const r = await Sys.steamDialog().catch(() => null);
    swBusy = false;
    const d = r && r.dialog, key = d ? d.title + '|' + d.buttons.join('|') : '';
    if (d && !S.dormant && !(key === swSkip.key && Date.now() < swSkip.until) && !['dlg', 'power', 'quick'].includes(S.screen)) steamAsk(d, key);
  }
  swT = setTimeout(swTick, 2500);
}
function steamAsk(d, key) {
  const from = S.screen, nav = NAV;
  const back = () => {
    closeDlg();
    if (from === 'game') { S.screen = 'game'; NAV = null; line.classList.add('off'); $('#hints').classList.add('hide'); return; }
    if (from === 'detail') return enterDetail(curG, { r: 0, c: 0 });
    if (from === 'library') return enterLibrary();
    if (from === 'settings') return enterSettings();
    if (NAV !== nav) { if (NAV) NAV.id = ''; enterHome({ r: 0, c: 0 }); }
  };
  play('notify');
  openDlg(`<span class="st-cap">STEAM PREGUNTA</span><h2>${esc((d.title || 'Steam').toUpperCase())}</h2>${d.text ? `<p>${esc(d.text)}</p>` : ''}
    <div class="slist">${d.buttons.map((b, i) => `<span class="txt-f sres" data-f data-i="${i}">${esc(b)}</span>`).join('')}</div>`, {
    onA: el => {
      const i = +el.dataset.i; play('select'); back();
      Sys.steamAnswer(i, d.buttons[i]).then(r => { if (!r.ok) toast(r.result === 'changed' ? 'Steam cambió la pregunta: aparecerá de nuevo' : 'Steam ya no lo pregunta', false); },
        () => toast('No se pudo responder a Steam', false));
      steamWatch(10000);
    },
    onB: () => { play('back'); swSkip = { key, until: Date.now() + 30000 }; back(); } });
  const dl = $('#dlg');
  NAV = mkNav([...dl.querySelectorAll('.slist [data-f]')].map(e => [e]), { place: (el, b) => ({ x: b.x, y: b.y + b.h + 4, w: b.w }) });
  NAV.id = 'dlg'; requestAnimationFrame(() => applyFocus());
  hints([['A', 'Responder'], ['B', 'Más tarde']]);
}
