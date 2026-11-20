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
  G = list.map((x, i) => ({ i, appid: x.appid, n: x.name, o: x.kind === 'rom' ? (x.system_name || 'Emulador') : x.kind === 'emulator' ? 'Emulador' : SRC[x.source] || 'Steam',
    src: x.source, kind: x.kind || null, sys: x.system_name || null, added: x.added || 0, min: x.playtime_min,
    h: Math.round(x.playtime_min / 60), lastT: x.last_played, last: ago(x.last_played), sz: sizeText(x.size_bytes),
    inst: x.installed, upd: x.updating, art: Object.assign({ capsule: false, hero: false, header: false, hero2x: false }, x.art), fav: favs.has(x.appid), perf: null }));
  const at = a => { const k = a === null ? -1 : G.findIndex(g => g.appid === a); return k < 0 ? null : k; };
  S.running = at(run); S.launching = at(lau);
  S.detailGone = cur !== null && at(cur) === null;
  if (cur !== null && at(cur) !== null) curG = at(cur);
  recent = homeRow();
  /* nothing installed yet (a new console): the account's games take the first row, ready to install */
  S.libNone = !recent.length;
  if (S.libNone) recent = G.slice(0, 6).map(g => g.i);
  S.libReady = true; S.libFound = r ? r.root_found : false; S.libOwnedKnown = !!(r && r.owned_known);
  /* "out": nobody is signed in to Steam on this console; "in"; null while Steam has not said */
  S.libLogged = r ? r.logged : null; S.libCached = !!(r && r.owned_cached);
  if (S.st) adopt(S.st);
}
/* INICIO's row (3.1.0-rc12): the games, Steam's and the emulators', together, most recently played (or
   arrived, for an emulator game copied and not played yet) first; the emulator apps themselves stay in
   the Library. Up to HOME_N; when the person has emulator games and none made it into the row, the
   latest of them take its last places, so they are always on Inicio with the rest. */
const HOME_N = 8, HOME_ROMS = 2;
function homeRow() {
  const play = G.filter(g => (g.inst || g.src === 'shortcut') && g.kind !== 'emulator');
  const row = play.slice(0, HOME_N);
  const roms = play.filter(g => g.kind === 'rom');
  if (roms.length && !row.some(g => g.kind === 'rom')) {
    const add = roms.slice(0, Math.min(HOME_ROMS, roms.length));
    row.splice(Math.max(1, row.length - add.length), add.length, ...add);
  }
  return row.slice(0, HOME_N).map(g => g.i);
}
/* Artwork: Steam's own cache, or what STONE fetched for games Steam had not shown (host artcache).
   A game with only the store's wide picture shows it at the top of its card, the name under it. */
const capUrl = g => g.art.capsule ? `url("${Bridge.artUrl(g.appid, 'capsule')}")` : g.art.header ? `url("${Bridge.artUrl(g.appid, 'header')}")` : 'none';
const capWide = g => !g.art.capsule && !!g.art.header;
/* An emulator game's box art (tall, no wide picture) in a wide card: the whole box in the middle over
   a dark, enlarged copy of itself, instead of a strip cut out of it (3.1.0-rc12, board 20-11-2026). */
const tallOnly = g => !g.art.hero && !g.art.hero2x && !g.art.header && !!g.art.capsule;
const boxBg = g => { const u = Bridge.artUrl(g.appid, 'capsule');
  return `background-image:url(&quot;${u}&quot;),linear-gradient(rgba(8,9,12,.62),rgba(8,9,12,.62)),url(&quot;${u}&quot;);background-size:contain,cover,cover;background-repeat:no-repeat;background-position:center`; };
const heroUrl = g => g.art.hero || g.art.capsule || g.art.header ? Bridge.artUrl(g.appid, g.art.hero ? 'hero' : g.art.capsule ? 'capsule' : 'header') : null;
/* The background of the screen: the picture at twice the size when STONE has it (artcache hero2x) */
const bgUrl = g => g.art.hero2x ? Bridge.artUrl(g.appid, 'hero2x') : heroUrl(g);
/* A cover without art: the machine itself in miniature (black gloss, the stone band, the light line); the
   name is never written on a cover, it shows under the row (Home) or at the foot of the grid (Library). */
/* A game without artwork wears STONE's own cover (the stone band and the light line) with what it is
   written on it: its console and its name for emulator games ("Juego (PlayStation 2)"), "EMULADOR" for
   the emulators, the origin for the rest. Until 3.1.0-rc6 it was blank (board, 14-11-2026). */
