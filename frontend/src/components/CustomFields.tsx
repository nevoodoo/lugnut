import { Plus, Trash2 } from "lucide-react";
import { Field } from "./Field";

export type Pairs = [string, string][];

// Blank or repeated names, keyed custom.<i> like the editor below expects.
export function customFieldErrors(pairs: Pairs): Record<string, string> {
  const out: Record<string, string> = {};
  const seen = new Set<string>();
  pairs.forEach(([k], i) => {
    const name = k.trim();
    if (!name) out[`custom.${i}`] = "Give this field a name or remove it";
    else if (seen.has(name)) out[`custom.${i}`] = "Another field already has this name";
    seen.add(name);
  });
  return out;
}

export const pairsToObject = (pairs: Pairs) => Object.fromEntries(pairs.map(([k, v]) => [k.trim(), v]));

export function CustomFields({ value, onChange, errs }: { value: Pairs; onChange: (p: Pairs) => void; errs: Record<string, string> }) {
  const edit = (i: number, j: 0 | 1, text: string) =>
    onChange(value.map((p, n) => (n === i ? (j ? [p[0], text] : [text, p[1]]) : p)));
  return (
    <>
      {value.map(([k, v], i) => (
        <div key={i} className="kv">
          <Field label="Name" error={errs[`custom.${i}`] ?? errs[`custom_fields.${k}`]}>
            {(a) => <input {...a} value={k} onChange={(e) => edit(i, 0, e.target.value)} />}
          </Field>
          <Field label="Value">{(a) => <input {...a} value={v} onChange={(e) => edit(i, 1, e.target.value)} />}</Field>
          <button type="button" className="icon-btn" aria-label={`Remove field ${k || i + 1}`} onClick={() => onChange(value.filter((_, n) => n !== i))}>
            <Trash2 size={18} aria-hidden="true" />
          </button>
        </div>
      ))}
      <button type="button" className="btn" onClick={() => onChange([...value, ["", ""]])}>
        <Plus size={18} aria-hidden="true" /> Add field
      </button>
    </>
  );
}
