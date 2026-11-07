/* Steam's own settings section for each STONE category (opened in Steam's interface). */
const STEAM_SEC = { 'Sistema': 'System', 'Pantalla': 'Display', 'Audio': 'Audio', 'Mandos': 'Controller', 'Red': 'Internet',
  'Bluetooth': 'Bluetooth', 'Almacenamiento': 'Storage', 'Energía': 'Power', 'Actualizaciones': 'System', 'Accesibilidad': 'Accessibility' };
/* How STONE draws inside Game Mode (read at start by /usr/libexec/stone-home). GPU: Chromium,
   at the screen's own resolution (4K on a 4K TV), the same engine as Steam's interface. Sin GPU:
   the WebKit shell drawing in software, the fallback (smooth only at low resolutions). */
const RENDER = ['GPU', 'Sin GPU'];
const RENDER_TXT = ['Chromium con la GPU, a la resolución del televisor. Recomendado',
  'Respaldo sin GPU (WebKit). Úsalo sólo si GPU falla: a 4K va lento'];
/* The resolution STONE is drawn at, in real pixels. */
const drawRes = () => `${Math.round(innerWidth * devicePixelRatio)} × ${Math.round(innerHeight * devicePixelRatio)}`;
/* STONE DISPLAY (stone_display/ through the host; the page never reads Linux). Read when Pantalla
   opens and again when the host says the display changed. */
const resTxt = m => m && m.w ? `${m.w} × ${m.h}${m.hz ? ' · ' + m.hz + ' Hz' : ''}` : 'Desconocida';
function loadDisplay(fresh) {
  S.dispLoading = true;
  Sys.display(!!fresh).then(r => { S.disp = r; }, () => { S.disp = { error: true }; }).then(() => {
    S.dispLoading = false;
    if (S.screen === 'settings' && CATS[cat] === 'Pantalla') enterSettings({ pane: !!NAV.pane, ri: NAV.pane ? NAV.c : 0 });
  });
}
Bridge.on('display', () => { S.disp = null; if (S.screen === 'settings' && CATS[cat] === 'Pantalla') loadDisplay(true); });
/* The link: the best picture the connection (adapter, cable) can carry, from stone_display/link.py. */
function linkRows(D) {
  const L = D.link;
  if (!L || !L.best_fluid) return [];
  const f = m => m ? `${m.w} × ${m.h} · ${m.hz} Hz${m.hz_assumed ? ' (supuesto)' : ''}` : 'ninguna';
  const goalMax = D.goal === 'max_res';
  return [
    { l: 'Conexión', s: L.reaches_4k60 ? 'Lleva 4K a 60 Hz o más' : (L.display_offers_4k60 ? '4K a 60 Hz no cabe en esta conexión' : 'Lo máximo que lleva la conexión'),
      v: f(L.target), act: 'info', where: L.advice || `Fluida: ${f(L.best_fluid)}. Máxima resolución: ${f(L.best_max_res)}. Detalle: stonectl display` },
    { l: 'Meta de imagen', s: goalMax ? 'La resolución más alta, aunque sean menos Hz' : 'La más alta a 60 Hz o más (recomendado para jugar)',
      v: goalMax ? 'Máxima resolución' : 'Fluidez', key: 'dispgoal' }];
}
function setDisplayGoal() {
  const next = S.disp && S.disp.goal === 'max_res' ? 0 : 1;
  play('select');
  toast(next === 1 ? 'STONE buscará la resolución más alta, aunque baje los Hz' : 'STONE buscará la resolución más alta a 60 Hz o más', false);
  Sys.displayGoal(next).catch(() => {}).then(() => { S.disp = null; loadDisplay(true); });
}
function displayRows() {
  const D = S.disp;
  if (!D) { if (!S.dispLoading) loadDisplay(); return [{ l: 'Televisor', s: 'Leyendo la pantalla…', v: '', ro: true }]; }
  if (D.error) return [{ l: 'Televisor', s: 'No se pudo leer la pantalla', v: '', ro: true }];
  if (!D.connected) return [{ l: 'Televisor', s: 'No hay ninguna pantalla conectada', v: '', ro: true }];
  const caps = [D.vrr && D.vrr.supported ? (D.vrr.range ? `VRR ${D.vrr.range.min}–${D.vrr.range.max} Hz` : 'VRR') : null,
    D.hdr && D.hdr.supported ? 'HDR' : null, D.max_hz ? `hasta ${D.max_hz} Hz` : null].filter(Boolean).join(' · ');
  const warn = (D.findings || []).find(f => f.level === 'warn');
  const games = D.game_env ? `${D.game_env.w} × ${D.game_env.h}` : 'Desconocida';
  return [
    { l: 'Televisor', s: `${D.name || 'Pantalla'}${D.connection ? ' · ' + D.connection : ''}${caps ? ' · ' + caps : ''}`, v: resTxt(D.native), act: 'info',
      where: warn ? warn.text : `Nativa ${resTxt(D.native)}. Salida actual ${resTxt(D.output)}. Diagnóstico completo: stonectl display` },
    { l: 'Salida', s: D.output ? (D.native && D.output.w < D.native.w ? 'Por debajo de la nativa del televisor' : 'La que envía la consola al televisor') : 'Steam no respondió todavía',
      v: resTxt(D.output), act: 'info', where: D.native && D.output && D.output.w < D.native.w
        ? 'Botón STEAM → Ajustes → Pantalla → Resolución: elige la nativa del televisor' : 'La resolución de salida la fija Steam (Ajustes → Pantalla)' },
    ...linkRows(D),
    { l: 'Juegos ven', s: D.policy === 'native' ? 'La resolución del televisor; cada juego decide cómo dibujar' : 'Lo que Steam da por defecto',
      v: D.policy === 'native' ? `Televisor · ${games}` : `Steam · ${games}`, key: 'gameres' }];
}
/* Steam's own settings, inside STONE. The list is whatever this Steam offers (stone_home/steamsettings.py):
   true/false ones can be changed with A, the rest are shown. Names are Steam's, split into words. */
