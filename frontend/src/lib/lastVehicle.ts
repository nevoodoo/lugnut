const KEY = "lugnut.lastVehicle";

// Per-browser convenience; storage can be blocked, so never let it throw.
export function getLastVehicle(): number | null {
  try {
    const n = Number(localStorage.getItem(KEY));
    return Number.isInteger(n) && n > 0 ? n : null;
  } catch {
    return null;
  }
}
export function setLastVehicle(id: number) {
  try {
    localStorage.setItem(KEY, String(id));
  } catch {
    /* ignore */
  }
}
