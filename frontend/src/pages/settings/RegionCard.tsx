import { useState, type FormEvent } from "react";
import { useRegions, useSaveSettings, type Settings as SettingsData } from "../../api/hooks";
import { Card } from "../../components/Card";
import { Field } from "../../components/Field";
import { errorsOf } from "./errorsOf";

interface Region {
  code: string;
  name: string;
  currency: string;
  distance_unit: SettingsData["distance_unit"];
  volume_unit: SettingsData["volume_unit"];
  date_format: string;
  timezone: string;
}
type Draft = Omit<SettingsData, "discord_webhook_set"> & { discord_webhook_set?: undefined };

const DATE_FORMATS = ["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"];

const ZONES = (() => {
  try {
    return Intl.supportedValuesOf("timeZone");
  } catch {
    return [];
  }
})();

// "Melbourne" or "new york" -> the one zone it names, else undefined.
function resolveZone(text: string, zones: string[]): string | undefined {
  const t = text.trim().toLowerCase().replace(/ /g, "_");
  const exact = zones.find((z) => z.toLowerCase() === t);
  if (exact) return exact;
  const hits = zones.filter((z) => z.toLowerCase().endsWith(`/${t}`));
  return hits.length === 1 ? hits[0] : undefined;
}

export function RegionCard({ settings }: { settings: SettingsData }) {
  const regions = (useRegions().data ?? []) as unknown as Region[];
  const save = useSaveSettings();
  const [draft, setDraft] = useState<Draft>(() => ({ ...settings, discord_webhook_set: undefined }) as Draft);
  const [tz, setTz] = useState(settings.timezone);
  const [asking, setAsking] = useState<Region | null>(null);
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(false);
  const zones = ZONES.includes(settings.timezone) ? ZONES : [settings.timezone, ...ZONES];
  const set = <K extends keyof Draft>(k: K, v: Draft[K]) => {
    setSaved(false);
    setDraft((d) => ({ ...d, [k]: v }));
  };

  function pickRegion(code: string) {
    const r = regions.find((x) => x.code === code);
    if (!r || code === draft.region) return;
    setAsking(r);
  }
  function answer(useDefaults: boolean) {
    if (!asking) return;
    setSaved(false);
    if (useDefaults) {
      const { currency, distance_unit, volume_unit, date_format, timezone } = asking;
      setDraft({ region: asking.code, currency, distance_unit, volume_unit, date_format, timezone });
      setTz(timezone);
    } else set("region", asking.code);
    setAsking(null);
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    const timezone = resolveZone(tz, zones);
    if (!timezone) return setErrs({ timezone: "Pick a timezone from the list, like Australia/Melbourne" });
    setErrs({});
    // The API's PUT is a full replace: current values first, then the edits.
    save.mutate(
      { ...settings, ...draft, timezone },
      {
        onSuccess: () => {
          setTz(timezone);
          setSaved(true);
        },
        onError: (err) => setErrs(errorsOf(err)),
      },
    );
  }

  const formats = DATE_FORMATS.includes(draft.date_format) ? DATE_FORMATS : [draft.date_format, ...DATE_FORMATS];
  return (
    <Card label="Region and units">
      <form className="fields" onSubmit={submit} noValidate>
        <Field label="Region" error={errs.region}>
          {(a) => (
            <select {...a} value={draft.region} onChange={(e) => pickRegion(e.target.value)}>
              {regions.map((r) => (
                <option key={r.code} value={r.code}>
                  {r.name}
                </option>
              ))}
            </select>
          )}
        </Field>
        {asking && (
          <div className="ask" role="group" aria-label="Region defaults">
            <p>Use {asking.name} defaults for units, currency, date format and timezone?</p>
            <div className="actions">
              <button type="button" className="btn primary" onClick={() => answer(true)}>
                Use defaults
              </button>
              <button type="button" className="btn" onClick={() => answer(false)}>
                Change region only
              </button>
              <button type="button" className="btn" onClick={() => setAsking(null)}>
                Cancel
              </button>
            </div>
          </div>
        )}
        <div className="pair">
          <Field label="Currency" error={errs.currency} hint="Three letters, like AUD. Saved amounts are not converted when you change currency.">
            {(a) => (
              <input {...a} value={draft.currency} maxLength={3} autoComplete="off" onChange={(e) => set("currency", e.target.value.toUpperCase())} />
            )}
          </Field>
          <Field label="Date format" error={errs.date_format}>
            {(a) => (
              <select {...a} value={draft.date_format} onChange={(e) => set("date_format", e.target.value)}>
                {formats.map((f) => (
                  <option key={f}>{f}</option>
                ))}
              </select>
            )}
          </Field>
          <Field label="Distance unit" error={errs.distance_unit}>
            {(a) => (
              <select {...a} value={draft.distance_unit} onChange={(e) => set("distance_unit", e.target.value as Draft["distance_unit"])}>
                <option value="km">Kilometres</option>
                <option value="mi">Miles</option>
              </select>
            )}
          </Field>
          <Field label="Volume unit" error={errs.volume_unit}>
            {(a) => (
              <select {...a} value={draft.volume_unit} onChange={(e) => set("volume_unit", e.target.value as Draft["volume_unit"])}>
                <option value="L">Litres</option>
                <option value="gal_us">US gallons</option>
                <option value="gal_imp">UK gallons</option>
              </select>
            )}
          </Field>
        </div>
        <Field label="Timezone" error={errs.timezone} hint="Type to search, like Melbourne">
          {(a) => (
            <>
              <input
                {...a}
                list="tz-list"
                value={tz}
                autoComplete="off"
                autoCapitalize="off"
                spellCheck={false}
                onChange={(e) => {
                  setSaved(false);
                  setTz(e.target.value);
                }}
                onBlur={() => setTz((t) => resolveZone(t, zones) ?? t)}
              />
              <datalist id="tz-list">
                {zones.map((z) => (
                  <option key={z} value={z} />
                ))}
              </datalist>
            </>
          )}
        </Field>
        {errs.form && !Object.keys(errs).some((k) => k !== "form") && (
          <p className="error" role="alert">
            {errs.form}
          </p>
        )}
        <div className="actions">
          <button className="btn primary" disabled={save.isPending || !!asking}>
            {save.isPending ? "Saving..." : "Save"}
          </button>
          <span role="status" className="muted">
            {saved && "Saved"}
          </span>
        </div>
      </form>
    </Card>
  );
}
