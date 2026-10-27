import { Car } from "lucide-react";

export function Home() {
  return (
    <section className="empty">
      <Car size={48} aria-hidden="true" />
      <h1>No vehicles yet</h1>
      <p>Adding vehicles comes in a later release.</p>
    </section>
  );
}
