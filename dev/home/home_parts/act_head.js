function act(a) {
  /* Steam's own window is in front (D-30): the controller is Steam's; only the guide button is STONE's */
  if (S.steamFront) { if (a === 'home' && !S.steamFront.full) Sys.steamHide().catch(() => {}); return; }
  if (S.screen === 'transition') return;
  if (S.screen === 'store') { showHints(); return storeInput(a); }
  if (S.screen === 'spage') { showHints(); return storePageInput(a); }
  if (S.screen === 'game') {
    if (a === 'home' || a === 'menu') return openQuick();
    if (a === 'a') { play('select'); return resumeGame(); }
    if (a === 'b') { play('back'); return returnHome(); }
    return;
  }
  showHints();
