/* ---------- COVERS of the sections (Biblioteca, Tienda, Explorar, Capturas…) ----------
   Steam has no art for these, so they wear the STONE MACHINE itself: its faceted stone band across the top,
   lit from above, the section's sign in the white of its top panel, and the white light line of its front
   under the band; the label sits below, on the black body. Signs in a 100×100 box: f filled, s thick
   strokes (both in white; w their width), l the lines cut into them, d the cut points (pips, buttons). */
const COVERS = {
  library: { f: 'M14 18h18v66H14zM36 18h18v66H36zM60.5 21.5l15.6-3.4 13.4 61.7-15.6 3.4z', l: 'M18 30h10M40 30h10' },
  store: { f: 'M12 38h76l-7 48H19z', s: 'M35 46V32a15 15 0 0 1 30 0v14', w: 5.5, d: [[35, 47], [65, 47]] },
  search: { s: 'M42 19a23 23 0 1 0 .01 0zM60 60l22 22' },
  surprise: { f: 'M50 12l34 19v38L50 88 16 69V31z', l: 'M16 31l34 19 34-19M50 50v38',
    d: [[50, 31], [26, 50], [40, 70], [59, 73], [67, 59.5], [75, 46]] },
  downloads: { f: 'M40 12h20v34h17L50 72 23 46h17zM14 80h72v7H14z' },
  emu: { f: 'M30 30h40c13 0 22 11 22 27 0 13-7 22-15 20-5-1-8-6-12-11H35c-4 5-7 10-12 11-8 2-15-7-15-20 0-16 9-27 22-27z',
    l: 'M27 47v14M20 54h14', d: [[69, 47], [77, 54], [69, 61], [61, 54]] },
  shots: { s: 'M14 32V14h18M68 14h18v18M86 68v18H68M32 86H14V68', f: 'M50 36a14 14 0 1 0 .01 0z' },
  login: { f: 'M50 16a16 16 0 1 0 .01 0zM18 88c0-20 14-33 32-33s32 13 32 33z' }
};
const COVER_OF = { library: 'library', store: 'store', search: 'search', surprise: 'surprise', downloads: 'downloads', emu: 'emu', noshots: 'shots', login: 'login' };
const coverMask = {};
function cover(act) {
  const k = COVER_OF[act], c = k && COVERS[k];
  if (!c) return '';
  if (!coverMask[k]) {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">${c.f ? `<path d="${c.f}"/>` : ''}` +
      `${c.s ? `<path d="${c.s}" fill="none" stroke="#000" stroke-width="${c.w || 10}" stroke-linecap="round" stroke-linejoin="round"/>` : ''}</svg>`;
    coverMask[k] = `url('data:image/svg+xml,${encodeURIComponent(svg)}')`;
  }
  const cut = (c.l ? `<path d="${c.l}"/>` : '') + (c.d || []).map(([x, y]) => `<circle cx="${x}" cy="${y}" r="3.6"/>`).join('');
  return `<i class="cov" aria-hidden="true"><i class="band"></i><i class="cg"><i class="panel" style="--m:${coverMask[k]}"></i>` +
    `${cut ? `<svg class="cut" viewBox="0 0 100 100">${cut}</svg>` : ''}</i><i class="ln"></i></i>`;
}
