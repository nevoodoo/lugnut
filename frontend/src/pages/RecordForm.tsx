import { useState, type FormEvent, type ReactNode } from "react";
import { Link, Navigate, useNavigate, useParams, useSearchParams } from "react-router";
import { ApiError } from "../api/client";
import {
  useDeleteRecord,
  useJobTypes,
  useRecord,
  useSaveRecord,
  useSettings,
  useVehicle,
  type LugnutRecord,
  type RecordIn,
  type Settings,
  type Vehicle,
} from "../api/hooks";
import { Attachments, useUploadQueue } from "../components/Attachments";
import { ConfirmDelete } from "../components/ConfirmDelete";
import { CustomFields, customFieldErrors, pairsToObject, type Pairs } from "../components/CustomFields";
import { DateInput } from "../components/DateInput";
import { Field } from "../components/Field";
import { LineItems, type Item } from "../components/LineItems";
import { MoneyInput, moneyError } from "../components/MoneyInput";
import { NumberInput } from "../components/NumberInput";
import { TypePicker } from "../components/TypePicker";
import { fieldErrors } from "../lib/errors";
import { lineItemsTotal, moneyToText, parseMoney, parseNumber, today, unitLabel } from "../lib/format";
import { isRecordType, optionLabel, RECORD_TYPES, useTypeLabel, type DetailField, type RecordType } from "../lib/recordTypes";

type Values = Record<string, string | boolean>;
const COMMON = ["date", "odometer", "cost", "title", "notes", "tags"];

const str = (v: unknown) => (v == null ? "" : String(v));
const blank = (s: string) => (s.trim() === "" ? null : s.trim());

// Saved record (or the type's defaults) to the strings and booleans the inputs hold.
function toValues(type: RecordType, r: LugnutRecord | undefined, s: Settings): { common: Values; details: Values } {
  const common: Values = {
    date: r ? str(r.date) : RECORD_TYPES[type].dated ? today(s.timezone) : "",
    odometer: str(r?.odometer),
    cost: moneyToText(r?.cost, s.currency),
    is_estimate: !!r?.is_estimate,
    title: str(r?.title),
    notes: str(r?.notes),
    tags: (r?.tags ?? []).join(", "),
  };
  const details: Values = {};
  for (const f of RECORD_TYPES[type].fields) {
    const v = r?.details[f.name];
    if (f.kind === "bool") details[f.name] = v === undefined ? !!f.default : !!v;
    else if (f.kind === "money") details[f.name] = moneyToText(v as number | null, s.currency);
    else if (f.kind === "select" && f.required) details[f.name] = str(v ?? f.default ?? f.options?.[0]);
    else details[f.name] = str(v);
  }
  return { common, details };
}

const toItems = (r: LugnutRecord | undefined, currency: string): Item[] =>
  ((r?.details.line_items ?? []) as { id: number; job_type_id: number | null; description: string | null; cost: number | null; quantity: number | null }[]).map(
    (li) => ({ key: li.id, job_type_id: li.job_type_id, description: str(li.description), cost: moneyToText(li.cost, currency), quantity: str(li.quantity) }),
  );

export function RecordForm() {
  const params = useParams();
  const [search] = useSearchParams();
  const recordId = Number(params.recordId ?? 0);
  const record = useRecord(recordId);
  const vehicleId = recordId ? (record.data?.vehicle_id ?? 0) : Number(params.id);
  const vehicle = useVehicle(vehicleId);
  const settings = useSettings();
  const jobTypes = useJobTypes();
  const type = record.data?.type ?? search.get("type");

  if (record.error instanceof ApiError && record.error.status === 404) return <Navigate to="/" replace />;
  if (record.isError || vehicle.isError) return <p className="error">Couldn't load this record.</p>;
  if (!settings.data || !vehicle.data || !jobTypes.data || (recordId && !record.data)) return null;
  if (!isRecordType(type))
    return (
      <div className="vform">
        <h1>Add a record</h1>
        <TypePicker vehicleId={vehicleId} />
      </div>
    );
  // Keyed so switching type or record starts the form fresh from the saved values.
  return <RecordFormBody key={`${type}-${recordId}`} type={type} record={record.data} vehicle={vehicle.data} s={settings.data} />;
}

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <fieldset className="card group">
      <legend className="label">{title}</legend>
      <div className="fields">{children}</div>
    </fieldset>
  );
}

