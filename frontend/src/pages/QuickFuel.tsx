import { useState, type FormEvent } from "react";
import { Navigate, useNavigate, useParams } from "react-router";
import { ApiError } from "../api/client";
import { useSaveRecord, useSettings, useVehicle, type Settings, type Vehicle } from "../api/hooks";
import { DateInput } from "../components/DateInput";
import { MoneyInput, moneyError } from "../components/MoneyInput";
import { NumberInput } from "../components/NumberInput";
import { fieldErrors } from "../lib/errors";
import { currencyDigits, parseMoney, parseNumber, today, unitLabel } from "../lib/format";

export function QuickFuel() {
  const id = Number(useParams().id);
  const vehicle = useVehicle(id);
  const settings = useSettings();
  if (vehicle.error instanceof ApiError && vehicle.error.status === 404) return <Navigate to="/garage" replace />;
  if (vehicle.isError || settings.isError) return <p className="error">Couldn't load this vehicle.</p>;
  if (!vehicle.data || !settings.data) return null;
  return <QuickFuelBody vehicle={vehicle.data} s={settings.data} />;
}

// One thumb-sized screen for the pump: volume, cost, odometer, save.
function QuickFuelBody({ vehicle, s }: { vehicle: Vehicle; s: Settings }) {
  const nav = useNavigate();
  const save = useSaveRecord();
  const [volume, setVolume] = useState("");
  const [cost, setCost] = useState("");
  const [odometer, setOdometer] = useState("");
  const [date, setDate] = useState(() => today(s.timezone));
  const [full, setFull] = useState(true);
  const [missed, setMissed] = useState(false);
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const vol = unitLabel(s.volume_unit);

  const v = parseNumber(volume);
  const c = parseMoney(cost, s.currency);
  const o = parseNumber(odometer);
  const digits = currencyDigits(s.currency);
  const perUnit =
    typeof v === "number" && v > 0 && typeof c === "number"
      ? new Intl.NumberFormat(undefined, { style: "currency", currency: s.currency, maximumFractionDigits: digits + 1 }).format(c / 10 ** digits / v)
      : null;

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const local: Record<string, string> = {};
    if (v === "invalid") local["details.volume"] = "Enter a number";
    if (o === "invalid") local.odometer = "Enter a number";
    if (c === "invalid") local.cost = moneyError(s.currency);
    if (Object.keys(local).length) return setErrs(local);
    setErrs({});
    setFormError("");
    // A blank volume is left out so the API answers "Field required" next to it.
    const details = { full_tank: full, missed_previous: missed, ...(v === null ? {} : { volume: v }) };
    save.mutate(
      { vehicleId: vehicle.id, body: { type: "fuel", date: date || null, odometer: o as number | null, cost: c as number | null, is_estimate: false, details } },
      {
        onSuccess: () => nav(`/vehicles/${vehicle.id}`),
        onError: (err) => {
          const mapped = err instanceof ApiError ? fieldErrors(err.detail) : {};
          setErrs(mapped);
          if (!Object.keys(mapped).length) setFormError(err.message);
        },
      },
    );
  }

  return (
    <form className="quickfuel" onSubmit={onSubmit} noValidate>
      <div>
        <div className="label">{vehicle.name}</div>
        <h1>Log fuel</h1>
      </div>
      <NumberInput className="big mono" label={`Volume (${vol})`} value={volume} onChange={setVolume} error={errs["details.volume"]} />
      <MoneyInput className="big mono" label="Cost" currency={s.currency} value={cost} onChange={setCost} error={errs.cost} />
      <p className="per-unit mono" aria-live="polite">
        {perUnit ? `${perUnit} per ${vol}` : `Price per ${vol} shows here`}
      </p>
      <NumberInput
        className="big mono"
        label={`Odometer (${vehicle.distance_unit_effective}, optional)`}
        value={odometer}
        onChange={setOdometer}
        error={errs.odometer}
      />
      <label className="check">
        <input type="checkbox" role="switch" checked={full} onChange={(e) => setFull(e.target.checked)} />
        Filled the tank
      </label>
      <label className="check">
        <input type="checkbox" role="switch" checked={missed} onChange={(e) => setMissed(e.target.checked)} />
        Missed logging the last fill
      </label>
      <DateInput label="Date" value={date} onChange={setDate} error={errs.date} />
      {formError && (
        <p className="error" role="alert">
          {formError}
        </p>
      )}
      <button className="btn primary thumb" disabled={save.isPending}>
        {save.isPending ? "Saving..." : "Save fill"}
      </button>
    </form>
  );
}
