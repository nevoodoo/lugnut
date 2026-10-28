import { Car, Plus } from "lucide-react";
import { Link } from "react-router";
import { useVehicles } from "../api/hooks";
import { EmptyState } from "../components/EmptyState";
import { Photo } from "../components/Photo";
import { PlateBadge } from "../components/PlateBadge";

const add = (
  <Link className="btn primary" to="/vehicles/new">
    <Plus size={18} aria-hidden="true" /> Add vehicle
  </Link>
);

export function Garage() {
  const { data, isPending, isError } = useVehicles();
  if (isPending) return null;
  if (isError) return <p className="error">Couldn't load your vehicles.</p>;
  if (!data.length)
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
      <ul className="garage-grid">
        {data.map((v) => (
          <li key={v.id}>
            <Link to={`/vehicles/${v.id}`} className="card garage-card">
              <Photo id={v.photo_attachment_id} />
              <div>
                <div className="label">{[v.year, v.make, v.model].filter(Boolean).join(" ")}</div>
                <strong>{v.name}</strong> <PlateBadge plate={v.plate} />
                {v.archived && <div className="label">Archived</div>}
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
