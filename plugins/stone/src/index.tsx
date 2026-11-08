import {
  ButtonItem,
  ConfirmModal,
  DropdownItem,
  Field,
  PanelSection,
  PanelSectionRow,
  Router,
  ToggleField,
  showModal,
  staticClasses,
} from "@decky/ui";
import { callable, definePlugin } from "@decky/api";
import { useCallback, useEffect, useState } from "react";

type Result = { ok?: boolean; error?: string | null };
type State = {
  version: string | null;
  stoned: {
    error?: string;
    profile?: string;
    safe_mode?: boolean;
    safe_reason?: string;
    per_game?: Record<string, string>;
    game?: { appid: string; profile: string } | null;
    thermal?: { reduced?: boolean };
  };
  metrics: { error?: string; gpu_temp_c?: number; gpu_clock_mhz?: number; cu_count?: number };
  calibration: {
    error?: string;
    running?: { step: number; of: number; step_mhz: number } | null;
    range?: { validated_max?: number; baseline?: number };
    last?: { result?: string; max_temp_c?: number } | null;
  };
  cu40: {
    error?: string;
    image_has?: boolean;
    active?: boolean;
    cus?: number | null;
    state?: "off" | "trial" | "confirmed" | "reverted";
    reason?: string | null;
    reboot_pending?: boolean;
    base_ceiling_mhz?: number;
    last_test?: { ok: boolean; peak_c?: number } | null;
  };
  test: { running: boolean; result: { ok: boolean; output: string } | null };
};
type Doctor = { checks?: [string, string, string][]; error?: string };

const uiReady = callable<[], Result>("ui_ready");
const getState = callable<[], State>("state");
const setProfile = callable<[string], Result>("set_profile");
const setGameProfile = callable<[string, string], Result>("set_game_profile");
const setSafeMode = callable<[boolean], Result>("set_safe_mode");
const calibrate = callable<[string], Result>("calibrate");
const calibrateCancel = callable<[], Result>("calibrate_cancel");
const cu40Enable = callable<[], Result>("cu40_enable");
const cu40Disable = callable<[], Result>("cu40_disable");
const cu40Test = callable<[], Result>("cu40_test");
const doctor = callable<[], Doctor>("doctor");
const reboot = callable<[], Result>("reboot");

const PROFILES = [
  { data: "silent", label: "Silencioso" },
  { data: "balanced", label: "Equilibrado" },
  { data: "performance", label: "Rendimiento" },
];
const GAME_PROFILES = [{ data: "global", label: "Igual que la consola" }, ...PROFILES];
const MARK: Record<string, string> = { ok: "Bien", warn: "Aviso", fail: "Fallo" };
const REFRESH_MS = 3000;

function confirm(title: string, description: string, ok: string, action: () => void) {
  showModal(
    <ConfirmModal strTitle={title} strDescription={description} strOKButtonText={ok} strCancelButtonText="Cancelar" onOK={action} />,
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <PanelSectionRow>
      <Field label={label} focusable={false}>
        {value}
      </Field>
    </PanelSectionRow>
  );
}

function Note({ text }: { text: string }) {
  return (
    <PanelSectionRow>
      <Field description={text} focusable={false} />
    </PanelSectionRow>
  );
}

function offerReboot(message: string) {
  confirm("Reiniciar", message, "Reiniciar ahora", () => void reboot());
}

