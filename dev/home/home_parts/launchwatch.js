/* ---------- STARTING A GAME, FOLLOWED STEP BY STEP (3.1.0-rc4) ----------
   Steam starts a game in steps and some wait for the person: a launch option, a licence agreement,
   saves in the cloud that do not match, an install script that failed, another session playing. In the
   STONE session those questions opened in Steam's hidden windows and the game waited for ever (board,
   13-11-2026: Batman: Arkham City on "SIGUE CARGANDO"). The host follows Steam's steps
   (launch.state); the loading screen says them and STONE asks the questions itself (launch.answer). */
const LW = { t: 0, g: null, asked: '', last: null };
const LW_STEP = {
  UpdatingAppInfo: 'COMPROBANDO LA CONFIGURACIÓN', ConnectingToSteam: 'CONECTANDO CON STEAM', SynchronizingCloud: 'SINCRONIZANDO CON LA NUBE',
  SynchronizingControllerConfig: 'SINCRONIZANDO EL MANDO', DownloadingDepots: 'DESCARGANDO CONTENIDO', DownloadingWorkshop: 'DESCARGANDO CONTENIDO',
  UpdatingDRM: 'ACTUALIZANDO EL EJECUTABLE', GettingLegacyKey: 'ACTUALIZANDO LA CLAVE', RunningInstallScript: 'INSTALANDO COMPONENTES',
  VerifyingFiles: 'VERIFICANDO ARCHIVOS', ProcessingShaderCache: 'PREPARANDO SOMBREADORES', CreatingProcess: 'ABRIENDO EL JUEGO',
  WaitingGameWindow: 'ABRIENDO EL JUEGO', DelayLaunch: 'ESPERANDO A STEAM', Completed: 'ABRIENDO EL JUEGO' };
const LW_NOTE = { RunningInstallScript: 'La primera vez, Steam instala lo que el juego necesita (DirectX, Visual C++…).',
  ProcessingShaderCache: 'La primera vez el juego prepara sus sombreadores: puede tardar unos minutos.',
  SynchronizingCloud: 'Steam trae tus partidas guardadas de la nube.' };
/* Steam's own reasons (Steam_AppUpdateError_N, its Spanish texts) */
const LW_ERR = { 2: 'la actualización está en pausa', 3: 'la actualización se canceló', 5: 'no tienes licencia para este juego', 6: 'no hay conexión a internet',
  7: 'se agotó el tiempo de conexión', 9: 'la configuración del juego no está disponible', 10: 'hubo un error al leer el disco', 11: 'hubo un error al escribir en el disco',
  12: 'no hay espacio suficiente en el disco', 13: 'hay archivos del juego dañados', 16: 'el juego ya se está ejecutando', 17: 'falta contenido compartido',
  18: 'el juego no está instalado', 19: 'el juego necesita actualizarse', 20: 'Steam está ocupado', 21: 'los servidores de contenido no responden',
  25: 'el juego aún no se ha lanzado', 26: 'no está disponible en tu región', 28: 'falta el ejecutable del juego', 29: 'el juego no es para esta plataforma',
  32: 'las descargas están desactivadas', 35: 'se está jugando desde otra sesión', 36: 'la descarga está dañada', 42: 'faltan archivos descargados',
  46: 'no se pudo crear el proceso del juego', 47: 'el cliente de Steam está desactualizado', 50: 'faltan archivos instalados',
  51: 'falló la herramienta de compatibilidad (Proton)', 57: 'Steam bloqueó los argumentos de inicio' };
