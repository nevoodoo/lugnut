import { Car, Plus } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router";
import { useVehicles, type Vehicle } from "../api/hooks";
import { EmptyState } from "../components/EmptyState";
import { Photo } from "../components/Photo";
import { PlateBadge } from "../components/PlateBadge";

const add = (
  <Link className="btn primary" to="/vehicles/new">
    <Plus size={18} aria-hidden="true" /> Add vehicle
  </Link>
);

function Grid({ vehicles }: { vehicles: Vehicle[] }) {
  return (
    <ul className="garage-grid">
      {vehicles.map((v) => (
        <li key={v.id}>
          <Link to={`/vehicles/${v.id}`} className="card garage-card">
            <Photo id={v.photo_attachment_id} />
            <div>
              <div className="label">{[v.year, v.make, v.model].filter(Boolean).join(" ")}</div>
              <strong>{v.name}</strong> <PlateBadge plate={v.plate} />
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}

export function Garage() {
  const [showArchived, setShowArchived] = useState(false);
  const { data, isPending, isError } = useVehicles();
  const archived = useVehicles(true);
  if (isPending) return null;
  if (isError) return <p className="error">Couldn't load your vehicles.</p>;
  const hasArchived = !!archived.data?.length;
  if (!data.length && !hasArchived)
    return (
      <EmptyState icon={Car} title="Your garage is empty" action={add}>
        Add a vehicle to start tracking.
      </EmptyState>
    );
  return (
    <>
      <div className="page-head">
        <h1>Garage</h1>
        {add}
      </div>
      {data.length ? <Grid vehicles={data} /> : <p className="muted">All your vehicles are archived.</p>}
      {hasArchived && (
        <label className="check">
          <input type="checkbox" checked={showArchived} onChange={(e) => setShowArchived(e.target.checked)} />
          Show archived
        </label>
      )}
      {hasArchived && showArchived && (
        <section aria-labelledby="archived-h">
          <h2 id="archived-h" className="label">
            Archived
          </h2>
          <Grid vehicles={archived.data!} />
        </section>
      )}
    </>
  );
}
