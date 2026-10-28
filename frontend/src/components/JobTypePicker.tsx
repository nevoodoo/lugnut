import { Plus } from "lucide-react";
import { useId, useState } from "react";
import { useCreateJobType, useJobTypes } from "../api/hooks";
import { Field } from "./Field";

// Type to search (native datalist); a name that isn't in the list can be added on the spot.
export function JobTypePicker(props: { value: number | null; onChange: (id: number | null, unmatched: boolean) => void; error?: string }) {
  const types = useJobTypes().data ?? [];
  const create = useCreateJobType();
  const listId = useId();
  const [text, setText] = useState(() => types.find((t) => t.id === props.value)?.name ?? "");
  const match = (name: string) => types.find((t) => t.name.toLowerCase() === name.trim().toLowerCase());
  const name = text.trim();
  const unknown = name !== "" && !match(name);

  function type(v: string) {
    setText(v);
    const id = match(v)?.id ?? null;
    props.onChange(id, id === null && v.trim() !== "");
  }

  return (
    <div className="jobtype">
      <Field label="Job type" error={props.error ?? create.error?.message} hint={unknown ? "Not in the list yet" : undefined}>
        {(a) => <input {...a} list={listId} autoComplete="off" value={text} onChange={(e) => type(e.target.value)} />}
      </Field>
      <datalist id={listId}>
        {types.map((t) => (
          <option key={t.id} value={t.name} />
        ))}
      </datalist>
      {unknown && (
        <button
          type="button"
          className="btn small"
          disabled={create.isPending}
          onClick={() => create.mutate(name, { onSuccess: (j) => props.onChange(j.id, false) })}
        >
          <Plus size={16} aria-hidden="true" /> Add "{name}"
        </button>
      )}
    </div>
  );
}
