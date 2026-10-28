import { useQueryClient } from "@tanstack/react-query";
import { useRef, useState, type ChangeEvent } from "react";
import { Link } from "react-router";
import { api, ApiError, notifyUnauthorized } from "../api/client";
import { useSettings, useVehicles } from "../api/hooks";
import { Card } from "../components/Card";
import { Field } from "../components/Field";
import { formatDate } from "../lib/format";
import { fieldErrors } from "../lib/errors";
import { resolveZone, ZONES } from "./settings/RegionCard";

type TaxType = "registration" | "insurance";
type VehicleChoice = number | "new";
interface Options {
  date_order?: string;
  source_timezone?: string;
  tax_types: Record<string, TaxType>;
  vehicle_map: Record<string, VehicleChoice>;
}
interface Preview {
  token: string;
  summary: {
    source_id: string;
    name: string;
    plate: string | null;
    matched_vehicle_id: number | null;
    matched_vehicle_name: string | null;
    matched_vehicle_archived: boolean;
    counts: Record<string, number>;
  }[];
  warnings: string[];
  skipped: Record<string, number>;
  guesses: { date_order: string; source_timezone: string };
  tax_choices: { source_id: string; description: string | null; date: string | null; guessed_type: TaxType }[];
  estimates: { source_id: string; title: string | null; date: string | null }[];
}
interface Result {
  created: Record<string, number>;
  skipped_existing: Record<string, number>;
  vehicles: { id: number; name: string }[];
  warnings: string[];
}

const ORDERS = [
  ["DMY", "Day, month, year"],
  ["MDY", "Month, day, year"],
  ["YMD", "Year, month, day"],
];

// fetch has no upload progress, so the file goes up with XHR.
function upload(file: File, onProgress: (pct: number) => void): Promise<Preview> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("file", file);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/import/lubelogger");
    xhr.setRequestHeader("X-Lugnut", "1");
    xhr.responseType = "json";
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(Math.round((e.loaded / e.total) * 100));
    xhr.onerror = () => reject(new Error("Couldn't reach the server"));
    xhr.onload = () => {
      if (xhr.status === 401) notifyUnauthorized();
      const body = xhr.response;
      if (xhr.status < 300) return resolve(body as Preview);
      const detail = body?.detail;
      const msg = Array.isArray(detail) ? (detail[0]?.msg ?? "Upload failed") : typeof detail === "string" ? detail : "Upload failed";
      reject(new ApiError(xhr.status, msg.replace(/^Value error, /, ""), detail));
    };
    xhr.send(form);
  });
}

const messageOf = (e: unknown): string => {
  if (e instanceof ApiError) {
    const first = Object.values(fieldErrors(e.detail))[0];
    return first ?? e.message;
  }
  return e instanceof Error ? e.message : String(e);
};

const one = (n: number, k: string) => `${n} ${n === 1 ? k.replace(/s$/, "") : k}`;
const label = (k: string) => k.replace(/(\w)records$/, "$1 records");

