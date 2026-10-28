import { Check } from "lucide-react";
import { useState, type FormEvent, type ReactNode } from "react";
import { Link } from "react-router";
import { ApiError } from "../api/client";
import { useCompleteReminder, type Reminder } from "../api/hooks";
import { fieldErrors } from "../lib/errors";
import { formatDate, formatDistance, parseNumber, today, type InstallSettings } from "../lib/format";
import { DateInput } from "./DateInput";
import { NumberInput } from "./NumberInput";
import { Stamp } from "./Stamp";

// "15/01/2026 · 12,000 km": whatever the reminder is due by.
export function dueText(r: Reminder, s: InstallSettings): string {
  const unit = r.distance_unit_effective;
  return [r.due_date ? formatDate(r.due_date, s) : "", r.due_km != null ? formatDistance(r.due_km, unit) : ""].filter(Boolean).join(" · ");
}

function DonePanel({ r, s, onClose }: { r: Reminder; s: InstallSettings; onClose: () => void }) {
  const complete = useCompleteReminder();
  const [date, setDate] = useState(() => today(s.timezone));
  const [odo, setOdo] = useState("");
  const [errs, setErrs] = useState<Record<string, string>>({});
  const unit = r.distance_unit_effective;

  function submit(e: FormEvent) {
    e.preventDefault();
    const n = parseNumber(odo);
    if (n === "invalid") return setErrs({ odometer: "Enter a number" });
    setErrs({});
    complete.mutate(
      { id: r.id, date: date || undefined, odometer: n ?? undefined },
      {
        onSuccess: onClose,
        onError: (err) => setErrs(err instanceof ApiError ? { ...fieldErrors(err.detail), form: err.message } : { form: err.message }),
      },
    );
  }

  return (
    <form className="done-panel" onSubmit={submit} noValidate aria-label={`Mark ${r.title} done`}>
      <div className="pair">
        <DateInput label="Done on" value={date} onChange={setDate} error={errs.date} />
        <NumberInput label="Odometer (optional)" value={odo} onChange={setOdo} error={errs.odometer} hint={`In ${unit}`} />
      </div>
      {errs.form && !errs.date && !errs.odometer && (
        <p className="error" role="alert">
          {errs.form}
        </p>
      )}
      <div className="actions">
        <button className="btn primary" disabled={complete.isPending}>
          {complete.isPending ? "Saving..." : "Mark done"}
        </button>
        <button type="button" className="btn" onClick={onClose}>
          Cancel
        </button>
      </div>
    </form>
  );
}

// One reminder: title (opens the form), what it's due by, state stamp, and an inline Done panel.
export function ReminderRow({ r, s, plate }: { r: Reminder; s: InstallSettings; plate?: ReactNode }) {
  const [open, setOpen] = useState(false);
  const doneAt = r.completed_at;
  const done = doneAt !== null;
  return (
    <li className="rem">
      <div className="rem-main">
        <Link className="rem-title" to={`/reminders/${r.id}`}>
          {r.title}
        </Link>
        {done ? <span className="stamp mono ok">Done</span> : <Stamp state={r.state}>{dueText(r, s)}</Stamp>}
      </div>
      <div className="rem-sub">
        {plate}
        {done ? <span className="muted">Completed {formatDate(doneAt?.slice(0, 10) ?? null, s)}</span> : null}
        {!done && (
          <button type="button" className="btn small" aria-expanded={open} onClick={() => setOpen(!open)}>
            <Check size={16} aria-hidden="true" /> Done
          </button>
        )}
      </div>
      {open && <DonePanel r={r} s={s} onClose={() => setOpen(false)} />}
    </li>
  );
}