function lwStart(g, first) {
  clearTimeout(LW.t); LW.g = g.appid; LW.asked = ''; LW.last = null;
  if (first) lwApply(g, first);
  LW.t = setTimeout(() => lwTick(g), 2500);
}
async function lwTick(g) {
  LW.t = 0;
  if (S.launching !== g.i || LW.g !== g.appid) return;
  if (S.screen !== 'dlg') {
    const r = await Bridge.call('launch.state', g.appid).catch(() => null);
    if (r && r.state && S.launching === g.i) lwApply(g, r.state);
  }
  if (S.launching === g.i) LW.t = setTimeout(() => lwTick(g), 2500);
}
function lwApply(g, st) {
  LW.last = st;
  const gm = $('#game'), last = (st.trace || []).filter(t => !/^(ask|answer|error):/.test(t)).pop();
  if (gm && gm.querySelector('.ld-step') && last && LW_STEP[last] && !DL.at[g.appid]) {
    ldT.forEach(clearTimeout); ldT = [];
    const [n, t] = st.progress || [0, 0];
    gm.querySelector('.ld-step').textContent = LW_STEP[last] + (t > 0 && n <= t ? ` · ${Math.floor(n * 100 / t)} %` : '');
    gm.querySelector('.ld-note').textContent = LW_NOTE[last] || 'B vuelve al inicio; el juego seguirá abriéndose.';
    if (last !== LW.step) { LW.step = last; clearTimeout(launchT); launchT = setTimeout(() => launchStalled(g), 90000); }
  }
  if (st.error) return lwError(g, st);
  if (st.request && st.request + st.action !== LW.asked) { LW.asked = st.request + st.action; lwAsk(g, st); }
}
const lwTech = st => st && st.trace && st.trace.length ? `Detalle técnico: Steam ${st.trace.join(' › ')}${st.details ? ' · ' + st.details : ''}` : '';
function lwAnswer(g, a) {
  play('select');
  Bridge.call('launch.answer', g.appid, a).then(r => { if (!r || !r.ok) toast('Steam ya no lo pregunta', false); }, () => toast('No se pudo responder a Steam', false));
  if (a === 'cancel') { S.launching = null; S.running = null; clearTimeout(launchT); loadingOff(); returnHome(); }
  else { S.screen = 'game'; NAV = null; line.classList.add('off'); $('#hints').classList.add('hide'); }
}
/* Steam's launch options come as its own localisation keys ("#Steam_LaunchOption_Game"). The console
   (19-11-2026) showed the key itself on a button that did not fit in the dialog. Steam's Spanish texts
   for them (steamui/localization/steamui_spanish-json.js, client 1794536281); %1$s is the game. */
const STEAM_LO = { Game: 'Jugar a «%1$s»', Application: 'Iniciar %1$s', SafeMode: 'Iniciar %1$s en modo seguro',
  Multiplayer: 'Iniciar %1$s en modo multijugador', VR: 'Iniciar %1$s en modo SteamVR', openxr: 'Iniciar %1$s en modo OpenXR',
  othervr: 'Iniciar %1$s en modo Oculus VR', osvr: 'Iniciar %1$s en modo OSVR', openvroverlay: 'Iniciar %1$s como superposición de SteamVR',
  Server: 'Iniciar servidor dedicado', Editor: 'Iniciar editor del juego', Config: 'Iniciar herramienta de disposición de mandos',
  Manual: 'Mostrar manual', Benchmark: 'Iniciar herramienta de benchmarking' };
