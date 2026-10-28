import type { components } from "../api/schema";

export type InstallSettings = components["schemas"]["SettingsOut"];
type Unit = InstallSettings["distance_unit"] | InstallSettings["volume_unit"];

const UNIT_LABELS: Record<Unit, string> = { km: "km", mi: "mi", L: "L", gal_us: "gal", gal_imp: "gal (UK)" };
export const unitLabel = (unit: Unit): string => UNIT_LABELS[unit];

// Money is integer minor units; the decimal places follow the currency (JPY 0, AUD 2).
const currencyDigits = (currency: string): number =>
  new Intl.NumberFormat(undefined, { style: "currency", currency }).resolvedOptions().maximumFractionDigits ?? 2;

export function formatMoney(minor: number | null, s: Pick<InstallSettings, "currency">): string {
  if (minor === null) return "";
  const d = currencyDigits(s.currency);
  return new Intl.NumberFormat(undefined, { style: "currency", currency: s.currency }).format(minor / 10 ** d);
}

// Decimal text from a form field to minor units. Empty is "no value", anything odd is "invalid".
export function parseMoney(text: string, currency: string): number | null | "invalid" {
  const t = text.trim();
  if (t === "") return null;
  const d = currencyDigits(currency);
  const frac = d ? `(?:\\.(\\d{1,${d}}))?` : "()";
  const m = new RegExp(`^[^\\d\\s,.-]?\\s*(\\d{1,3}(?:,\\d{3})+|\\d+)${frac}$`).exec(t);
  if (!m) return "invalid";
  return Number(m[1].replace(/,/g, "")) * 10 ** d + Number((m[2] ?? "").padEnd(d, "0") || 0);
}

export function formatDate(iso: string | null, s: Pick<InstallSettings, "date_format">): string {
  if (!iso) return "";
  const [YYYY, MM, DD] = iso.split("-");
  return s.date_format.replace("YYYY", YYYY).replace("MM", MM).replace("DD", DD);
}

const digits = (n: number, max: number) =>
  new Intl.NumberFormat(undefined, { maximumFractionDigits: max }).format(n);

// Whole numbers drop the decimal; Intl does that for us at maximumFractionDigits: 1.
export function formatDistance(n: number | null, unit: "km" | "mi"): string {
  return n === null ? "" : `${digits(n, 1)} ${unit}`;
}

export function formatVolume(n: number | null, s: Pick<InstallSettings, "volume_unit">): string {
  return n === null ? "" : `${digits(n, 2)} ${unitLabel(s.volume_unit)}`;
}
