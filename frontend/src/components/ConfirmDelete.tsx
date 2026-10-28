import { Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

// A delete button that asks inline first; the question gets focus so screen readers hear it.
export function ConfirmDelete(props: {
  label: string;
  question: string;
  pending: boolean;
  error?: string;
  onConfirm: () => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const ref = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    if (confirming) ref.current?.focus();
  }, [confirming]);
  return (
    <div className="danger card">
      {confirming ? (
        <>
          <p ref={ref} tabIndex={-1} role="alert">
            {props.question}
          </p>
          <div className="actions">
            <button type="button" className="btn danger-btn" disabled={props.pending} onClick={props.onConfirm}>
              Yes, delete
            </button>
            <button type="button" className="btn" onClick={() => setConfirming(false)}>
              Keep it
            </button>
          </div>
          {props.error && (
            <p className="error" role="alert">
              {props.error}
            </p>
          )}
        </>
      ) : (
        <button type="button" className="btn danger-btn" onClick={() => setConfirming(true)}>
          <Trash2 size={18} aria-hidden="true" /> {props.label}
        </button>
      )}
    </div>
  );
}
