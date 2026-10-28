import { useId, type ReactNode } from "react";

// A labelled control with its error beside it. The child gets the id and aria wiring via render prop.
export function Field(props: {
  label: string;
  error?: string;
  hint?: string;
  children: (a: { id: string; "aria-invalid": boolean; "aria-describedby"?: string }) => ReactNode;
}) {
  const id = useId();
  const note = props.error ? `${id}-e` : props.hint ? `${id}-h` : undefined;
  return (
    <div className="field">
      <label htmlFor={id}>{props.label}</label>
      {props.children({ id, "aria-invalid": !!props.error, "aria-describedby": note })}
      {props.error ? (
        <small id={`${id}-e`} className="error" role="alert">
          {props.error}
        </small>
      ) : (
        props.hint && <small id={`${id}-h`}>{props.hint}</small>
      )}
    </div>
  );
}
