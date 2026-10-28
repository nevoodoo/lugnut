import { ArrowDownRight, ArrowUpRight, FileText, Fuel, Gauge, Pencil, Receipt } from "lucide-react";
import { useEffect } from "react";
import { Link, Navigate, useParams } from "react-router";
import { useInsights, useReminders, useRecords, useSettings, useVehicle } from "../api/hooks";
import { ApiError } from "../api/client";
import { Card } from "../components/Card";
import { OdometerBlock } from "../components/OdometerBlock";
import { Photo } from "../components/Photo";
import { PhotoUpload } from "../components/PhotoUpload";
import { PlateBadge } from "../components/PlateBadge";
import { RecordRows } from "../components/RecordRows";
import { ReminderRow } from "../components/ReminderRow";
import { formatDate, formatEconomy, perDistance, type InstallSettings } from "../lib/format";
import { setLastVehicle } from "../lib/lastVehicle";

function Due({ vehicleId, s }: { vehicleId: number; s: InstallSettings }) {
  const { data } = useReminders({ vehicle_id: vehicleId });
  if (!data?.length) return null;
  return (
    <Card label="Coming up">
      <ul className="rows">
        {data.map((r) => (
          <ReminderRow key={r.id} r={r} s={s} />
        ))}
      </ul>
      <Link className="link-tap" to={`/vehicles/${vehicleId}/reminders/new`}>Add a reminder</Link>
    </Card>
  );
}

function Stats({ vehicleId }: { vehicleId: number }) {
  const { data: d } = useInsights(vehicleId);
  if (!d) return null;
  const m = { currency: d.currency };
  const pct = d.economy.change_pct;
  const good = pct !== null && pct !== 0 && (pct < 0) === d.lower_is_better;
  const Arrow = pct !== null && pct < 0 ? ArrowDownRight : ArrowUpRight;
  const na = (t: string) => t || "n/a";
  return (
    <Card label="Stats">
      <ul className="rows">
        <li className="row">
          <span>Fuel average</span>
          <span className="mono">
            {na(formatEconomy(d.economy.average, d.economy_unit))}
            {pct !== null && (
              <span className={`ins-change${pct === 0 ? "" : good ? " good" : " bad"}`}>
                <Arrow size={16} aria-hidden="true" />
                {pct > 0 ? "+" : ""}
                {pct.toFixed(1)}%
              </span>
            )}
          </span>
        </li>
        <li className="row">
          <span>Cost this year</span>
          <span className="mono">{na(perDistance(d.this_year.per_distance, m, d.distance_unit))}</span>
        </li>
        <li className="row">
          <span>Cost since purchase</span>
          <span className="mono">{na(perDistance(d.all_time.per_distance, m, d.distance_unit))}</span>
        </li>
      </ul>
      <Link className="link-tap" to={`/vehicles/${vehicleId}/insights`}>See insights</Link>
    </Card>
  );
}

function Recent({ vehicleId, unit }: { vehicleId: number; unit: "km" | "mi" }) {
  const { data } = useRecords(vehicleId, { limit: 5 });
  if (!data?.length) return null;
  return (
    <section className="card recent">
      <div className="page-head">
        <h2 className="label">Recent records</h2>
        <Link className="link-tap" to={`/vehicles/${vehicleId}/records`}>All records</Link>
      </div>
      <RecordRows records={data} unit={unit} />
    </section>
  );
}

// Shown only when the vehicle has neither records nor reminders.
function Empty({ vehicleId }: { vehicleId: number }) {
  const records = useRecords(vehicleId, { limit: 5 });
  const reminders = useReminders({ vehicle_id: vehicleId });
  if (!records.data || !reminders.data || records.data.length || reminders.data.length) return null;
  return <p className="muted">Nothing logged yet. Log fuel or add a record.</p>;
}

export function VehicleHome() {
  const id = Number(useParams().id);
  const vehicle = useVehicle(id);
  const settings = useSettings();
  useEffect(() => {
    if (vehicle.data) setLastVehicle(id);
  }, [id, vehicle.data]);

  if (vehicle.error instanceof ApiError && vehicle.error.status === 404) return <Navigate to="/garage" replace />;
  if (vehicle.isError || settings.isError) return <p className="error">Couldn't load this vehicle.</p>;
  const v = vehicle.data;
  const s = settings.data;
  if (!v || !s) return null;

  const unit = v.distance_unit_effective;
  const subtitle = [v.year, [v.make, v.model].filter(Boolean).join(" "), v.fuel_type].filter(Boolean).join(" · ");
  const hasPhoto = v.photo_attachment_id !== null;
  const caption = v.purchase_date ? `Bought ${formatDate(v.purchase_date, s)}` : "";

  return (
    <div className="vh">
      <div className="vh-top">
        <figure className={`vh-photo${hasPhoto ? " has-photo" : ""}`}>
          <Photo id={v.photo_attachment_id} alt={`Photo of ${v.name}`} />
          <div className="vh-overlay" aria-hidden="true">
            <div>
              <div className="label">{subtitle}</div>
              <div className="vh-name">{v.name}</div>
            </div>
            <PlateBadge plate={v.plate} />
          </div>
          {caption && <figcaption>{caption}</figcaption>}
        </figure>
        <div className="vh-info">
          <div className={hasPhoto ? "vh-title hide-narrow" : "vh-title"}>
            <div className="label">{subtitle}</div>
            <h1>{v.name}</h1>
            <PlateBadge plate={v.plate} />
          </div>
          <OdometerBlock value={v.current_odometer} unit={unit} />
          <div className="actions">
            <Link className="btn primary" to={`/vehicles/${id}/fuel`}>
              <Fuel size={18} aria-hidden="true" /> Log fuel
            </Link>
            <Link className="btn" to={`/vehicles/${id}/records/new?type=odometer`}>
              <Gauge size={18} aria-hidden="true" /> Odometer
            </Link>
            <Link className="btn" to={`/vehicles/${id}/records/new?type=toll`}>
              <Receipt size={18} aria-hidden="true" /> Expense
            </Link>
            <Link className="btn" to={`/vehicles/${id}/edit`}>
              <Pencil size={18} aria-hidden="true" /> Edit
            </Link>
            <Link className="btn" to={`/documents?vehicle=${id}`}>
              <FileText size={18} aria-hidden="true" /> Documents
            </Link>
            <PhotoUpload vehicleId={id} hasPhoto={hasPhoto} />
          </div>
        </div>
      </div>
      <div className="vh-cards">
        <Due vehicleId={id} s={s} />
        <Stats vehicleId={id} />
        <Recent vehicleId={id} unit={unit} />
        <Empty vehicleId={id} />
      </div>
    </div>
  );
}
