import type { Reminder } from "../api/hooks";

// Rubber-stamp status label. The state word is in the text, so colour is never the only cue.
export function Stamp({ state, children }: { state: Reminder["state"]; children: string }) {
  return (
    <span className={`stamp mono ${state}`}>
      {state === "ok" ? "" : `${state} `}
      {children}
    </span>
  );
}
