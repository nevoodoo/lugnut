"""Safe extraction of a LubeLogger backup zip: only the members the import reads, size-capped."""

import os
import re
import zipfile
from typing import BinaryIO

NEEDED = re.compile(r"data/cartracker\.db|config/userConfig\.json|(documents|images)/[^/]+")
MAX_MEMBER = 100 * 2**20
MAX_TOTAL = 2 * 2**30
_CHUNK = 64 * 1024


class ArchiveError(ValueError):
    def __init__(self, msg: str, status: int = 422) -> None:
        super().__init__(msg)
        self.status = status


def _target(base: str, name: str) -> str:
    """Where a member lands under base; raises if its normalised path escapes base."""
    full = os.path.normpath(os.path.join(base, name))
    if not full.startswith(base):
        raise ArchiveError("backup contains a file path outside the archive")
    return full


def extract(src: BinaryIO, dest: str) -> None:
    """Extract the needed members of the zip in src into the existing directory dest."""
    base = os.path.normpath(dest) + os.sep
    try:
        zf = zipfile.ZipFile(src)
    except (zipfile.BadZipFile, OSError):
        raise ArchiveError("not a zip file") from None
    with zf:
        members = zf.infolist()
        for info in members:  # check every path first, wanted or not
            _target(base, info.filename.replace("\\", "/"))
        total = 0
        for info in members:
            name = info.filename.replace("\\", "/")
            if info.is_dir() or not NEEDED.fullmatch(name):
                continue
            if info.flag_bits & 0x1:
                raise ArchiveError("backup is encrypted")
            if info.file_size > MAX_MEMBER:
                raise ArchiveError(f"{name} is larger than 100 MiB", 413)
            total += info.file_size
            if total > MAX_TOTAL:
                raise ArchiveError("backup is larger than 2 GiB uncompressed", 413)
            target = _target(base, name)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            try:
                _copy(zf, info, target)
            except FileExistsError:
                raise ArchiveError(f"backup lists {name} twice") from None
            except (zipfile.BadZipFile, EOFError, NotImplementedError, OSError) as e:
                raise ArchiveError(f"could not read {name} from the backup: {e}") from None
    if not os.path.isfile(base + "data/cartracker.db"):
        raise ArchiveError("backup has no data/cartracker.db")


def _copy(zf: zipfile.ZipFile, info: zipfile.ZipInfo, target: str) -> None:
    # Streamed; zipfile stops at the declared size, the count below is a second guard.
    n = 0
    with zf.open(info) as f, open(target, "xb") as out:
        while chunk := f.read(_CHUNK):
            n += len(chunk)
            if n > MAX_MEMBER:
                raise ArchiveError(f"{info.filename} is larger than 100 MiB", 413)
            out.write(chunk)
