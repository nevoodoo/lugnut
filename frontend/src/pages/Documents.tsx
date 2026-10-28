import { FileText, Paperclip } from "lucide-react";
import { Link, useSearchParams } from "react-router";
import { useAttachments, useSettings, useVehicles, type Attachment } from "../api/hooks";
import { EmptyState } from "../components/EmptyState";
import { photoUrl } from "../components/Photo";
import { Field } from "../components/Field";
import { dateInZone, formatDate, type InstallSettings } from "../lib/format";
import { getLastVehicle } from "../lib/lastVehicle";

const size = (n: number) => (n < 1024 * 1024 ? `${Math.ceil(n / 1024)} KB` : `${(n / 1024 / 1024).toFixed(1)} MB`);

function Meta({ a, s }: { a: Attachment; s: InstallSettings }) {
  return (
    <>
      <span className="muted">
        {formatDate(dateInZone(a.created_at, s.timezone), s)} · {size(a.size)}
      </span>
      {a.record_id !== null && <Link to={`/records/${a.record_id}`}>View record</Link>}
    </>
  );
}

export function Documents() {
  const [search, setSearch] = useSearchParams();
  const vehicles = useVehicles();
  const settings = useSettings();
  const ids = vehicles.data?.map((v) => v.id) ?? [];
  const asked = Number(search.get("vehicle"));
  const id = [asked, getLastVehicle()].find((n) => n !== null && ids.includes(n)) ?? ids[0] ?? 0;
  const files = useAttachments(id);

  if (vehicles.isError || settings.isError || files.isError) return <p className="error">Couldn't load documents.</p>;
  if (!vehicles.data || !settings.data) return null;
  const s = settings.data;
  const images = files.data?.filter((a) => a.content_type.startsWith("image/")) ?? [];
  const others = files.data?.filter((a) => !a.content_type.startsWith("image/")) ?? [];

  return (
    <div className="records">
      <h1>Documents</h1>
      {vehicles.data.length > 1 && (
        <Field label="Vehicle">
          {(a) => (
            <select {...a} value={id} onChange={(e) => setSearch({ vehicle: e.target.value }, { replace: true })}>
              {vehicles.data.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name}
                </option>
              ))}
            </select>
          )}
        </Field>
      )}
      {files.data && files.data.length === 0 ? (
        <EmptyState icon={Paperclip} title="No documents">
          Photos and PDFs you attach to a record show up here.
        </EmptyState>
      ) : (
        <>
          {images.length > 0 && (
            <section className="card">
              <h2 className="label">Photos</h2>
              <ul className="doc-grid">
                {images.map((a) => (
                  <li key={a.id}>
                    <a href={photoUrl(a.id)} target="_blank" rel="noreferrer" className="doc-thumb">
                      <img src={photoUrl(a.id)} alt={a.filename} loading="lazy" />
                    </a>
                    <div className="doc-cap">
                      <span className="doc-name">{a.filename}</span>
                      <Meta a={a} s={s} />
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}
          {others.length > 0 && (
            <section className="card">
              <h2 className="label">Files</h2>
              <ul className="rows">
                {others.map((a) => (
                  <li key={a.id} className="row doc-row">
                    <FileText size={24} aria-hidden="true" />
                    <div className="doc-cap">
                      <a className="doc-name" href={photoUrl(a.id)} target="_blank" rel="noreferrer">
                        {a.filename}
                      </a>
                      <Meta a={a} s={s} />
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  );
}
