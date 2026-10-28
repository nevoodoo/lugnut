import { Camera } from "lucide-react";
import { useId } from "react";
import { useSetPhoto, useUpload } from "../api/hooks";

// Upload, then point the vehicle at it. fetch has no upload progress, so show the busy state.
export function PhotoUpload({ vehicleId, hasPhoto }: { vehicleId: number; hasPhoto: boolean }) {
  const id = useId();
  const upload = useUpload();
  const setPhoto = useSetPhoto();
  const busy = upload.isPending || setPhoto.isPending;
  const error = upload.error ?? setPhoto.error;

  function pick(file: File | undefined) {
    if (!file) return;
    upload.mutate(
      { vehicleId, file },
      { onSuccess: (a) => setPhoto.mutate({ vehicleId, attachmentId: a.id }) },
    );
  }

  return (
    <div className="photo-upload">
      <label htmlFor={id} className={`btn${busy ? " busy" : ""}`}>
        <Camera size={18} aria-hidden="true" />
        {busy ? "Uploading photo..." : hasPhoto ? "Change photo" : "Add photo"}
      </label>
      <input
        id={id}
        className="visually-hidden"
        type="file"
        accept="image/*"
        capture="environment"
        disabled={busy}
        onChange={(e) => {
          pick(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
      {busy && <progress aria-label="Uploading photo" />}
      {error && (
        <p className="error" role="alert">
          Photo failed: {error.message}
        </p>
      )}
    </div>
  );
}
