/* ---------- Library: Steam's games (installed, and the rest of the account through Steam's
   interface) and shortcuts, read by the host ----------
   The host sorts by last played, installed first. Artwork comes from Steam's own cache through stone://art. */
let G = [], recent = [];
const favs = new Set();
const WANT = new Set();          /* games being bought away from the console: installed when Steam lists them */
const SRC = { steam: 'Steam', shortcut: 'Acceso directo' };
function ago(t) {
  if (!t) return 'Nunca';
  const s = Date.now() / 1000 - t, d = Math.round(s / 86400), pl = (n, a, b) => `Hace ${n} ${n === 1 ? a : b}`;
  if (s < 3600) return pl(Math.max(1, Math.round(s / 60)), 'min', 'min');
  if (s < 86400) return pl(Math.round(s / 3600), 'hora', 'horas');
  if (d <= 1) return 'Ayer';
  if (d < 7) return pl(d, 'día', 'días');
  if (d < 30) return pl(Math.round(d / 7), 'semana', 'semanas');
  if (d < 365) return pl(Math.round(d / 30), 'mes', 'meses');
  return pl(Math.round(d / 365), 'año', 'años');
}
const sizeText = b => !b ? '—' : b >= 1e9 ? (b / 1e9).toFixed(b >= 1e10 ? 0 : 1).replace('.', ',') + ' GB' : Math.max(1, Math.round(b / 1e6)) + ' MB';
const playText = g => !g.min ? 'Sin jugar' : g.min < 60 ? `${g.min} min jugados` : `${g.h} h jugadas`;
async function loadLibrary() {
  let r = null;
  try { r = await Sys.library(); } catch (e) { r = null; }
  const list = r ? r.games : [];
  /* S.running, S.launching and the open game page are positions in G: each one follows its game */
  const idOf = i => i !== null && i !== undefined && G[i] ? G[i].appid : null;
  const run = idOf(S.running), lau = idOf(S.launching), cur = typeof curG === 'number' ? idOf(curG) : null;
  G = list.map((x, i) => ({ i, appid: x.appid, n: x.name, o: SRC[x.source] || 'Steam', src: x.source, min: x.playtime_min,
    h: Math.round(x.playtime_min / 60), lastT: x.last_played, last: ago(x.last_played), sz: sizeText(x.size_bytes),
    inst: x.installed, upd: x.updating, art: Object.assign({ capsule: false, hero: false, header: false, hero2x: false }, x.art), fav: favs.has(x.appid), perf: null }));
  const at = a => { const k = a === null ? -1 : G.findIndex(g => g.appid === a); return k < 0 ? null : k; };
  S.running = at(run); S.launching = at(lau);
  S.detailGone = cur !== null && at(cur) === null;
  if (cur !== null && at(cur) !== null) curG = at(cur);
  recent = G.filter(g => g.inst || g.src === 'shortcut').slice(0, 6).map(g => g.i);
  /* nothing installed yet (a new console): the account's games take the first row, ready to install */
  S.libNone = !recent.length;
  if (S.libNone) recent = G.slice(0, 6).map(g => g.i);
  S.libReady = true; S.libFound = r ? r.root_found : false; S.libOwnedKnown = !!(r && r.owned_known);
  /* "out": nobody is signed in to Steam on this console; "in"; null while Steam has not said */
  S.libLogged = r ? r.logged : null; S.libCached = !!(r && r.owned_cached);
  if (S.st) adopt(S.st);
}
/* Artwork: Steam's own cache, or what STONE fetched for games Steam had not shown (host artcache).
   A game with only the store's wide picture shows it at the top of its card, the name under it. */
const capUrl = g => g.art.capsule ? `url("${Bridge.artUrl(g.appid, 'capsule')}")` : g.art.header ? `url("${Bridge.artUrl(g.appid, 'header')}")` : 'none';
const capWide = g => !g.art.capsule && !!g.art.header;
const heroUrl = g => g.art.hero || g.art.capsule || g.art.header ? Bridge.artUrl(g.appid, g.art.hero ? 'hero' : g.art.capsule ? 'capsule' : 'header') : null;
/* The background of the screen: the picture at twice the size when STONE has it (artcache hero2x) */
const bgUrl = g => g.art.hero2x ? Bridge.artUrl(g.appid, 'hero2x') : heroUrl(g);
/* A cover without art: the machine itself in miniature (black gloss, the stone band, the light line); the
   name is never written on a cover, it shows under the row (Home) or at the foot of the grid (Library). */
const nameTag = () => '<span class="ph"></span>';
/* Background blur from a 64×36 copy of the hero: one tiny image scaled up, no live blur filter.
   A small LRU keeps the last ones; game mode empties it. */
const BLUR = new Map(), BLUR_MAX = 24;
function blurOf(g, cb) {
  if (BLUR.has(g.appid)) { const v = BLUR.get(g.appid); BLUR.delete(g.appid); BLUR.set(g.appid, v); return v; }
  const u = heroUrl(g); if (!u) return null;
  const img = new Image(); img.decoding = 'async';
  img.onload = () => {
    try {
      const c = document.createElement('canvas'); c.width = 64; c.height = 36;
      c.getContext('2d').drawImage(img, 0, 0, 64, 36);
      BLUR.set(g.appid, c.toDataURL('image/png'));
      while (BLUR.size > BLUR_MAX) BLUR.delete(BLUR.keys().next().value);
      if (cb) cb();
    } catch (e) { /* artwork that cannot be read stays sharp-only */ }
  };
  img.src = u; return null;
}
function trimArt() { BLUR.clear(); }
