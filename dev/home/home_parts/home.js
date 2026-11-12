/* ---------- HOME ---------- */
let metaT = 0;
const runTag = i => S.running === i ? '<span class="run">EN CURSO</span>' : '';
function homeHTML() {
  let cards = '';
  if (S.section === 0) {
    /* Nobody signed in to Steam on this console: the first thing Home offers */
    if (S.libLogged === 'out') cards += `<div class="card wide vein" data-f data-act="login">${cover('login')}<b>Inicia sesión en Steam</b><span>Tus juegos vienen de tu cuenta de Steam</span></div>`;
    if (G.length && recent.length) {
      const g0 = G[recent[0]], hu = heroUrl(g0);
      cards += `<div class="card hero${g0.inst || g0.src === 'shortcut' ? '' : ' dim'}" data-f data-g="${g0.i}" style="background-image:${hu ? `url(&quot;${hu}&quot;)` : 'none'};background-color:var(--shale)">${hu ? '' : nameTag(g0)}${runTag(g0.i)}</div>`;
      recent.slice(1).forEach(i => { const g = G[i]; cards += `<div class="card cap${g.inst || g.src === 'shortcut' ? '' : ' dim'}${capWide(g) ? ' hdr' : ''}" data-f data-g="${i}" style="background-image:${capUrl(g).replace(/"/g, '&quot;')}">${g.art.capsule || g.art.header ? '' : nameTag(g)}${runTag(i)}</div>`; });
    } else if (S.libLogged !== 'out') {
      cards += `<div class="card wide" data-f data-act="${S.libReady ? 'store' : 'library'}">${cover(S.libReady ? 'store' : 'library')}<b>${S.libReady ? 'Sin juegos' : 'Biblioteca'}</b><span>${S.libReady ? 'Abre la tienda para conseguir el primero' : 'Leyendo la biblioteca de Steam…'}</span></div>`;
    }
    cards += `<div class="card tile" data-f data-act="library">${cover('library')}Biblioteca</div><div class="card tile" data-f data-act="store">${cover('store')}Tienda</div>`;
  } else if (S.section === 2) {
    [['Tienda', 'Ofertas, novedades y lo más vendido en Steam', 'store'], ['Buscar juegos', 'Tu biblioteca y la tienda de Steam', 'search'],
      ['Sorpréndeme', 'STONE elige uno de tus juegos instalados', 'surprise'], ['Descargas', 'Descargas y actualizaciones de juegos', 'downloads'], ['Emuladores', 'Juegos de otras consolas', 'emu']]
      .forEach(([t, s, k]) => { cards += `<div class="card wide" data-f data-act="${k}">${cover(k)}<b>${t}</b><span>${s}</span></div>`; });
  } else {
    if (!SHOTS) loadShots();
    if (SHOTS && SHOTS.length) SHOTS.slice(0, 12).forEach((sh, k) => { cards += `<div class="card cap shot" data-f data-act="shot" data-k="${k}" style="background-image:url(&quot;${Bridge.artUrl(sh.appid === '0' ? '0' : '0', sh.kind)}&quot;)"></div>`; });
    else cards += `<div class="card wide" data-f data-act="noshots">${cover('noshots')}<b>Capturas</b><span>${SHOTS ? 'Aún no hay capturas. Durante el juego: botón STEAM + R1' : 'Leyendo las capturas…'}</span></div>`;
  }
  const ico = {
    lib: '<svg width="26" height="26" viewBox="0 0 26 26" fill="none" stroke-width="2" aria-hidden="true"><rect x="3" y="4" width="6" height="18"/><rect x="11" y="4" width="6" height="18"/><path d="M19 5l4 1-3 16-4-1"/></svg>',
    exp: '<svg width="26" height="26" viewBox="0 0 26 26" fill="none" stroke-width="2" aria-hidden="true"><circle cx="13" cy="13" r="9"/><path d="M16.5 9.5l-2 5-5 2 2-5z"/></svg>',
    set: '<svg width="26" height="26" viewBox="0 0 26 26" fill="none" stroke-width="2" aria-hidden="true"><path d="M4 7h18M4 13h18M4 19h18"/><rect x="8" y="5" width="4" height="4" fill="#141517"/><rect x="15" y="11" width="4" height="4" fill="#141517"/><rect x="6" y="17" width="4" height="4" fill="#141517"/></svg>',
    pow: '<svg width="26" height="26" viewBox="0 0 26 26" fill="none" stroke-width="2" aria-hidden="true"><path d="M13 3v9"/><path d="M7.5 7a8 8 0 1 0 11 0"/></svg>',
    sea: '<svg width="26" height="26" viewBox="0 0 26 26" fill="none" stroke-width="2" aria-hidden="true"><circle cx="11.5" cy="11.5" r="7"/><path d="M17 17l6 6"/></svg>',
    sto: '<svg width="26" height="26" viewBox="0 0 26 26" fill="none" stroke-width="2" aria-hidden="true"><path d="M5 9h16l-1.5 13h-13z"/><path d="M9 9V7a4 4 0 0 1 8 0v2"/></svg>'
  };
  const label = S.section === 0 ? `<b>${S.libNone && G.length ? 'Tu cuenta' : 'Recientes'}</b>${G.length ? ` · ${G.length} juego${G.length === 1 ? '' : 's'}` : ''}`
    : S.section === 2 ? '<b>Explorar</b>' : '<b>Media</b>';
  return `<div class="st-head"></div><div class="st-deep"></div>
    <div class="st-label l1">${label}</div>
    <div class="clip"><div class="track" data-sx="0">${cards}</div></div>
    <div class="horizon"></div>
    <div class="ctx"><div class="kicker" id="hk"></div><div class="ctx-title" id="ht"></div><div class="meta" id="hm"></div></div>
    <div class="sys">
      <span class="txt-f" data-f data-act="search">${ico.sea}Buscar</span>
      <span class="txt-f" data-f data-act="store">${ico.sto}Tienda</span>
      <span class="txt-f" data-f data-act="library">${ico.lib}Biblioteca</span>
      <span class="txt-f" data-f data-act="explore">${ico.exp}Explorar</span>
      <span class="txt-f" data-f data-act="settings">${ico.set}Ajustes</span>
      <span class="txt-f" data-f data-act="power">${ico.pow}Apagar</span>
    </div>`;
}
function homeContext(el) {
  const hk = $('#hk'), ht = $('#ht'), hm = $('#hm');
  hm.classList.remove('on'); clearTimeout(metaT);
  const gi = el.dataset.g;
  if (gi !== undefined) {
    const g = G[+gi], first = el.classList.contains('hero'), playable = g.inst || g.src === 'shortcut';
    hk.innerHTML = !playable ? 'EN TU CUENTA · SIN INSTALAR' : first ? `CONTINUAR${S.running === g.i ? ' · <span class="now">EN CURSO</span>' : ''}` : 'RECIENTE';
    ht.textContent = g.n;
    hm.textContent = !playable ? `${g.upd ? 'Instalándose' : 'Pulsa A para instalarlo'} · ${playText(g)}`
      : `${S.running === g.i ? 'Abierto ahora' : g.last} · ${playText(g)}${g.o !== 'Steam' ? ' · ' + g.o : ''}`;
    metaT = setTimeout(() => hm.classList.add('on'), S.rm ? 150 : 600);
    bgGame(g, true, 'home');           /* CRISTAL: the game's own art, sharp, fills the screen */
    [NAV && NAV.rows[0][NAV.c + 1], NAV && NAV.rows[0][NAV.c - 1]].forEach(nx => { if (nx && nx.dataset.g !== undefined) blurOf(G[+nx.dataset.g]); });
  } else {
    const a = el.dataset.act;
    const label = { login: ['Steam', 'Con el código QR de Steam y tu móvil, sin escribir contraseñas'], store: ['Tienda', 'Ofertas, novedades y lo más vendido en Steam'],
      surprise: ['Sorpréndeme', 'Para cuando no sabes a qué jugar'], search: ['Buscar', 'Tus juegos y la tienda de Steam (Y)'], library: ['Biblioteca', S.libReady ? `${G.length} juego${G.length === 1 ? '' : 's'}` : 'Leyendo…'], explore: ['Explorar', 'Tienda, descargas y emuladores'], settings: ['Ajustes', 'Pantalla, audio, rendimiento y más'], power: ['Apagar', 'Apagar o reiniciar'],
      downloads: ['Descargas', 'Lo que se descarga y el espacio libre'], emu: ['Emuladores', 'Juegos de otras consolas'], noshots: ['Capturas', 'Durante el juego: botón STEAM + R1'],
      shot: (() => { const sh = SHOTS && SHOTS[+el.dataset.k], g = sh && G.find(x => x.appid === sh.appid); return ['Captura', sh ? `${g ? g.n : 'Juego ' + sh.appid} · ${new Date(sh.time * 1000).toLocaleDateString('es-CL')}` : '']; })() }[a] || ['', ''];
    hk.textContent = S.section === 2 ? 'EXPLORAR' : S.section === 3 ? 'MEDIA' : 'SISTEMA';
    if (a === 'search') hk.textContent = 'BUSCAR';
    if (a === 'login') hk.textContent = 'TU CUENTA';
    ht.textContent = label[0]; hm.textContent = label[1];
    metaT = setTimeout(() => hm.classList.add('on'), S.rm ? 150 : 600);
    if (el.closest('.sys') == null || S.section !== 0) setBg(neutralBg, '');
  }
}
function enterHome(opts = {}) {
  S.screen = 'home'; S.from = 'home';
  if (S.section === 1 || S.section === 4) S.section = 0;
  const h = $('#home');
  /* keep: redrawn in place (the library changed): the row does not slide back from the start */
  const keepSx = opts.keep && h.querySelector('.track') ? h.querySelector('.track').dataset.sx : null;
  h.innerHTML = homeHTML();
  showScreen('home'); chrome(true, true);
  const track = h.querySelector('.track');
  if (keepSx !== null) { track.style.transition = 'none'; track.dataset.sx = keepSx; track.style.transform = `translateX(${keepSx}px)`; requestAnimationFrame(() => { track.style.transition = ''; }); }
  const rows = [[...track.children], [...h.querySelectorAll('.sys [data-f]')]];
  const prev = NAV && NAV.id === 'home' ? NAV : null;
  /* sys: one of the system row's items by name (the row has changed over time; names do not) */
  if (opts.sys) { opts.r = 1; opts.c = Math.max(0, rows[1].findIndex(e => e.dataset.act === opts.sys)); }
  NAV = mkNav(rows, {
    r: opts.r ?? (prev ? prev.r : 0), c: opts.c ?? (prev ? prev.c : 0),
    place: (el, b, r) => r === 0 ? { x: b.x, y: 668, w: b.w * (S.rm ? 1 : 1.06) } : { x: b.x, y: b.y + b.h + 14, w: b.w },
    scroll: el => {
      if (!el.closest('.track')) return;
      let sx = +track.dataset.sx; const l = el.offsetLeft, r = l + el.offsetWidth * 1.06, view = 1728;
      if (l + sx < 0) sx = -l; else if (r + sx > view) sx = view - r;
      track.dataset.sx = sx; track.style.transform = `translateX(${sx}px)`;
    },
    onFocus: homeContext
  });
  NAV.id = 'home';
  if (NAV.c >= rows[NAV.r].length) NAV.c = rows[NAV.r].length - 1;
  requestAnimationFrame(() => applyFocus({ slow: opts.slow }));
  hints([['A', S.section === 0 ? 'Abrir' : 'Elegir'], ['LB RB', 'Sección']]);
}
function homeA(el) {
  const a = el.dataset.act;
  if (el.dataset.g !== undefined) {
    const g = G[+el.dataset.g];
    if (S.running === g.i && el.classList.contains('hero')) { play('select'); return resumeGame(); }
    play('select'); return enterDetail(g.i);
  }
  if (a === 'search') { play('select'); return openSearch(); }
  if (a === 'login') return steamOpen('login');
  if (a === 'store') { play('select'); return enterStore(); }
  if (a === 'surprise') return surprise();
  if (a === 'library') { play('select'); S.section = 1; return enterLibrary(); }
  if (a === 'explore') { play('select'); S.section = 2; return enterHome({ r: 0, c: 0 }); }
  if (a === 'settings') { play('select'); return enterSettings(); }
  if (a === 'power') { play('select'); return openPower(); }
  if (a === 'downloads') { play('select'); return openCat('Almacenamiento'); }
  if (a === 'emu') { play('select'); return openCat('Emuladores'); }
  if (a === 'shot') { play('select'); return shotViewer(+el.dataset.k); }
  if (a === 'noshots') { play('select'); return toast('Las capturas que hagas jugando aparecen aquí', false); }
}
function section(d) {
  const n = S.section + d;
  if (n < 0 || n > 4) return bump(d);
  play('nav'); S.section = n;
  if (n === 1) enterLibrary(); else if (n === 4) enterStore(); else { if (NAV) NAV.id = ''; enterHome({ r: 0, c: 0 }); }
}

