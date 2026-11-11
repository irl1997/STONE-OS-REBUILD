/* ---------- TIENDA (M13, D-34): Steam's store, read by the host and drawn by STONE ----------
   The lists and prices are Steam's own (its public store, in the place the console connects from).
   STONE shows them and takes the person to buy: in Steam's own interface (COMPRAR EN STEAM) or on the
   phone (a QR code of the game's page). A free game, and a game already in the account, install here. */
const STORE = { data: null, err: null, busy: false, tab: 0, found: null, q: '', t: 0 };
const STORE_COLS = 4, STORE_W = 400, STORE_H = 187, STORE_GAP = (1728 - STORE_COLS * STORE_W) / (STORE_COLS - 1), STORE_ROW = 312;
const storeTabs = () => [...(STORE.data || []).map(s => s.title), STORE.found ? `«${STORE.q}»` : 'Buscar'];
const storeIsSearch = () => STORE.tab >= (STORE.data || []).length;
const storeItems = () => storeIsSearch() ? (STORE.found || []) : STORE.data[STORE.tab].items;
const storeMine = appid => G.find(g => g.appid === appid && g.src === 'steam') || null;
function storeLoad() {
  if (STORE.busy) return;
  const first = !STORE.data;           /* the first lists: the focus goes to the first game */
  STORE.busy = true; STORE.err = null;
  Sys.storeFeatured().then(r => { STORE.data = r.sections; STORE.t = Date.now(); }, e => { STORE.err = (e && e.message) || 'La tienda de Steam no responde'; })
    .then(() => { STORE.busy = false; if (S.screen === 'store') enterStore(first ? {} : { r: NAV.r, c: NAV.c }); });
}
function storePrice(it) {
  const mine = storeMine(it.appid);
  if (mine) return mine.inst ? 'Instalado' : mine.upd ? 'Instalándose' : 'En tu cuenta';
  if (it.soon) return 'Próximamente';
  if (it.free) return 'Gratis';
  return it.price || 'Ver precio';
}
function storeCard(it, k) {
  const row = Math.floor(k / STORE_COLS), col = k % STORE_COLS;
  const img = it.art ? `url(&quot;${Bridge.artUrl(it.appid, 'header')}&quot;)` : 'none';
  return `<div class="card scard" data-f data-s="${k}" data-a="${it.appid}" style="left:${(col * (STORE_W + STORE_GAP)).toFixed(2)}px;top:${row * STORE_ROW}px;background-image:${img}">
    ${it.art ? '' : `<span class="nm">${esc(it.name.toUpperCase())}</span>`}${it.discount ? `<span class="off">−${it.discount} %</span>` : ''}
    <span class="cap2"><b>${esc(it.name)}</b><i>${it.was && !storeMine(it.appid) ? `<s>${esc(it.was)}</s>` : ''}${esc(storePrice(it))}</i></span></div>`;
}
function enterStore(opts = {}) {
  S.screen = 'store'; S.from = 'store'; S.section = 4;
  let st = $('#store');
  if (!st) { st = document.createElement('section'); st.id = 'store'; st.className = 'screen'; stage.insertBefore(st, $('#game')); }
  if (!STORE.data && !STORE.err) storeLoad();
  else if (STORE.data && Date.now() - STORE.t > 900000) storeLoad();          /* the shop window changes during the day */
  if (STORE.tab > (STORE.data || []).length) STORE.tab = 0;
  const ready = !!STORE.data, items = ready ? storeItems() : [];
  const keepSy = opts.keep && st.querySelector('.grid') ? st.querySelector('.grid').dataset.sy : null;
  const msg = !ready ? (STORE.err ? `${STORE.err}` : 'Leyendo la tienda de Steam…')
    : !items.length ? (storeIsSearch() ? (STORE.found ? 'Steam no tiene juegos con ese nombre.' : 'Pulsa A en «Buscar» (o Y) y escribe el nombre de un juego.') : 'Steam no tiene juegos en esta lista ahora.') : '';
  const tabs = ready ? storeTabs() : (STORE.err ? ['Reintentar'] : []);
  st.innerHTML = `<div class="filters">${tabs.map((t, k) => `<span class="txt-f${ready && k === STORE.tab ? ' cur' : ''}" data-f data-tab="${k}">${esc(t)}</span>`).join('')}</div>
    <div class="count">${ready && items.length ? `${items.length} juegos · precios de Steam` : 'Tienda de Steam'}</div>
    <div class="gclip"><div class="grid" data-sy="0" style="height:${Math.ceil(items.length / STORE_COLS) * STORE_ROW}px">${items.map(storeCard).join('')}</div></div>
    ${msg ? `<div class="empty">${esc(msg)}</div>` : ''}
    <div class="sel" id="ssel"></div>`;
  showScreen('store'); chrome(true, true); setBg(neutralBg, '');
  const grid = st.querySelector('.grid'), cards = [...grid.children];
  const rows = [[...st.querySelectorAll('.filters [data-f]')]];
  for (let k = 0; k < cards.length; k += STORE_COLS) rows.push(cards.slice(k, k + STORE_COLS));
  if (!rows[0].length) rows[0] = [st.querySelector('.count')];
  let r = opts.r ?? (cards.length ? 1 : 0), c = opts.c ?? 0;
  if (r >= rows.length) r = rows.length - 1;
  if (c >= rows[r].length) c = rows[r].length - 1;
  if (keepSy !== null) { grid.style.transition = 'none'; grid.dataset.sy = keepSy; grid.style.transform = `translateY(${keepSy}px)`; requestAnimationFrame(() => { grid.style.transition = ''; }); }
  NAV = mkNav(rows, {
    r, c,
    place: (el, b, rr) => rr === 0 ? { x: b.x, y: b.y + b.h + 6, w: b.w } : { x: b.x, y: b.y + STORE_H + 12, w: STORE_W * (S.rm ? 1 : 1.06) },
    scroll: el => {
      if (!el.closest('.grid')) return;
      let sy = +grid.dataset.sy; const t = el.offsetTop, bot = t + STORE_ROW, view = 676;
      if (t - 30 + sy < 0) sy = -(t - 4); else if (bot + sy > view) sy = view - bot;
      grid.dataset.sy = sy; grid.style.transform = `translateY(${sy}px)`;
    },
    onFocus: el => {
      const s = $('#ssel');
      if (el.dataset.s === undefined) { s.textContent = ready ? 'Las listas de la tienda de Steam' : ''; return; }
      const it = storeItems()[+el.dataset.s], mine = storeMine(it.appid);
      s.textContent = `${it.name} · ${storePrice(it)}${it.was && !mine ? ` · antes ${it.was} · −${it.discount} %` : ''}`;
    }
  });
  NAV.id = 'store';
  requestAnimationFrame(() => applyFocus());
  hints([['A', 'Ver'], ['Y', 'Buscar'], ['LB RB', 'Sección'], ['B', 'Inicio']]);
}
function storeA(el) {
  if (!el) return;
  if (el.dataset.tab !== undefined) {
    play('select');
    if (!STORE.data) { STORE.err = null; storeLoad(); return enterStore({ r: 0, c: 0 }); }
    const k = +el.dataset.tab;
    if (k >= STORE.data.length && (STORE.tab === k || !STORE.found)) return storeSearch();
    STORE.tab = k; return enterStore({ r: 0, c: k });
  }
  if (el.dataset.s === undefined) return;
  const it = storeItems()[+el.dataset.s], at = { r: NAV.r, c: NAV.c };
  play('select');
  enterStorePage(it.appid, () => enterStore(at), it);
}
function storeSearch() {
  const at = NAV && NAV.id === 'store' ? { r: NAV.r, c: NAV.c } : { r: 0, c: 0 };
  osk('BUSCAR EN LA TIENDA', q => {
    if (q === null || !q.trim()) return enterStore(at);
    STORE.q = q.trim().slice(0, 40); STORE.found = []; STORE.tab = (STORE.data || []).length;
    enterStore({ r: 0, c: STORE.tab });
    toast('Buscando en la tienda de Steam…', false);
    Bridge.call('store.search', q.trim()).then(r => { STORE.found = r.results; }, e => { STORE.found = []; play('error'); toast((e && e.message) || 'La tienda no responde', false); })
      .then(() => { if (S.screen === 'store' && storeIsSearch()) enterStore({ r: STORE.found.length ? 1 : 0, c: STORE.found.length ? 0 : STORE.tab }); });
  });
}
function storeInput(a) {
  if (['up', 'down', 'left', 'right'].includes(a)) return move(a);
  if (a === 'a') return storeA(focusEl());
  if (a === 'lb' || a === 'rb') return section(a === 'lb' ? -1 : 1);
  if (a === 'y') { play('select'); return storeSearch(); }
  if (a === 'b' || a === 'home') { play('back'); S.section = 0; if (NAV) NAV.id = ''; return enterHome({ r: 0, c: 0 }); }
}
/* Pictures fetched by the host after the list was drawn */
function storeArt(got) {
  const lists = [...(STORE.data || []).map(s => s.items), STORE.found || []];
  lists.forEach(items => items.forEach(it => { if (got[it.appid] && got[it.appid].header) it.art = true; }));
  document.querySelectorAll('#store .scard').forEach(el => {
    const a = got[el.dataset.a]; if (!a || !a.header) return;
    el.style.backgroundImage = `url("${Bridge.artUrl(el.dataset.a, 'header')}")`;
    const nm = el.querySelector('.nm'); if (nm) nm.remove();
  });
  if (S.screen === 'spage' && got[SPG.id]) { if (got[SPG.id].hero) SPG.hero = true; if (got[SPG.id].header) SPG.header = true; storePageBg(); }
}

