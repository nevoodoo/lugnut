import { useMutation, useQuery, useQueryClient, type QueryKey } from "@tanstack/react-query";
import { api } from "./client";
import type { components } from "./schema";

type S = components["schemas"];
export type Settings = S["SettingsOut"];
export type Vehicle = S["VehicleOut"];
export type VehicleIn = S["VehicleIn"];
export type LugnutRecord = S["RecordOut"];
export type RecordIn = S["RecordIn"];
export type JobType = S["JobTypeOut"];
export type Reminder = S["ReminderOut"];
export type ReminderIn = S["ReminderIn"];
export type Token = S["TokenOut"];

export interface RecordFilters {
  type?: S["RecordOut"]["type"];
  from?: string;
  to?: string;
  limit?: number;
  offset?: number;
}
export interface ReminderFilters {
  vehicle_id?: number;
  state?: string;
  include_completed?: boolean;
}

// Query string from the defined entries only.
function qs(params: object): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined) q.set(k, String(v));
  return q.size ? `?${q}` : "";
}

const useGet = <T>(key: QueryKey, path: string, enabled = true) =>
  useQuery({ queryKey: key, queryFn: () => api<T>(path), enabled });

// ---- queries ----
export const useSettings = () => useGet<Settings>(["settings"], "/settings");
export const useRegions = () => useGet<Record<string, unknown>[]>(["regions"], "/regions");
// The API returns only archived vehicles when archived=true, so the two lists are separate queries.
export const useVehicles = (archived = false) =>
  useGet<Vehicle[]>(archived ? ["vehicles", "archived"] : ["vehicles"], `/vehicles${archived ? "?archived=true" : ""}`);
export const useVehicle = (id: number) => useGet<Vehicle>(["vehicles", id], `/vehicles/${id}`);
export const useRecords = (vehicleId: number, filters: RecordFilters = {}) =>
  useGet<LugnutRecord[]>(["records", vehicleId, filters], `/vehicles/${vehicleId}/records${qs(filters)}`);
export const useRecord = (id: number) => useGet<LugnutRecord>(["record", id], `/records/${id}`);
export const useJobTypes = () => useGet<JobType[]>(["job-types"], "/job-types");
export const useReminders = (filters: ReminderFilters = {}) =>
  useGet<Reminder[]>(["reminders", filters], `/reminders${qs(filters)}`);
export const useTokens = () => useGet<Token[]>(["tokens"], "/tokens");
// ponytail: no GET list for a vehicle's attachments exists yet; add the endpoint and a hook when a screen needs it.

// ---- mutations ----
// Each one takes its invalidation list up front; a prefix key refreshes every variant under it.
function useWrite<V, R = unknown>(fn: (v: V) => Promise<R>, invalidate: QueryKey[]) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => Promise.all(invalidate.map((queryKey) => qc.invalidateQueries({ queryKey }))),
  });
}

// Records change odometers, costs and expiry reminders, so they refresh vehicles and reminders too.
const RECORD_KEYS: QueryKey[] = [["records"], ["record"], ["vehicles"], ["reminders"]];

export const useSaveVehicle = () =>
  useWrite(
    ({ id, body }: { id?: number; body: VehicleIn }) =>
      api<Vehicle>(id ? `/vehicles/${id}` : "/vehicles", id ? "PUT" : "POST", body),
    [["vehicles"], ["records"], ["record"], ["reminders"]],
  );
export const useDeleteVehicle = () =>
  useWrite(
    (id: number) => api<void>(`/vehicles/${id}`, "DELETE"),
    [["vehicles"], ["records"], ["record"], ["reminders"]],
  );

export const useSaveRecord = () =>
  useWrite(
    ({ id, vehicleId, body }: { id?: number; vehicleId: number; body: RecordIn }) =>
      api<LugnutRecord>(id ? `/records/${id}` : `/vehicles/${vehicleId}/records`, id ? "PUT" : "POST", body),
    RECORD_KEYS,
  );
export const useDeleteRecord = () =>
  useWrite((id: number) => api<void>(`/records/${id}`, "DELETE"), RECORD_KEYS);

export const useUpload = () =>
  useWrite(({ vehicleId, file, recordId }: { vehicleId: number; file: File; recordId?: number }) => {
    const form = new FormData();
    form.append("file", file);
    if (recordId !== undefined) form.append("record_id", String(recordId));
    return api<S["AttachmentOut"]>(`/vehicles/${vehicleId}/attachments`, "POST", form);
  }, [["records"], ["record"]]);
export const useSetPhoto = () =>
  useWrite(
    ({ vehicleId, attachmentId }: { vehicleId: number; attachmentId: number | null }) =>
      api(`/vehicles/${vehicleId}/photo`, "PUT", { attachment_id: attachmentId }),
    [["vehicles"]],
  );

export const useSaveReminder = () =>
  useWrite(
    ({ id, vehicleId, body }: { id?: number; vehicleId: number; body: ReminderIn }) =>
      api<Reminder>(id ? `/reminders/${id}` : `/vehicles/${vehicleId}/reminders`, id ? "PUT" : "POST", body),
    [["reminders"]],
  );
export const useCompleteReminder = () =>
  useWrite(
    ({ id, date, odometer }: { id: number; date?: string; odometer?: number }) =>
      api<Reminder>(`/reminders/${id}/complete`, "POST", { date, odometer }),
    [["reminders"]],
  );
export const useDeleteReminder = () =>
  useWrite((id: number) => api<void>(`/reminders/${id}`, "DELETE"), [["reminders"]]);

export const useSaveSettings = () =>
  useWrite(
    (body: S["SettingsIn"]) => api<Settings>("/settings", "PUT", body),
    [["settings"], ["vehicles"], ["records"], ["record"], ["reminders"]],
  );
export const useSetDiscord = () =>
  useWrite((url: string | null) => api<Settings>("/settings/discord", "PUT", { url }), [["settings"]]);
export const useTestDiscord = () =>
  useWrite(() => api<{ ok: boolean; error?: string }>("/settings/discord/test", "POST"), []);

export const useCreateToken = () =>
  useWrite((body: S["TokenIn"]) => api<S["TokenCreated"]>("/tokens", "POST", body), [["tokens"]]);
export const useRevokeToken = () =>
  useWrite((id: number) => api<void>(`/tokens/${id}`, "DELETE"), [["tokens"]]);
