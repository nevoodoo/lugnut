import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export function EmptyState(props: { icon: LucideIcon; title: string; children?: ReactNode; action?: ReactNode }) {
  const Icon = props.icon;
  return (
    <section className="empty">
      <Icon size={48} aria-hidden="true" />
      <h1>{props.title}</h1>
      {props.children && <p>{props.children}</p>}
      {props.action}
    </section>
  );
}
