import { useState } from "react";
import { moneyToText, parseMoney } from "../lib/format";
import { Field } from "./Field";

export const moneyError = (currency: string) => `Enter an amount like ${moneyToText(8450, currency)}`;

// Decimal text in the install currency. Says so inline once you leave a field it can't read.
export function MoneyInput(props: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  currency: string;
  error?: string;
  placeholder?: string;
  className?: string;
}) {
  const [left, setLeft] = useState(false);
  const bad = left && parseMoney(props.value, props.currency) === "invalid";
  return (
    <Field label={props.label} error={props.error ?? (bad ? moneyError(props.currency) : undefined)} hint={`In ${props.currency}`}>
      {(a) => (
        <input
          {...a}
          className={props.className}
          inputMode="decimal"
          autoComplete="off"
          placeholder={props.placeholder}
          value={props.value}
          onChange={(e) => props.onChange(e.target.value)}
          onBlur={() => setLeft(true)}
        />
      )}
    </Field>
  );
}
