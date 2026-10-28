import { Paperclip, X } from "lucide-react";
import { useId, useState } from "react";
import { useDeleteAttachment, useUpload, type LugnutRecord } from "../api/hooks";

interface Upload {
  file: File;
  state: "waiting" | "uploading" | "done" | "failed";
  error?: string;
}
const STATE_TEXT = { waiting: "Uploads after saving", uploading: "Uploading...", done: "Uploaded", failed: "Failed" };

const size = (n: number) => (n < 1024 * 1024 ? `${Math.ceil(n / 1024)} KB` : `${(n / 1024 / 1024).toFixed(1)} MB`);

// Files picked on the form. A saved record uploads at once; a new one waits for its id.
export function useUploadQueue(vehicleId: number) {
  const upload = useUpload();
  const [queue, setQueue] = useState<Upload[]>([]);
  const mark = (file: File, patch: Partial<Upload>) => setQueue((q) => q.map((u) => (u.file === file ? { ...u, ...patch } : u)));

  // One at a time so each row shows its own result. Returns whether all of them made it.
  async function send(files: File[], recordId: number): Promise<boolean> {
    let ok = true;
    for (const file of files) {
      mark(file, { state: "uploading", error: undefined });
      try {
        await upload.mutateAsync({ vehicleId, file, recordId });
        mark(file, { state: "done" });
      } catch (e) {
        ok = false;
        mark(file, { state: "failed", error: e instanceof Error ? e.message : String(e) });
      }
    }
    return ok;
  }

  return {
    queue,
    add: (files: File[], recordId?: number) => {
      setQueue((q) => [...q.filter((u) => u.state !== "done"), ...files.map((file) => ({ file, state: "waiting" as const }))]);
      if (recordId !== undefined) void send(files, recordId);
    },
    drop: (file: File) => setQueue((q) => q.filter((u) => u.file !== file)),
    sendWaiting: (recordId: number) => send(queue.filter((u) => u.state !== "done").map((u) => u.file), recordId),
  };
}

export function Attachments({ record, uploads }: { record?: LugnutRecord; uploads: ReturnType<typeof useUploadQueue> }) {
  const id = useId();
  const del = useDeleteAttachment();
  const [confirm, setConfirm] = useState<number | null>(null);
  const saved = record?.attachments ?? [];
  const pending = uploads.queue.filter((u) => !(record && u.state === "done")); // done ones are in the saved list

  return (
    <div className="attachments">
      {(saved.length > 0 || pending.length > 0) && (
        <ul className="rows">
          {saved.map((a) => (
            <li key={a.id} className="row">
              <a className="link-tap" href={`/api/attachments/${a.id}/file`} target="_blank" rel="noreferrer">
                {a.filename}
              </a>
              <span className="actions">
                <span className="muted">{size(a.size)}</span>
                {confirm === a.id ? (
                  <button type="button" className="btn small danger-btn" disabled={del.isPending} onClick={() => del.mutate(a.id, { onSuccess: () => setConfirm(null) })}>
                    Remove {a.filename}?
                  </button>
                ) : (
                  <button type="button" className="icon-btn" aria-label={`Remove ${a.filename}`} onClick={() => setConfirm(a.id)}>
                    <X size={18} aria-hidden="true" />
                  </button>
                )}
              </span>
            </li>
          ))}
          {pending.map((u, i) => (
            <li key={`${u.file.name}-${i}`} className="row">
              <span>{u.file.name}</span>
              <span className="actions">
                <span className={u.state === "failed" ? "error" : "muted"} role={u.state === "failed" ? "alert" : undefined}>
                  {STATE_TEXT[u.state]}
                  {u.error && `: ${u.error}`}
                </span>
                {(u.state === "waiting" || u.state === "failed") && (
                  <button type="button" className="icon-btn" aria-label={`Don't upload ${u.file.name}`} onClick={() => uploads.drop(u.file)}>
                    <X size={18} aria-hidden="true" />
                  </button>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
      {del.error && (
        <p className="error" role="alert">
          Couldn't remove the file: {del.error.message}
        </p>
      )}
      <label htmlFor={id} className="btn">
        <Paperclip size={18} aria-hidden="true" /> Add files
      </label>
      <input
        id={id}
        className="visually-hidden"
        type="file"
        multiple
        onChange={(e) => {
          uploads.add([...(e.target.files ?? [])], record?.id);
          e.target.value = "";
        }}
      />
    </div>
  );
}
