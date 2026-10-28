import { Link } from "react-router";
import { useSettings, type LugnutRecord } from "../api/hooks";
import { formatDate, formatDistance, formatMoney } from "../lib/format";
import { recordSummary, useTypeLabel } from "../lib/recordTypes";

// The logbook table: date, what it was with its type tag, odometer, cost. Each row opens the record.
export function RecordRows({ records, unit }: { records: LugnutRecord[]; unit: "km" | "mi" }) {
  const s = useSettings().data;
  const label = useTypeLabel();
  if (!s) return null;
  return (
    <ul className="recs">
      <li className="rec rec-head" aria-hidden="true">
        <span>Date</span>
        <span>Record</span>
        <span>Odometer</span>
        <span className="rec-cost">Cost</span>
      </li>
      {records.map((r) => {
        const type = label(r.type);
        const summary = recordSummary(r, type, s);
        return (
          <li key={r.id}>
            <Link className="rec" to={`/records/${r.id}`}>
              <span className="rec-date mono">{formatDate(r.date ?? null, s)}</span>
              <span className="rec-title">
                {summary} {!summary.startsWith(type) && <span className="tag">{type}</span>}
                {r.is_estimate && <span className="stamp mono">est.</span>}
              </span>
              <span className="rec-odo mono">{r.odometer == null ? "n/a" : formatDistance(r.odometer, unit)}</span>
              <span className="rec-cost mono">{formatMoney(r.cost ?? null, s)}</span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
