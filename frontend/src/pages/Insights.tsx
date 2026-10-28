import { ArrowDownRight, ArrowUpRight, ChartNoAxesColumn } from "lucide-react";
import type { ReactNode } from "react";
import { Link, Navigate, useParams } from "react-router";
import { ApiError } from "../api/client";
import { useInsights, useSettings, useVehicle, type Insights as InsightsData } from "../api/hooks";
import { BarChart } from "../components/BarChart";
import { Card } from "../components/Card";
import { EconomyChart } from "../components/EconomyChart";
import { formatDate, formatDistance, formatEconomy, formatMoney, type InstallSettings } from "../lib/format";

type Summary = InsightsData["this_year"];
type Money = Pick<InstallSettings, "currency">;
type Dates = Pick<InstallSettings, "date_format">;

const cap = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);

function perDistance(v: number | null, m: Money, unit: string): string {
  return v === null ? "" : `${formatMoney(Math.round(v), m)}/${unit}`;
}

function Muted({ children }: { children: ReactNode }) {
  return <p className="muted ins-note">{children}</p>;
}

function CostColumn({ title, c, m, unit }: { title: string; c: Summary; m: Money; unit: string }) {
  const cats = Object.entries(c.by_category).sort((a, b) => b[1] - a[1]);
  return (
    <div className="ins-col">
      <h3 className="label">{title}</h3>
      <p className="stat mono">{formatMoney(c.total, m)}</p>
      {c.per_distance !== null && <p className="mono ins-sub">{perDistance(c.per_distance, m, unit)}</p>}
      {c.missing.includes("no_costs") && <Muted>No costs recorded yet.</Muted>}
      {c.missing.includes("not_enough_readings") && <Muted>Add at least two odometer readings to see cost per {unit}.</Muted>}
      <ul className="rows">
        {cats.map(([name, amount]) => (
          <li key={name} className="row">
            <span>{cap(name)}</span>
            <span className="mono">{formatMoney(amount, m)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Running({ d, m }: { d: InsightsData; m: Money }) {
  return (
    <Card label="Running costs">
      <div className="ins-cols">
        <CostColumn title="This year" c={d.this_year} m={m} unit={d.distance_unit} />
        <CostColumn title="All time" c={d.all_time} m={m} unit={d.distance_unit} />
      </div>
      {d.monthly.some((x) => x.total > 0) && <BarChart months={d.monthly} currency={d.currency} />}
    </Card>
  );
}

function Ownership({ d, m, vehicleId }: { d: InsightsData; m: Money; vehicleId: number }) {
  const o = d.ownership;
  const sub = [o.per_month !== null && `${formatMoney(o.per_month, m)}/month`, o.per_distance !== null && perDistance(o.per_distance, m, d.distance_unit)]
    .filter(Boolean)
    .join(" · ");
  return (
    <Card label="Cost of ownership">
      {o.total !== null && (
        <>
          <p className="stat mono">{formatMoney(o.total, m)}</p>
          {sub && <p className="mono ins-sub">{sub}</p>}
          <ul className="rows">
            {o.purchase_price !== null && (
              <li className="row">
                <span>Purchase price</span>
                <span className="mono">{formatMoney(o.purchase_price, m)}</span>
              </li>
            )}
            <li className="row">
              <span>Running costs</span>
              <span className="mono">{formatMoney(o.running, m)}</span>
            </li>
            {o.sold_price !== null && (
              <li className="row">
                <span>Sale price</span>
                <span className="mono">&minus;{formatMoney(o.sold_price, m)}</span>
              </li>
            )}
          </ul>
        </>
      )}
      {o.missing.includes("no_purchase_price") && (
        <Muted>
          Add the purchase price on the vehicle to see the total cost of ownership.{" "}
          <Link className="ins-link" to={`/vehicles/${vehicleId}/edit`}>
            Edit vehicle
          </Link>
        </Muted>
      )}
      {o.missing.includes("not_enough_readings") && <Muted>Add at least two odometer readings to see cost per {d.distance_unit}.</Muted>}
    </Card>
  );
}

function Upcoming({ d, m, s }: { d: InsightsData; m: Money; s: Dates }) {
  const byId = new Map(d.upcoming.map((u) => [u.id, u]));
  const grouped = new Set(d.groups.flat());
  const row = (u: InsightsData["upcoming"][number]) => (
    <li key={u.id} className="row ins-up">
      <span>
        <Link to={`/reminders/${u.id}`}>{u.title}</Link>
        <span className="muted ins-sub-line">{u.last_cost !== null ? `Last time: ${formatMoney(u.last_cost, m)}` : "No past cost found"}</span>
      </span>
      <span className="mono">{u.projected_date ? formatDate(u.projected_date, s) : "No date yet"}</span>
    </li>
  );
  return (
    <Card label="Coming up">
      {d.groups.map((g) => {
        const items = g.flatMap((id) => byId.get(id) ?? []);
        const known = items.reduce((sum, u) => sum + (u.last_cost ?? 0), 0);
        return (
          <div key={g.join("-")} className="ins-group">
            <p>These are due within a month of each other. Doing them in one visit could save a trip.</p>
            <ul className="rows">{items.map(row)}</ul>
            {known > 0 && <p className="mono ins-sub">Known costs: {formatMoney(known, m)}</p>}
          </div>
        );
      })}
      <ul className="rows">{d.upcoming.filter((u) => !grouped.has(u.id)).map(row)}</ul>
      {d.upcoming.length === 0 && <Muted>No reminders to plan around.</Muted>}
    </Card>
  );
}

function Economy({ d, s }: { d: InsightsData; s: Dates }) {
  const e = d.economy;
  const pct = e.change_pct;
  const good = pct !== null && pct !== 0 && (pct < 0) === d.lower_is_better;
  const Arrow = pct !== null && pct < 0 ? ArrowDownRight : ArrowUpRight;
  return (
    <Card label="Fuel economy">
      {e.average !== null && (
        <div className="ins-cols">
          <div className="ins-col">
            <h3 className="label">Average</h3>
            <p className="stat mono">{formatEconomy(e.average, d.economy_unit)}</p>
          </div>
          {e.recent !== null && (
            <div className="ins-col">
              <h3 className="label">Recent</h3>
              <p className="stat mono">{formatEconomy(e.recent, d.economy_unit)}</p>
              {pct !== null && (
                <p className={`mono ins-change${pct === 0 ? "" : good ? " good" : " bad"}`}>
                  <Arrow size={18} aria-hidden="true" />
                  {pct > 0 ? "+" : ""}
                  {pct.toFixed(1)}% vs average
                </p>
              )}
            </div>
          )}
        </div>
      )}
      {e.segments.length > 0 && <EconomyChart segments={e.segments} unit={d.economy_unit} s={s} />}
      {e.skipped > 0 && (
        <Muted>
          {e.skipped} {e.skipped === 1 ? "fill was" : "fills were"} skipped because of missed fills, missing odometer readings or readings that went backwards.
        </Muted>
      )}
      {e.missing.includes("no_fuel") && <Muted>No fuel records yet.</Muted>}
      {e.missing.includes("not_enough_full_fills") && <Muted>Fuel economy needs two full tanks with odometer readings.</Muted>}
    </Card>
  );
}

function every(j: InsightsData["repeat_jobs"][number], unit: "km" | "mi"): string {
  const parts = [
    j.avg_distance !== null && formatDistance(j.avg_distance >= 1000 ? Math.round(j.avg_distance / 100) * 100 : Math.round(j.avg_distance), unit),
    j.avg_days !== null && (j.avg_days < 45 ? `${Math.round(j.avg_days)} days` : `${Math.round(j.avg_days / 30.4)} months`),
  ].filter(Boolean);
  return parts.length ? `every ${parts.join(" or ")}` : "";
}

function Repeats({ d, m, s }: { d: InsightsData; m: Money; s: Dates }) {
  if (d.repeat_jobs.length === 0) return null;
  const unit = d.distance_unit;
  return (
    <Card label="Repeat jobs">
      <div className="table-wrap">
        <table className="ins-table">
          <thead>
            <tr>
              <th scope="col">Job</th>
              <th scope="col">Done</th>
              <th scope="col">Typical interval</th>
              <th scope="col">Typical cost</th>
              <th scope="col">Next expected</th>
            </tr>
          </thead>
          <tbody>
            {d.repeat_jobs.map((j) => {
              const next = [j.next_date && formatDate(j.next_date, s), j.next_odometer !== null && formatDistance(Math.round(j.next_odometer), unit)]
                .filter(Boolean)
                .join(" or ");
              return (
                <tr key={j.name}>
                  <th scope="row">{j.name}</th>
                  <td className="mono">{j.count}&times;</td>
                  <td>{every(j, unit) || "Not enough history"}</td>
                  <td className="mono">{j.avg_cost !== null ? formatMoney(j.avg_cost, m) : ""}</td>
                  <td className="mono">{next || "Not enough history"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

export function Insights() {
  const id = Number(useParams().id);
  const vehicle = useVehicle(id);
  const insights = useInsights(id);
  const settings = useSettings();
  if (vehicle.error instanceof ApiError && vehicle.error.status === 404) return <Navigate to="/garage" replace />;
  if (vehicle.isError || insights.isError || settings.isError) return <p className="error">Couldn't load the insights.</p>;
  const d = insights.data;
  const s = settings.data;
  if (!d || !s || !vehicle.data) return null;
  const m = { currency: d.currency };
  return (
    <div className="ins">
      <div className="page-head">
        <h1 className="ins-title">
          <ChartNoAxesColumn size={24} aria-hidden="true" /> Insights
        </h1>
        <span className="label">{vehicle.data.name}</span>
      </div>
      <div className="ins-cards">
        <div className="ins-wide">
          <Running d={d} m={m} />
        </div>
        <Ownership d={d} m={m} vehicleId={id} />
        <Upcoming d={d} m={m} s={s} />
        <Economy d={d} s={s} />
        <div className="ins-wide">
          <Repeats d={d} m={m} s={s} />
        </div>
      </div>
    </div>
  );
}
