function bgGame(g, sharp, veil) {
  S.bgFor = { i: g.i, sharp, veil };
  accentFor(g);
  const u = heroUrl(g);
  if (!u) return setBg(neutralBg, veil, true);
  if (sharp) return setBg(`url("${u}")`, veil, true);
  const b = blurOf(g, () => { if (S.bgFor && S.bgFor.i === g.i && !S.bgFor.sharp) setBg(`url(${BLUR.get(g.appid)})`, S.bgFor.veil, true); });
  if (b) return setBg(`url(${b})`, veil, true);
  $('#veil').className = veil;
}

/* CRISTAL: the colour of the game in focus, read from its own art (a 24 × 14 copy, colourful and
   bright pixels counting most) and made vivid enough to glow. It tints the focus, the page's shade
   and the accents. Unknown (no art, unreadable): STONE's amber. */
const ACCENT = new Map(), ACCENT_MAX = 64, ACCENT_DEFAULT = '#f0a23b';
function setAccent(c) { stage.style.setProperty('--accent', c || ACCENT_DEFAULT); }
function vivid(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn;
  let h = 0;
  if (d) h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
  h = Math.round((h * 60 + 360) % 360);
  const l = (mx + mn) / 2, s = d ? d / (1 - Math.abs(2 * l - 1)) : 0;
  if (s < .12) return null;                      /* grey art: no colour to take, keep STONE's own */
  return `hsl(${h}, ${Math.round(Math.max(.62, Math.min(.92, s)) * 100)}%, ${Math.round(Math.max(.56, Math.min(.66, l + .18)) * 100)}%)`;
}
function accentFor(g) {
  if (ACCENT.has(g.appid)) return setAccent(ACCENT.get(g.appid));
  const u = heroUrl(g);
  if (!u) return setAccent(null);
  const img = new Image(); img.decoding = 'async';
  img.onload = () => {
    let c = null;
    try {
      const cv = document.createElement('canvas'); cv.width = 24; cv.height = 14;
      const x = cv.getContext('2d'); x.drawImage(img, 0, 0, 24, 14);
      const d = x.getImageData(0, 0, 24, 14).data;
      let r = 0, gg = 0, b = 0, w = 0;
      for (let i = 0; i < d.length; i += 4) {
        const mx = Math.max(d[i], d[i + 1], d[i + 2]), mn = Math.min(d[i], d[i + 1], d[i + 2]);
        const wt = (mx ? (mx - mn) / mx : 0) ** 2 * (mx / 255) + .01;
        r += d[i] * wt; gg += d[i + 1] * wt; b += d[i + 2] * wt; w += wt;
      }
      c = vivid(r / w, gg / w, b / w);
    } catch (e) { c = null; }           /* artwork that cannot be read keeps the default */
    ACCENT.set(g.appid, c);
    while (ACCENT.size > ACCENT_MAX) ACCENT.delete(ACCENT.keys().next().value);
    if (S.bgFor && S.bgFor.i === g.i) setAccent(c);
  };
  img.src = u;
}
