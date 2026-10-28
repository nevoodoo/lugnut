import { useState, type FormEvent } from "react";
import { useSetDiscord, useTestDiscord } from "../../api/hooks";
import { Card } from "../../components/Card";
import { Field } from "../../components/Field";
import { errorsOf } from "./errorsOf";

export function DiscordCard({ isSet }: { isSet: boolean }) {
  const set = useSetDiscord();
  const test = useTestDiscord();
  const [url, setUrl] = useState("");
  const [err, setErr] = useState("");
  const [result, setResult] = useState("");
  const [removing, setRemoving] = useState(false);

  function submit(e: FormEvent) {
    e.preventDefault();
    setErr("");
    setResult("");
    set.mutate(url.trim(), {
      onSuccess: () => setUrl(""),
      onError: (x) => setErr(errorsOf(x).url ?? errorsOf(x).form),
    });
  }
  return (
    <Card label="Discord">
      <p>
        <span className={`stamp mono ${isSet ? "ok" : "soon"}`}>{isSet ? "Webhook set" : "No webhook"}</span>{" "}
        <span className="muted">Reminders post to this channel. The address is never shown.</span>
      </p>
      <form className="fields" onSubmit={submit} noValidate>
        <Field label={isSet ? "Replace webhook URL" : "Webhook URL"} error={err}>
          {(a) => <input {...a} type="url" autoComplete="off" spellCheck={false} placeholder="https://discord.com/api/webhooks/..." value={url} onChange={(e) => setUrl(e.target.value)} />}
        </Field>
        <div className="actions">
          <button className="btn primary" disabled={!url.trim() || set.isPending}>
            Save webhook
          </button>
          {isSet && (
            <>
              <button
                type="button"
                className="btn"
                disabled={test.isPending}
                onClick={() => {
                  setResult("");
                  test.mutate(undefined, {
                    onSuccess: (r) => setResult(r.ok ? "Test message sent." : `Test failed: ${r.error ?? "unknown error"}`),
                    onError: (x) => setResult(`Test failed: ${x.message}`),
                  });
                }}
              >
                {test.isPending ? "Sending..." : "Send test"}
              </button>
              <button type="button" className="btn danger-btn" aria-expanded={removing} onClick={() => setRemoving(true)}>
                Remove
              </button>
            </>
          )}
        </div>
        {removing && (
          <div className="ask" role="alert">
            <p>Remove the Discord webhook? Reminders will stop posting.</p>
            <div className="actions">
              <button
                type="button"
                className="btn danger-btn"
                disabled={set.isPending}
                onClick={() =>
                  set.mutate(null, {
                    onSuccess: () => {
                      setResult("");
                      setRemoving(false);
                    },
                  })
                }
              >
                Yes, remove
              </button>
              <button type="button" className="btn" onClick={() => setRemoving(false)}>
                Keep it
              </button>
            </div>
          </div>
        )}
        {result && (
          <p role="status" className={result.startsWith("Test failed") ? "error" : "muted"}>
            {result}
          </p>
        )}
      </form>
    </Card>
  );
}
