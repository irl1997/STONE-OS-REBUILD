/* ---------- THE NETWORK ICON AT THE TOP RIGHT (3.1.0-rc6) ----------
   Until rc5 it was a fixed drawing of a full Wi-Fi signal, there with or without a network (board,
   14-11-2026: no Wi-Fi, and the icon showed signal). Now it says what NetworkManager says (net.status):
   cable, Wi-Fi with its bars, a network without internet, Wi-Fi off, nothing. Read every 15 s outside
   games and after every network change; losing and getting back internet is said once. */
const NETI = { t: 0, last: null, seen: false };
const NET_SVG = {
  arcs: lit => `<svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke-width="2.2" stroke-linecap="round" aria-hidden="true">
    <path d="M4 11 Q14 3 24 11" opacity="${lit >= 3 ? 1 : .28}"/><path d="M8 15 Q14 10 20 15" opacity="${lit >= 2 ? 1 : .28}"/><path d="M12 19 Q14 17.5 16 19" opacity="${lit >= 1 ? 1 : .28}"/></svg>`,
  cable: '<svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke-width="2" aria-hidden="true"><rect x="7" y="6" width="14" height="12" rx="2"/><path d="M11 18v4M17 18v4M10.5 10h7"/></svg>',
  slash: '<path d="M5 23 L23 5" stroke-width="2.4" stroke-linecap="round"/>'
};
function netState(N) {
  if (!N || N.error) return { k: 'unknown', t: 'Red: sin datos' };
  const cable = N.devices.find(d => d.type === 'ethernet' && d.state === 'connected');
  const wifi = N.devices.find(d => d.type === 'wifi');
  const noNet = N.online && (N.internet === 'limited' || N.internet === 'portal' || N.internet === 'none');
  if (cable) return { k: noNet ? 'cable-warn' : 'cable', t: noNet ? 'Cable conectado, sin internet' : 'Conectado por cable' };
  if (wifi && wifi.state === 'connected') {
    const sig = N.signal == null ? 3 : N.signal >= 67 ? 3 : N.signal >= 34 ? 2 : 1;
    return { k: noNet ? 'wifi-warn' : 'wifi', bars: sig, t: `${N.ssid || 'Wi-Fi'}${N.signal != null ? ` · señal ${N.signal} %` : ''}${noNet ? ' · sin internet' : ''}` };
  }
  if (wifi && (N.radio === false || wifi.state === 'unavailable')) return { k: 'off', t: 'Wi-Fi apagado' };
  return { k: 'none', t: 'Sin conexión' };
}
function netIcon(N) {
  const st = $('#status'); if (!st) return;
  let el = $('#neticon');
  if (!el) {
    el = document.createElement('span'); el.id = 'neticon';
    const old = st.querySelector(':scope > svg');
    if (old) st.replaceChild(el, old); else st.insertBefore(el, st.firstChild);
  }
  const s = netState(N);
  const warn = '<span class="nwarn">!</span>';
  el.className = 'n-' + s.k;
  el.title = s.t; el.setAttribute('aria-label', s.t);
  el.innerHTML = s.k === 'cable' ? NET_SVG.cable : s.k === 'cable-warn' ? NET_SVG.cable + warn
    : s.k === 'wifi' ? NET_SVG.arcs(s.bars) : s.k === 'wifi-warn' ? NET_SVG.arcs(s.bars) + warn
    : s.k === 'unknown' ? NET_SVG.arcs(0) : NET_SVG.arcs(0).replace('</svg>', NET_SVG.slash + '</svg>');
  /* losing internet and getting it back is said, once each (not at start) */
  const up = !!(N && N.online && N.internet !== 'limited' && N.internet !== 'portal' && N.internet !== 'none');
  if (NETI.seen && NETI.last !== null && up !== NETI.last && S.screen !== 'game' && S.screen !== 'off') {
    if (up) toast('Conectado a internet', false);
    else if (!(S.screen === 'settings' && CATS[cat] === 'Red')) { play('notify'); toast(N && N.online ? 'La red no tiene salida a internet' : 'Sin conexión a internet: Ajustes → Red', false); }
  }
  NETI.last = up; NETI.seen = true;
}
/* What needs internet says so first, as SteamOS does, instead of a confusing "Steam no respondió".
   Only a known lack of internet stops it (no reading yet: it goes on). */
function needNet(what) {
  if (NETI.last !== false) return true;
  play('error'); toast(`Sin conexión a internet: ${what} necesita internet. Ajustes → Red`, false); netIconKick(0);
  return false;
}
function netIconKick(ms) {
  clearTimeout(NETI.t);
  NETI.t = setTimeout(netIconTick, ms == null ? 400 : ms);
}
async function netIconTick() {
  NETI.t = 0;
  if (S.screen !== 'game' && S.screen !== 'off' && !S.dormant) {
    const N = await Bridge.call('net.status').catch(e => ({ error: (e && e.message) || 'no disponible' }));
    netIcon(N);
    if (S.screen === 'settings' && CATS[cat] === 'Red' && CX.net && !CX.net.error && N && !N.error
        && JSON.stringify(N) !== JSON.stringify(CX.net)) { CX.net = N; enterSettings({ pane: !!(NAV && NAV.pane), ri: NAV && NAV.pane ? NAV.c : 0 }); }
  }
  NETI.t = setTimeout(netIconTick, 15000);
}
netIconKick(1500);
