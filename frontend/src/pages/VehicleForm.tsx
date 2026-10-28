import { useState, type FormEvent, type ReactNode } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router";
import { ApiError } from "../api/client";
import { useDeleteVehicle, useSaveVehicle, useSettings, useVehicle, type Vehicle, type VehicleIn } from "../api/hooks";
import { ConfirmDelete } from "../components/ConfirmDelete";
import { CustomFields, customFieldErrors, pairsToObject, type Pairs } from "../components/CustomFields";
import { Field } from "../components/Field";
import { MoneyInput, moneyError } from "../components/MoneyInput";
import { PhotoUpload } from "../components/PhotoUpload";
import { fieldErrors } from "../lib/errors";
import { moneyToText, parseMoney } from "../lib/format";

type Form = Record<string, string> & { archived: string };
const TEXT = ["name", "year", "make", "model", "plate", "fuel_type", "vin", "engine_number", "colour"] as const;
const DATES = ["purchase_date", "sold_date"] as const;
const MONEY = ["purchase_price", "sold_price"] as const;

const toForm = (v: Vehicle | undefined, currency: string): Form => {
  const f: Form = { odometer_adjustment: String(v?.odometer_adjustment ?? 0), distance_unit: v?.distance_unit ?? "", archived: v?.archived ? "1" : "" };
  for (const k of [...TEXT, ...DATES]) f[k] = v?.[k] == null ? "" : String(v[k]);
  for (const k of MONEY) f[k] = moneyToText(v?.[k], currency);
  return f;
};

const blank = (s: string) => (s.trim() === "" ? null : s.trim());

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <fieldset className="card group">
      <legend className="label">{title}</legend>
      <div className="fields">{children}</div>
    </fieldset>
  );
}

export function VehicleForm() {
  const raw = useParams().id;
  const id = raw ? Number(raw) : undefined;
  const vehicle = useVehicle(id ?? 0);
  const settings = useSettings();
  if (id !== undefined && vehicle.error instanceof ApiError && vehicle.error.status === 404)
    return <Navigate to="/garage" replace />;
  if (!settings.data || (id !== undefined && !vehicle.data)) return null;
  // Mount the form once the data is here so its state starts from the saved vehicle.
  return <VehicleFormBody id={id} vehicle={vehicle.data} currency={settings.data.currency} unit={settings.data.distance_unit} />;
}

