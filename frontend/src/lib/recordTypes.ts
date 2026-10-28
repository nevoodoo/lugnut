import {
  BadgeAlert,
  ClipboardCheck,
  Fuel,
  Gauge,
  IdCard,
  ListTodo,
  Milestone,
  ShieldCheck,
  SquareParking,
  StickyNote,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { useRegions, useSettings, type LugnutRecord } from "../api/hooks";
import { formatVolume, type InstallSettings } from "./format";

export type RecordType = LugnutRecord["type"];
export type Details = Record<string, unknown>;

export interface DetailField {
  name: string;
  label: string;
  kind: "text" | "date" | "money" | "number" | "bool" | "select";
  options?: string[];
  required?: boolean; // a select with no "Not set" choice
  default?: string | boolean;
}

interface TypeDef {
  label: string;
  icon: LucideIcon;
  dated: boolean;
  fields: DetailField[];
  summary?: (d: Details, s: InstallSettings) => unknown; // what follows the label when there's no title
}

// Mirrors records/schemas.py. The record form renders from this table; add a field here, not a form.
export const RECORD_TYPES: Record<RecordType, TypeDef> = {
  work: {
    label: "Work done",
    icon: Wrench,
    dated: true,
    fields: [
      { name: "category", label: "Category", kind: "select", options: ["service", "repair", "upgrade"], required: true },
      { name: "workshop", label: "Workshop", kind: "text" },
      { name: "invoice_number", label: "Invoice number", kind: "text" },
    ],
    summary: (d) => d.workshop ?? d.category,
  },
  fuel: {
    label: "Fuel",
    icon: Fuel,
    dated: true,
    fields: [
      { name: "volume", label: "Volume", kind: "number" },
      { name: "full_tank", label: "Filled the tank", kind: "bool", default: true },
      { name: "missed_previous", label: "Missed the last fill", kind: "bool" },
    ],
    summary: (d, s) => formatVolume((d.volume as number) ?? null, s),
  },
  odometer: { label: "Odometer", icon: Gauge, dated: true, fields: [] },
  registration: {
    label: "Registration",
    icon: IdCard,
    dated: true,
    fields: [
      { name: "plate", label: "Plate", kind: "text" },
      { name: "expiry_date", label: "Expires", kind: "date" },
      { name: "period_months", label: "Period in months", kind: "number" },
    ],
  },
  insurance: {
    label: "Insurance",
    icon: ShieldCheck,
    dated: true,
    fields: [
      { name: "insurer", label: "Insurer", kind: "text" },
      { name: "policy_number", label: "Policy number", kind: "text" },
      { name: "start_date", label: "Starts", kind: "date" },
      { name: "expiry_date", label: "Expires", kind: "date" },
      { name: "excess", label: "Excess", kind: "money" },
      { name: "excess_notes", label: "Excess notes", kind: "text" },
    ],
    summary: (d) => d.insurer,
  },
  inspection: {
    label: "Inspection",
    icon: ClipboardCheck,
    dated: true,
    fields: [
      { name: "result", label: "Result", kind: "select", options: ["pass", "fail", "advisory"] },
      { name: "expiry_date", label: "Expires", kind: "date" },
      { name: "inspector", label: "Inspector", kind: "text" },
    ],
    summary: (d) => d.result,
  },
  toll: {
    label: "Toll",
    icon: Milestone,
    dated: true,
    fields: [{ name: "location", label: "Location", kind: "text" }],
    summary: (d) => d.location,
  },
  parking: {
    label: "Parking",
    icon: SquareParking,
    dated: true,
    fields: [{ name: "location", label: "Location", kind: "text" }],
    summary: (d) => d.location,
  },
  fine: {
    label: "Fine",
    icon: BadgeAlert,
    dated: true,
    fields: [
      { name: "offence", label: "Offence", kind: "text" },
      { name: "due_date", label: "Due", kind: "date" },
      { name: "paid", label: "Paid", kind: "bool" },
      { name: "reference", label: "Reference", kind: "text" },
    ],
    summary: (d) => d.offence,
  },
  todo: {
    label: "To do",
    icon: ListTodo,
    dated: false,
    fields: [
      { name: "priority", label: "Priority", kind: "select", options: ["low", "medium", "high"], required: true, default: "medium" },
      { name: "status", label: "Status", kind: "select", options: ["backlog", "in_progress", "done"], required: true },
      { name: "quoted", label: "Quoted", kind: "money" },
    ],
  },
  note: { label: "Note", icon: StickyNote, dated: false, fields: [{ name: "pinned", label: "Pinned", kind: "bool" }] },
};

export const TYPES = Object.keys(RECORD_TYPES) as RecordType[];
export const isRecordType = (t: string | null): t is RecordType => !!t && t in RECORD_TYPES;
export const optionLabel = (o: string) => (o[0].toUpperCase() + o.slice(1)).replace(/_/g, " ");

// Labels with the install region's names (Rego, MOT, ...) swapped in.
export function useTypeLabel(): (t: RecordType) => string {
  const region = useSettings().data?.region;
  const labels = useRegions().data?.find((r) => r.code === region)?.labels as Record<string, string> | undefined;
  return (t) => labels?.[t] ?? RECORD_TYPES[t].label;
}

// "Service, Cavalo" style: the title, else the type label and its most telling detail.
export function recordSummary(r: LugnutRecord, label: string, s: InstallSettings): string {
  if (r.title) return r.title;
  const extra = RECORD_TYPES[r.type].summary?.(r.details, s);
  return extra ? `${label}, ${typeof extra === "string" ? extra : String(extra)}` : label;
}
