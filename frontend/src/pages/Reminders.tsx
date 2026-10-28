import { Bell, Plus } from "lucide-react";
import { Link, useSearchParams } from "react-router";
import { useReminders, useSettings, useVehicles, type Reminder } from "../api/hooks";
import { EmptyState } from "../components/EmptyState";
import { PlateBadge } from "../components/PlateBadge";
import { ReminderRow } from "../components/ReminderRow";

const STATES: { state: Reminder["state"]; title: string }[] = [
  { state: "overdue", title: "Overdue" },
  { state: "due", title: "Due" },
  { state: "soon", title: "Coming up" },
  { state: "ok", title: "Later" },
];

export function Reminders() {
  const [search, setSearch] = useSearchParams();
  const vehicleId = Number(search.get("vehicle")) || undefined;
  const completed = search.get("completed") === "1";
  const vehicles = useVehicles();
  const settings = useSettings();
  const reminders = useReminders({ vehicle_id: vehicleId, include_completed: completed || undefined });

  if (vehicles.isError || reminders.isError || settings.isError) return <p className="error">Couldn't load reminders.</p>;
  if (!vehicles.data || !reminders.data || !settings.data) return null;
  const s = settings.data;
  const byId = new Map(vehicles.data.map((v) => [v.id, v]));
  const to = (vehicle: number | undefined, done: boolean) => {
    const q = new URLSearchParams();
    if (vehicle) q.set("vehicle", String(vehicle));
    if (done) q.set("completed", "1");
    return q.size ? `?${q}` : ".";
  };
  const chip = (id: number | undefined, text: string) => (
    <li key={id ?? "all"}>
      <Link className="chip" to={to(id, completed)} aria-current={vehicleId === id ? "page" : undefined}>
        {text}
      </Link>
    </li>
  );
  // Completed ones are listed after the open ones, whatever their stored state.
  const open = reminders.data.filter((r) => !r.completed_at);
  const finished = reminders.data.filter((r) => r.completed_at);
  const addFor = vehicleId ?? vehicles.data[0]?.id;

  return (
    <div className="records">
      <div className="page-head">
        <h1>Reminders</h1>
        {addFor !== undefined && (
          <Link className="btn primary" to={`/vehicles/${addFor}/reminders/new`}>
            <Plus size={18} aria-hidden="true" /> Add reminder
          </Link>
        )}
      </div>
      <nav aria-label="Filter by vehicle">
        <ul className="chips">
          {chip(undefined, "All vehicles")}
          {vehicles.data.map((v) => chip(v.id, v.name))}
        </ul>
      </nav>
      <label className="check">
        <input
          type="checkbox"
          checked={completed}
          onChange={(e) => setSearch(to(vehicleId, e.target.checked).slice(1), { replace: true })}
        />
        Show completed
      </label>
      {reminders.data.length === 0 ? (
        <EmptyState icon={Bell} title="No reminders">
          Add one for a service, or log a rego record and it appears here.
        </EmptyState>
      ) : (
        [...STATES.map(({ state, title }) => ({ key: state, title, list: open.filter((r) => r.state === state) })), { key: "done", title: "Completed", list: finished }]
          .filter((g) => g.list.length)
          .map((g) => (
            <section key={g.key} className="card">
              <h2 className="label">{g.title}</h2>
              <ul className="rows">
                {g.list.map((r) => {
                  const v = byId.get(r.vehicle_id);
                  return (
                    <ReminderRow
                      key={r.id}
                      r={r}
                      s={s}
                      plate={
                        v && (
                          <span className="rem-veh">
                            <PlateBadge plate={v.plate} />
                            <span>{v.name}</span>
                          </span>
                        )
                      }
                    />
                  );
                })}
              </ul>
            </section>
          ))
      )}
    </div>
  );
}
