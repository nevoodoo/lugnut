import { Check, Copy, LogOut } from "lucide-react";
import { useRef, useState, type FormEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError, type User } from "../api/client";
import {
  useCreateToken,
  useLogout,
  useRegions,
  useRevokeToken,
  useSaveSettings,
  useSetDiscord,
  useSettings,
  useTestDiscord,
  useTokens,
  type Settings as SettingsData,
} from "../api/hooks";
import { Card } from "../components/Card";
import { ConfirmDelete } from "../components/ConfirmDelete";
import { Field } from "../components/Field";
import { fieldErrors } from "../lib/errors";
import { dateInZone, formatDate } from "../lib/format";

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
const errorsOf = (e: unknown): Record<string, string> =>
  e instanceof ApiError ? { ...fieldErrors(e.detail), form: e.message } : { form: e instanceof Error ? e.message : String(e) };

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

function RegionSection({ settings }: { settings: SettingsData }) {
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
          <Field label="Currency" error={errs.currency} hint="Three letters, like AUD">
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

function DiscordSection({ isSet }: { isSet: boolean }) {
  const set = useSetDiscord();
  const test = useTestDiscord();
  const [url, setUrl] = useState("");
  const [err, setErr] = useState("");
  const [result, setResult] = useState("");

  function submit(e: FormEvent) {
    e.preventDefault();
    setErr("");
    setResult("");
    set.mutate(url.trim(), {
      onSuccess: () => setUrl(""),
      onError: (x) => setErr(errorsOf(x).url ?? errorsOf(x).form),
    });
  }
  return (
    <Card label="Discord">
      <p>
        <span className={`stamp mono ${isSet ? "ok" : "soon"}`}>{isSet ? "Webhook set" : "No webhook"}</span>{" "}
        <span className="muted">Reminders post to this channel. The address is never shown.</span>
      </p>
      <form className="fields" onSubmit={submit} noValidate>
        <Field label={isSet ? "Replace webhook URL" : "Webhook URL"} error={err}>
          {(a) => <input {...a} type="url" autoComplete="off" spellCheck={false} placeholder="https://discord.com/api/webhooks/..." value={url} onChange={(e) => setUrl(e.target.value)} />}
        </Field>
        <div className="actions">
          <button className="btn primary" disabled={!url.trim() || set.isPending}>
            Save webhook
          </button>
          {isSet && (
            <>
              <button
                type="button"
                className="btn"
                disabled={test.isPending}
                onClick={() => {
                  setResult("");
                  test.mutate(undefined, {
                    onSuccess: (r) => setResult(r.ok ? "Test message sent." : `Test failed: ${r.error ?? "unknown error"}`),
                    onError: (x) => setResult(`Test failed: ${x.message}`),
                  });
                }}
              >
                {test.isPending ? "Sending..." : "Send test"}
              </button>
              <button type="button" className="btn danger-btn" disabled={set.isPending} onClick={() => set.mutate(null, { onSuccess: () => setResult("") })}>
                Remove
              </button>
            </>
          )}
        </div>
        <div role="status">
          {result && <p className={result.startsWith("Test failed") ? "error" : "muted"}>{result}</p>}
        </div>
      </form>
    </Card>
  );
}

function TokensSection({ s }: { s: SettingsData }) {
  const tokens = useTokens();
  const create = useCreateToken();
  const revoke = useRevokeToken();
  const [name, setName] = useState("");
  const [scope, setScope] = useState<"read" | "write">("read");
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [fresh, setFresh] = useState<string | null>(null);
  const [copied, setCopied] = useState("");
  const box = useRef<HTMLInputElement>(null);
  const when = (iso: string) => formatDate(dateInZone(iso, s.timezone), s);

  function submit(e: FormEvent) {
    e.preventDefault();
    setErrs({});
    create.mutate(
      { name: name.trim(), scope },
      {
        onSuccess: (t) => {
          setFresh(t.token);
          setCopied("");
          setName("");
        },
        onError: (x) => setErrs(errorsOf(x)),
      },
    );
  }
  async function copy() {
    try {
      await navigator.clipboard.writeText(fresh ?? "");
      setCopied("Copied.");
    } catch {
      box.current?.select();
      setCopied("Couldn't copy. It's selected, so press Ctrl+C.");
    }
  }

  return (
    <Card label="API tokens">
      {fresh && (
        <div className="token-new" role="group" aria-label="New token">
          <p>
            <strong>Copy it now. You won't see it again.</strong>
          </p>
          <input ref={box} className="mono token-box" readOnly value={fresh} aria-label="New token" onFocus={(e) => e.currentTarget.select()} />
          <div className="actions">
            <button type="button" className="btn primary" onClick={copy}>
              <Copy size={18} aria-hidden="true" /> Copy
            </button>
            <button type="button" className="btn" onClick={() => setFresh(null)}>
              <Check size={18} aria-hidden="true" /> Done
            </button>
            <span role="status" className="muted">
              {copied}
            </span>
          </div>
        </div>
      )}
      {tokens.isError ? (
        <p className="error">Couldn't load tokens.</p>
      ) : tokens.data?.length === 0 ? (
        <p className="muted">No tokens yet.</p>
      ) : (
        <ul className="rows">
          {tokens.data?.map((t) => (
            <li key={t.id} className="token-row">
              <div className="rem-main">
                <strong>{t.name}</strong>
                <span className="stamp mono ok">{t.scope}</span>
              </div>
              <div className="muted">
                Created {when(t.created_at)} · {t.last_used_at ? `Last used ${when(t.last_used_at)}` : "Never used"}
              </div>
              <ConfirmDelete
                label="Revoke"
                question={`Revoke ${t.name}? Anything using it will stop working.`}
                pending={revoke.isPending}
                error={revoke.isError ? revoke.error.message : undefined}
                onConfirm={() => revoke.mutate(t.id)}
              />
            </li>
          ))}
        </ul>
      )}
      <form className="fields" onSubmit={submit} noValidate>
        <div className="pair">
          <Field label="Token name" error={errs.name}>
            {(a) => <input {...a} value={name} autoComplete="off" onChange={(e) => setName(e.target.value)} />}
          </Field>
          <Field label="Scope" error={errs.scope} hint="Read can't change anything">
            {(a) => (
              <select {...a} value={scope} onChange={(e) => setScope(e.target.value as "read" | "write")}>
                <option value="read">Read</option>
                <option value="write">Write</option>
              </select>
            )}
          </Field>
        </div>
        {errs.form && !errs.name && !errs.scope && (
          <p className="error" role="alert">
            {errs.form}
          </p>
        )}
        <div className="actions">
          <button className="btn primary" disabled={!name.trim() || create.isPending}>
            Create token
          </button>
        </div>
      </form>
    </Card>
  );
}

export function Settings() {
  const settings = useSettings();
  const logout = useLogout();
  const qc = useQueryClient();
  const user = qc.getQueryData<User>(["me"]);
  if (settings.isError) return <p className="error">Couldn't load settings.</p>;
  if (!settings.data) return null;
  return (
    <div className="records settings">
      <h1>Settings</h1>
      <RegionSection settings={settings.data} />
      <DiscordSection isSet={settings.data.discord_webhook_set} />
      <TokensSection s={settings.data} />
      <Card label="Account">
        <p>Signed in as {user?.username}.</p>
        <div className="actions">
          <button className="btn" onClick={() => logout.mutate()}>
            <LogOut size={18} aria-hidden="true" /> Sign out
          </button>
        </div>
      </Card>
    </div>
  );
}