function loadSteamSet(refresh) {
  S.ssLoading = true;
  Bridge.call('steam.settings', refresh === true).then(r => { S.ss = r; }, () => { S.ss = { available: false, settings: [], error: 'No se pudo leer Steam' }; }).then(() => {
    S.ssLoading = false;
    if (S.screen === 'settings' && CATS[cat] === 'Steam') enterSettings({ pane: !!NAV.pane, ri: NAV.pane ? NAV.c : 0 });
  });
}
function steamSetRows() {
  const ss = S.ss;
  if (!ss) { if (!S.ssLoading) loadSteamSet(); return [{ l: 'Leyendo…', s: 'Preguntando a Steam qué ajustes ofrece', v: '', ro: true }]; }
  const head = { l: 'Actualizar la lista', s: ss.available ? `${ss.settings.length} ajustes leídos de este Steam` : (ss.error || 'Steam no respondió'), v: 'Actualizar', act: 'sset', refresh: true };
  const rows = (ss.settings || []).slice().sort((a, b) => a.area.localeCompare(b.area) || a.label.localeCompare(b.label)).map(x => ({
    l: x.label, s: x.area, v: x.type === 'bool' ? (x.value ? 'Sí' : 'No') : String(x.value),
    act: x.writable ? 'sset' : 'info', sset: x, where: `${x.area}: ${x.label} = ${x.value}${x.writable ? '' : ' (solo lectura)'}` }));
  return [head, ...rows];
}
function ssetA(r) {
  play('select');
  if (r.refresh) { S.ss = null; return loadSteamSet(true); }
  const x = r.sset;
  Bridge.call('steam.setSetting', x.id, !x.value).then(res => {
    toast(res && res.ok ? `${x.label}: ${!x.value ? 'Sí' : 'No'}` : 'Steam no aceptó el cambio', false);
    S.ss = null; loadSteamSet(true);
  }, () => toast('No se pudo cambiar', false));
}
/* Emulators: fixed catalog in the host (stone_home/emulators.py), installed from Flathub. */
const EMU_STATE = {};
function loadEmulators() {
  S.emuLoading = true;
  Sys.emulators().then(r => { S.emu = r; }, () => { S.emu = []; }).then(() => {
    S.emuLoading = false;
    if (S.screen === 'settings' && CATS[cat] === 'Emuladores') enterSettings({ pane: !!NAV.pane, ri: NAV.pane ? NAV.c : 0 });
  });
}
Bridge.on('emulator', d => {
  EMU_STATE[d.key] = d;
  toast(d.text, false);
  if (d.state === 'done') { loadEmulators(); loadLibrary(); }
  else if (S.screen === 'settings' && CATS[cat] === 'Emuladores') enterSettings({ pane: !!NAV.pane, ri: NAV.pane ? NAV.c : 0 });
});
function emuA(r) {
  const e = r.emu;
  if (e.installed) { play('select'); return toast(`${e.name} está en tu biblioteca, como acceso directo`, false); }
  if (EMU_STATE[e.key] && EMU_STATE[e.key].state === 'installing') { play('error'); return toast(`${e.name} se está instalando`, false); }
  play('select');
  EMU_STATE[e.key] = { state: 'installing', text: `Instalando ${e.name}…` };
  enterSettings({ pane: true, ri: NAV.c });
  return sys('emuInstall', e.key);
}
/* Smoothness, measured on the console: STONE moves through Home by itself for a few seconds and
   records the time between frames (requestAnimationFrame). Logged to home.log for diagnosis. */
