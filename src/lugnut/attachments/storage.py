import hashlib
import logging
import os
import re
import secrets

from fastapi import HTTPException, UploadFile

from lugnut.settings import Settings

log = logging.getLogger(__name__)

MAX_BYTES = 25 * 2**20
_CHUNK = 64 * 1024
_NAME = re.compile(r"[0-9a-f]{32}\.(jpg|png|webp|heic|pdf)")


def sniff(head: bytes) -> tuple[str, str] | None:
    """(content_type, extension) from magic bytes only; the client's header and name are ignored."""
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "jpg"
    if head.startswith(b"\x89PNG"):
        return "image/png", "png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp", "webp"
    if head[4:12] in (b"ftypheic", b"ftypheix", b"ftypmif1"):
        return "image/heic", "heic"
    if head.startswith(b"%PDF-"):
        return "application/pdf", "pdf"
    return None


def path(settings: Settings, stored_name: str) -> str:
    base = str(settings.attachments_dir.resolve()) + os.sep
    full = os.path.normpath(os.path.join(base, stored_name))
    if not full.startswith(base):
        raise ValueError("invalid stored name")
    if not _NAME.fullmatch(stored_name):
        raise ValueError("invalid stored name")
    return full


def save(settings: Settings, upload: UploadFile) -> tuple[str, str, int, str]:
    """Stream to disk. Returns (stored_name, content_type, size, sha256)."""
    kind = sniff(upload.file.read(16))
    if kind is None:
        raise HTTPException(415, "Unsupported file type")
    content_type, ext = kind
    upload.file.seek(0)
    settings.attachments_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{secrets.token_hex(16)}.{ext}"
    dest = path(settings, stored_name)
    digest, size = hashlib.sha256(), 0
    try:
        with open(dest, "xb") as out:
            while chunk := upload.file.read(_CHUNK):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise HTTPException(413, "File too large")
                digest.update(chunk)
                out.write(chunk)
    except BaseException:
        delete(settings, stored_name)
        raise
    return stored_name, content_type, size, digest.hexdigest()


def delete(settings: Settings, stored_name: str) -> None:
    try:
        os.remove(path(settings, stored_name))
    except FileNotFoundError:
        pass
    except (OSError, ValueError):
        log.exception("could not delete attachment file %s", stored_name)


def delete_many(settings: Settings, stored_names: list[str]) -> None:
    for n in stored_names:
        delete(settings, n)
