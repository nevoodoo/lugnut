import { Plus, Receipt } from "lucide-react";
import { Link, Navigate, useParams, useSearchParams } from "react-router";
import { ApiError } from "../api/client";
import { useRecords, useVehicle, type LugnutRecord } from "../api/hooks";
import { EmptyState } from "../components/EmptyState";
import { RecordRows } from "../components/RecordRows";
import { isRecordType, TYPES, useTypeLabel } from "../lib/recordTypes";

const monthName = (ym: string) =>
  new Intl.DateTimeFormat(undefined, { month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(`${ym}-01`));

// Newest first from the API; undated to-dos and notes come last.
function byMonth(records: LugnutRecord[]): [string, LugnutRecord[]][] {
  const groups = new Map<string, LugnutRecord[]>();
  for (const r of records) {
    const k = r.date ? r.date.slice(0, 7) : "";
    groups.set(k, [...(groups.get(k) ?? []), r]);
  }
  return [...groups];
}

export function Records() {
  const id = Number(useParams().id);
  const [search] = useSearchParams();
  const raw = search.get("type");
  const type = isRecordType(raw) ? raw : undefined;
  const vehicle = useVehicle(id);
  // ponytail: the first 500 only; add "Load more" with offset when a vehicle outgrows it.
  const records = useRecords(id, { type, limit: 500 });
  const label = useTypeLabel();

  if (vehicle.error instanceof ApiError && vehicle.error.status === 404) return <Navigate to="/garage" replace />;
  if (vehicle.isError || records.isError) return <p className="error">Couldn't load records.</p>;
  if (!vehicle.data || !records.data) return null;
  const v = vehicle.data;
  const chip = (t: string | undefined, text: string) => (
    <li key={t ?? "all"}>
      <Link className="chip" to={t ? `?type=${t}` : "."} aria-current={type === t ? "page" : undefined}>
        {text}
      </Link>
    </li>
  );

  return (
    <div className="records">
      <div className="page-head">
        <div>
          <div className="label">{v.name}</div>
          <h1>Records</h1>
        </div>
        <Link className="btn primary" to={`/vehicles/${id}/records/new`}>
          <Plus size={18} aria-hidden="true" /> Add record
        </Link>
      </div>
      <nav aria-label="Filter by type">
        <ul className="chips">
          {chip(undefined, "All")}
          {TYPES.map((t) => chip(t, label(t)))}
        </ul>
      </nav>
      {records.data.length === 0 ? (
        <EmptyState icon={Receipt} title={type ? `No ${label(type).toLowerCase()} records` : "No records yet"}>
          Fuel, services, rego and the rest end up here.
        </EmptyState>
      ) : (
        byMonth(records.data).map(([ym, rs]) => (
          <section key={ym} className="card month">
            <h2 className="label">{ym ? monthName(ym) : "No date"}</h2>
            <RecordRows records={rs} unit={v.distance_unit_effective} />
          </section>
        ))
      )}
    </div>
  );
}
