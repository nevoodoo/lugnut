import type { components } from "../api/schema";
import { formatDate, formatEconomy, type InstallSettings } from "../lib/format";

type Segment = components["schemas"]["SegmentOut"];

const W = 360;
const H = 150;
const LEFT = 34;
const TOP = 12;
const BASE = H - 14;

// One dot per tank on a line. Outliers are hollow rust rings.
export function EconomyChart({ segments, unit, s }: { segments: Segment[]; unit: string; s: Pick<InstallSettings, "date_format"> }) {
  const values = segments.map((g) => g.value);
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const pad = (hi - lo || 1) * 0.15;
  const y = (v: number) => TOP + ((hi + pad - v) / (hi - lo + 2 * pad)) * (BASE - TOP);
  const x = (i: number) => (segments.length < 2 ? (LEFT + W) / 2 : LEFT + 6 + (i / (segments.length - 1)) * (W - LEFT - 12));
  const points = segments.map((g, i) => `${x(i)},${y(g.value)}`).join(" ");
  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Fuel economy per tank in ${unit}. The table below has the figures.`}>
        <line x1={LEFT} x2={W} y1={BASE} y2={BASE} className="chart-axis" />
        <text x="0" y={y(hi) + 4} className="chart-text">{hi.toFixed(1)}</text>
        <text x="0" y={y(lo) + 4} className="chart-text">{lo.toFixed(1)}</text>
        <polyline points={points} className="econ-line" />
        {segments.map((g, i) => (
          <circle key={i} cx={x(i)} cy={y(g.value)} r={g.outlier ? 5 : 3.5} className={g.outlier ? "dot out" : "dot"} />
        ))}
      </svg>
      <figcaption className="muted">Hollow rust rings are tanks that look off, such as a missed fill.</figcaption>
      <table className="visually-hidden">
        <caption>Fuel economy per tank</caption>
        <thead>
          <tr>
            <th scope="col">Date</th>
            <th scope="col">Economy</th>
            <th scope="col">Note</th>
          </tr>
        </thead>
        <tbody>
          {segments.map((g, i) => (
            <tr key={i}>
              <th scope="row">{formatDate(g.date, s) || `Tank ${i + 1}`}</th>
              <td>{formatEconomy(g.value, unit)}</td>
              <td>{g.outlier ? "Outlier" : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
