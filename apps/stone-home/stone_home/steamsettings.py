"""Steam's own settings inside STONE (Ajustes → Steam), the way Steam's interface keeps them.

Steam's interface holds its settings in `window.settingsStore.clientSettings` (a plain object, kept up to
date by SteamClient.Settings.RegisterForSettingsChanges) and changes one with
`settingsStore.GetClientSetting(name)` → [value, setter], whose setter serialises the change and calls
SteamClient.Settings.SetSetting (its code, client 1792618285: the hook `G(name)` of its settings pages).

Until 3.1.0-rc7 STONE built this list by calling every `Get…()` function SteamClient exposed with no
arguments: the console's diagnostic report (14-11-2026) showed Steam raising an exception for dozens of
them (Storage.GetJSON, Screenshots…, RemotePlay…, OpenVR…) every time the page was read, and some of
those functions read things STONE has no business reading. Now nothing is called to read: the values
are taken from Steam's own store, and only the settings listed below, with a Spanish name, are shown.
Only true/false ones are changed, through Steam's own setter, and only when Steam holds a true/false.
"""

import json

# name in Steam's client settings -> (Spanish label, area). Settings a person changes at home; Steam's
# names (its settings pages). Ones STONE handles itself (Bluetooth, the screen, the frame limit) are not here.
CURATED = {
    "controller_xbox_support": ("Soporte para mandos Xbox", "Mandos"),
    "controller_ps_support": ("Soporte para mandos PlayStation", "Mandos"),
    "controller_switch_support": ("Soporte para mandos de Nintendo", "Mandos"),
    "controller_generic_support": ("Soporte para otros mandos", "Mandos"),
    "controller_combine_nintendo_joycons": ("Usar dos Joy-Con como un solo mando", "Mandos"),
    "controller_power_off_timeout": ("Apagar el mando tras minutos sin uso", "Mandos"),
    "enable_overlay": ("Superposición de Steam durante el juego", "Juegos"),
    "enable_shader_precache": ("Descargar sombreadores precompilados", "Juegos"),
    "download_while_app_running": ("Descargar mientras se juega", "Descargas"),
    "restrict_auto_updates": ("Actualizar juegos solo en un horario", "Descargas"),
    "library_low_bandwidth_mode": ("Modo de poco ancho de banda", "Descargas"),
    "cloud_enabled": ("Steam Cloud (partidas en la nube)", "Cuenta"),
    "disable_all_toasts": ("Desactivar todos los avisos de Steam", "Avisos"),
    "disable_toasts_in_game": ("Sin avisos de Steam durante el juego", "Avisos"),
    "play_sound_on_toast": ("Sonido en los avisos de Steam", "Avisos"),
    "save_uncompressed_screenshots": ("Guardar capturas sin comprimir", "Capturas"),
    "enable_hardware_video_decoding": ("Decodificar vídeo con la GPU", "Sistema"),
    "accessibility_reduce_motion": ("Reducir movimiento en Steam", "Accesibilidad"),
    # Steam's «Activar HDR» (its Display page: setting "gamescope_hdr_enabled", 3.1.0-rc8). With it on and
    # a TV that takes HDR, gamescope's output goes HDR a few seconds after Steam starts.
    "gamescope_hdr_enabled": ("HDR en la salida de vídeo", "Pantalla"),
}

# read only, for the diagnostic report: what Steam has set for gamescope's output
DISPLAY_KEYS = ("gamescope_hdr_enabled", "gamescope_game_resolution_global", "gamescope_native_external_res_in_steam")


def read_expression(keys):
    return ("(()=>{const S=window.settingsStore;if(!S)return null;let c=null;try{c=S.clientSettings;}catch(e){}"
            "if(!c||typeof c!=='object')return null;const o={};"
            f"for(const k of {json.dumps(list(keys))}){{const v=c[k];"
            "if(typeof v==='boolean'||typeof v==='number'||(typeof v==='string'&&v.length<=80))o[k]=v;}"
            "return JSON.stringify(o);})()")


READ_EXPRESSION = read_expression(sorted(CURATED))


def read_display(cef):
    """{key: value} of DISPLAY_KEYS as Steam holds them, or None when its interface does not answer."""
    raw = cef.ui_value(read_expression(DISPLAY_KEYS))
    try:
        v = json.loads(raw) if isinstance(raw, str) else None
    except ValueError:
        v = None
    return v if isinstance(v, dict) else None


def write_expression(name, value):
    """Change one true/false setting with Steam's own setter, only if Steam holds a true/false for it."""
    if name not in CURATED or not isinstance(value, bool):
        raise ValueError("unknown or not a true/false setting")
    n, v = json.dumps(name), "true" if value else "false"
    return ("(()=>{const S=window.settingsStore;if(!S||!S.GetClientSetting)return null;"
            f"const c=S.clientSettings;if(!c||typeof c[{n}]!=='boolean')return 'changed';"
            f"const r=S.GetClientSetting({n});if(!Array.isArray(r)||typeof r[1]!=='function')return null;"
            f"r[1]({v});return 'ok';}})()")


class SteamSettings:
    def __init__(self, cef):
        self.cef = cef
        self._bool = set()                  # names whose last value read was true/false: the only ones that change

    def read(self, refresh=False):
        """{"available", "settings": [{id, label, area, value, type, writable}], "count", "error"}."""
        raw = self.cef.ui_value(READ_EXPRESSION)
        try:
            vals = json.loads(raw) if isinstance(raw, str) else None
        except ValueError:
            vals = None
        if not isinstance(vals, dict):
            return {"available": False, "settings": [], "count": 0,
                    "error": "La interfaz de Steam no respondió (¿Steam está arrancando?)"}
        out, self._bool = [], set()
        for name, (label, area) in CURATED.items():
            if name not in vals:
                continue
            v = vals[name]
            if isinstance(v, bool):
                self._bool.add(name)
            out.append({"id": name, "label": label, "area": area, "value": v,
                        "type": "bool" if isinstance(v, bool) else "number" if isinstance(v, (int, float)) else "text",
                        "writable": isinstance(v, bool)})
        return {"available": True, "settings": out, "count": len(out), "error": None}

    def set_bool(self, sid, value):
        if sid not in CURATED or sid not in self._bool or not isinstance(value, bool):
            raise ValueError("unknown, read-only or not a true/false setting")
        res = self.cef.ui_value(write_expression(sid, value))
        return {"ok": res == "ok", "id": sid, "value": value}
