import { Car } from "lucide-react";

export function Home() {
  return (
    <section className="empty">
      <Car size={48} aria-hidden="true" />
      <h1>Add your first vehicle</h1>
      <p>Your garage is empty. Vehicles, fuel, service records and reminders will live here.</p>
    </section>
  );
}
