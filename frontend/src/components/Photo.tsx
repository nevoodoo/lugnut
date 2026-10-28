import { Car } from "lucide-react";
import { useState } from "react";

export const photoUrl = (attachmentId: number) => `/api/attachments/${attachmentId}/file`;

// Fixed-size box so a missing or broken image never shifts the layout.
export function Photo({ id, alt = "" }: { id: number | null; alt?: string }) {
  const [failed, setFailed] = useState<number | null>(null);
  const broken = id === null || failed === id;
  return (
    <div className="photo">
      {broken ? (
        <Car size={40} aria-hidden="true" />
      ) : (
        <img src={photoUrl(id)} alt={alt} onError={() => setFailed(id)} />
      )}
    </div>
  );
}
