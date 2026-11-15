/* ---------- ACTIVIDAD (3.1.0-rc10) ----------
   The console's owner (15-11-2026): "cuando descargo las actualizaciones no hay nada que me señale que se
   está descargando". Everything STONE (or Steam, for STONE) does in the background now shows in one
   place, on every screen: a turning ring and what is happening, in the status at the top right.

     STONE OS update   uupd running (update.state, its own JSON progress records: module and %)
     Steam downloads   install.js (DL.at), the one moving first
     emulators/ports   installing or updating (EMU_STATE)
     USB copy          emugames.js (EG.copy)
     anything else     busy(key, text) while it lasts: OptiScaler's download, the diagnostic report...

   A row of Ajustes that is working shows the same ring (row.busy). The ring only turns: no text is
   rewritten unless it changed, so nothing flickers. */
const ACT = new Map();
function busy(key, text) {
  if (text) ACT.set(key, text); else ACT.delete(key);
  actPaint();
}
function actItems() {
  const out = [];
  const u = S.upd;
  if (u && u.running) out.push({ t: 'Actualizando STONE OS', p: u.progress && u.progress.overall != null ? u.progress.overall : null });
  const dls = typeof DL !== 'undefined' ? Object.entries(DL.at || {}) : [];
  const dl = dls.find(([, d]) => d.stage !== 'queued' && d.stage !== 'paused');
  if (dl) {
    const g = G.find(x => String(x.appid) === String(dl[0])), d = dl[1];
    out.push({ t: `${DL_STAGE[d.stage] || 'Descargando'}${g ? ' ' + g.n : ''}`, p: d.progress != null ? Math.min(100, Math.floor(d.progress * 100)) : null });
  }
  if (typeof EMU_STATE !== 'undefined') {
    Object.values(EMU_STATE).filter(d => d && ['installing', 'updating'].includes(d.state))
      .forEach(d => out.push({ t: d.state === 'updating' ? 'Actualizando un emulador' : 'Instalando', p: d.pct != null ? Math.round(d.pct) : null }));
  }
  if (typeof EG !== 'undefined' && EG.copy) out.push({ t: 'Copiando juegos del USB', p: EG.copy.total ? Math.floor(EG.copy.done * 100 / EG.copy.total) : null });
  ACT.forEach(t => out.push({ t, p: null }));
  return out;
}
function actPaint() {
  const st = $('#status');
  if (!st) return;
  const it = actItems();
  let chip = $('#actv');
  if (!chip) {
    if (!it.length) return;
    chip = document.createElement('span'); chip.id = 'actv';
    chip.innerHTML = '<i class="spin" aria-hidden="true"></i><span class="lbl"></span>';
    st.insertBefore(chip, $('#clock'));
  }
  chip.hidden = !it.length;
  if (!it.length) return;
  const a = it[0], txt = `${a.t}${a.p != null ? ` · ${a.p} %` : ''}${it.length > 1 ? ` · +${it.length - 1}` : ''}`;
  if (chip.lastChild.textContent !== txt) chip.lastChild.textContent = txt;
}
/* STONE OS's update: looked at every 30 s (every 3 s while uupd works). Bazzite's own timer can start it
   too, so it is followed whoever started it; the end says whether a new version is ready. */
let updT = 0, updWas = false;
async function updWatch() {
  clearTimeout(updT);
  const u = S.dormant ? S.upd : await Bridge.call('update.state').catch(() => null);
  S.upd = u;
  actPaint();
  const running = !!(u && u.running);
  if (S.screen === 'settings' && CATS[cat] === 'Actualizaciones') enterSettings({ pane: !!(NAV && NAV.pane), ri: NAV && NAV.pane ? NAV.c : 0 });
  if (!running && (updWas || (S.updAsked && Date.now() - S.updAsked > 8000))) updEnded(u);   /* a quick "no update" too */
  updWas = running;
  updT = setTimeout(updWatch, running || S.updAsked ? 3000 : 30000);
}
async function updEnded(u) {
  const i = await Sys.info().catch(() => null);
  if (i) S.info = i;
  const dep = i && i.deployments, asked = S.updAsked;
  S.updAsked = 0;
  if (S.screen === 'settings' && CATS[cat] === 'Actualizaciones') enterSettings({ pane: !!(NAV && NAV.pane), ri: NAV && NAV.pane ? NAV.c : 0 });
  if (dep && dep.staged) { play('notify'); longToast(`Actualización lista: ${dep.staged.version || 'versión nueva'}. Ajustes → Actualizaciones → Reiniciar y actualizar`, 9000); }
  else if (u && u.result && u.result !== 'success') { play('error'); toast('La actualización no terminó bien. Revisa la conexión y vuelve a intentarlo', false); }
  else if (asked) toast('Ya tienes la última versión de STONE OS', false);
}
setTimeout(updWatch, 6000);