function Cu40({ st, refresh, setError }: { st: State; refresh: () => void; setError: (e: string | null) => void }) {
  const cu = st.cu40;
  const report = (r: Result) => setError(r.error ?? null);
  if (cu.error) return <Note text={`No se pudo leer el estado de 40 CU: ${cu.error}`} />;
  if (!cu.image_has) return <Note text="Esta versión de STONE OS no trae el desbloqueo de 40 CU." />;

  const enable = () =>
    confirm(
      "Activar 40 CU",
      "Es un cambio de la comunidad, no de AMD: no todas las placas lo aguantan. La GPU consume unos 30 W más y se calienta más. " +
        `STONE empieza con un máximo de ${cu.base_ceiling_mhz} MHz. Después de reiniciar hay que pasar una prueba de 3 minutos; ` +
        "si falla, o si hay errores de GPU, STONE vuelve solo a 24 CU.",
      "Activar",
      async () => {
        const r = await cu40Enable();
        report(r);
        refresh();
        if (r.ok) offerReboot("40 CU se usará desde el próximo arranque.");
      },
    );
  const disable = () =>
    confirm("Volver a 24 CU", "La GPU volverá a 24 CU desde el próximo arranque.", "Volver a 24 CU", async () => {
      const r = await cu40Disable();
      report(r);
      refresh();
      if (r.ok) offerReboot("24 CU se usará desde el próximo arranque.");
    });
  const test = () =>
    confirm(
      "Probar 40 CU",
      "La prueba exige a la GPU durante 3 minutos. No abras juegos mientras tanto. Si falla, STONE vuelve a 24 CU en el próximo arranque.",
      "Empezar la prueba",
      async () => {
        report(await cu40Test());
        refresh();
      },
    );

  const label = cu.active ? `40 CU${cu.cus ? ` (el driver cuenta ${cu.cus})` : ""}` : "24 CU";
  return (
    <>
      <Info label="Este arranque" value={label} />
      {cu.reason && cu.state === "reverted" && <Note text={`Se volvió a 24 CU: ${cu.reason}`} />}
      {cu.reboot_pending && (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => void reboot()}>
            Reiniciar para aplicar
          </ButtonItem>
        </PanelSectionRow>
      )}
      {st.test.running && <Note text="Prueba en marcha. No abras juegos." />}
      {st.test.result && <Note text={st.test.result.ok ? "Prueba aprobada: 40 CU confirmado." : `La prueba falló: ${st.test.result.output}`} />}
      {cu.state === "trial" && cu.active && !st.test.running && !cu.reboot_pending && (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={test}>
            Probar 40 CU (3 min)
          </ButtonItem>
        </PanelSectionRow>
      )}
      {!cu.reboot_pending && (cu.state === "off" || cu.state === "reverted") && (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={enable}>
            Activar 40 CU
          </ButtonItem>
        </PanelSectionRow>
      )}
      {!cu.reboot_pending && (cu.state === "trial" || cu.state === "confirmed") && !st.test.running && (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={disable}>
            Volver a 24 CU
          </ButtonItem>
        </PanelSectionRow>
      )}
    </>
  );
}

function Calibration({ st, refresh, setError }: { st: State; refresh: () => void; setError: (e: string | null) => void }) {
  const c = st.calibration;
  if (c.error) return null;
  const start = () =>
    confirm(
      "Calibrar la GPU",
      "STONE sube la GPU paso a paso y prueba cada paso con carga. Se detiene ante el primer error o calor, y solo usa lo que haya pasado. No abras juegos mientras tanto. Puede tardar varios minutos.",
      "Calibrar",
      async () => {
        const r = await calibrate("standard");
        setError(r.error ?? null);
        refresh();
      },
    );
  return (
    <>
      <Info label="Máximo validado" value={c.range?.validated_max ? `${c.range.validated_max} MHz` : "Sin calibrar"} />
      {c.running ? (
        <>
          <Note text={`Paso ${c.running.step} de ${c.running.of}: ${c.running.step_mhz} MHz`} />
          <PanelSectionRow>
            <ButtonItem layout="below" onClick={() => void calibrateCancel().then(refresh)}>
              Cancelar
            </ButtonItem>
          </PanelSectionRow>
        </>
      ) : (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={start}>
            Calibrar
          </ButtonItem>
        </PanelSectionRow>
      )}
    </>
  );
}

