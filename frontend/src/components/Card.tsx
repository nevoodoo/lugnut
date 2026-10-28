import type { ReactNode } from "react";

export function Card({ label, children }: { label?: string; children: ReactNode }) {
  return (
    <section className="card">
      {label && <h2 className="label">{label}</h2>}
      {children}
    </section>
  );
}