/* ---------- A game's page in the store ---------- */
const SPG = { id: null, d: null, err: null, back: null, row: null, hero: false, header: false, installing: false };
function enterStorePage(appid, back, row) {
  Object.assign(SPG, { id: appid, d: null, err: null, back, row: row || null, hero: false, header: !!(row && row.art), installing: false });
  storePageDraw();
  Sys.storeDetails(appid).then(d => { if (SPG.id === appid) SPG.d = d; }, e => { if (SPG.id === appid) SPG.err = (e && e.message) || 'La tienda de Steam no responde'; })
    .then(() => { if (S.screen === 'spage' && SPG.id === appid) storePageDraw({ r: NAV.r, c: NAV.c }); });
  Sys.artWant(appid).catch(() => {});
}
function storePageBg() {
  const u = SPG.hero ? Bridge.artUrl(SPG.id, 'hero') : SPG.header ? Bridge.artUrl(SPG.id, 'header') : null;
  setBg(u ? `url("${u}")` : neutralBg, 'side');
}
function storePageDraw(opts = {}) {
  S.screen = 'spage';
  const d = SPG.d, row = SPG.row, mine = storeMine(SPG.id);
  const name = (d && d.name) || (row && row.name) || (mine && mine.n) || 'Juego';
  const free = d ? d.free : !!(row && row.free), soon = d ? d.soon : !!(row && row.soon);
  const price = d ? d.price : row && row.price, was = d ? d.was : row && row.was, pct = d ? d.discount : row && row.discount;
  let prim, act, sec;
  if (mine) { prim = mine.inst ? 'ABRIR EN TU BIBLIOTECA' : mine.upd ? 'INSTALÁNDOSE…' : 'INSTALAR DESDE TU BIBLIOTECA'; act = 'lib'; sec = [['Volver', 'back']]; }
  else if (SPG.err && !row) { prim = 'VOLVER'; act = 'back'; sec = []; }
  else if (!d && !row) { prim = 'LEYENDO…'; act = 'wait'; sec = [['Volver', 'back']]; }
  else if (soon) { prim = 'PRÓXIMAMENTE'; act = 'soon'; sec = [['Ver en el móvil', 'qr'], ['Volver', 'back']]; }
  else if (free) { prim = SPG.installing ? 'INSTALANDO…' : 'INSTALAR'; act = 'install'; sec = [['Volver', 'back']]; }
  else { prim = 'COMPRAR EN STEAM'; act = 'buy'; sec = [['Comprar con el móvil', 'qr'], ['Volver', 'back']]; }
  const state = mine ? (mine.inst ? 'Instalado' : mine.upd ? 'Instalándose' : 'En tu cuenta') : WANT.has(SPG.id) ? 'STONE lo instala al comprarlo' : 'No está en tu cuenta';
  const tags = d && d.genres && d.genres.length ? ' · ' + d.genres.slice(0, 3).join(' · ') : '';
  const by = d ? [d.by && d.by.join(', '), d.release].filter(Boolean).join(' · ') : '';
  $('#detail').innerHTML = `
    <div class="col"><div class="origin">TIENDA DE STEAM${esc(tags)}</div><h1${name.length > 22 ? ' class="long"' : ''}>${esc(name.toUpperCase())}</h1>
      <div class="stats">${esc(by || (SPG.err ? SPG.err : d ? '' : 'Leyendo la ficha de Steam…'))}</div>
      <div class="stats about">${esc(d && d.about ? d.about : '')}</div></div>
    <div class="primary txt-f" data-f data-act="${act}" id="dprim">${prim}</div>
    <div class="second">${sec.map(([s, a]) => `<span class="txt-f" data-f data-act="${a}">${s}</span>`).join('')}</div>
    <div class="info"><div><span>Precio</span><b>${esc(soon ? 'Sin precio todavía' : free ? 'Gratis' : price || '—')}</b></div>
      ${was ? `<div><span>Antes</span><b>${esc(was)} · −${pct} %</b></div>` : ''}
      <div><span>Lanzamiento</span><b>${esc((d && d.release) || '—')}</b></div><div><span>Estado</span><b>${esc(state)}</b></div></div>`;
  showScreen('detail'); chrome(true, false);
  storePageBg();
  const el = $('#detail'), second = [...el.querySelectorAll('.second [data-f]')];
  const rows = [[el.querySelector('#dprim')]]; if (second.length) rows.push(second);
  let r = opts.r || 0, c = opts.c || 0;
  if (r >= rows.length) r = 0;
  if (c >= rows[r].length) c = 0;
  NAV = mkNav(rows, { r, c, place: (e, b, rr) => ({ x: b.x, y: b.y + b.h + (rr === 0 ? 16 : 12), w: b.w }) });
  NAV.id = 'spage';
  requestAnimationFrame(() => applyFocus());
  hints([['A', 'Elegir'], ['B', 'Volver']]);
}
function storePageInput(a) {
  /* down from the big button goes to the first of the small ones (not to the nearest one by position) */
  if (a === 'down' && NAV.r === 0 && NAV.rows[1]) { NAV.r = 1; NAV.c = 0; play('nav'); return applyFocus(); }
  if (['up', 'down', 'left', 'right'].includes(a)) return move(a);
  if (a === 'b') { play('back'); return SPG.back(); }
  if (a === 'home') { S.section = 0; if (NAV) NAV.id = ''; return enterHome({ r: 0, c: 0 }); }
  if (a !== 'a') return;
  const el = focusEl(), k = el && el.dataset.act, mine = storeMine(SPG.id);
  if (k === 'back') { play('back'); return SPG.back(); }
  if (k === 'wait') { play('error'); return toast('Leyendo la ficha de Steam…', false); }
  if (k === 'soon') { play('error'); return toast('Todavía no está a la venta en Steam', false); }
  if (k === 'lib' && mine) { play('select'); S.from = 'home'; return enterDetail(mine.i); }
  if (k === 'install') {
    if (SPG.installing) { play('error'); return toast('Ya se está instalando: la descarga se ve en Ajustes → Almacenamiento', false); }
    play('select');
    return sys('install', SPG.id).then(r => {
      if (!r) return;
      SPG.installing = true; steamWatch(20000);
      toast('Instalando: la descarga se ve en Ajustes → Almacenamiento', false);
      if (S.screen === 'spage') storePageDraw({ r: 0, c: 0 });
    });
  }
  if (k === 'buy') { WANT.add(SPG.id); savePrefs(); return steamOpen('app', SPG.id); }
  if (k === 'qr') { play('select'); return storeQr(SPG.id); }
}
/* COMPRAR CON EL MÓVIL: the game's page on Steam's web store as a QR code. Nothing is typed on the
   console and STONE installs the game by itself when Steam lists it in the account (WANT). */