function Health() {
  const [result, setResult] = useState<Doctor | null>(null);
  const [busy, setBusy] = useState(false);
  const run = async () => {
    setBusy(true);
    setResult(await doctor());
    setBusy(false);
  };
  return (
    <>
      <PanelSectionRow>
        <ButtonItem layout="below" disabled={busy} onClick={run}>
          {busy ? "Comprobando…" : "Comprobar la consola"}
        </ButtonItem>
      </PanelSectionRow>
      {result?.error && <Note text={result.error} />}
      {result?.checks?.map(([level, title, detail]) => (
        <PanelSectionRow key={title}>
          <Field label={`${MARK[level] ?? level} · ${title}`} description={detail} focusable={false} />
        </PanelSectionRow>
      ))}
    </>
  );
}

function Content() {
  const [st, setSt] = useState<State | null>(null);
  const [error, setError] = useState<string | null>(null);
  const refresh = useCallback(() => {
    getState().then(setSt, (e) => setError(String(e)));
  }, []);
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, REFRESH_MS);
    return () => clearInterval(t);
  }, [refresh]);

  if (!st) return <PanelSection title="STONE">{error ? <Note text={error} /> : <Note text="Leyendo…" />}</PanelSection>;

  const s = st.stoned;
  const m = st.metrics;
  const running = Router.MainRunningApp;
  const appid = s.game?.appid ?? (running ? String(running.appid) : null);
  const report = (r: Result) => {
    setError(r.error ?? null);
    refresh();
  };

  return (
    <>
      {error && (
        <PanelSection>
          <Note text={error} />
        </PanelSection>
      )}
      <PanelSection title="Rendimiento">
        {s.error ? (
          <Note text={`El servicio de rendimiento no responde: ${s.error}`} />
        ) : (
          <>
            {s.safe_mode && <Note text="Modo seguro: la GPU usa la configuración de fábrica." />}
            {s.thermal?.reduced && <Note text="Temperatura alta: rendimiento reducido a Silencioso." />}
            <PanelSectionRow>
              <DropdownItem
                label="Perfil de la consola"
                rgOptions={PROFILES}
                selectedOption={s.profile}
                disabled={s.safe_mode}
                onChange={(o) => void setProfile(o.data as string).then(report)}
              />
            </PanelSectionRow>
            {appid && (
              <PanelSectionRow>
                <DropdownItem
                  label={running ? `Perfil de ${running.display_name}` : "Perfil de este juego"}
                  rgOptions={GAME_PROFILES}
                  selectedOption={s.per_game?.[appid] ?? "global"}
                  disabled={s.safe_mode}
                  onChange={(o) => void setGameProfile(appid, o.data as string).then(report)}
                />
              </PanelSectionRow>
            )}
            {m.gpu_temp_c != null && <Info label="GPU" value={`${m.gpu_temp_c} °C${m.gpu_clock_mhz ? ` · ${m.gpu_clock_mhz} MHz` : ""}`} />}
          </>
        )}
      </PanelSection>
      <PanelSection title="40 CU">
        <Cu40 st={st} refresh={refresh} setError={setError} />
      </PanelSection>
      <PanelSection title="Calibración">
        <Calibration st={st} refresh={refresh} setError={setError} />
      </PanelSection>
      <PanelSection title="Salud">
        <Health />
        {!s.error && s.safe_reason !== "kernel" && (
          <PanelSectionRow>
            <ToggleField label="Modo seguro" checked={!!s.safe_mode} onChange={(on) => void setSafeMode(on).then(report)} />
          </PanelSectionRow>
        )}
      </PanelSection>
      {st.version && (
        <PanelSection>
          <Note text={`STONE OS ${st.version}`} />
        </PanelSection>
      )}
    </>
  );
}

function Mark() {
  return (
    <svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M2 8h20M2 14h20" />
      <path d="M2 11h20" strokeWidth="1" />
    </svg>
  );
}

export default definePlugin(() => {
  // The plugin's frontend only loads inside Steam's interface: this is the moment stoned waits for.
  void uiReady();
  return {
    name: "STONE",
    titleView: <div className={staticClasses.Title}>STONE</div>,
    content: <Content />,
    icon: <Mark />,
  };
});
