// FastAPI 422 detail: [{loc: ["body", "details", "line_items", 1, "job_type_id"], msg}].
// Returns {"details.line_items.1.job_type_id": msg}, the first message per field.
export function fieldErrors(detail: unknown): Record<string, string> {
  const out: Record<string, string> = {};
  if (!Array.isArray(detail)) return out;
  for (const e of detail) {
    if (!e || !Array.isArray(e.loc) || typeof e.msg !== "string") continue;
    const path = e.loc.slice(e.loc[0] === "body" ? 1 : 0).join(".");
    if (path && !(path in out)) out[path] = e.msg.replace(/^Value error, /, "");
  }
  return out;
}