const EMU_NAMES = new Set(['RetroDECK', 'RetroArch', 'Dolphin', 'PCSX2', 'PPSSPP', 'RPCS3', 'Cemu', 'Azahar', 'melonDS', 'mGBA', 'Flycast', 'xemu', 'Eden', 'Ryujinx (Ryubing)']);
const ROM_SYS = ['GameCube', 'Wii', 'PlayStation 2', 'PlayStation Portable', 'PlayStation 3', 'Wii U', 'Nintendo 3DS', 'Nintendo DS', 'Game Boy Advance', 'Dreamcast', 'Xbox', 'Nintendo Switch'];
function coverText(g) {
  if (!g || !g.n) return null;
  if (EMU_NAMES.has(g.n)) return ['EMULADOR', g.n];
  const m = /^(.*) \(([^()]+)\)$/.exec(g.n);
  if (m && ROM_SYS.includes(m[2])) return [m[2].toUpperCase(), m[1]];
  if (m && m[2] === 'Switch 2') return ['SWITCH 2 · PORT', m[1]];
  if (m && m[2] === 'emulador de Switch 2') return ['EMULADOR', m[1]];
  if (g.kind === 'rom' && g.sys) { const sfx = ` (${g.sys})`; return [g.sys.toUpperCase(), g.n.endsWith(sfx) ? g.n.slice(0, -sfx.length) : g.n]; }
  if (g.kind === 'emulator') return ['EMULADOR', g.n];
  return [(g.src === 'shortcut' ? 'ACCESO DIRECTO' : g.o || 'STEAM').toUpperCase(), g.n];
}
const nameTag = g => { const t = coverText(g); return `<span class="ph">${t ? `<span class="pht"><span class="lbl">${esc(t[0])}</span><em>${esc(t[1])}</em></span>` : ''}</span>`; };
/* Background blur: a 240 × 135 copy of the game's picture, cut to the screen's shape and blurred once
   when it is made (no live blur filter). Until 3.1.0-rc12 it was a 64 × 36 copy enlarged 30 times,
   which showed its pixels as soft blocks (board, 20-11-2026: emulator games' backgrounds "pixeleados").
   A small LRU keeps the last ones; game mode empties it. */
const BLUR = new Map(), BLUR_MAX = 24, BLUR_W = 240, BLUR_H = 135;
function blurPaint(img) {
  const c = document.createElement('canvas'); c.width = BLUR_W; c.height = BLUR_H;
  const x = c.getContext('2d'), iw = img.naturalWidth || 1, ih = img.naturalHeight || 1;
  /* the picture covering the canvas (like the screen), a little larger so the blur has no dark edges */
  const k = Math.max(BLUR_W / iw, BLUR_H / ih) * 1.12, w = iw * k, h = ih * k;
  x.imageSmoothingEnabled = true; x.imageSmoothingQuality = 'high';
  if (typeof x.filter === 'string') {
    x.filter = 'blur(9px) saturate(1.15)';
    x.drawImage(img, (BLUR_W - w) / 2, (BLUR_H - h) / 2, w, h);
    return c;
  }
  /* no canvas filter: down to a few pixels, then up again in steps of two (each step smooth) */
  let s = document.createElement('canvas'); s.width = 30; s.height = 17;
  const k2 = Math.max(30 / iw, 17 / ih);
  s.getContext('2d').drawImage(img, (30 - iw * k2) / 2, (17 - ih * k2) / 2, iw * k2, ih * k2);
  while (s.width * 2 < BLUR_W) {
    const n = document.createElement('canvas'); n.width = s.width * 2; n.height = s.height * 2;
    const nx = n.getContext('2d'); nx.imageSmoothingQuality = 'high'; nx.drawImage(s, 0, 0, n.width, n.height); s = n;
  }
  x.drawImage(s, 0, 0, BLUR_W, BLUR_H);
  return c;
}
function blurOf(g, cb) {
  if (BLUR.has(g.appid)) { const v = BLUR.get(g.appid); BLUR.delete(g.appid); BLUR.set(g.appid, v); return v; }
  const u = heroUrl(g); if (!u) return null;
  const img = new Image(); img.decoding = 'async';
  img.onload = () => {
    try {
      BLUR.set(g.appid, blurPaint(img).toDataURL('image/jpeg', .9));
      while (BLUR.size > BLUR_MAX) BLUR.delete(BLUR.keys().next().value);
      if (cb) cb();
    } catch (e) { /* artwork that cannot be read stays sharp-only */ }
  };
  img.src = u; return null;
}
function trimArt() { BLUR.clear(); }
