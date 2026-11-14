/* ---------- STEAM'S OWN ACTIONS: CLOSING A GAME, PAUSING A DOWNLOAD (3.1.0-rc5) ----------
   Until rc4 a game that hung, or had no menu to quit, could not be closed from STONE, and a download
   could not be paused. Both are Steam's own buttons, read from its code (client 1792618285): "Exit game"
   asks "¿Salir del juego?" / "Los datos no guardados podrían perderse." and calls Apps.TerminateApp;
   pause stops Steam's downloads, resume lets this game's go on (host: game.close, downloads.control). */
function closeGameAsk(from) {
  const g = G[S.running]; if (!g) return;
  const back = () => {
    if (from === 'quick') { S.screen = 'game'; return openQuick(); }
    if (from === 'detail' && G[curG]) return enterDetail(curG, { r: 1, c: 0 });
    returnHome();
  };
  if (from === 'quick') closeQuick(true);
  play('notify');
  openDlg(`<span class="st-cap">CERRAR JUEGO</span><h2>${esc(g.n.toUpperCase())}</h2><p>¿Salir del juego? Los datos no guardados podrían perderse.</p>
    <div class="btns"><span class="txt-f" data-f data-b="no">CANCELAR</span><span class="txt-f" data-f data-b="yes">SALIR DEL JUEGO</span></div>`, {
    onA: el => { closeDlg(); if (el.dataset.b !== 'yes') { play('back'); return back(); } play('select'); closeGame(g); },
    onB: () => { closeDlg(); play('back'); back(); } });
}
async function closeGame(g) {
  returnHome();
  toast(`Cerrando ${g.n}…`, false);
  let r = null;
  try { r = await Sys.gameClose(g.appid); } catch (e) { r = null; }
  if (!r || !r.ok) { play('error'); return toast(`Steam no respondió. Puedes salir desde el menú de ${g.n}`, false); }
  /* stoned sees the game end and Home says so (gameEnded); if it is still there after a while, say it */
  setTimeout(() => { if (S.running === g.i) toast(`${g.n} sigue abierto: puede estar guardando. Si no se cierra, sal desde su menú`, false); }, 20000);
}
/* The download of the game on its page: pause it, resume it, or start it now if it waits in the queue. */
function downloadDlg(g) {
  const d = DL.at[g.appid];
  if (!d) { play('error'); return toast(`${g.n} se está preparando en Steam: el avance aparecerá aquí`, false); }
  const paused = d.stage === 'paused', queued = d.stage === 'queued';
  const text = paused ? 'La descarga está en pausa.' : queued ? 'Puedes descargarlo ya: la descarga en curso esperará.'
    : 'Si la pausas, Steam pausa sus descargas hasta que la reanudes.';
  const [label, act] = paused ? ['REANUDAR', 'resume'] : queued ? ['DESCARGAR AHORA', 'resume'] : ['PAUSAR', 'pause'];
  play('select');
  openDlg(`<span class="st-cap">${g.inst ? 'ACTUALIZACIÓN' : 'DESCARGA'}</span><h2>${esc(g.n.toUpperCase())}</h2><p>${esc(dlLine(d) || DL_STAGE[d.stage] || '')}</p><p>${text}</p>
    <div class="btns"><span class="txt-f" data-f data-b="go">${label}</span><span class="txt-f" data-f data-b="no">VOLVER</span></div>`, {
    onA: el => { closeDlg(); if (el.dataset.b === 'go') downloadControl(g, act); else play('back'); enterDetail(curG, { r: 0, c: 0 }); },
    onB: () => { closeDlg(); play('back'); enterDetail(curG, { r: 0, c: 0 }); } });
}
async function downloadControl(g, act) {
  let r = null;
  try { r = await Sys.downloadsControl(g.appid, act); } catch (e) { r = null; }
  if (!r || !r.ok) { play('error'); return toast('Steam no respondió. Inténtalo de nuevo en unos segundos', false); }
  toast(act === 'pause' ? 'Descargas en pausa' : `${g.n}: descargando`, false);
  dlKick(600);
}