/* EXPERIENCE ENGINE · Thermal Forecast (experience.py thermal_forecast, same rule): least squares over
   the last 5 minutes of stoned's GPU temperature; minutes to the profile's limit at this pace. */
const THERM = [];
function thermPush(m) {
  if (!m || m.gpu_temp_c == null) return;
  const t = Date.now() / 1000; THERM.push([t, m.gpu_temp_c]);
  while (THERM.length && t - THERM[0][0] > 300) THERM.shift();
}
function thermalForecast(limit) {
  if (!limit || THERM.length < 6 || THERM[THERM.length - 1][0] - THERM[0][0] < 60) return null;
  const n = THERM.length, mt = THERM.reduce((a, p) => a + p[0], 0) / n, mc = THERM.reduce((a, p) => a + p[1], 0) / n;
  const v = THERM.reduce((a, p) => a + (p[0] - mt) ** 2, 0); if (!v) return null;
  const slope = THERM.reduce((a, p) => a + (p[0] - mt) * (p[1] - mc), 0) / v * 60;
  if (slope < 0.2) return null;
  const now = mc + slope / 60 * (THERM[n - 1][0] - mt);
  return Math.max(0, (limit - now) / slope);
}

/* ---------- SEARCH (M13): the library in the page, Steam's store through the host ----------
   Y (or Buscar) opens the on-screen keyboard; results list the person's games first (play or install)
   and then the store: a free game installs from STONE, a paid one is bought in Steam. */
