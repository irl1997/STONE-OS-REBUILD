function act(a) {
  /* Steam's own window is in front (D-34): the controller is Steam's; only the guide button is STONE's */
  /* Steam's own window is in front (D-34): the controller is Steam's. A press that reaches STONE means
     STONE is the one on screen (Steam still starting, its window not up yet): B or the guide button
     give up waiting, as the curtain says (3.1.0-rc6; before, only the guide button did, unsaid). */
  if (S.steamFront) {
    if ((a === 'home' || a === 'b') && !S.steamFront.full && !S.steamFront.opening) { play('back'); Sys.steamHide().catch(() => sfEnd('closed')); }
    return;
  }
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
  /* A pressed before a screen has its focus (the library still drawing, a slow first frame): nothing
     happens, instead of an error in the screen's handler (seen in the simulation, 3.1.0-rc2). */
  if (a === 'a' && S.screen !== 'dlg' && !focusEl()) return;