function RecordFormBody({ type, record, vehicle, s }: { type: RecordType; record?: LugnutRecord; vehicle: Vehicle; s: Settings }) {
  const nav = useNavigate();
  const save = useSaveRecord();
  const del = useDeleteRecord();
  const uploads = useUploadQueue(vehicle.id);
  const label = useTypeLabel()(type);
  const def = RECORD_TYPES[type];
  const Icon = def.icon;
  const [init] = useState(() => toValues(type, record, s));
  const [common, setCommon] = useState(init.common);
  const [details, setDetails] = useState(init.details);
  const [items, setItems] = useState<Item[]>(() => toItems(record, s.currency));
  const [custom, setCustom] = useState<Pairs>(() => Object.entries(record?.custom_fields ?? {}));
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [created, setCreated] = useState<number>(); // set when a new record saved but a file didn't
  const back = `/vehicles/${vehicle.id}/records`;
  const unit = vehicle.distance_unit_effective;

  const parsedItems = items.map((it) => ({ cost: parseMoney(it.cost, s.currency), quantity: parseNumber(it.quantity) }));
  const total = lineItemsTotal(parsedItems.map((p) => ({ cost: p.cost === "invalid" ? null : p.cost, quantity: p.quantity === "invalid" ? null : p.quantity })));
  // Rows with no job type, description or cost aren't saved; kept maps sent rows back to on-screen ones.
  const kept = items.flatMap((it, i) => (it.job_type_id !== null || it.unmatched || it.description.trim() || it.cost.trim() ? [i] : []));
  const known = (k: string) =>
    COMMON.includes(k) || k.startsWith("tags") || k.startsWith("custom_fields") || k.startsWith("details.line_items.") || def.fields.some((f) => k === `details.${f.name}`);

  function build(): { body?: RecordIn; local: Record<string, string> } {
    const local: Record<string, string> = customFieldErrors(custom);
    const money = (key: string, text: string) => {
      const m = parseMoney(text, s.currency);
      if (m === "invalid") local[key] = moneyError(s.currency);
      return m === "invalid" ? null : m;
    };
    const num = (key: string, text: string) => {
      const n = parseNumber(text);
      if (n === "invalid") local[key] = "Enter a number";
      return n === "invalid" ? null : n;
    };
    // Blank details are left out, so a required one comes back from the API as "Field required".
    const d: Record<string, unknown> = {};
    for (const f of def.fields) {
      const v = details[f.name];
      if (typeof v === "boolean") d[f.name] = v;
      else if (v.trim() === "") continue;
      else if (f.kind === "money") d[f.name] = money(`details.${f.name}`, v);
      else if (f.kind === "number") d[f.name] = num(`details.${f.name}`, v);
      else d[f.name] = v.trim();
    }
    if (type === "work")
      d.line_items = kept.map((i) => {
        const it = items[i];
        if (it.unmatched) local[`details.line_items.${i}.job_type_id`] = "Pick a job type or add it";
        return {
          job_type_id: it.job_type_id,
          description: blank(it.description),
          cost: money(`details.line_items.${i}.cost`, it.cost),
          quantity: num(`details.line_items.${i}.quantity`, it.quantity),
        };
      });
    const cost = money("cost", common.cost as string);
    const body: RecordIn = {
      type,
      date: blank(common.date as string),
      odometer: num("odometer", common.odometer as string),
      // A work record with no cost of its own takes its line items' total.
      cost: cost ?? (type === "work" && parsedItems.some((p) => typeof p.cost === "number") ? total : null),
      is_estimate: !!common.is_estimate,
      title: blank(common.title as string),
      notes: blank(common.notes as string),
      tags: (common.tags as string).split(",").map((t) => t.trim()).filter(Boolean),
      custom_fields: pairsToObject(custom),
      details: d,
    };
    return { body: Object.keys(local).length ? undefined : body, local };
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const { body, local } = build();
    if (!body) return setErrs(local);
    setErrs({});
    setFormError("");
    save.mutate(
      { id: record?.id, vehicleId: vehicle.id, body },
      {
        onSuccess: async (r) => {
          if (record || (await uploads.sendWaiting(r.id))) nav(back);
          else setCreated(r.id);
        },
        onError: (err) => {
          const raw = err instanceof ApiError ? fieldErrors(err.detail) : {};
          const mapped = Object.fromEntries(
            Object.entries(raw).map(([k, m]) => [k.replace(/^details\.line_items\.(\d+)/, (_, j) => `details.line_items.${kept[Number(j)]}`), m]),
          );
          setErrs(mapped);
          const stray = Object.entries(mapped).filter(([k]) => !known(k));
          if (!Object.keys(mapped).length) setFormError(err.message);
          else if (stray.length) setFormError(stray.map(([k, m]) => `${k}: ${m}`).join("; "));
        },
      },
    );
  }

  const setC = (k: string) => (v: string) => setCommon((p) => ({ ...p, [k]: v }));
  const setD = (k: string) => (v: string | boolean) => setDetails((p) => ({ ...p, [k]: v }));

  function detail(f: DetailField) {
    const v = details[f.name];
    const err = errs[`details.${f.name}`];
    switch (f.kind) {
      case "bool":
        return (
          <label key={f.name} className="check">
            <input type="checkbox" checked={!!v} onChange={(e) => setD(f.name)(e.target.checked)} />
            {f.label}
          </label>
        );
      case "money":
        return <MoneyInput key={f.name} label={f.label} currency={s.currency} value={v as string} onChange={setD(f.name)} error={err} />;
      case "number":
        return (
          <NumberInput key={f.name} label={f.label} value={v as string} onChange={setD(f.name)} error={err} hint={f.name === "volume" ? `In ${unitLabel(s.volume_unit)}` : undefined} />
        );
      case "date":
        return <DateInput key={f.name} label={f.label} value={v as string} onChange={setD(f.name)} error={err} />;
      case "select":
        return (
          <Field key={f.name} label={f.label} error={err}>
            {(a) => (
              <select {...a} value={v as string} onChange={(e) => setD(f.name)(e.target.value)}>
                {!f.required && <option value="">Not set</option>}
                {f.options?.map((o) => (
                  <option key={o} value={o}>
                    {optionLabel(o)}
                  </option>
                ))}
              </select>
            )}
          </Field>
        );
      default:
        return (
          <Field key={f.name} label={f.label} error={err}>
            {(a) => <input {...a} value={v as string} onChange={(e) => setD(f.name)(e.target.value)} />}
          </Field>
        );
    }
  }

  return (
    <form className="vform rform" onSubmit={onSubmit} noValidate>
      <div>
        <div className="label">{vehicle.name}</div>
        <h1 className="form-title">
          <Icon size={26} aria-hidden="true" /> {record ? label : `New ${label.toLowerCase()}`}
        </h1>
      </div>
      <Group title="Record">
        <div className="pair">
          <DateInput label={def.dated ? "Date" : "Date (optional)"} value={common.date as string} onChange={setC("date")} error={errs.date} />
          <NumberInput
            label={type === "odometer" ? "Odometer" : "Odometer (optional)"}
            value={common.odometer as string}
            onChange={setC("odometer")}
            error={errs.odometer}
            hint={`In ${unit}`}
          />
        </div>
        <MoneyInput
          label="Cost"
          currency={s.currency}
          value={common.cost as string}
          onChange={setC("cost")}
          error={errs.cost}
          placeholder={type === "work" && total ? moneyToText(total, s.currency) : undefined}
        />
        <label className="check">
          <input type="checkbox" checked={!!common.is_estimate} onChange={(e) => setCommon((p) => ({ ...p, is_estimate: e.target.checked }))} />
          This cost is an estimate
        </label>
        <Field label="Title" error={errs.title} hint="Leave blank to describe it from the details.">
          {(a) => <input {...a} value={common.title as string} onChange={(e) => setC("title")(e.target.value)} />}
        </Field>
      </Group>
      {(def.fields.length > 0 || type === "work") && (
        <Group title={`${label} details`}>
          <div className="detail-grid">{def.fields.map(detail)}</div>
          {type === "work" && <LineItems items={items} onChange={setItems} currency={s.currency} total={total} errs={errs} />}
        </Group>
      )}
      <Group title="Notes">
        <Field label="Notes" error={errs.notes}>
          {(a) => <textarea {...a} rows={3} value={common.notes as string} onChange={(e) => setC("notes")(e.target.value)} />}
        </Field>
        <Field label="Tags" error={errs.tags ?? errs["tags.0"]} hint="Separate tags with commas.">
          {(a) => <input {...a} value={common.tags as string} onChange={(e) => setC("tags")(e.target.value)} />}
        </Field>
      </Group>
      <Group title="Custom fields">
        <CustomFields value={custom} onChange={setCustom} errs={errs} />
      </Group>
      <Group title="Files">
        <Attachments record={record} uploads={uploads} />
      </Group>
      {formError && (
        <p className="error" role="alert">
          {formError}
        </p>
      )}
      {created ? (
        <div className="card danger" role="alert">
          <p>The record is saved, but some files didn't upload. Open the record to try them again.</p>
          <div className="actions">
            <Link className="btn" to={`/records/${created}`}>
              Open the record
            </Link>
            <Link className="btn" to={back}>
              Back to records
            </Link>
          </div>
        </div>
      ) : (
        <div className="actions">
          <button className="btn primary" disabled={save.isPending}>
            {save.isPending ? "Saving..." : "Save"}
          </button>
          <Link className="btn" to={back}>
            Cancel
          </Link>
        </div>
      )}
      {record && (
        <ConfirmDelete
          label="Delete record"
          question={`Delete this ${label.toLowerCase()} record and its files? This can't be undone.`}
          pending={del.isPending}
          error={del.error?.message}
          onConfirm={() => del.mutate(record.id, { onSuccess: () => nav(back, { replace: true }) })}
        />
      )}
    </form>
  );
}

