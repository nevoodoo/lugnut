import type { components } from "../api/schema";

export type InstallSettings = components["schemas"]["SettingsOut"];
type Unit = InstallSettings["distance_unit"] | InstallSettings["volume_unit"];

const UNIT_LABELS: Record<Unit, string> = { km: "km", mi: "mi", L: "L", gal_us: "gal", gal_imp: "gal (UK)" };
export const unitLabel = (unit: Unit): string => UNIT_LABELS[unit];

// Money is integer minor units with two decimals, in every currency the API serves.
export function formatMoney(minor: number | null, s: Pick<InstallSettings, "currency">): string {
  if (minor === null) return "";
  return new Intl.NumberFormat(undefined, { style: "currency", currency: s.currency }).format(minor / 100);
}

// Decimal text from a form field to minor units. Empty is "no value", anything odd is "invalid".
export function parseMoney(text: string): number | null | "invalid" {
  const t = text.trim();
  if (t === "") return null;
  const m = /^[^\d\s,.-]?\s*(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?$/.exec(t);
  if (!m) return "invalid";
  return Number(m[1].replace(/,/g, "")) * 100 + Number((m[2] ?? "").padEnd(2, "0"));
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
