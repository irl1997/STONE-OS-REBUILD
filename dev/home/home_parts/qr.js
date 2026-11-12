/* ---------- QR code (byte mode, error correction M, versions 1 to 6: up to 106 bytes) ----------
   Drawn by STONE itself so a phone can open a game's page on Steam's web store: the page never
   loads anything from the internet. ISO/IEC 18004: Reed-Solomon over GF(256) with polynomial 0x11d,
   the 8 masks scored by the standard's penalty rules, format bits with BCH(15,5). tests/test_qr.py
   compares it, module by module, with matrices recorded from the python-qrcode library. */
const QR_M = [null, [1, 16, 10], [1, 28, 16], [1, 44, 26], [2, 32, 18], [2, 43, 24], [4, 27, 16]];   /* blocks, data per block, ec per block */
function qrMatrix(text) {
  const data = [...new TextEncoder().encode(String(text))];
  let ver = 1;
  while (ver <= 6 && data.length > QR_M[ver][0] * QR_M[ver][1] - 2) ver++;
  if (ver > 6) return null;
  const [nb, nd, ne] = QR_M[ver], total = nb * nd, n = 17 + 4 * ver;
  /* data bits: mode 0100, length (8 bits), bytes, terminator, pad bytes 0xEC 0x11 */
  const bits = [];
  const put = (v, len) => { for (let i = len - 1; i >= 0; i--) bits.push((v >> i) & 1); };
  put(4, 4); put(data.length, 8); data.forEach(b => put(b, 8));
  put(0, Math.min(4, total * 8 - bits.length));
  while (bits.length % 8) bits.push(0);
  const cw = [];
  for (let i = 0; i < bits.length; i += 8) cw.push(bits.slice(i, i + 8).reduce((a, b) => a * 2 + b, 0));
  for (let k = 0; cw.length < total; k++) cw.push(k % 2 ? 0x11 : 0xEC);
  /* Reed-Solomon */
  const EXP = [], LOG = [];
  for (let i = 0, x = 1; i < 255; i++) { EXP[i] = x; LOG[x] = i; x <<= 1; if (x & 256) x ^= 0x11d; }
  const mul = (a, b) => a && b ? EXP[(LOG[a] + LOG[b]) % 255] : 0;
  let gen = [1];
  for (let i = 0; i < ne; i++) { const nx = Array(gen.length + 1).fill(0); gen.forEach((c, k) => { nx[k] ^= c; nx[k + 1] ^= mul(c, EXP[i]); }); gen = nx; }
  const blocks = [], ecs = [];
  for (let b = 0; b < nb; b++) {
    const blk = cw.slice(b * nd, b * nd + nd), rem = blk.concat(Array(ne).fill(0));
    for (let i = 0; i < nd; i++) { const f = rem[i]; if (f) gen.forEach((c, k) => { rem[i + k] ^= mul(c, f); }); }
    blocks.push(blk); ecs.push(rem.slice(nd));
  }
  const stream = [];
  for (let i = 0; i < nd; i++) blocks.forEach(b => stream.push(b[i]));
  for (let i = 0; i < ne; i++) ecs.forEach(e => stream.push(e[i]));
  /* function patterns */
  const M = Array.from({ length: n }, () => Array(n).fill(null));
  const set = (r, c, v) => { if (r >= 0 && r < n && c >= 0 && c < n) M[r][c] = v; };
  const finder = (r0, c0) => { for (let r = -1; r <= 7; r++) for (let c = -1; c <= 7; c++) set(r0 + r, c0 + c, r >= 0 && r <= 6 && c >= 0 && c <= 6 && (r === 0 || r === 6 || c === 0 || c === 6 || (r >= 2 && r <= 4 && c >= 2 && c <= 4))); };
  finder(0, 0); finder(0, n - 7); finder(n - 7, 0);
  if (ver > 1) { const p = n - 7; for (let r = -2; r <= 2; r++) for (let c = -2; c <= 2; c++) M[p + r][p + c] = Math.max(Math.abs(r), Math.abs(c)) !== 1; }
  for (let i = 8; i < n - 8; i++) { if (M[6][i] === null) M[6][i] = i % 2 === 0; if (M[i][6] === null) M[i][6] = i % 2 === 0; }
  M[n - 8][8] = true;                                                   /* the dark module */
  const fmt = [];                                                        /* format cells (bit 0 first), reserved now, written per mask */
  for (let i = 0; i <= 5; i++) fmt.push([[i, 8], [8, n - 1 - i]]);
  fmt.push([[7, 8], [8, n - 7]], [[8, 8], [8, n - 8]], [[n - 7, 8], [8, 7]]);
  for (let i = 9; i <= 14; i++) fmt.push([[n - 15 + i, 8], [8, 14 - i]]);
  fmt.forEach(pair => pair.forEach(([r, c]) => { M[r][c] = false; }));
  /* data, zigzag from the bottom right */
  const isData = M.map(row => row.map(v => v === null));
  let bi = 0;
  for (let right = n - 1, up = true; right >= 1; right -= 2, up = !up) {
    if (right === 6) right = 5;
    for (let k = 0; k < n; k++) {
      const r = up ? n - 1 - k : k;
      for (const c of [right, right - 1]) {
        if (!isData[r][c]) continue;
        const byte = stream[bi >> 3];
        M[r][c] = byte !== undefined && ((byte >> (7 - (bi & 7))) & 1) === 1;
        bi++;
      }
    }
  }
  const MASKS = [(r, c) => (r + c) % 2 === 0, r => r % 2 === 0, (r, c) => c % 3 === 0, (r, c) => (r + c) % 3 === 0,
    (r, c) => (Math.floor(r / 2) + Math.floor(c / 3)) % 2 === 0, (r, c) => (r * c) % 2 + (r * c) % 3 === 0,
    (r, c) => ((r * c) % 2 + (r * c) % 3) % 2 === 0, (r, c) => ((r + c) % 2 + (r * c) % 3) % 2 === 0];
  const build = m => {
    const Q = M.map((row, r) => row.map((v, c) => isData[r][c] ? v !== MASKS[m](r, c) : v));
    let d = (0 << 3) | m, rem = d;                                        /* level M = 00 */
    for (let i = 0; i < 10; i++) rem = (rem << 1) ^ ((rem >> 9) * 0x537);
    const f = ((d << 10) | rem) ^ 0x5412;
    fmt.forEach((pair, i) => pair.forEach(([r, c]) => { Q[r][c] = ((f >> i) & 1) === 1; }));
    return Q;
  };
  const penalty = Q => {
    let p = 0;
    const runs = line => { let run = 1; for (let i = 1; i <= n; i++) { if (i < n && line[i] === line[i - 1]) run++; else { if (run >= 5) p += run - 2; run = 1; } } };
    const cols = Q[0].map((_, c) => Q.map(row => row[c]));
    Q.forEach(runs); cols.forEach(runs);
    for (let r = 0; r < n - 1; r++) for (let c = 0; c < n - 1; c++) if (Q[r][c] === Q[r][c + 1] && Q[r][c] === Q[r + 1][c] && Q[r][c] === Q[r + 1][c + 1]) p += 3;
    const pat = line => { for (let i = 0; i + 11 <= n; i++) { const s = line.slice(i, i + 11).map(v => v ? 1 : 0).join(''); if (s === '10111010000' || s === '00001011101') p += 40; } };
    Q.forEach(pat); cols.forEach(pat);
    const dark = Q.reduce((a, row) => a + row.filter(Boolean).length, 0);
    p += Math.floor(Math.abs(dark * 100 / (n * n) - 50) / 5) * 10;
    return p;
  };
  let best = null, bp = Infinity, bm = 0;
  for (let m = 0; m < 8; m++) { const Q = build(m), p = penalty(Q); if (p < bp) { bp = p; best = Q; bm = m; } }
  best.version = ver; best.mask = bm;
  return best;
}
/* The code as one SVG path on a light plate with the quiet zone the standard asks for (4 modules). */
function qrSvg(text, px) {
  const Q = qrMatrix(text);
  if (!Q) return '';
  const n = Q.length, s = n + 8;
  let d = '';
  Q.forEach((row, r) => row.forEach((v, c) => { if (v) d += `M${c + 4} ${r + 4}h1v1h-1z`; }));
  return `<svg class="qr" width="${px}" height="${px}" viewBox="0 0 ${s} ${s}" shape-rendering="crispEdges" role="img" aria-label="Código QR"><rect width="${s}" height="${s}" fill="#ede9e3"/><path d="${d}" fill="#0a0a0b"/></svg>`;
}
