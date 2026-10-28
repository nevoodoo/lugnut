import os
from pathlib import PurePath
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from lugnut.attachments import storage
from lugnut.attachments.models import Attachment
from lugnut.auth.deps import DB, utcnow
from lugnut.auth.routes import Reader, Writer
from lugnut.records.models import Record
from lugnut.timeutil import UtcDatetime
from lugnut.vehicles.models import Vehicle

router = APIRouter(prefix="/api")


class AttachmentOut(BaseModel):
    id: int
    vehicle_id: int
    record_id: int | None
    filename: str
    content_type: str
    size: int
    sha256: str
    created_at: UtcDatetime


class PhotoIn(BaseModel):
    attachment_id: int | None


def _get(db: DB, attachment_id: int) -> Attachment:
    a = db.get(Attachment, attachment_id)
    if a is None:
        raise HTTPException(404, "Attachment not found")
    return a


def _out(a: Attachment) -> AttachmentOut:
    return AttachmentOut.model_validate(a, from_attributes=True)


@router.post("/vehicles/{vehicle_id}/attachments", status_code=201)
def upload_attachment(
    vehicle_id: int,
    file: UploadFile,
    request: Request,
    _: Writer,
    db: DB,
    record_id: Annotated[int | None, Form()] = None,
) -> AttachmentOut:
    if db.get(Vehicle, vehicle_id) is None:
        raise HTTPException(404, "Vehicle not found")
    if record_id is not None:
        rec = db.get(Record, record_id)
        if rec is None or rec.vehicle_id != vehicle_id:
            raise HTTPException(422, "record_id is not a record of this vehicle")
    settings = request.app.state.settings
    stored_name, content_type, size, sha256 = storage.save(settings, file)
    a = Attachment(
        vehicle_id=vehicle_id,
        record_id=record_id,
        filename=PurePath((file.filename or "").replace("\\", "/")).name or "file",
        content_type=content_type,
        size=size,
        sha256=sha256,
        stored_name=stored_name,
        created_at=utcnow(),
    )
    try:
        db.add(a)
        db.commit()
    except BaseException:
        storage.delete(settings, stored_name)
        raise
    return _out(a)


@router.get("/attachments/{attachment_id}")
def read_attachment(attachment_id: int, _: Reader, db: DB) -> AttachmentOut:
    return _out(_get(db, attachment_id))


@router.get("/attachments/{attachment_id}/file")
def download_attachment(attachment_id: int, request: Request, _: Reader, db: DB) -> FileResponse:
    a = _get(db, attachment_id)
    try:
        full = storage.path(request.app.state.settings, a.stored_name)
    except ValueError:
        raise HTTPException(404, "File missing") from None
    if not os.path.isfile(full):
        raise HTTPException(404, "File missing")
    return FileResponse(
        full,
        media_type=a.content_type,
        content_disposition_type="inline" if a.content_type.startswith("image/") else "attachment",
        filename=a.filename,
        headers={"X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox"},
    )


@router.delete("/attachments/{attachment_id}", status_code=204)
def delete_attachment(attachment_id: int, request: Request, _: Writer, db: DB) -> None:
    a = _get(db, attachment_id)
    name = a.stored_name
    db.delete(a)
    db.commit()
    storage.delete(request.app.state.settings, name)


@router.put("/vehicles/{vehicle_id}/photo")
def set_photo(vehicle_id: int, body: PhotoIn, _: Writer, db: DB) -> dict[str, int | None]:
    v = db.get(Vehicle, vehicle_id)
    if v is None:
        raise HTTPException(404, "Vehicle not found")
    if body.attachment_id is not None:
        a = db.get(Attachment, body.attachment_id)
        if a is None or a.vehicle_id != vehicle_id or not a.content_type.startswith("image/"):
            raise HTTPException(422, "attachment_id must be an image attachment of this vehicle")
    v.photo_attachment_id = body.attachment_id
    db.commit()
    return {"photo_attachment_id": v.photo_attachment_id}
