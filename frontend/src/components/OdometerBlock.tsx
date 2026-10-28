import { formatDistance } from "../lib/format";

export function OdometerBlock({ value, unit }: { value: number | null; unit: "km" | "mi" }) {
  return value === null ? (
    <div className="odo none">No odometer yet</div>
  ) : (
    <div className="odo mono" aria-label={`Odometer ${formatDistance(value, unit)}`}>
      {formatDistance(value, unit)}
    </div>
  );
}
