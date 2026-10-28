import { Field } from "./Field";

export function NumberInput(props: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  error?: string;
  hint?: string;
  className?: string;
}) {
  return (
    <Field label={props.label} error={props.error} hint={props.hint}>
      {(a) => (
        <input
          {...a}
          className={props.className}
          inputMode="decimal"
          autoComplete="off"
          value={props.value}
          onChange={(e) => props.onChange(e.target.value)}
        />
      )}
    </Field>
  );
}
