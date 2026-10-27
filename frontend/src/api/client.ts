import type { components } from "./schema";

export type User = components["schemas"]["UserOut"];

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

// Set by main.tsx: called on any 401 so the app can fall back to the login screen.
let onUnauthorized: () => void = () => {};
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn;
}

// Every request goes through here: JSON in/out, and the header the API requires on writes.
export async function api<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    headers: { "X-Lugnut": "1", ...(body ? { "Content-Type": "application/json" } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401) onUnauthorized();
  if (!res.ok) {
    const detail = await res.json().then(
      (j) => j.detail,
      () => undefined,
    );
    throw new ApiError(res.status, typeof detail === "string" ? detail : res.statusText);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}