export function ImportLubeLogger() {
  const settings = useSettings().data;
  const vehicles = useVehicles().data ?? [];
  const archived = useVehicles(true).data ?? [];
  const qc = useQueryClient();
  const [pct, setPct] = useState<number | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [opts, setOpts] = useState<Options>({ tax_types: {}, vehicle_map: {} });
  const [tz, setTz] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);
  const errorRef = useRef<HTMLParagraphElement>(null);

  async function pick(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    setPct(0);
    try {
      const p = await upload(file, setPct);
      setPreview(p);
      setTz(p.guesses.source_timezone);
      setOpts({ tax_types: {}, vehicle_map: {} });
    } catch (err) {
      setError(messageOf(err));
    }
    setPct(null);
    e.target.value = "";
  }

  async function change(next: Options) {
    if (!preview) return;
    const prev = opts;
    setOpts(next);
    setBusy(true);
    setError("");
    try {
      const p = await api<Preview>(`/import/lubelogger/${preview.token}/preview`, "POST", next);
      setPreview(p);
      setTz(p.guesses.source_timezone);
    } catch (err) {
      setOpts(prev);
      setError(messageOf(err));
    }
    setBusy(false);
  }

  async function commit() {
    if (!preview) return;
    setBusy(true);
    setError("");
    try {
      setResult(await api<Result>(`/import/lubelogger/${preview.token}/commit`, "POST", opts));
      setBusy(false);
      setTimeout(() => resultRef.current?.focus(), 0);
      await qc.invalidateQueries();
      return;
    } catch (err) {
      setError(messageOf(err));
      setTimeout(() => errorRef.current?.focus(), 0);
    }
    setBusy(false);
  }

  function setZone(text: string) {
    const zone = resolveZone(text, ZONES);
    if (!zone) return setError("Pick a timezone from the list, like Australia/Melbourne");
    setTz(zone);
    if (zone !== preview?.guesses.source_timezone) void change({ ...opts, source_timezone: zone });
  }

  const fmt = (d: string | null) => (d && settings ? formatDate(d, settings) : (d ?? ""));
  const sum = (o: Record<string, number>) => Object.values(o).reduce((a, b) => a + b, 0);

  return (
    <div className="records settings import">
      <h1>Import from LubeLogger</h1>
      {error && (
        <p className="error" role="alert" tabIndex={-1} ref={errorRef}>
          {error}
        </p>
      )}

      {result ? (
        <div ref={resultRef} tabIndex={-1} className="result">
        <Card label="Imported">
          <p>
            Added {one(result.created.vehicles, "vehicles")}, {one(result.created.records, "records")},{" "}
            {one(result.created.reminders, "reminders")} and {one(result.created.attachments, "files")}. {sum(result.skipped_existing)} were already here and left alone.
          </p>
          {result.warnings.length > 0 && (
            <ul>
              {result.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          )}
          <ul className="plain">
            {result.vehicles.map((v) => (
              <li key={v.id}>
                <Link to={`/vehicles/${v.id}`}>{v.name}</Link>
              </li>
            ))}
          </ul>
        </Card>
        </div>
      ) : !preview ? (
        <Card label="Choose your backup">
          <p>
            Pick the backup zip from LubeLogger, under Settings, Backup. Nothing is added until you confirm. Running the import again only adds
            records that are new.
          </p>
          <input type="file" accept=".zip,application/zip" onChange={pick} disabled={pct !== null} aria-label="LubeLogger backup file" />
          {pct !== null && (
            <p role="status">
              <progress value={pct} max={100} /> {pct < 100 ? `Uploading ${pct}%` : "Reading the backup..."}
            </p>
          )}
        </Card>
      ) : (
        <>
          <Card label="Guesses">
            <p className="muted">LubeLogger doesn't say how it wrote dates or which timezone it ran in. Check these.</p>
            <div className="pair">
              <Field label="Date order">
                {(a) => (
                  <select {...a} value={opts.date_order ?? preview.guesses.date_order} disabled={busy} onChange={(e) => change({ ...opts, date_order: e.target.value })}>
                    {ORDERS.map(([v, t]) => (
                      <option key={v} value={v}>
                        {t}
                      </option>
                    ))}
                  </select>
                )}
              </Field>
              <Field label="Timezone" hint="Type to search, like Melbourne">
                {(a) => (
                  <>
                    <input
                      {...a}
                      list="import-tz"
                      value={tz}
                      disabled={busy}
                      autoComplete="off"
                      autoCapitalize="off"
                      spellCheck={false}
                      onChange={(e) => setTz(e.target.value)}
                      onBlur={(e) => setZone(e.target.value)}
                    />
                    <datalist id="import-tz">
                      {ZONES.map((z) => (
                        <option key={z} value={z} />
                      ))}
                    </datalist>
                  </>
                )}
              </Field>
            </div>
          </Card>

          <Card label="Vehicles">
            <div className="table-wrap">
              <table>
                <caption className="visually-hidden">Vehicles in the backup</caption>
                <thead>
                  <tr>
                    <th>In the backup</th>
                    <th>Goes into</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.summary.map((v) => {
                    const match = v.matched_vehicle_name && `Matches ${v.matched_vehicle_name}${v.matched_vehicle_archived ? " (archived)" : ""}`;
                    return (
                      <tr key={v.source_id}>
                        <td>
                          {v.name}
                          {v.plate && <span className="muted"> {v.plate}</span>}
                          <p className="muted">
                            {Object.entries(v.counts)
                              .filter(([, n]) => n)
                              .map(([k, n]) => one(n, k))
                              .join(", ")}
                          </p>
                        </td>
                        <td>
                          <p className="muted">{match || "Will be added as a new vehicle"}</p>
                          <select
                            aria-label={`Where ${v.name} goes`}
                            value={v.matched_vehicle_id ?? "new"}
                            disabled={busy}
                            onChange={(e) =>
                              change({ ...opts, vehicle_map: { ...opts.vehicle_map, [v.source_id]: e.target.value === "new" ? "new" : Number(e.target.value) } })
                            }
                          >
                            <option value="new">Add as new vehicle</option>
                            {vehicles.map((x) => (
                              <option key={x.id} value={x.id}>
                                {x.name}
                              </option>
                            ))}
                            {archived.length > 0 && (
                              <optgroup label="Archived">
                                {archived.map((x) => (
                                  <option key={x.id} value={x.id}>
                                    {x.name}
                                  </option>
                                ))}
                              </optgroup>
                            )}
                          </select>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>

          {preview.tax_choices.length > 0 && (
            <Card label="Tax records">
              <p className="muted">Each becomes a registration or an insurance record. Change any that were guessed wrong.</p>
              <div className="table-wrap">
                <table>
                  <caption className="visually-hidden">Tax records in the backup</caption>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Description</th>
                      <th>Type</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.tax_choices.map((t) => (
                      <tr key={t.source_id}>
                        <td>{fmt(t.date)}</td>
                        <td>{t.description}</td>
                        <td>
                          <select
                            aria-label={`Type of ${t.description ?? "tax record"} on ${fmt(t.date)}`}
                            value={t.guessed_type}
                            disabled={busy}
                            onChange={(e) => change({ ...opts, tax_types: { ...opts.tax_types, [t.source_id]: e.target.value as TaxType } })}
                          >
                            <option value="registration">Registration</option>
                            <option value="insurance">Insurance</option>
                          </select>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {preview.estimates.length > 0 && (
            <Card label="Marked as estimates">
              <p className="muted">These mention an estimate in their notes or description.</p>
              <ul className="plain">
                {preview.estimates.map((e) => (
                  <li key={e.source_id}>
                    {fmt(e.date)} {e.title}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {(preview.warnings.length > 0 || Object.keys(preview.skipped).length > 0) && (
            <Card label="Warnings and skipped">
              <ul>
                {preview.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
                {Object.entries(preview.skipped).map(([k, n]) => (
                  <li key={k}>
                    Skipped {n} {label(k)}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          <div className="actions">
            <button className={`btn primary${busy ? " busy" : ""}`} disabled={busy} onClick={commit}>
              {busy ? "Working..." : "Import"}
            </button>
            <button className="btn" disabled={busy} onClick={() => { setPreview(null); setError(""); }}>
              Choose another file
            </button>
            <span className="muted">Running this again later only adds records that are new.</span>
          </div>
        </>
      )}
    </div>
  );
}