function measureSmoothness() {
  if (S.measuring) return;
  S.measuring = true;
  const ri = NAV.c, d = [];
  let last = performance.now(), run = true;
  const tick = t => { d.push(t - last); last = t; if (run) requestAnimationFrame(tick); };
  toast('Midiendo la fluidez: STONE se mueve sola unos segundos', false);
  enterHome({ r: 0, c: 0 });
  requestAnimationFrame(t => { last = t; requestAnimationFrame(tick); });
  const steps = ['right', 'right', 'right', 'left', 'left', 'left', 'right', 'right', 'left', 'left', 'right', 'left'];
  let k = 0;
  const iv = setInterval(() => {
    if (k < steps.length) { act(steps[k++]); return; }
    clearInterval(iv); run = false; S.measuring = false;
    const s = [...d].sort((a, b) => a - b), avg = d.reduce((a, b) => a + b, 0) / Math.max(1, d.length);
    S.smooth = { fps: Math.round(1000 / avg), p99: Math.round(s[Math.floor(s.length * .99)] || 0), slow: d.filter(x => x > 25).length, n: d.length, mode: S.render, res: drawRes() };
    console.info(`[stone] smoothness mode=${RENDER[S.render]} res=${S.smooth.res} fps=${S.smooth.fps} p99=${S.smooth.p99}ms slow=${S.smooth.slow}/${S.smooth.n}`);
    cat = CATS.indexOf('Pantalla'); enterSettings({ pane: true, ri });
    toast(`${RENDER[S.render]}: ${S.smooth.fps} cuadros por segundo de media; el más lento, ${S.smooth.p99} ms`, false);
  }, 450);
}
/* Opens the matching section of Steam's settings over STONE; if Steam cannot be reached, says where it is. */
function openSteamSettings(r) {
  if (!r.sec) return toast(r.where, false);
  return Sys.openSteamSettings(r.sec).then(res => { if (!res || !res.ok) toast(r.where, false); }, () => toast(r.where, false));
}
/* A new drawing mode applies when STONE Home starts: save, say so, restart. */
function applyRender() {
  clearTimeout(saveT);
  toast(`Modo de imagen: ${RENDER[S.render]}. STONE se reinicia…`, false);
  Sys.prefsSet({ sound: S.sound, vol: S.vol, hc: S.hc, rm: S.rm, ts: S.ts, safe: S.safe, idle: S.idle, tech: S.tech,
    adv_ack: S.advAck, engine: S.render, favorites: [...favs] })
    .then(() => setTimeout(() => Sys.restart().catch(() => toast('Se aplica la próxima vez que abras STONE', false)), 900))
    .catch(() => toast('No se pudo guardar el modo de imagen', false));
  enterSettings({ pane: true, ri: NAV.c });
}
/* Bazzite checks for a new image by itself and leaves it ready for the next restart (M01). */
function updTimerText(u) {
  if (!u) return 'No se pudo leer el servicio de actualización automática';
  if (!u.enabled) return 'Desactivada en este sistema';
  const t = s => new Date(s * 1000).toLocaleString('es', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  return `Activa${u.last ? ' · última ' + t(u.last) : ''}${u.next ? ' · próxima ' + t(u.next) : ''}`;
}
/* STONE HEALTH (M19): read when Salud opens; nothing here changes the console. */
function loadHealth() {
  if (S.healthLoading) return;
  S.healthLoading = true;
  Sys.health().then(r => { S.health = r; }, () => { S.health = { error: true }; }).then(() => {
    S.healthLoading = false;
    if (S.screen === 'settings' && CATS[cat] === 'Salud') enterSettings({ pane: !!NAV.pane, ri: NAV.pane ? NAV.c : 0 });
  });
}
const LVL = { ok: 'Bien', warn: 'Aviso', fail: 'Fallo' };
function healthRows() {
  const H = S.health;
  if (!H) { loadHealth(); return [{ l: 'Leyendo…', s: 'CPU, memoria, discos, servicios y registros', v: '' }]; }
  if (H.error) return [{ l: 'No se pudo leer el estado', s: 'Prueba de nuevo o usa stone-doctor en una terminal', v: '' }];
  const st = S.st || {};
  const rows = H.checks.map(([lvl, t, d]) => ({ l: t, s: d, v: LVL[lvl] || lvl, act: 'info', where: d }));
  rows.push({ l: 'Estabilidad', s: st.safe_mode ? `Safe Mode activo (${SAFE_REASON[st.safe_reason] || st.safe_reason})` : st.last_failure ? 'Hubo un fallo reciente: STONE volvió a la última configuración buena' : 'Sin fallos de rendimiento recientes',
    v: st.safe_mode ? 'Aviso' : 'Bien', act: 'info', where: 'Detalle en Ajustes → Rendimiento' });
  rows.push({ l: 'Volver a comprobar', s: 'Lee todo de nuevo', v: '', act: 'health' });
  return rows;
}
function catRows() {
  /* Settings Steam already handles open in Steam's own settings; if that fails, STONE says where. */
  const steam = (t, d, where) => ({ l: t, s: d, v: 'Abrir en Steam', act: 'steam', where, sec: STEAM_SEC[CATS[cat]] });
  const rel = (S.info && S.info.release) || {}, dep = (S.info && S.info.deployments) || null;
  switch (CATS[cat]) {
    case 'Pantalla': return { d: 'Ajusta cómo se ve STONE en tu televisor.', rows: [
      ...displayRows(),
      { l: 'Área segura', s: 'Usa ← → hasta que las cuatro esquinas se vean completas', v: `${S.safe} %`, key: 'safe' },
      steam('Resolución y frecuencia', 'Las fija Steam para todo el sistema', 'Botón STEAM → Ajustes → Pantalla'),
      steam('HDR', 'Según el televisor y el juego', 'Botón STEAM → Ajustes → Pantalla'),
      { l: 'Tamaño del texto', s: 'Se aplica a STONE Home', v: SIZES[S.ts], key: 'ts' },
      { l: 'Modo de imagen', s: RENDER_TXT[S.render], v: RENDER[S.render], key: 'render' },
      { l: 'Resolución de STONE', s: devicePixelRatio > 1.5 || innerWidth * devicePixelRatio >= 3800 ? 'Dibujada a la resolución del televisor'
        : 'Si tu televisor es 4K y aquí no dice 3840 × 2160, mira «Cómo»', v: drawRes(), act: 'info',
        where: 'Steam decide el tamaño de cada app. Botón STEAM → Biblioteca → STONE → ⚙ → Propiedades → General → Resolución del juego: Nativa. Luego reinicia STONE' },
      { l: 'Medir fluidez', s: S.smooth ? `Última medida, ${RENDER[S.smooth.mode]} a ${S.smooth.res}: ${S.smooth.fps} FPS · cuadro más lento ${S.smooth.p99} ms · ${S.smooth.slow} de ${S.smooth.n} cuadros lentos`
        : 'STONE recorre el inicio unos segundos y mide los cuadros por segundo del modo actual', v: 'Medir', act: 'measure' }] };
    case 'Audio': return { d: 'La salida de sonido de la consola y su volumen. Izquierda y derecha cambian el volumen.', rows: [...audioRows(),
      { l: 'Sonidos de STONE', s: 'Botones, encendido y apagado', v: S.sound ? 'Activados' : 'Desactivados', key: 'sound' },
      { l: 'Volumen de la interfaz', s: 'Independiente del volumen de los juegos', v: Math.round(S.vol * 100) + ' %', key: 'vol' }] };
    case 'Red': return { d: 'El cable de red se configura solo. Para Wi-Fi, elige una red y escribe su contraseña con el mando.', rows: netRows() };
    case 'Bluetooth': return { d: 'Mandos, auriculares y teclados. Para emparejar, ponlos en modo emparejamiento y busca.', rows: btRows() };
    case 'Salud': return { d: 'El estado de STONE MACHINE, leído ahora. Nada de esta pantalla cambia la consola.', rows: healthRows() };
    case 'Steam': return { d: 'Los ajustes de Steam, con el aspecto de STONE. La lista sale de lo que ofrece este Steam; los de sí/no se cambian con A.', rows: steamSetRows() };
    case 'Emuladores': {
      if (!S.emu) { if (!S.emuLoading) loadEmulators(); return { d: 'Emuladores de otras consolas, desde Flathub.', rows: [{ l: 'Leyendo…', s: 'Buscando qué emuladores están instalados', v: '', ro: true }] }; }
      return { d: 'Se instalan desde Flathub y aparecen en tu biblioteca como accesos directos. Los juegos y BIOS los pones tú. RetroDECK reúne la mayoría de consolas en una sola app.',
        rows: S.emu.map(e => { const st = EMU_STATE[e.key]; const busy = st && st.state === 'installing';
          return { l: e.name, s: busy ? st.text : e.plays, v: e.installed ? 'Instalado' : busy ? 'Instalando…' : 'Instalar', act: 'emu', emu: e }; }) };
    }
    case 'Rendimiento': return { d: `Perfil activo: ${profOf(S.prof).n}. Elige entre silencio y rendimiento, o ajusta tu propio perfil.`, rows: [
      { l: 'Performance Center', s: 'SILENT, BALANCED, PERFORMANCE y CUSTOM', v: 'Abrir', act: 'perf' },
      { l: 'Modo técnico', s: 'Temperaturas, frecuencia y consumo en el menú de STONE durante el juego', v: S.tech ? 'Activado' : 'Desactivado', key: 'tech' },
      cu40Row(),
      { l: 'Safe Mode', s: S.safeMode ? `Activo: ${SAFE_REASON[S.safeReason] || 'valores de fábrica'}` : 'Sólo valores de fábrica: sin CUSTOM, sin perfiles por juego ni pruebas', v: S.safeMode ? 'Salir' : 'Activar', act: 'safe' }] };
    case 'Energía': return { d: 'STONE MACHINE no tiene modo de reposo. Apagarla cuando no se usa ahorra entre 55 y 105 W.', rows: [
      { l: 'Apagar tras inactividad', s: 'Sólo en STONE Home, nunca con un juego abierto', v: IDLE[S.idle], key: 'idle' }] };
    case 'Accesibilidad': return { d: 'Haz que STONE sea más fácil de leer y más tranquilo.', rows: [
      { l: 'Alto contraste', s: 'Línea de 4 px y texto secundario más claro', v: S.hc ? 'Activado' : 'Desactivado', key: 'hc' },
      { l: 'Reducir movimiento', s: 'Sin escalas ni desplazamientos de fondo', v: S.rm ? 'Activado' : 'Desactivado', key: 'rm' },
      { l: 'Tamaño del texto', s: 'Se aplica a STONE Home', v: SIZES[S.ts], key: 'ts' }] };
    case 'Acerca de': return { d: 'STONE MACHINE · STONE OS', rows: [
      { l: 'Versión', s: rel.STONE_VERSION ? `STONE OS ${rel.STONE_VERSION}${rel.STONE_COMMIT ? ' · ' + rel.STONE_COMMIT.slice(0, 7) : ''}` : 'Leyendo…', v: '' },
      { l: 'Hardware', s: S.caps ? (S.caps.board ? `AMD BC-250 detectada · Zen 2 ${cores()} núcleos · GPU ${cu40Top() ? 40 : 24} CU · 16 GB GDDR6` : 'No se detectó una AMD BC-250: el ajuste de rendimiento está desactivado') : 'Leyendo…', v: '' },
      { l: 'Sistema base', s: rel.STONE_BASE_IMAGE ? `Bazzite · ${rel.STONE_BASE_IMAGE}${rel.STONE_BASE_DIGEST ? ' @ ' + rel.STONE_BASE_DIGEST.slice(7, 19) : ''}` : 'Bazzite (imagen derivada de bazzite-deck)', v: '' },
      { l: 'Componentes', s: [rel.STONE_KERNEL && `kernel ${rel.STONE_KERNEL}`, rel.STONE_MESA && `Mesa ${rel.STONE_MESA}`, rel.STONE_GOVERNOR_VERSION && `regulador ${rel.STONE_GOVERNOR_VERSION}`].filter(Boolean).join(' · ') || '—', v: '' },
      { l: 'Modo escritorio', s: 'Para usuarios avanzados', v: 'En Steam', act: 'info', where: 'Botón STEAM → Energía → Cambiar a escritorio' }] };
    case 'Actualizaciones': return { d: 'Las actualizaciones llegan como una imagen completa y se aplican al reiniciar. Si una falla, la anterior sigue disponible.', rows: [
      { l: 'Estado', s: !dep ? 'No se pudo leer el estado del sistema' : dep.staged ? `Actualización lista: ${dep.staged.version || 'nueva versión'}. Se aplica al reiniciar` : `Instalada: ${(dep.booted && dep.booted.version) || rel.STONE_VERSION || '—'}`, v: '' },
      ...(dep && dep.staged ? [{ l: 'Reiniciar y actualizar', s: 'La consola se reinicia con la versión nueva', v: 'Reiniciar', act: 'reboot' }] : []),
      { l: 'Comprobación automática', s: updTimerText(S.info && S.info.updates), v: '' },
      ...(S.info && S.info.session === 'stone' ? [] : [steam('Buscar actualizaciones', 'Sistema y Steam se actualizan desde Steam', 'Botón STEAM → Ajustes → Sistema → Buscar actualizaciones')]),
      { l: 'Volver a la versión anterior', s: dep && dep.rollback ? `Guardada: ${dep.rollback.version || 'versión anterior'}` : 'No hay una versión anterior guardada todavía', v: 'Cómo', act: 'info', where: 'Reinicia y, en el menú de arranque, elige la segunda entrada. STONE OS arranca con la versión anterior' }] };
    default: return { d: `${CATS[cat]}: lo gestiona Steam.`, rows: [steam(`Abrir ${CATS[cat].toLowerCase()}`, 'Panel nativo de Steam', `Botón STEAM → Ajustes → ${CATS[cat]}`)] };
  }
}

/* CPU cores the system sees (threads / 2: Zen 2 has 2 threads per core). Boards sold
   unlocked report 8; the BC-250's stock firmware 6. */
function cores() { const t = navigator.hardwareConcurrency || 12; return Math.max(1, Math.round(t / 2)); }

/* 40 CU (M04, D-31): switched from here with STONE's own confirmation; stone-cu40 does the work
   through pkexec (polkit allows these three command lines to the console administrator only). The
   kernel uses it from the next boot; the boot guard turns it off by itself after GPU errors. */
function cu40Row() {
  const c = S.caps && S.caps.cu40, L = 'GPU · unidades de cálculo';
  if (!S.caps) return { l: L, s: 'Leyendo…', v: '' };
  if (!c || !c.available) return { l: L, s: 'Esta versión de STONE OS no trae el desbloqueo de 40 CU', v: '24 CU' };
  if (c.active) return { l: L, s: `40 CU en uso · máximo validado de esta consola: ${c.ceiling_mhz} MHz`, v: '40 CU', act: 'cu40' };
  return { l: L, s: '24 CU en uso · 40 CU disponible (la configuración de STONE MACHINE)', v: 'Activar 40 CU', act: 'cu40' };
}
const CU40_WARN = `<p>Es un cambio de la comunidad, no de AMD: no todas las placas lo aguantan. Con 40 CU la GPU consume unos 30 W más y se calienta más.</p>
  <p>STONE empieza con un máximo prudente y la calibración busca después el máximo estable de tu consola. Si aparecen errores de GPU, STONE vuelve sola a 24 CU en el siguiente arranque.</p>`;
function cu40Dlg(ri) {
  const c = S.caps && S.caps.cu40, on = c && c.active;
  const back = () => { closeDlg(); play('back'); enterSettings({ pane: true, ri }); };
  if (on) {
    return openDlg(`<h2>40 CU</h2><p>Las 40 unidades de cálculo están en uso.</p><p>La prueba de 3 minutos comprueba que la GPU calcula bien a plena carga. Apagar 40 CU vuelve a 24 desde el próximo arranque.</p>
      <div class="btns"><span class="txt-f" data-f data-b="test">PROBAR</span><span class="txt-f" data-f data-b="off">APAGAR 40 CU</span><span class="txt-f" data-f data-b="no">VOLVER</span></div>`, {
      onA: el => { if (el.dataset.b === 'no') return back(); play('select'); closeDlg(); cu40Run(el.dataset.b === 'test' ? 'test' : 'disable', ri); }, onB: back });
  }
  openDlg(`<h2>ACTIVAR 40 CU</h2>${CU40_WARN}<p>Se aplica al reiniciar.</p>
    <div class="btns"><span class="txt-f" data-f data-b="yes">ACTIVAR</span><span class="txt-f" data-f data-b="no">CANCELAR</span></div>`, {
    onA: el => { if (el.dataset.b !== 'yes') return back(); play('select'); closeDlg(); cu40Run('enable', ri); }, onB: back });
}
async function cu40Run(op, ri) {
  toast(op === 'test' ? 'Probando la GPU durante 3 minutos…' : 'Cambiando el arranque…', false);
  let r = null;
  try { r = await Sys.cu40(op); } catch (e) { play('error'); toast(e.code === 'PermissionDenied' ? 'Hace falta ser el administrador de la consola' : `No se pudo: ${e.message}`, false); return enterSettings({ pane: true, ri }); }
  if (!r.ok) { play('error'); toast((r.text.split('\n').filter(Boolean).slice(-2).join(' ')) || 'No se pudo', false); return enterSettings({ pane: true, ri }); }
  if (op === 'test') { toast('Prueba aprobada: las 40 CU calcularon bien', false); return enterSettings({ pane: true, ri }); }
  rebootDlg(op === 'enable' ? '40 CU se usará desde el próximo arranque.' : 'La GPU vuelve a 24 CU desde el próximo arranque.', () => enterSettings({ pane: true, ri }));
}
function rebootDlg(msg, later) {
  openDlg(`<h2>REINICIAR</h2><p>${msg}</p><div class="btns"><span class="txt-f" data-f data-b="now">REINICIAR AHORA</span><span class="txt-f" data-f data-b="later">MÁS TARDE</span></div>`, {
    onA: el => { closeDlg(); if (el.dataset.b === 'now') { play('select'); return shutdown(true); } play('back'); later(); }, onB: () => { closeDlg(); later(); } });
}

/* Game resolution environment (Juegos ven): Televisor = every game sees the display's own
   resolution (Steam "Native"); Steam = Steam's default. The host applies it to every game. */
function setGamePolicy() {
  const next = S.disp && S.disp.policy === 'native' ? 1 : 0;
  play('select');
  toast(next === 0 ? 'Los juegos verán la resolución del televisor' : 'Los juegos usarán la resolución que Steam da por defecto', false);
  Sys.displayPolicy(next).then(r => { if (r && !r.ok) toast('Steam no respondió: se aplica al abrir el próximo juego', false); })
    .catch(() => {}).then(() => { S.disp = null; loadDisplay(true); });
}