const fold = t => String(t).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
function openSearch() {
  const from = S.screen;
  osk('BUSCAR JUEGOS', q => { if (q === null || !q.trim()) return from === 'library' ? enterLibrary() : enterHome({ sys: 'search' }); searchResults(q.trim(), from); });
}
function searchResults(q, from) {
  const words = fold(q).split(/\s+/).filter(Boolean);
  const lib = G.filter(g => words.every(w => fold(g.n).includes(w))).slice(0, 8);
  let store = null, storeErr = null;
  const under = () => from === 'library' ? enterLibrary() : enterHome({ sys: 'search' });
  const back = () => { closeDlg(); play('back'); return under(); };
  const draw = () => {
    const mine = new Set(G.map(g => g.appid));
    const libRows = lib.map(g => `<span class="txt-f sres" data-f data-g="${g.i}">${esc(g.n)}<small>${g.inst ? 'Instalado · JUGAR' : 'En tu cuenta · INSTALAR'}</small></span>`).join('');
    const st = store === null ? '<p>Buscando en la tienda de Steam…</p>' : storeErr ? `<p>${esc(storeErr)}</p>`
      : store.filter(s => !mine.has(s.appid)).slice(0, 8).map((s, k) => `<span class="txt-f sres" data-f data-s="${k}">${esc(s.name)}<small>${s.free ? 'Gratis · VER' : esc(s.price || 'De pago') + ' · VER'}</small></span>`).join('') || '<p>Nada más en la tienda.</p>';
    openDlg(`<h2>«${esc(q)}»</h2><div class="slist"><span class="st-cap">EN TU BIBLIOTECA</span>${libRows || '<p>Ningún juego tuyo coincide.</p>'}<span class="st-cap">EN LA TIENDA DE STEAM</span>${st}</div>
      <div class="btns"><span class="txt-f" data-f data-b="again">BUSCAR OTRA COSA</span><span class="txt-f" data-f data-b="no">VOLVER</span></div>`, {
      onA: el => {
        if (el.dataset.b === 'no') return back();
        if (el.dataset.b === 'again') { closeDlg(); return openSearch(); }
        play('select'); closeDlg();
        if (el.dataset.g !== undefined) return enterDetail(+el.dataset.g);
        /* a game of the store: its page (price, COMPRAR EN STEAM, the phone, or INSTALAR when free) */
        const row = store.filter(s => !mine.has(s.appid))[+el.dataset.s];
        enterStorePage(row.appid, () => { under(); draw(); }, row);
      }, onB: back });
    const d = $('#dlg');
    const rows = [...d.querySelectorAll('.slist [data-f]')].map(e => [e]).concat([[...d.querySelectorAll('.btns [data-f]')]]);
    NAV = mkNav(rows, { place: (el, b) => ({ x: b.x, y: b.y + b.h + 4, w: b.w }) }); NAV.id = 'dlg';
    requestAnimationFrame(() => applyFocus());
  };
  draw();
  if (S.libReady && !S.libOwnedKnown) toast('La interfaz de Steam no responde: solo aparecen tus juegos instalados', false);
  Bridge.call('store.search', q).then(r => { store = r.results; }, e => { storeErr = (e && e.message) || 'La tienda no responde'; })
    .then(() => { if (S.screen === 'dlg' && $('#dlg h2') && $('#dlg h2').textContent === `«${q}»`) draw(); });
}

