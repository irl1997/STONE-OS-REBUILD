/* ---------- The library follows Steam ----------
   The host watches Steam (the account answering some seconds after the start, a game bought on the
   phone, an install that ends) and says "library"; artwork STONE fetches for games Steam had not
   cached arrives as "art". The screen in front is redrawn in place: same focus, same scroll. */
let libBusy = false, libAgain = false;
const libSnap = () => JSON.stringify([G.map(g => [g.appid, g.n, g.inst, g.upd, g.art.capsule, g.art.hero, g.art.header]), S.libLogged, S.libFound, recent.map(i => G[i] && G[i].appid)]);
async function reloadLibrary() {
  if (libBusy) { libAgain = true; return; }
  libBusy = true;
  const before = libSnap(), f = focusEl();
  const focus = f && f.dataset && f.dataset.g !== undefined && G[+f.dataset.g] ? G[+f.dataset.g].appid : null;
  await loadLibrary();
  libBusy = false;
  wantedArrived();
  if (libSnap() !== before) libRedraw(focus);
  if (libAgain) { libAgain = false; reloadLibrary(); }
}
function libRedraw(focusAppid) {
  const k = focusAppid === null ? -1 : G.findIndex(g => g.appid === focusAppid);
  if (S.steamFront || !NAV) return;
  if (S.screen === 'home' && NAV.id === 'home') {
    if (S.section !== 0) return;
    const c = k >= 0 ? recent.indexOf(k) : -1;
    return enterHome(NAV.r === 0 && c >= 0 ? { r: 0, c, keep: true } : { keep: true });
  }
  if (S.screen === 'library' && NAV.id === 'library') {
    const list = libList(), rowsN = Math.ceil(list.length / 6), pos = k >= 0 ? list.findIndex(g => g.i === k) : -1;
    if (pos >= 0 && NAV.r > 0) return enterLibrary({ r: Math.floor(pos / 6) + 1, c: pos % 6, keep: true });
    if (!list.length || NAV.r === 0) return enterLibrary({ r: 0, c: Math.min(NAV.c, FILTERS.length), keep: true });
    const r = Math.min(NAV.r, rowsN), len = Math.min(6, list.length - (r - 1) * 6);
    return enterLibrary({ r, c: Math.min(NAV.c, len - 1), keep: true });
  }
  if (S.screen === 'detail' && NAV.id === 'detail') return S.detailGone ? enterHome({ r: 0, c: 0 }) : enterDetail(curG, { r: NAV.r, c: NAV.c });
  if (S.screen === 'spage') return storePageDraw({ r: 0, c: 0 });      /* the game arrived: its big button changed */
  if (S.screen === 'store') return enterStore({ r: NAV.r, c: NAV.c, keep: true });
}
Bridge.on('library', () => { if (S.libReady) reloadLibrary(); });
Bridge.on('art', d => {
  const got = (d && d.art) || {}, ids = new Set(Object.keys(got));
  G.forEach(g => {
    const a = got[g.appid]; if (!a) return;
    g.art.capsule = g.art.capsule || !!a.capsule; g.art.hero = g.art.hero || !!a.hero;
    g.art.header = !g.art.capsule && (g.art.header || !!a.header);
  });
  document.querySelectorAll('#home .card[data-g], #library .card[data-g]').forEach(el => {
    const g = G[+el.dataset.g]; if (!g || !ids.has(g.appid)) return;
    const nm = el.querySelector('.nm');
    if (el.classList.contains('hero')) { const u = heroUrl(g); if (u) { el.style.backgroundImage = `url("${u}")`; if (nm) nm.remove(); } return; }
    el.style.backgroundImage = capUrl(g); el.classList.toggle('hdr', capWide(g));
    if (nm && g.art.capsule) nm.remove();
  });
  /* the big picture behind the game being looked at */
  if (S.bgFor && G[S.bgFor.i] && ids.has(G[S.bgFor.i].appid) && ['home', 'detail'].includes(S.screen)) { bgCur = ''; bgGame(G[S.bgFor.i], S.bgFor.sharp, S.bgFor.veil); }
  storeArt(got);
});
/* Games bought away from the console (the phone, Steam's own store): installed as soon as Steam
   lists them in the account, without anyone asking again. */
function wantedArrived() {
  if (!WANT.size || !S.libOwnedKnown) return;
  let changed = false;
  G.forEach(g => {
    if (!WANT.has(g.appid) || g.src !== 'steam') return;
    WANT.delete(g.appid); changed = true;
    if (g.inst || g.upd) return;
    Sys.install(g.appid).then(() => { steamWatch(20000); play('notify'); longToast(`${g.n} ya está en tu cuenta: STONE lo está instalando`, 8000); },
      () => longToast(`${g.n} ya está en tu cuenta. Instálalo desde tu biblioteca`, 8000));
  });
  if (changed) savePrefs();
}
/* SORPRÉNDEME: STONE picks one of the installed games, the ones not played for longest first. */
function surprise() {
  const pool = G.filter(g => (g.inst || g.src === 'shortcut') && S.running !== g.i);
  if (!pool.length) { play('error'); return toast('Aún no hay juegos instalados entre los que elegir', false); }
  const old = [...pool].sort((a, b) => (a.lastT || 0) - (b.lastT || 0)).slice(0, Math.max(1, Math.ceil(pool.length / 2)));
  const g = old[Math.floor(Math.random() * old.length)];
  play('select'); enterDetail(g.i);
  toast(`STONE elige: ${g.n}${g.min ? '' : ' · todavía sin jugar'}`, false);
}
/* PARTE DE SESIÓN: when a game ends, how long it was played and how the console was (read then from
   stoned, never estimated). Shown once, at Home. */
let playT0 = 0;
function sessionStart() { if (!playT0) playT0 = Date.now(); }
function sessionReport(g) {
  const t0 = playT0; playT0 = 0;
  if (!S.report || !g || !t0) return;
  const min = Math.round((Date.now() - t0) / 60000);
  if (min < 1) return;
  const dur = min < 60 ? `${min} min` : `${Math.floor(min / 60)} h ${String(min % 60).padStart(2, '0')} min`;
  PerfAPI.getMetrics().then(m => m, () => null).then(m => {
    const temp = m && m.gpu_temp_c != null ? ` · GPU ${Math.round(m.gpu_temp_c)} °C al terminar` : '';
    setTimeout(() => longToast(`PARTE DE SESIÓN · ${g.n} · ${dur}${temp} · ${profOf(g.perf || S.prof).n}`, 9000), 1400);
  });
}
