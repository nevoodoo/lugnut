export function PlateBadge({ plate }: { plate: string | null | undefined }) {
  return plate ? <span className="plate mono">{plate}</span> : null;
}