/* Settings opened straight at one category (Explorar → Descargas, Emuladores). */
function openCat(name) { const k = CATS.indexOf(name); if (k >= 0) cat = k; return enterSettings({ pane: true, ri: 0 }); }

/* ---------- STONE MEDIA: the screenshots Steam saved (media.py), without Steam's screen ---------- */
let SHOTS = null, shotsBusy = false;
function loadShots() {
  if (shotsBusy) return; shotsBusy = true;
  Sys.shots().then(r => { SHOTS = r.shots; }, () => { SHOTS = []; }).then(() => { shotsBusy = false; if (S.screen === 'home' && S.section === 3) enterHome({ r: 0, c: 0 }); });
}
function shotViewer(k) {
  const n = SHOTS.length, sh = SHOTS[k], g = G.find(x => x.appid === sh.appid);
  const when = new Date(sh.time * 1000).toLocaleString('es-CL', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  const back = () => { closeDlg(); $('#dlg').classList.remove('viewer'); play('back'); enterHome({ r: 0, c: Math.min(k, 11) }); };
  openDlg(`<div class="shot-img" style="background-image:url(&quot;${Bridge.artUrl('0', sh.kind)}&quot;)"></div>
    <div class="shot-cap"><b>${esc(g ? g.n : 'Juego ' + sh.appid)}</b><span>${esc(when)} · ${k + 1} de ${n}</span></div>
    <div class="btns"><span class="txt-f" data-f data-b="prev">ANTERIOR</span><span class="txt-f" data-f data-b="next">SIGUIENTE</span><span class="txt-f" data-f data-b="no">VOLVER</span></div>`, {
    onA: el => { if (el.dataset.b === 'no') return back(); play('nav'); shotViewer((k + (el.dataset.b === 'next' ? 1 : n - 1)) % n); NAV.c = el.dataset.b === 'next' ? 1 : 0; applyFocus(); },
    onB: back }, false, true);
  $('#dlg').classList.add('viewer');
}
