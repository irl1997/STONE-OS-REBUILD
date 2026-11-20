const FILTERS = ['Todos', 'Steam', 'Emuladores', 'Favoritos', 'Por instalar', 'Sorpréndeme'];
const FILTER_SURPRISE = FILTERS.length - 1;       /* not a filter: STONE picks a game (surprise()) */
function libList() {
  const f = S.filter;
  return G.filter(g => f === 0 || f === FILTER_SURPRISE || (f === 1 && g.src === 'steam') || (f === 2 && g.src === 'shortcut') || (f === 3 && g.fav)
    || (f === 4 && g.src === 'steam' && !g.inst));
}
function emptyText() {
  if (S.libLogged === 'out') return 'Nadie ha iniciado sesión en Steam en esta consola. En Inicio, elige «Inicia sesión en Steam».';
  if (!S.libFound) return 'Steam todavía no ha creado su biblioteca. Si la consola acaba de encenderse, espera unos segundos.';
  if (S.filter === 3) return 'Aún no hay favoritos. Márcalos desde la ficha de cada juego.';
  if (S.filter === 2) return 'Aún no hay juegos de emuladores. Conecta un USB con tus juegos o añádelos en Ajustes → Emuladores.';
  if (S.filter === 4) return G.length ? 'Todos los juegos de tu cuenta están instalados.' : 'Aún no hay juegos en tu cuenta.';
  return G.length ? 'No hay juegos con este filtro.' : 'Aún no hay juegos. Abre la Tienda (RB) para conseguir el primero.';
}