function VehicleFormBody(props: { id?: number; vehicle?: Vehicle; currency: string; unit: string }) {
  const { id, vehicle, currency } = props;
  const nav = useNavigate();
  const save = useSaveVehicle();
  const del = useDeleteVehicle();
  const [f, setF] = useState<Form>(() => toForm(vehicle, currency));
  const [custom, setCustom] = useState<Pairs>(() => Object.entries(vehicle?.custom_fields ?? {}));
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");
  const [delError, setDelError] = useState("");
  const set = (k: string) => (e: { target: { value: string } }) => setF((p) => ({ ...p, [k]: e.target.value }));

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const local: Record<string, string> = customFieldErrors(custom);
    const money: Record<string, number | null> = {};
    for (const k of MONEY) {
      const m = parseMoney(f[k], currency);
      if (m === "invalid") local[k] = moneyError(currency);
      else money[k] = m;
    }
    const adj = Number(f.odometer_adjustment || 0);
    if (!Number.isFinite(adj)) local.odometer_adjustment = "Enter a number";
    const year = blank(f.year);
    if (year !== null && !/^\d{4}$/.test(year)) local.year = "Enter a four digit year";
    if (Object.keys(local).length) return setErrs(local);

    const body = {
      name: f.name.trim(),
      year: year === null ? null : Number(year),
      make: blank(f.make),
      model: blank(f.model),
      plate: blank(f.plate),
      vin: blank(f.vin),
      engine_number: blank(f.engine_number),
      colour: blank(f.colour),
      fuel_type: blank(f.fuel_type) as VehicleIn["fuel_type"],
      distance_unit: blank(f.distance_unit) as VehicleIn["distance_unit"],
      purchase_date: blank(f.purchase_date),
      purchase_price: money.purchase_price,
      sold_date: blank(f.sold_date),
      sold_price: money.sold_price,
      odometer_adjustment: adj,
      custom_fields: pairsToObject(custom),
      archived: !!f.archived,
    } satisfies VehicleIn;
    setErrs({});
    setFormError("");
    save.mutate(
      { id, body },
      {
        onSuccess: (v) => nav(`/vehicles/${v.id}`),
        onError: (err) => {
          const mapped = err instanceof ApiError ? fieldErrors(err.detail) : {};
          setErrs(mapped);
          if (!Object.keys(mapped).length) setFormError(err.message);
        },
      },
    );
  }

  const text = (k: string, label: string, props: React.InputHTMLAttributes<HTMLInputElement> = {}, hint?: string) => (
    <Field label={label} error={errs[k]} hint={hint}>
      {(a) => <input {...a} {...props} value={f[k]} onChange={set(k)} />}
    </Field>
  );
  const money = (k: string, label: string) => (
    <MoneyInput label={label} currency={currency} value={f[k]} onChange={(v) => setF((p) => ({ ...p, [k]: v }))} error={errs[k]} />
  );
  const fuel = ["petrol", "diesel", "hybrid", "lpg"];

  return (
    <form className="vform" onSubmit={onSubmit} noValidate>
      <h1>{id ? "Edit vehicle" : "Add vehicle"}</h1>
      <Group title="Basics">
        {text("name", "Name", { required: true, maxLength: 120, autoFocus: !id })}
        {text("year", "Year", { inputMode: "numeric", maxLength: 4 })}
        {text("make", "Make")}
        {text("model", "Model")}
        {text("plate", "Plate")}
        <Field label="Fuel type" error={errs.fuel_type}>
          {(a) => (
            <select {...a} value={f.fuel_type} onChange={set("fuel_type")}>
              <option value="">Not set</option>
              {fuel.map((x) => (
                <option key={x} value={x}>
                  {x[0].toUpperCase() + x.slice(1)}
                </option>
              ))}
            </select>
          )}
        </Field>
      </Group>
      <Group title="Identity">
        {text("vin", "VIN")}
        {text("engine_number", "Engine number")}
        {text("colour", "Colour")}
      </Group>
      <Group title="Ownership">
        {text("purchase_date", "Purchase date", { type: "date" })}
        {money("purchase_price", "Purchase price")}
        {text("sold_date", "Sold date", { type: "date" })}
        {money("sold_price", "Sold price")}
      </Group>
      <Group title="Units">
        <Field label="Distance unit" error={errs.distance_unit} hint="Overrides the install default for this vehicle.">
          {(a) => (
            <select {...a} value={f.distance_unit} onChange={set("distance_unit")}>
              <option value="">Install default ({props.unit})</option>
              <option value="km">km</option>
              <option value="mi">mi</option>
            </select>
          )}
        </Field>
        {text("odometer_adjustment", "Odometer adjustment", { inputMode: "decimal" }, "Added to the highest recorded reading.")}
      </Group>
      <Group title="Custom fields">
        <CustomFields value={custom} onChange={setCustom} errs={errs} />
      </Group>
      {id && vehicle && (
        <Group title="Photo">
          <PhotoUpload vehicleId={id} hasPhoto={vehicle.photo_attachment_id !== null} />
        </Group>
      )}
      <label className="check">
        <input type="checkbox" checked={!!f.archived} onChange={(e) => setF((p) => ({ ...p, archived: e.target.checked ? "1" : "" }))} />
        Archived (hide from the garage list)
      </label>
      {formError && (
        <p className="error" role="alert">
          {formError}
        </p>
      )}
      <div className="actions">
        <button className="btn primary" disabled={save.isPending}>
          {save.isPending ? "Saving..." : "Save"}
        </button>
        <Link className="btn" to={id ? `/vehicles/${id}` : "/garage"}>
          Cancel
        </Link>
      </div>
      {id && (
        <ConfirmDelete
          label="Delete vehicle"
          question={`Delete ${vehicle?.name}? Its records and files will be deleted too. This can't be undone.`}
          pending={del.isPending}
          error={delError}
          onConfirm={() => del.mutate(id, { onSuccess: () => nav("/garage"), onError: (e) => setDelError(e.message) })}
        />
      )}
    </form>
  );
}