function steamLabel(label, gameName) {
  const m = /^#?Steam_LaunchOption_(\w+)$/i.exec(String(label || '').trim());
  if (!m) return String(label || '').replace(/^#/, '');
  const k = Object.keys(STEAM_LO).find(x => x.toLowerCase() === m[1].toLowerCase());
  return k ? STEAM_LO[k].replace('%1$s', gameName) : m[1].replace(/_/g, ' ');
}
/* list: Steam's choices as rows (the launch options can be long); the buttons below only cancel */
function lwDlg(g, cap, text, buttons, extra, list) {
  play('notify');
  const rows = list ? `<div class="slist">${list.map(([l], i) => `<span class="txt-f sres" data-f data-l="${i}">${esc(l)}</span>`).join('')}</div>` : '';
  openDlg(`<span class="st-cap">${cap}</span><h2>${esc(g.n.toUpperCase())}</h2>${extra || ''}<p>${esc(text)}</p>${rows}
    <div class="btns">${buttons.map(([l], i) => `<span class="txt-f" data-f data-i="${i}">${esc(l)}</span>`).join('')}</div>`, {
    onA: el => { const a = el.dataset.l !== undefined ? list[+el.dataset.l][1] : buttons[+el.dataset.i][1]; closeDlg(); lwAnswer(g, a); },
    onB: () => { closeDlg(); lwAnswer(g, 'cancel'); } });
  if (list) {
    const d = $('#dlg');
    NAV = mkNav([...d.querySelectorAll('.slist [data-f]')].map(e => [e]).concat([[...d.querySelectorAll('.btns [data-f]')]]), { place: (el, b) => ({ x: b.x, y: b.y + b.h + 4, w: b.w }) });
    NAV.id = 'dlg'; requestAnimationFrame(() => applyFocus());
  }
}
function lwAsk(g, st) {
  const r = st.request;
  if (['CreatingProcess', 'ShowInterstitials', 'ShowCDKey', 'ShowDurationControl', 'ShowVROculusOnly'].includes(r)) {
    /* steps Steam's own interface goes through with one OK */
    return Bridge.call('launch.answer', g.appid, r === 'ShowCDKey' || r === 'ShowDurationControl' ? '' : r === 'ShowVROculusOnly' ? '1' : r).catch(() => {});
  }
  if (r === 'ProcessingShaderCache') return;              /* Steam goes on by itself; OMITIR is offered if it takes long */
  if (r === 'ShowLaunchOption') {
    const o = st.options || [];
    if (!o.length) return lwAnswer(g, '0');
    return lwDlg(g, 'OPCIÓN DE INICIO', 'Este juego tiene varias formas de iniciarse. Elige una:', [['CANCELAR', 'cancel']], '',
      o.slice(0, 6).map(x => [x.label ? steamLabel(x.label, g.n) : `Opción ${x.index + 1}`, String(x.index)]));
  }
  if (r === 'ShowEula') {
    const e = (st.eulas || [])[0], qr = e ? `<div class="qrrow">${qrSvg(e.url, 220)}<div><p class="url">${esc(e.url.slice(8))}</p></div></div>` : '';
    return lwDlg(g, 'CONTRATO DE LICENCIA', 'El juego pide aceptar su contrato de licencia antes de abrirse. Léelo en el móvil con el código. Si lo aceptas, STONE se lo comunica a Steam.',
      [['NO ACEPTO', 'cancel'], ['ACEPTO Y JUGAR', 'ShowEula']], qr);
  }
  if (r === 'SynchronizingCloud' || r === 'SynchronizingControllerConfig') {
    if (st.details === 'cloudconflict') return lwDlg(g, 'PARTIDAS EN LA NUBE', 'Las partidas guardadas de esta consola y las de la nube de Steam no coinciden. ¿Cuáles quieres usar?',
      [['LAS DE LA NUBE', 'KeepRemote'], ['LAS DE ESTA CONSOLA', 'KeepLocal'], ['CANCELAR', 'cancel']]);
    if (st.details === 'pendingcloudsessions') return lwDlg(g, 'PARTIDAS EN LA NUBE', 'Hay una partida de este juego abierta en otro equipo que todavía no subió a la nube. Si juegas ahora, puedes perder ese progreso.',
      [['CANCELAR', 'cancel'], ['JUGAR DE TODOS MODOS', 'IgnorePendingCloudSessions']]);
    return lwDlg(g, 'PARTIDAS EN LA NUBE', 'Steam no pudo sincronizar tus partidas con la nube. Puedes jugar igual: se sincronizarán más tarde.',
      [['JUGAR SIN SINCRONIZAR', 'IgnoreCloud'], ['CANCELAR', 'cancel']]);
  }
  if (r === 'RunningInstallScript') return lwDlg(g, 'COMPONENTES', 'Falló la instalación de un componente que el juego usa (por ejemplo DirectX o Visual C++). Muchas veces el juego funciona igual.',
    [['SEGUIR DE TODOS MODOS', 'IgnoreInstallError'], ['CANCELAR', 'cancel']]);
  if (r === 'KickingOtherSession') return lwDlg(g, 'OTRA SESIÓN', 'Tu cuenta está jugando a un juego en otro equipo. Si sigues, ese equipo se desconecta de Steam.',
    [['CANCELAR', 'cancel'], ['SEGUIR', 'KickOtherSession']]);
  if (r === 'ShowGameArgs') return lwDlg(g, 'ARGUMENTOS DE INICIO', `El juego se iniciará con argumentos personalizados: ${st.details || '—'}`,
    [['CANCELAR', 'cancel'], ['INICIAR', 'ShowGameArgs']]);
  /* a question STONE does not know: Steam's window, as before */
  lwDlg(g, 'STEAM PREGUNTA', 'Steam pide algo para abrir el juego. Puedes verlo en su ventana o cancelar.', [['CANCELAR', 'cancel']], `<p class="tech">${esc(lwTech(st))}</p>`);
}
function lwError(g, st) {
  if (LW.asked === 'error' + st.action) return;
  LW.asked = 'error' + st.action;
  clearTimeout(LW.t); clearTimeout(launchT);
  const n = /^AppError_(\d+)$/.test(st.error || '') ? +st.error.slice(9) : null;
  const why = n !== null ? (LW_ERR[n] || `error ${n} de Steam`) : (st.error || 'error desconocido');
  S.launching = null; S.running = null; loadingOff();
  play('error');
  const back = () => { closeDlg(); returnHome(); };
  openDlg(`<span class="st-cap">NO SE PUDO ABRIR</span><h2>${esc(g.n.toUpperCase())}</h2><p>Steam no pudo abrir el juego: ${esc(why)}.</p>
    <p class="tech">${esc(lwTech(st) + (st.error_details ? ' · ' + st.error_details : ''))}</p>
    <div class="btns"><span class="txt-f" data-f data-b="ok">ENTENDIDO</span></div>`, { onA: back, onB: back });
}