function storeQr(appid) {
  const back = dlgOver(), url = `https://store.steampowered.com/app/${appid}`;
  WANT.add(appid); savePrefs();
  openDlg(`<span class="st-cap">COMPRAR CON EL MÓVIL</span><h2>ESCANEA EL CÓDIGO</h2>
    <div class="qrrow">${qrSvg(url, 300)}<div><p>Abre la cámara del móvil, apunta al código y compra el juego con tu cuenta de Steam.</p>
    <p>Cuando Steam lo añada a tu cuenta, STONE lo instala sola: no hace falta volver a esta pantalla.</p><p class="url">${esc(url.slice(8))}</p></div></div>
    <div class="btns"><span class="txt-f" data-f data-b="ok">LISTO</span><span class="txt-f" data-f data-b="no">NO INSTALAR SOLA</span></div>`, {
    onA: el => {
      play('select');
      if (el.dataset.b === 'no') { WANT.delete(appid); savePrefs(); toast('STONE no lo instalará sola: aparecerá en tu biblioteca para instalarlo tú', false); }
      back(); if (S.screen === 'spage') storePageDraw({ r: NAV.r, c: NAV.c });
    }, onB: () => { play('back'); back(); if (S.screen === 'spage') storePageDraw({ r: NAV.r, c: NAV.c }); } });
}
