import { Field } from "./Field";

export function DateInput(props: { label: string; value: string; onChange: (v: string) => void; error?: string }) {
  return (
    <Field label={props.label} error={props.error}>
      {(a) => <input {...a} type="date" value={props.value} onChange={(e) => props.onChange(e.target.value)} />}
    </Field>
  );
}
