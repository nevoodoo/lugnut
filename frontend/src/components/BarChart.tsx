import type { components } from "../api/schema";
import { formatMoney } from "../lib/format";

type Month = components["schemas"]["MonthOut"];

const W = 360;
const H = 150;
const TOP = 8;
const BASE = H - 22;
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function monthName(ym: string): string {
  const [y, m] = ym.split("-");
  return `${MONTHS[Number(m) - 1] ?? m} ${y}`;
}

export function median(values: number[]): number {
  const s = [...values].sort((a, b) => a - b);
  const mid = s.length >> 1;
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

// One bar per month. Bars over 1.5x the median non-zero month are rust, the rest ink.
export function BarChart({ months, currency }: { months: Month[]; currency: string }) {
  const money = { currency };
  const max = Math.max(...months.map((m) => m.total), 1);
  const typical = median(months.map((m) => m.total).filter((t) => t > 0));
  const slot = W / Math.max(months.length, 1);
  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Monthly running costs for the last 24 months. The table below has the figures.">
        <line x1="0" x2={W} y1={BASE} y2={BASE} className="chart-axis" />
        {months.map((m, i) => {
          const h = (m.total / max) * (BASE - TOP);
          const high = typical > 0 && m.total > typical * 1.5;
          return (
            <g key={m.month}>
              {m.total > 0 && (
                <rect x={i * slot + slot * 0.15} y={BASE - h} width={slot * 0.7} height={h} className={high ? "bar high" : "bar"} />
              )}
              {i % 6 === 0 && (
                <text x={i * slot + slot * 0.15} y={H - 5} className="chart-text">
                  {monthName(m.month).replace(/ 20/, " '")}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      <figcaption className="muted">Rust bars are more than 1.5 times a typical month.</figcaption>
      <table className="visually-hidden">
        <caption>Running costs by month</caption>
        <thead>
          <tr>
            <th scope="col">Month</th>
            <th scope="col">Total</th>
          </tr>
        </thead>
        <tbody>
          {months.map((m) => (
            <tr key={m.month}>
              <th scope="row">{monthName(m.month)}</th>
              <td>{formatMoney(m.total, money)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
