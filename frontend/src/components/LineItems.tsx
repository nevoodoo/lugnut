import { ArrowDown, ArrowUp, Plus, Trash2 } from "lucide-react";
import { formatMoney } from "../lib/format";
import { Field } from "./Field";
import { JobTypePicker } from "./JobTypePicker";
import { MoneyInput } from "./MoneyInput";
import { NumberInput } from "./NumberInput";

export interface Item {
  key: number; // stable React key; the server's id for saved rows
  job_type_id: number | null;
  unmatched?: boolean; // job type text typed that isn't a known type
  description: string;
  cost: string;
  quantity: string;
}

let next = -1;
export const blankItem = (): Item => ({ key: next--, job_type_id: null, description: "", cost: "", quantity: "" });

export function LineItems(props: {
  items: Item[];
  onChange: (items: Item[]) => void;
  currency: string;
  total: number;
  errs: Record<string, string>;
}) {
  const { items, onChange, currency, errs } = props;
  const edit = (i: number, patch: Partial<Item>) => onChange(items.map((it, n) => (n === i ? { ...it, ...patch } : it)));
  const move = (i: number, by: number) => {
    const out = [...items];
    [out[i], out[i + by]] = [out[i + by], out[i]];
    onChange(out);
  };
  const e = (i: number, k: string) => errs[`details.line_items.${i}.${k}`];

  return (
    <div className="line-items">
      <h3 className="label">Line items</h3>
      <ol>
        {items.map((it, i) => (
          <li key={it.key} className="line-item" aria-label={`Line item ${i + 1}`}>
            <JobTypePicker value={it.job_type_id} onChange={(id, unmatched) => edit(i, { job_type_id: id, unmatched })} error={e(i, "job_type_id")} />
            <div className="li-desc">
              <Field label="Description" error={e(i, "description")}>
                {(a) => <input {...a} value={it.description} onChange={(ev) => edit(i, { description: ev.target.value })} />}
              </Field>
            </div>
            <div className="li-cost">
              <MoneyInput label="Cost each" currency={currency} value={it.cost} onChange={(v) => edit(i, { cost: v })} error={e(i, "cost")} />
            </div>
            <div className="li-qty">
              <NumberInput label="Qty" value={it.quantity} onChange={(v) => edit(i, { quantity: v })} error={e(i, "quantity")} hint="Blank is 1" />
            </div>
            <div className="li-actions">
              <button type="button" className="icon-btn" aria-label={`Move line ${i + 1} up`} disabled={i === 0} onClick={() => move(i, -1)}>
                <ArrowUp size={18} aria-hidden="true" />
              </button>
              <button type="button" className="icon-btn" aria-label={`Move line ${i + 1} down`} disabled={i === items.length - 1} onClick={() => move(i, 1)}>
                <ArrowDown size={18} aria-hidden="true" />
              </button>
              <button type="button" className="icon-btn" aria-label={`Remove line ${i + 1}`} onClick={() => onChange(items.filter((_, n) => n !== i))}>
                <Trash2 size={18} aria-hidden="true" />
              </button>
            </div>
          </li>
        ))}
      </ol>
      <div className="li-foot">
        <button type="button" className="btn" onClick={() => onChange([...items, blankItem()])}>
          <Plus size={18} aria-hidden="true" /> Add line
        </button>
        <span aria-live="polite">
          Total <b className="mono">{formatMoney(props.total, { currency })}</b>
        </span>
      </div>
    </div>
  );
}
