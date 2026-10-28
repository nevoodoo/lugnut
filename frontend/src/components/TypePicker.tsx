import { Link } from "react-router";
import { RECORD_TYPES, TYPES, useTypeLabel } from "../lib/recordTypes";

// One tile per record type. Fuel goes to the quick fuel screen; the rest to the record form.
export function TypePicker({ vehicleId, onPick }: { vehicleId: number; onPick?: () => void }) {
  const label = useTypeLabel();
  return (
    <ul className="type-grid">
      {TYPES.map((t) => {
        const Icon = RECORD_TYPES[t].icon;
        const to = t === "fuel" ? `/vehicles/${vehicleId}/fuel` : `/vehicles/${vehicleId}/records/new?type=${t}`;
        return (
          <li key={t}>
            <Link className="type-tile" to={to} onClick={onPick}>
              <Icon size={22} aria-hidden="true" />
              {label(t)}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
