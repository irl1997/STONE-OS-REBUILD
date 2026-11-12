/* ---------- STONE OS simulation: the host side, played in the page ----------
   Replaces Bridge (transport to stone_home/host.py) so the real interface runs with no console.
   Same method names, arguments and answer shapes as host.py. EVERYTHING here is simulated:
   the library, the display, Steam's settings, the downloads. There are no measurements and no
   frame rates: the numbers shown are the ones the rules in stone_display/link.py would give
   for each connection, nothing else. Built into the simulation page by development/build_simulation.py. */
const SimPanel = { adapter: 'passive' };      /* the connection: passive DP→HDMI (≈300 MHz) or active DP 1.4→HDMI 2.0 */
const Bridge = (() => {
  const listeners = {};
  const emit = (ev, d) => (listeners[ev] || []).forEach(f => { try { f(d); } catch (e) { console.error(e); } });
  window.__stoneEvent = emit;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const ok = v => JSON.parse(JSON.stringify(v));
  const bad = (code, msg) => { throw new PerfError(code, msg); };

  /* ---- preferences ---- */
  /* ?ts=2: text at 1.5× · ?hc: high contrast (to look at the accessibility settings) · ?lite: glass without blur */
  let prefs = { sound: true, vol: 0.7, hc: /[?&]hc/.test(location.search), rm: false, ts: Math.max(0, Math.min(2, +(new URLSearchParams(location.search).get('ts') || 0))), safe: 5, idle: 2, tech: false, adv_ack: false, favorites: ['1091500'],
    engine: 0, game_res: 0, display_goal: 'fluid', optimized: 1, wanted: [], report: true, glass: /[?&]lite/.test(location.search) ? 0 : 1 };

  /* ---- library (simulated; Steam's art is not available here, STONE paints its own covers) ---- */
  const DAY = 86400, now = Date.now() / 1000;
  const GAMES = [
    { appid: '1091500', name: 'Cyberpunk 2077', source: 'steam', installed: true, last: now - 3600 * 5, min: 5400, size: 71e9, kind: 'upscaler' },
    { appid: '1245620', name: 'ELDEN RING', source: 'steam', installed: true, last: now - DAY * 2, min: 7800, size: 49e9, kind: 'anticheat' },
    { appid: '1551360', name: 'Forza Horizon 5', source: 'steam', installed: true, last: now - DAY * 4, min: 1900, size: 110e9, kind: 'upscaler' },
    { appid: '1145350', name: 'Hades II', source: 'steam', installed: true, last: now - DAY * 6, min: 2200, size: 12e9, kind: 'plain' },
    { appid: '1174180', name: 'Red Dead Redemption 2', source: 'steam', installed: true, last: now - DAY * 12, min: 3600, size: 119e9, kind: 'upscaler' },
    { appid: '413150', name: 'Stardew Valley', source: 'steam', installed: true, last: now - DAY * 20, min: 6100, size: 0.6e9, kind: 'plain' },
    { appid: '730', name: 'Counter-Strike 2', source: 'steam', installed: true, last: now - DAY * 30, min: 900, size: 33e9, kind: 'online' },
    { appid: '367520', name: 'Hollow Knight', source: 'steam', installed: true, last: now - DAY * 45, min: 1500, size: 2.1e9, kind: 'plain' },
    { appid: '2668430', name: 'The Legend of Heroes: Trails through Daybreak II · Deluxe Edition', source: 'steam', installed: true, last: now - DAY * 1, min: 1500, size: 2.1e9, kind: 'plain' },
    { appid: '1086940', name: "Baldur's Gate 3", source: 'steam', installed: false, last: 0, min: 0, size: 150e9, kind: 'upscaler' },
    { appid: '620', name: 'Portal 2', source: 'steam', installed: false, last: now - DAY * 200, min: 600, size: 12e9, kind: 'plain' }
  ];
  const gameOf = appid => GAMES.find(g => g.appid === appid) || bad('InvalidValue', 'unknown game');
  const SIM = { t0: Date.now(), signed: !/nosteam/.test(location.search), fresh: /fresh/.test(location.search), art: false, front: null };
  if (SIM.fresh) GAMES.forEach(g => { g.hidden = g.installed; });        /* a new console: nothing installed yet */
  if (/noart/.test(location.search)) setTimeout(() => { SIM.art = true; const art = {}; GAMES.filter(g => !g.installed).forEach(g => { art[g.appid] = { capsule: !g.wide, hero: !g.wide, header: !!g.wide }; }); emit('art', { art }); }, 4000);
  if (/late/.test(location.search)) setTimeout(() => emit('library', { reason: 'changed' }), 6200);
  /* The store (simulated: invented prices in one currency, as Steam's public store gives them) */
  const STORE_ALL = [
    { appid: '3527290', name: 'PEAK', price: '2.604 CLP', was: '4.200 CLP', discount: 38, by: 'Team PEAK', genres: ['Acción', 'Aventura', 'Indie'], about: 'PEAK es un juego cooperativo de escalada en el que un solo error puede ser fatal. En solitario o en grupo, la única esperanza de salir de la isla es subir hasta la cima.' },
    { appid: '266410', name: 'iRacing', price: '2.645 CLP', was: '6.613 CLP', discount: 60 },
    { appid: '2358720', name: 'Black Myth: Wukong', price: '49.990 CLP' },
    { appid: '1091500', name: 'Cyberpunk 2077', price: '13.790 CLP', was: '34.490 CLP', discount: 60 },
    { appid: '2807960', name: 'Battlefield 6', price: '54.990 CLP' },
    { appid: '570', name: 'Dota 2', free: true },
    { appid: '1172470', name: 'Apex Legends', free: true },
    { appid: '3240220', name: 'Grand Theft Auto V Enhanced', price: '20.390 CLP' },
    { appid: '1086940', name: "Baldur's Gate 3", price: '42.000 CLP' },
    { appid: '2246340', name: 'Monster Hunter Wilds', price: '31.990 CLP', was: '39.990 CLP', discount: 20 },
    { appid: '1903340', name: 'Clair Obscur: Expedition 33 · Edición con un nombre realmente largo para ver cómo se corta', price: '33.500 CLP' },
    { appid: '4000001', name: 'Lo que viene', soon: true },
    { appid: '4000002', name: 'Otro estreno', soon: true },
    { appid: '2001120', name: 'Split Fiction', price: '36.990 CLP' },
    { appid: '2767030', name: 'Marvel Rivals', free: true }
  ];
  const STORE_SECTIONS = [['specials', 'Ofertas', ['3527290', '266410', '1091500', '2246340']],
    ['top_sellers', 'Lo más vendido', ['2358720', '2807960', '570', '3240220', '1086940', '1903340', '2001120', '1172470', '2767030']],
    ['new_releases', 'Novedades', ['2001120', '2767030']], ['coming_soon', 'Próximamente', ['4000001', '4000002']]];
  const storeItem = appid => STORE_ALL.find(i => i.appid === appid) || null;
  const storeRow = it => ({ appid: it.appid, name: it.name, free: !!it.free, price: it.free || it.soon ? null : it.price, was: it.was || null, discount: it.discount || 0, soon: !!it.soon,
    have: null, art: !/noart/.test(location.search) || SIM.art });
  function addOwned(appid) {
    const it = storeItem(appid); if (!it) return null;
    let g = GAMES.find(x => x.appid === appid);
    if (!g) { g = { appid, name: it.name, source: 'steam', installed: false, last: 0, min: 0, size: 20e9, kind: 'plain', fromStore: true, wide: /wide/.test(location.search) }; GAMES.push(g); }
    return g;
  }
  SimPanel.buy = appid => { addOwned(appid); emit('library', { reason: 'changed' }); };
  /* Steam's own window, as a stand-in over the whole page (in the console it is a real window in front) */
  function steamWindow(on, what, appid) {
    let w = document.getElementById('simsteam');
    if (!w) { w = document.createElement('div'); w.id = 'simsteam'; w.style.cssText = 'position:fixed;inset:0;z-index:99990;background:#1b2838;color:#c7d5e0;display:none;flex-direction:column;align-items:center;justify-content:center;gap:18px;font:18px/1.5 system-ui,sans-serif;text-align:center';
      document.body.appendChild(w); }
    w.style.display = on ? 'flex' : 'none';
    if (!on) return;
    const it = appid && storeItem(appid);
    w.innerHTML = `<b style="font-size:30px;letter-spacing:.1em">VENTANA DE STEAM (simulada)</b><span>${what === 'login' ? 'Inicio de sesión de Steam: código QR o usuario y contraseña' : it ? 'Tienda de Steam · ' + it.name : 'Tienda de Steam'}</span>
      <span style="display:flex;gap:10px">${what === 'login' ? '<button data-k="sign">Iniciar sesión</button>' : it ? '<button data-k="buy">Comprar</button>' : ''}<button data-k="close">Botón guía: volver a STONE</button></span>`;
    w.querySelectorAll('button').forEach(bn => { bn.style.cssText = 'font:inherit;padding:8px 14px;background:#2a475e;color:#fff;border:0;border-radius:4px;cursor:pointer';
      bn.onclick = () => { const k = bn.dataset.k;
        if (k === 'sign') { SIM.signed = true; return endFront('signed'); }
        if (k === 'buy') { setTimeout(() => SimPanel.buy(appid), 2500); return endFront('closed'); }
        endFront('closed'); }; });
  }
  function endFront(why) { const fr = SIM.front; SIM.front = null; steamWindow(false); if (fr) emit('steam', { front: false, why, what: fr.what }); }
  SimPanel.endFront = endFront; SimPanel.sim = SIM;
  /* Emulators (simulated): versions and which ones have a newer one on Flathub */
  const EMUS = [['retrodeck', 'RetroDECK', 'Todo en uno: la mayoría de consolas clásicas en una sola app, pensada para mando', '0.9.1', '0.9.4'], ['retroarch', 'RetroArch', 'Consolas clásicas con núcleos de libretro'],
    ['dolphin', 'Dolphin', 'GameCube y Wii', '2509', null], ['pcsx2', 'PCSX2', 'PlayStation 2'], ['ppsspp', 'PPSSPP', 'PlayStation Portable'], ['rpcs3', 'RPCS3', 'PlayStation 3'], ['cemu', 'Cemu', 'Wii U'],
    ['azahar', 'Azahar', 'Nintendo 3DS'], ['melonds', 'melonDS', 'Nintendo DS'], ['mgba', 'mGBA', 'Game Boy Advance'], ['flycast', 'Flycast', 'Dreamcast'], ['xemu', 'xemu', 'Xbox original'],
    ['eden', 'Eden', 'Nintendo Switch', '0.2.0', '0.2.1'], ['ryujinx', 'Ryujinx (Ryubing)', 'Nintendo Switch']]
    .map(([key, name, plays, version, newer]) => ({ key, name, plays, installed: !!version, version: version || null, newer: newer || null }))
    .concat([{ key: 'switch2', name: 'Nintendo Switch 2', plays: 'Nintendo Switch 2', installed: false, version: null,
      not_yet: 'Todavía no hay un emulador de Switch 2 que se pueda instalar en esta consola. Los proyectos que existen son experimentales: no están publicados en Flathub y arrancan muy pocos juegos. Cuando haya uno publicado, llegará a esta lista con una actualización de STONE OS.' }]);

  /* ---- display: what stone_display/link.py concludes for each adapter ---- */
  const hzTxt = m => m;
  function displayStatus() {
    const passive = SimPanel.adapter === 'passive', max = prefs.display_goal === 'max_res';
    const f60 = passive ? { w: 2560, h: 1440, hz: 60 } : { w: 3840, h: 2160, hz: 60 };
    const mres = passive ? { w: 3840, h: 2160, hz: 30 } : { w: 3840, h: 2160, hz: 60 };
    const target = max ? mres : f60;
    return {
      connected: true, name: 'TV 4K (simulado)', connection: 'HDMI', connector: 'HDMI-A-1', native: { w: 3840, h: 2160, hz: 60 },
      output: target, preferred: { w: 3840, h: 2160, hz: 60 }, max_hz: 60, rates: [24, 30, 50, 60],
      vrr: { supported: false, range: null, active: false }, hdr: { supported: true, active: false },
      game_env: prefs.game_res === 1 ? { w: 1280, h: 800 } : { w: target.w, h: target.h }, steam_default: { w: 1280, h: 800 },
      policy: prefs.game_res === 1 ? 'steam' : 'native', safe: { w: 1920, h: 1080, hz: 60 }, steam: true, steam_error: null,
      findings: passive ? [{ level: 'warn', code: 'LINK_LIMITS_MODES', text: 'El adaptador DisplayPort→HDMI no lleva 4K a 60 Hz: STONE usa 2560 × 1440 a 60 Hz (o 4K a 30 Hz si eliges máxima resolución). Con un adaptador activo DP 1.4 → HDMI 2.0 (4K 60 Hz) llegaría a 4K a 60 Hz.' }] : [],
      link: { best_fluid: f60, best_max_res: mres, target, reaches_4k60: !passive, display_offers_4k60: true, limited_by_link: passive,
        unreachable: [], goal: max ? 'max_res' : 'fluid',
        advice: passive ? 'Esta conexión (≈300 MHz de reloj de píxel) no alcanza 4K a 60 Hz. Para 4K a 60 Hz: un adaptador activo DisplayPort 1.4 → HDMI 2.0 («4K 60 Hz»). Simulación del cálculo de STONE DISPLAY.'
          : 'La conexión lleva 4K a 60 Hz. Para 120 Hz el televisor tendría que ofrecer ese modo.' },
      goal: max ? 'max_res' : 'fluid'
    };
  }

  /* ---- Steam's own settings, as the discovery layer would list them for one Steam (names split into words) ---- */
  const SS_ES = { 'Enable Hdr': 'Activar HDR', 'Use Native Resolution': 'Usar la resolución nativa', 'Screen Brightness': 'Brillo de pantalla', 'Game Volume': 'Volumen de los juegos',
    'Mute On Minimize': 'Silenciar al minimizar', 'Enable Xbox Support': 'Soporte para mandos Xbox', 'Enable Playstation Support': 'Soporte para mandos PlayStation', 'Haptics Enabled': 'Vibración háptica',
    'Enable Wifi Power Save': 'Ahorro de energía del Wi-Fi', 'Allow Downloads During Gameplay': 'Descargar mientras se juega', 'Download Region': 'Región de descarga', 'Show Fps Counter': 'Mostrar contador de FPS',
    'Enable Animations': 'Animaciones', 'Enable Steam Play': 'Activar Steam Play', 'Enable Developer Mode': 'Modo desarrollador', 'Show Toast Notifications': 'Mostrar avisos emergentes' };
  const SS_AREA = { Display: 'Pantalla', Audio: 'Audio', Controller: 'Mandos', Network: 'Red', Downloads: 'Descargas', Interface: 'Interfaz', Compatibility: 'Compatibilidad', System: 'Sistema', Notifications: 'Notificaciones' };
  const STEAMSET = [
    { id: 'Settings.Display.EnableHdr', label: 'Enable Hdr', area: 'Display', value: false, writable: true },
    { id: 'Settings.Display.UseNativeResolution', label: 'Use Native Resolution', area: 'Display', value: true, writable: true },
    { id: 'Settings.Display.ScreenBrightness', label: 'Screen Brightness', area: 'Display', value: 0.8, writable: false },
    { id: 'Settings.Audio.GameVolume', label: 'Game Volume', area: 'Audio', value: 0.7, writable: false },
    { id: 'Settings.Audio.MuteOnMinimize', label: 'Mute On Minimize', area: 'Audio', value: false, writable: true },
    { id: 'Settings.Controller.EnableXboxSupport', label: 'Enable Xbox Support', area: 'Controller', value: true, writable: true },
    { id: 'Settings.Controller.EnablePlaystationSupport', label: 'Enable Playstation Support', area: 'Controller', value: true, writable: true },
    { id: 'Settings.Controller.HapticsEnabled', label: 'Haptics Enabled', area: 'Controller', value: true, writable: true },
    { id: 'Settings.Network.EnableWifiPowerSave', label: 'Enable Wifi Power Save', area: 'Network', value: false, writable: true },
    { id: 'Settings.Downloads.AllowDownloadsDuringGameplay', label: 'Allow Downloads During Gameplay', area: 'Downloads', value: false, writable: true },
    { id: 'Settings.Downloads.DownloadRegion', label: 'Download Region', area: 'Downloads', value: 'Chile', writable: false },
    { id: 'Settings.Interface.ShowFpsCounter', label: 'Show Fps Counter', area: 'Interface', value: false, writable: true },
    { id: 'Settings.Interface.EnableAnimations', label: 'Enable Animations', area: 'Interface', value: true, writable: true },
    { id: 'Settings.Compatibility.EnableSteamPlay', label: 'Enable Steam Play', area: 'Compatibility', value: true, writable: true },
    { id: 'Settings.System.EnableDeveloperMode', label: 'Enable Developer Mode', area: 'System', value: false, writable: true },
    { id: 'Settings.Notifications.ShowToastNotifications', label: 'Show Toast Notifications', area: 'Notifications', value: true, writable: true }
  ].map(x => Object.assign({}, x, { label_en: x.label, label: SS_ES[x.label] || x.label, area: SS_AREA[x.area] || x.area })).map(x => Object.assign({ type: typeof x.value === 'boolean' ? 'bool' : typeof x.value === 'number' ? 'number' : 'text' }, x));

  /* ---- image enhancement: components, per-game choices, install, optimization ---- */
  const comps = { helixsr: null, optiscaler: null };            /* what STONE has downloaded */
  const gs = {};                                                /* per game: { mode, path, preset, opti (installed by STONE), helix, done } */
  const st = appid => gs[appid] || (gs[appid] = { mode: 'recommended', path: null, preset: null, opti: false, helix: false, done: 0 });
  const LABEL = { native: 'Sin mejora (nativo)', game_upscaler: 'FSR del juego', gamescope: 'FSR de pantalla (Gamescope)', helixsr: 'HelixSR', optiscaler: 'OptiScaler' };
  const PRESETS = ['quality', 'balanced', 'performance', 'ultra_performance'];
  const PRESET_ES = { quality: 'Calidad', balanced: 'Equilibrado', performance: 'Rendimiento', ultra_performance: 'Ultra rendimiento' };
  const protectedGame = g => g.kind === 'anticheat' || g.kind === 'online';
  function avail(g) {
    const s = st(g.appid), prot = protectedGame(g);
    const a = { native: { available: true }, gamescope: { available: true, guidance_only: true, reason: 'Solo orientación: se activa desde Steam' } };
    a.game_upscaler = g.kind === 'upscaler' ? { available: true } : { available: false, reason: 'este juego no trae FSR propio' };
    if (prot) { a.helixsr = a.optiscaler = { available: false, reason: g.kind === 'online' ? 'solo en línea: STONE no inyecta nada' : 'tiene anti-cheat: STONE no inyecta nada' }; }
    else {
      a.optiscaler = s.opti ? { available: true } : { available: false, reason: 'not installed' };
      a.helixsr = s.helix ? { available: true } : { available: false, reason: 'not installed' };
    }
    return a;
  }
  const recPath = g => g.kind === 'upscaler' ? 'game_upscaler' : 'native';
  const cur = g => { const s = st(g.appid); return { path: s.mode === 'custom' ? s.path : recPath(g), preset: s.mode === 'custom' ? s.preset : (g.kind === 'upscaler' ? 'quality' : null) }; };
  const summary = g => {
    const c = cur(g), d = displayStatus(), t = d.link.target;
    const how = c.path === 'native' ? 'Nativo' : `${LABEL[c.path]} · ${PRESET_ES[c.preset] || 'Calidad'}`;
    return `${how} · salida ${t.w} × ${t.h} a ${t.hz} Hz`;
  };
  const MATRIX = g => g.kind === 'upscaler' ? 9 : g.kind === 'plain' ? 4 : 3;

  const M = {
    /* ?nosteam: nobody signed in · ?fresh: an account with nothing installed · ?late: Steam answers about the
       account 6 s after the start · ?noart: the games not installed get their covers 4 s later */
    library: () => {
      if (!SIM.signed) return { root_found: true, owned_known: true, owned_cached: false, logged: 'out', account: false, games: [] };
      const live = !(/late/.test(location.search)) || Date.now() - SIM.t0 > 6000;
      const list = GAMES.filter(g => (live || g.installed) && !g.hidden);
      return { root_found: true, owned_known: live, owned_cached: false, logged: live ? 'in' : null, account: true,
        games: list.slice().sort((x, y) => y.installed - x.installed || y.last - x.last).map(g => ({
          appid: g.appid, name: g.name, source: g.source, installed: g.installed, updating: !!g.updating, playtime_min: g.min, last_played: g.last,
          size_bytes: g.size, art: g.installed || SIM.art || !/noart/.test(location.search) ? { capsule: !g.wide, hero: !g.wide, header: !!g.wide } : { capsule: false, hero: false, header: false },
          launch: g.installed ? 'steam://rungameid/' + g.appid : null })) };
    },
    launch: async ([appid]) => { gameOf(appid); if (/ask/.test(location.search)) SimPanel.ask = Date.now() + 3000; if (/slow/.test(location.search)) { SimPanel.running = appid; setTimeout(() => SimStoned.sim.steamLaunch(appid), 12000); return { ok: true }; } SimStoned.sim.steamLaunch(appid); SimPanel.running = appid; SimPanel.refresh && SimPanel.refresh(); return { ok: true }; },
    /* installing: the game shows "instalándose", then installed; the host says "library" each time */
    install: async ([appid]) => {
      let g = GAMES.find(x => x.appid === appid);
      if (!g) { const it = storeItem(appid); if (!it || !it.free) bad('InvalidValue', 'unknown game'); g = addOwned(appid); }
      g.updating = true; emit('library', { reason: 'changed' });
      setTimeout(() => { g.updating = false; g.installed = true; g.last = Date.now() / 1000; emit('library', { reason: 'changed' }); }, 9000);
      return { ok: true, via: 'steam-ui' };
    },
    openSteam: async () => ({ ok: true }), openSteamSettings: async () => ({ ok: true }), restart: async () => ({ ok: true }),
    power: async ([a]) => { toast(`Simulación: «${a === 'off' ? 'Apagar' : 'Reiniciar'}» no hace nada aquí`, false); return { ok: true }; },
    systemInfo: () => ({ session: 'stone', release: { STONE_VERSION: '3.0.0-rc1 (simulación)', STONE_BASE_IMAGE: 'bazzite-deck', STONE_KERNEL: 'simulado', STONE_MESA: 'simulado', STONE_GOVERNOR_VERSION: 'simulado' },
      boot_time: Math.round(now - 3600), deployments: { booted: { image: 'simulación', version: '0.1.0-rc23', timestamp: now }, staged: null, rollback: null } }),
    'prefs.get': () => prefs,
    'health.status': async () => { await wait(300); return { snapshot: {}, checks: [
      ['ok', 'CPU', '16 hilos en línea · AMD BC-250 (simulado)'], ['ok', 'Memoria', '14.6 GB'],
      ['ok', 'Disco /', '412 GB libres de 476 GB'], ['ok', 'Servicio de rendimiento (stoned)', 'en marcha'],
      ['ok', 'Regulador de GPU', 'en marcha'], ['ok', 'Guardia de arranque', 'en espera'], ['ok', 'Caja negra', 'en espera'],
      ['ok', 'GPU', 'Sin errores en este arranque'], ['ok', 'Caja negra', 'Los arranques anteriores terminaron bien']] }; },
    'boot.mark': () => null, 'boot.history': () => [],
    'game.look': () => ({ available: true, reason: null, chosen: null, looks: ['NATURAL', 'CLARITY', 'CINEMA', 'VIVID', 'RETRO'].map(l => ({ key: l.toLowerCase(), label: l, description: 'Aspecto ' + l })) }),
    'game.setLook': () => ({ ok: true }),
    'game.frameGen': () => ({ available: false, reason: 'Solo con FSR (OptiScaler) instalado por STONE en este juego', on: false, experimental: true }), 'game.setFrameGen': ([, on]) => ({ ok: true, on }),
    'audio.status': () => ({ outputs: [{ id: 51, name: 'HDMI · Televisor', default: true }, { id: 52, name: 'Auriculares USB', default: false }], volume: 0.6, muted: false }),
    'audio.volume': () => ({ ok: true }), 'audio.default': () => ({ ok: true }),
    'net.status': () => ({ devices: [{ device: 'enp1s0', type: 'ethernet', state: 'connected', connection: 'Cable' }, { device: 'wlan0', type: 'wifi', state: 'disconnected', connection: null }], online: true }),
    'net.wifiList': async () => { await wait(600); return { networks: [{ ssid: 'Casa', signal: 82, secure: true, active: false }, { ssid: 'Invitados', signal: 54, secure: false, active: false }] }; },
    'net.wifiConnect': async () => { await wait(800); return { ok: true }; }, 'net.wifiDisconnect': () => ({ ok: true }),
    'bt.devices': () => ({ devices: [{ mac: 'AA:BB:CC:DD:EE:01', name: 'Mando inalámbrico', icon: 'input-gaming', paired: true, connected: true, battery: 80 }] }),
    'bt.scan': async () => { await wait(1500); return { devices: [{ mac: 'AA:BB:CC:DD:EE:01', name: 'Mando inalámbrico', icon: 'input-gaming', paired: true, connected: true, battery: 80 }, { mac: 'AA:BB:CC:DD:EE:02', name: 'Auriculares', icon: 'audio-headset', paired: false, connected: false, battery: null }] }; },
    'bt.action': async () => { await wait(800); return { ok: true }; },
    'storage.status': async () => { await wait(400); return { libraries: [{ path: '/var/home/stone/.local/share/Steam', free: 412 * 2 ** 30, total: 476 * 2 ** 30, low: false }],
      downloads: [{ appid: '1091500', name: 'Cyberpunk 2077', downloaded: 3.2 * 2 ** 30, total: 12 * 2 ** 30, progress: 0.27, installed: true }],
      games: [{ appid: '1091500', name: 'Cyberpunk 2077', size: 71 * 2 ** 30, shader_cache: 1.4 * 2 ** 30, prefix: 0.3 * 2 ** 30 }], alerts: [] }; },
    'store.search': async ([q]) => { await wait(700); if (/offline/.test(location.search)) bad('Unsupported', 'La tienda de Steam no responde (URLError): ¿hay conexión a internet?');
      const w = q.toLowerCase(); return { results: STORE_ALL.filter(i => i.name.toLowerCase().includes(w)).concat(STORE_ALL.filter(i => !i.name.toLowerCase().includes(w)).slice(0, 2)).slice(0, 8).map(storeRow) }; },
    'store.featured': async () => { await wait(600); if (/offline/.test(location.search)) bad('Unsupported', 'La tienda de Steam no responde (URLError): ¿hay conexión a internet?');
      return { sections: STORE_SECTIONS.map(([key, title, ids]) => ({ key, title, items: ids.map(id => storeRow(storeItem(id))) })) }; },
    'store.details': async ([appid]) => { await wait(500); const it = storeItem(appid); if (!it) bad('Unsupported', 'Steam no tiene ficha de tienda para este juego en tu región.');
      setTimeout(() => emit('art', { art: { [appid]: { capsule: false, hero: true, header: true } } }), 1200);
      return Object.assign(storeRow(it), { about: it.about || 'Descripción simulada del juego, como la da la tienda de Steam: un párrafo corto que cuenta de qué trata y que nunca ocupa más de tres líneas en la ficha de STONE.',
        genres: it.genres || ['Acción', 'Aventura'], release: it.soon ? 'Próximamente' : '16 JUN 2025', by: [it.by || 'Estudio de ejemplo'], kind: 'game', url: 'https://store.steampowered.com/app/' + appid }); },
    'art.want': () => ({ queued: 0 }),
    'session.info': () => ({ session: 'stone' }),
    /* Steam's own window in front (D-34), played with a stand-in window. ?nowindow: Steam shows nothing.
       SimPanel.buy(appid): the purchase arrives in the account (as after paying in Steam or on the phone). */
    'steam.show': async ([what, appid]) => {
      SIM.front = { what, appid };
      if (/nowindow/.test(location.search)) { setTimeout(() => { SIM.front = null; emit('steam', { front: false, why: 'nowindow', what }); }, 2500); return { managed: true }; }
      /* ?slowsteam: Steam is still starting (a new console): STONE waits for it */
      const slow = /slowsteam/.test(location.search) ? 6000 : 0;
      if (slow) setTimeout(() => { if (SIM.front) emit('steam', { front: true, waiting: true, what }); }, 300);
      setTimeout(() => { if (!SIM.front) return; steamWindow(true, what, appid); emit('steam', { front: true, shown: true, what }); }, 1800 + slow);
      return { managed: true };
    },
    'steam.hide': () => { if (!SIM.front) return { managed: false }; endFront('closed'); return { managed: true }; },
    'steam.full': async ([why]) => { setTimeout(() => { toast('Simulación: aquí Steam ocuparía la pantalla y STONE volvería después', false); emit('steam', { front: false, why: 'closed', what: why }); }, 2500); return { ok: true }; },
    'steam.status': () => ({ session: 'stone', interface: true, account: SIM.signed, logged: SIM.signed ? 'in' : 'out', owned_known: true, owned_cached: false, front: !!SIM.front, root_found: true }),
    'roms.scan': async () => { await wait(300); return { base: '/var/home/stone/Emulation', systems: [{ key: 'ps2', name: 'PlayStation 2', emulator: 'PCSX2', emulator_key: 'pcsx2', installed: true, games: [{ name: 'Juego de ejemplo', path: '/x.iso' }] }] }; },
    'roms.folders': () => ({ base: '/var/home/stone/Emulation' }), 'roms.add': async () => { await wait(500); return { found: 1, new: 1, added: 1, queued: 0 }; },
    'storage.clearShaderCache': () => ({ ok: true, freed: 1.4 * 2 ** 30 }), 'storage.uninstall': () => ({ ok: true }),
    'game.experience': () => ({ confidence: { level: 'medium', text: 'Medido en esta consola', detail: '2 mediciones limpias' }, last: { avg_fps: 58.4, low1_fps: 41.2, stutters_per_min: 0.6, verdict: 'fluido', gpu_temp_max: 74, config: 'x' }, regression: [], autopilot: { quality: 'a', balanced: 'b', fluid: 'c' } }),
    'firstrun.status': () => ({ done: !/first/.test(location.search), steam_account: SIM.signed }),   /* ?first, ?first&nosteam */ 'firstrun.complete': () => ({ done: true }),
    'prefs.set': ([p]) => (prefs = Object.assign({}, prefs, p)),
    /* Steam asking: ?ask shows one cloud-save question a few seconds after a game starts */
    'steam.dialog': () => ({ dialog: SimPanel.ask && SimPanel.running && Date.now() > SimPanel.ask ? { title: 'Conflicto de la nube de Steam', text: 'Los archivos guardados en este equipo no coinciden con los de la nube de Steam. ¿Cuáles quieres conservar?', buttons: ['Usar los de la nube', 'Usar los de este equipo', 'Jugar sin sincronizar'] } : null }),
    'steam.dialogAnswer': () => { SimPanel.ask = 0; return { ok: true, result: 'ok' }; },
    'media.screenshots': () => ({ shots: /noshots/.test(location.search) ? [] : GAMES.slice(0, 7).map((g, i) => ({ appid: g.appid, time: Math.round(now - i * 86400 * 1.7), kind: 'shot' + i })) }),
    emulators: () => EMUS.map(e => Object.assign({ busy: false }, e)),
    emuInstall: async ([key]) => { setTimeout(() => { const e = EMUS.find(x => x.key === key); e.installed = true; e.version = '1.0'; emit('emulator', { key, state: 'done', text: `Simulación: ${e.name} instalado` }); }, 1800); return { ok: true }; },
    emuCheck: async () => { await wait(900); if (/offline/.test(location.search)) bad('Unsupported', 'No se pudo consultar Flathub: Could not resolve host'); return { keys: EMUS.filter(e => e.installed && e.newer).map(e => e.key), checked: true }; },
    emuUpdate: async ([key]) => {
      const list = key === 'all' ? EMUS.filter(e => e.installed) : EMUS.filter(e => e.key === key);
      list.forEach((e, i) => setTimeout(() => {
        emit('emulator', { key: e.key, state: 'updating', text: `Actualizando ${e.name} desde Flathub…` });
        setTimeout(() => { const was = e.newer; if (was) { e.version = e.newer; e.newer = null; } emit('emulator', { key: e.key, state: 'done', text: was ? `${e.name} actualizado a la versión ${e.version}` : `${e.name} ya está al día (versión ${e.version})` }); }, 1500);
      }, i * 1800));
      if (key === 'all') setTimeout(() => emit('emulator', { key: 'all', state: 'done', updated: list.length, of: list.length }), list.length * 1800 + 1700);
      return { ok: true };
    },

    'display.status': () => displayStatus(),
    'display.gamePolicy': ([p]) => { prefs.game_res = p; return { ok: true, changed: 10, error: null }; },
    'display.goal': ([g]) => { prefs.display_goal = g ? 'max_res' : 'fluid'; return { ok: true, goal: prefs.display_goal, error: null }; },

    'steam.settings': async ([refresh]) => { await wait(refresh ? 500 : 250); return { available: true, settings: ok(STEAMSET), count: STEAMSET.length, error: null }; },
    'steam.setSetting': async ([id, v]) => { const x = STEAMSET.find(s => s.id === id); if (!x || !x.writable) bad('InvalidValue', 'unknown, read-only or not a true/false setting'); await wait(200); x.value = v; return { ok: true, id, value: v }; },

    'game.status': () => ({ active: !!SimPanel.running }),
    'game.recommended': ([appid]) => {
      const g = gameOf(appid), s = st(appid);
      const meas = s.done > 0;
      return { mode: s.mode, label: s.mode === 'custom' ? 'TU CONFIGURACIÓN' : 'STONE RECOMMENDED', summary: summary(g),
        why: 'Simulación: reglas de STONE para este juego y esta conexión', settings: summary(g),
        status: s.mode === 'custom' ? 'USER_MODIFIED' : meas ? 'AUTO_GENERATED' : 'RECOMMENDED',
        status_text: s.mode === 'custom' ? 'Tu configuración' : meas ? 'Medido en esta consola' : 'Recomendado por STONE',
        target: displayStatus().link.target, output: displayStatus().output, internal: null, trail: [], stale: false };
    },
    'game.modes': ([appid]) => ({ chosen: st(appid).mode, modes: ['recommended', 'custom'] }),
    'game.profile': ([appid]) => ({ id: appid, appid, name: gameOf(appid).name, status: 'RECOMMENDED', availability: avail(gameOf(appid)) }),
    'game.apply': async ([appid, mode]) => { st(appid).mode = mode; return { ok: true }; },
    'game.image': ([appid]) => {
      const g = gameOf(appid), s = st(appid), a = avail(g), c = cur(g), out = [{ key: 'auto', label: 'STONE decide', available: true, reason: null, selected: s.mode !== 'custom' }];
      for (const key of ['native', 'game_upscaler', 'gamescope', 'helixsr', 'optiscaler']) {
        const x = a[key];
        if ((key === 'helixsr' || key === 'optiscaler') && !x.available && /not installed/.test(x.reason || '')) continue;
        out.push({ key, label: LABEL[key], available: !!x.available, reason: x.reason || null, guidance_only: !!x.guidance_only, selected: s.mode === 'custom' && c.path === key });
      }
      return { mode: s.mode, path: c.path, preset: c.preset, choices: out, by_stone: s.opti, presets: PRESETS };
    },
    'game.setImage': async ([appid, key, preset]) => {
      const g = gameOf(appid), s = st(appid);
      if (key === 'auto') { s.mode = 'recommended'; s.path = s.preset = null; return { ok: true }; }
      const a = avail(g)[key]; if (!a || !a.available) bad('InvalidValue', `${key}: ${(a && a.reason) || 'no disponible'}`);
      s.mode = 'custom'; s.path = key; s.preset = key === 'native' ? null : (preset || s.preset || 'quality'); return { ok: true };
    },
    components: async ([kind]) => {
      if (!kind) return { helixsr: comps.helixsr, optiscaler: comps.optiscaler };
      await wait(1600); comps[kind] = { tag: 'versión simulada', verified: 'sha256 simulado' }; return { ok: true, kind, tag: comps[kind].tag };
    },
    'game.installPlan': async ([appid, kind]) => {
      const g = gameOf(appid);
      if (protectedGame(g)) return { ok: false, error: g.kind === 'online' ? 'Este juego es solo en línea: STONE no instala nada dentro' : 'Este juego tiene anti-cheat: STONE no instala nada dentro' };
      if (!comps[kind]) return { ok: false, needs_download: true, error: 'primero hay que descargar el componente' };
      return { ok: true, needs_download: false, tag: comps[kind].tag, component: { tag: comps[kind].tag }, folder: `…/steamapps/common/${g.name}/`, files: kind === 'optiscaler' ? 14 : 6 };
    },
    'game.install': async ([appid]) => { await wait(900); st(appid).opti = true; return { ok: true }; },
    'game.uninstallImage': async ([appid]) => { const s = st(appid); s.opti = false; if (s.path === 'optiscaler') { s.mode = 'recommended'; s.path = s.preset = null; } return { ok: true }; },
    'game.optimizeStatus': ([appid]) => {
      const g = gameOf(appid), s = st(appid), total = MATRIX(g), done = Math.min(s.done, total);
      const names = ['Nativo', 'FSR del juego · Calidad', 'FSR del juego · Equilibrado', 'FSR del juego · Rendimiento', 'OptiScaler · Calidad', 'HelixSR · Calidad', 'FSR de pantalla', 'Calidad ultra rendimiento', 'Nativo con tope de FPS'];
      return { done, total, next: done < total ? names[done % names.length] : null, benchmark: g.kind === 'upscaler' ? 'Ajustes → Gráficos → Benchmark' : null, stale: false,
        recommended: summary(g), status: done ? 'AUTO_GENERATED' : 'RECOMMENDED', measured: done };
    },
    'game.optimizeStart': async ([appid]) => {
      const g = gameOf(appid), s = st(appid); s.done += 1; SimStoned.sim.steamLaunch(appid); SimPanel.running = appid; SimPanel.refresh && SimPanel.refresh();
      return { ok: true, settings: summary(g), summary: summary(g) };
    },
    'game.restoreRecommended': async ([appid]) => { const s = st(appid); s.mode = 'recommended'; s.path = s.preset = null; return { ok: true }; }
  };

  /* covers: generated here (Steam's own artwork is not available in the simulation): a landscape in
     the game's own colours (sky, sun, three ridges, haze), like the key art Steam gives each game.
     The capsule and the store picture carry the name; the hero (the wide background) does not. */
  const artCache = {};
  function artOf(appid, kind) {
    if (/^shot\d+$/.test(kind)) { const g = GAMES[+kind.slice(4) % GAMES.length]; return artOf(g.appid, 'hero'); }
    const k = appid + kind; if (artCache[k]) return artCache[k];
    const g = GAMES.find(x => x.appid === appid) || storeItem(appid);
    const W = { hero: 1920, header: 460, capsule: 300 }[kind] || 300, H = { hero: 620, header: 215, capsule: 450 }[kind] || 450;
    let seed = 7; for (const ch of appid) seed = (seed * 31 + ch.charCodeAt(0)) % 100003;
    const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
    const hue = Math.floor(rnd() * 360), hue2 = (hue + 30 + Math.floor(rnd() * 80)) % 360;
    const c = document.createElement('canvas'); c.width = W; c.height = H; const x = c.getContext('2d');
    const sky = x.createLinearGradient(0, 0, 0, H);
    sky.addColorStop(0, `hsl(${hue2},70%,${28 + rnd() * 12}%)`); sky.addColorStop(.55, `hsl(${hue},78%,${52 + rnd() * 10}%)`); sky.addColorStop(1, `hsl(${(hue + 20) % 360},85%,${68 + rnd() * 8}%)`);
    x.fillStyle = sky; x.fillRect(0, 0, W, H);
    const sx = W * (.25 + rnd() * .5), sy = H * (.38 + rnd() * .14), sr = Math.min(W, H) * (.12 + rnd() * .08);
    const glow = x.createRadialGradient(sx, sy, 0, sx, sy, sr * 4);
    glow.addColorStop(0, `hsla(${(hue + 40) % 360},100%,85%,.9)`); glow.addColorStop(.25, `hsla(${(hue + 30) % 360},100%,70%,.45)`); glow.addColorStop(1, 'hsla(0,0%,100%,0)');
    x.fillStyle = glow; x.fillRect(0, 0, W, H);
    x.fillStyle = `hsla(${(hue + 45) % 360},100%,92%,.95)`; x.beginPath(); x.arc(sx, sy, sr, 0, 7); x.fill();
    for (let layer = 0; layer < 3; layer++) {
      const base = H * (.58 + layer * .13), amp = H * (.16 - layer * .035);
      x.fillStyle = `hsl(${(hue2 + layer * 12) % 360},${55 - layer * 8}%,${30 - layer * 9}%)`;
      x.beginPath(); x.moveTo(0, H);
      for (let px = 0; px <= W; px += W / 24) x.lineTo(px, base - amp * (.5 + .5 * Math.sin(px / W * (3 + layer * 2) + rnd() * 2)) * (.6 + rnd() * .4));
      x.lineTo(W, H); x.closePath(); x.fill();
    }
    const haze = x.createLinearGradient(0, H * .5, 0, H); haze.addColorStop(0, 'hsla(0,0%,100%,0)'); haze.addColorStop(1, `hsla(${hue},60%,12%,.55)`);
    x.fillStyle = haze; x.fillRect(0, H * .5, W, H * .5);
    if (kind !== 'hero') {
      const words = (g ? g.name : appid).split(' '), lines = []; let line = '';
      x.font = `800 ${Math.round(H * (kind === 'header' ? .15 : .085))}px Inter, Helvetica, sans-serif`;
      for (const wd of words) { const tt = line ? line + ' ' + wd : wd; if (x.measureText(tt).width > W * .84 && line) { lines.push(line); line = wd; } else line = tt; }
      lines.push(line);
      const n = Math.min(lines.length, 4), lh = H * (kind === 'header' ? .16 : .095), y0 = kind === 'header' ? H * .5 - (n - 1) * lh / 2 : H * .11;
      x.textAlign = 'center'; x.textBaseline = 'middle'; x.shadowColor = 'rgba(0,0,0,.45)'; x.shadowBlur = H * .03;
      x.fillStyle = '#fff'; lines.slice(0, 4).forEach((l, i) => x.fillText(l.toUpperCase(), W / 2, y0 + i * lh));
    }
    return (artCache[k] = c.toDataURL('image/jpeg', .86));
  }
  async function call(method, ...args) {
    if (method.startsWith('perf.')) {
      const f = SimStoned[method.slice(5)];
      if (!f) throw new PerfError('Unsupported', method);
      return f(...args);
    }
    const f = M[method];
    if (!f) throw new PerfError('InvalidValue', 'método desconocido: ' + method);
    return f(args);
  }
  return { call, on: (ev, f) => { SimStoned.on(ev, f); (listeners[ev] = listeners[ev] || []).push(f); }, artUrl: (appid, kind) => artOf(appid, kind) };
})();
const PerfAPI = SimStoned;
window.SimPanel = SimPanel; window.SimStoned = SimStoned;
