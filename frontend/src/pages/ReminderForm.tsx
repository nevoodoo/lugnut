import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router";
import { ApiError } from "../api/client";
import {
  useDeleteReminder,
  useRecord,
  useReminder,
  useSaveReminder,
  useSettings,
  useVehicle,
  type Reminder,
  type ReminderIn,
  type Settings,
  type Vehicle,
} from "../api/hooks";
import { ConfirmDelete } from "../components/ConfirmDelete";
import { DateInput } from "../components/DateInput";
import { Field } from "../components/Field";
import { NumberInput } from "../components/NumberInput";
import { fieldErrors } from "../lib/errors";
import { formatDate, parseNumber } from "../lib/format";
import { useTypeLabel } from "../lib/recordTypes";

const str = (v: unknown) => (v == null ? "" : String(v));
const blank = (s: string) => (s.trim() === "" ? null : s.trim());

export function ReminderForm() {
  const params = useParams();
  const reminderId = Number(params.reminderId ?? 0);
  const reminder = useReminder(reminderId);
  const vehicleId = reminderId ? (reminder.data?.vehicle_id ?? 0) : Number(params.id);
  const vehicle = useVehicle(vehicleId);
  const settings = useSettings();

  if (reminder.error instanceof ApiError && reminder.error.status === 404) return <Navigate to="/reminders" replace />;
  if (reminder.isError || vehicle.isError) return <p className="error">Couldn't load this reminder.</p>;
  if (!settings.data || !vehicle.data || (reminderId && !reminder.data)) return null;
  return <Body key={reminderId} reminder={reminder.data} vehicle={vehicle.data} s={settings.data} />;
}

function SourceLink({ r, s }: { r: Reminder; s: Settings }) {
  const record = useRecord(r.source_record_id ?? 0);
  const label = useTypeLabel();
  if (!record.data) return null;
  const type = record.data.type;
  return (
    <p>
      <Link to={`/records/${record.data.id}`}>
        From {label(type).toLowerCase()} record of {formatDate(record.data.date ?? null, s)}
      </Link>
    </p>
  );
}

function Body({ reminder: r, vehicle, s }: { reminder?: Reminder; vehicle: Vehicle; s: Settings }) {
  const nav = useNavigate();
  const save = useSaveReminder();
  const del = useDeleteReminder();
  const expiry = r?.kind === "expiry";
  const unit = vehicle.distance_unit_effective;
  const [v, setV] = useState({
    title: str(r?.title),
    notes: str(r?.notes),
    due_date: str(r?.due_date),
    due_km: str(r?.due_km),
    repeat_months: str(r?.repeat_months),
    repeat_km: str(r?.repeat_km),
    warn_days: str(r?.warn_days ?? 30),
    warn_km: str(r?.warn_km),
  });
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const set = (k: keyof typeof v) => (x: string) => setV((p) => ({ ...p, [k]: x }));
  const text = (k: keyof typeof v) => (e: { target: { value: string } }) => set(k)(e.target.value);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const local: Record<string, string> = {};
    const num = (k: keyof typeof v, whole = false) => {
      const n = parseNumber(v[k]);
      if (n === "invalid" || (whole && n !== null && !Number.isInteger(n))) {
        local[k] = whole ? "Enter a whole number" : "Enter a number";
        return null;
      }
      return n;
    };
    if (!v.title.trim()) local.title = "Enter a title";
    const due_km = num("due_km");
    const repeat_km = num("repeat_km");
    const repeat_months = num("repeat_months", true);
    const warn_km = num("warn_km");
    const warn_days = num("warn_days", true) ?? 30;
    if (!expiry && !v.due_date && due_km === null && !local.due_km) local.due_date = "Set a due date or a due distance";
    if (Object.keys(local).length) return setErrs(local);
    // An expiry reminder only accepts title, notes and warn days; the rest goes back exactly as stored.
    const body: ReminderIn =
      expiry && r
        ? { title: v.title.trim(), notes: blank(v.notes), warn_days, due_date: r.due_date, due_km: r.due_km, repeat_months: r.repeat_months, repeat_km: r.repeat_km, warn_km: r.warn_km }
        : { title: v.title.trim(), notes: blank(v.notes), due_date: blank(v.due_date), due_km, repeat_months, repeat_km, warn_days, warn_km };
    setErrs({});
    setFormError("");
    save.mutate(
      { id: r?.id, vehicleId: vehicle.id, body },
      {
        onSuccess: () => nav(r ? "/reminders" : `/vehicles/${vehicle.id}`),
        onError: (err) => {
          const mapped = err instanceof ApiError ? fieldErrors(err.detail) : {};
          setErrs(mapped);
          if (!Object.keys(mapped).length) setFormError(err.message);
        },
      },
    );
  }

  return (
    <form className="vform rform" onSubmit={onSubmit} noValidate>
      <div>
        <div className="label">{vehicle.name}</div>
        <h1 className="form-title">{r ? "Edit reminder" : "New reminder"}</h1>
      </div>
      {expiry && r && (
        <div className="card source">
          <SourceLink r={r} s={s} />
          <p className="muted">The due date comes from that record. Change it there.</p>
        </div>
      )}
      <fieldset className="card group">
        <legend className="label">Reminder</legend>
        <div className="fields">
          <Field label="Title" error={errs.title}>
            {(a) => <input {...a} value={v.title} onChange={text("title")} />}
          </Field>
          <Field label="Notes (optional)" error={errs.notes}>
            {(a) => <textarea {...a} rows={3} value={v.notes} onChange={text("notes")} />}
          </Field>
        </div>
      </fieldset>
      {!expiry && (
        <fieldset className="card group">
          <legend className="label">Due</legend>
          <div className="fields">
            <div className="pair">
              <DateInput label="Due date" value={v.due_date} onChange={set("due_date")} error={errs.due_date} />
              <NumberInput label="Due distance" value={v.due_km} onChange={set("due_km")} error={errs.due_km} hint={`In ${unit}`} />
            </div>
            <div className="pair">
              <NumberInput label="Repeat every (months)" value={v.repeat_months} onChange={set("repeat_months")} error={errs.repeat_months} hint="Leave blank for a one-off" />
              <NumberInput label="Repeat every (distance)" value={v.repeat_km} onChange={set("repeat_km")} error={errs.repeat_km} hint={`In ${unit}`} />
            </div>
          </div>
        </fieldset>
      )}
      <fieldset className="card group">
        <legend className="label">Warn me</legend>
        <div className="pair">
          <NumberInput label="Days before" value={v.warn_days} onChange={set("warn_days")} error={errs.warn_days} />
          {!expiry && (
            <NumberInput label="Distance before" value={v.warn_km} onChange={set("warn_km")} error={errs.warn_km} hint={`In ${unit}. Blank uses the default`} />
          )}
        </div>
      </fieldset>
      {formError && (
        <p className="error" role="alert">
          {formError}
        </p>
      )}
      <div className="actions">
        <button className="btn primary" disabled={save.isPending}>
          {save.isPending ? "Saving..." : "Save"}
        </button>
        <Link className="btn" to={r ? "/reminders" : `/vehicles/${vehicle.id}`}>
          Cancel
        </Link>
      </div>
      {r && (
        <ConfirmDelete
          label="Delete reminder"
          question="Delete this reminder? This can't be undone."
          pending={del.isPending}
          error={del.error?.message}
          onConfirm={() => del.mutate(r.id, { onSuccess: () => nav("/reminders", { replace: true }) })}
        />
      )}
    </form>
  );
}
