import { Check, Copy, KeyRound } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useCreateToken, useRevokeToken, useTokens, type Settings as SettingsData } from "../../api/hooks";
import { Card } from "../../components/Card";
import { ConfirmDelete } from "../../components/ConfirmDelete";
import { Field } from "../../components/Field";
import { dateInZone, formatDate } from "../../lib/format";
import { errorsOf } from "./errorsOf";

export function TokensCard({ s }: { s: SettingsData }) {
  const tokens = useTokens();
  const create = useCreateToken();
  const revoke = useRevokeToken();
  const [name, setName] = useState("");
  const [scope, setScope] = useState<"read" | "write">("read");
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [fresh, setFresh] = useState<string | null>(null);
  const [copied, setCopied] = useState("");
  const box = useRef<HTMLInputElement>(null);
  const { reset } = create;
  // Drop the raw token from the mutation cache when leaving the page.
  useEffect(() => reset, [reset]);
  const when = (iso: string) => formatDate(dateInZone(iso, s.timezone), s);

  function submit(e: FormEvent) {
    e.preventDefault();
    setErrs({});
    create.mutate(
      { name: name.trim(), scope },
      {
        onSuccess: (t) => {
          setFresh(t.token);
          setCopied("");
          setName("");
        },
        onError: (x) => setErrs(errorsOf(x)),
      },
    );
  }
  async function copy() {
    try {
      await navigator.clipboard.writeText(fresh ?? "");
      setCopied("Copied.");
    } catch {
      box.current?.select();
      setCopied("Couldn't copy. It's selected, so press Ctrl+C.");
    }
  }

  return (
    <Card label="API tokens">
      {fresh && (
        <div className="token-new" role="group" aria-label="New token">
          <p>
            <strong>Copy it now. You won't see it again.</strong>
          </p>
          <input ref={box} className="mono token-box" readOnly value={fresh} aria-label="New token" onFocus={(e) => e.currentTarget.select()} />
          <div className="actions">
            <button type="button" className="btn primary" onClick={copy}>
              <Copy size={18} aria-hidden="true" /> Copy
            </button>
            <button type="button" className="btn" onClick={() => {
                setFresh(null);
                reset();
              }}>
              <Check size={18} aria-hidden="true" /> Done
            </button>
            <span role="status" className="muted">
              {copied}
            </span>
          </div>
        </div>
      )}
      {tokens.isError ? (
        <p className="error">Couldn't load tokens.</p>
      ) : tokens.data?.length === 0 ? (
        <p className="muted">No tokens yet.</p>
      ) : (
        <ul className="rows">
          {tokens.data?.map((t) => (
            <li key={t.id} className="token-row">
              <div className="rem-main">
                <strong>{t.name}</strong>
                <span className="stamp mono ok">{t.scope}</span>
              </div>
              <div className="muted">
                Created {when(t.created_at)} · {t.last_used_at ? `Last used ${when(t.last_used_at)}` : "Never used"}
              </div>
              <ConfirmDelete
                label="Revoke"
                icon={KeyRound}
                confirmLabel="Yes, revoke"
                question={`Revoke ${t.name}? Anything using it will stop working.`}
                pending={revoke.isPending}
                error={revoke.isError ? revoke.error.message : undefined}
                onConfirm={() => revoke.mutate(t.id)}
              />
            </li>
          ))}
        </ul>
      )}
      <h3 className="label token-new-head">New token</h3>
      <form className="fields" onSubmit={submit} noValidate>
        <div className="pair">
          <Field label="Token name" error={errs.name}>
            {(a) => <input {...a} value={name} autoComplete="off" onChange={(e) => setName(e.target.value)} />}
          </Field>
          <Field label="Scope" error={errs.scope} hint="Read can't change anything">
            {(a) => (
              <select {...a} value={scope} onChange={(e) => setScope(e.target.value as "read" | "write")}>
                <option value="read">Read</option>
                <option value="write">Write</option>
              </select>
            )}
          </Field>
        </div>
        {errs.form && !errs.name && !errs.scope && (
          <p className="error" role="alert">
            {errs.form}
          </p>
        )}
        <div className="actions">
          <button className="btn primary" disabled={!name.trim() || create.isPending}>
            Create token
          </button>
        </div>
      </form>
    </Card>
  );
}
