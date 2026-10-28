"""Read-only reader for LiteDB v5 data files, as found in a LubeLogger backup.

Only what a full dump needs: the header page maps collection names to page IDs, and every
document lives in data pages whose blocks chain together. Index and collection pages are
ignored. LiteDB's BSON stores 0x13 as a .NET System.Decimal, not IEEE Decimal128.
"""

import struct
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

PAGE = 8192
HEADER = 32
MAGIC = b"** This is a LiteDB file **"
FILE_VERSION = 8
DATA_PAGE = 4
END = 0xFFFFFFFF
MAX_DEPTH = 64
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
DATE_MAX_MS = 253402300800000
DATE_MIN_MS = -62135596800000

Doc = dict[str, Any]


class LiteDBError(ValueError):
    """The file is not a LiteDB v5 database this reader can open, or it is corrupt."""


def read_collections(db: bytes) -> dict[str, list[Doc]]:
    """Return every collection's documents, keyed by collection name."""
    if db[:1] == b"\x01":
        raise LiteDBError("database is encrypted; LiteDB passwords are not supported")
    if len(db) < PAGE or db[32 : 32 + len(MAGIC)] != MAGIC:
        raise LiteDBError("not a LiteDB database")
    if db[59] != FILE_VERSION:
        raise LiteDBError(f"unsupported LiteDB file version {db[59]} (need LiteDB v5)")
    try:
        names = _doc(db[192:PAGE], 0, 0)[0]
        by_col: defaultdict[int, list[Doc]] = defaultdict(list)
        for pid in range(len(db) // PAGE):
            page = _page(db, pid)
            if page[4] != DATA_PAGE or page[23] == 0:
                continue
            (col_id,) = struct.unpack_from("<I", page, 19)
            for idx in range(page[30] + 1):
                block = _block(page, idx)
                if block is not None and block[0] == 0:
                    raw = _follow(db, pid, idx, block)
                    by_col[col_id].append(_doc(raw, 0, 0)[0])
    except (struct.error, IndexError, UnicodeDecodeError) as e:
        raise LiteDBError(f"corrupt LiteDB file: {e}") from e
    return {name: by_col.get(col, []) for name, col in names.items() if isinstance(col, int)}


def _page(db: bytes, pid: int) -> bytes:
    if pid >= len(db) // PAGE:
        raise LiteDBError(f"corrupt LiteDB file: page {pid} is past the end of the file")
    return db[pid * PAGE : (pid + 1) * PAGE]


def _block(page: bytes, idx: int) -> bytes | None:
    """The data block in slot `idx`, or None for a free slot."""
    length, pos = struct.unpack_from("<HH", page, PAGE - (idx + 1) * 4)
    if length == 0:
        return None
    if length < 6 or pos < HEADER or pos + length > PAGE - (idx + 1) * 4:
        raise LiteDBError(f"corrupt LiteDB file: slot {idx} is out of bounds")
    return page[pos : pos + length]


def _follow(db: bytes, pid: int, idx: int, block: bytes) -> bytes:
    """Concatenate the payloads along a document's NextBlock chain."""
    parts = [block[6:]]
    seen = {(pid, idx)}
    pid, idx = struct.unpack_from("<IB", block, 1)
    while pid != END:
        if (pid, idx) in seen:
            raise LiteDBError("corrupt LiteDB file: data block chain loops")
        seen.add((pid, idx))
        page = _page(db, pid)
        nxt = _block(page, idx) if page[4] == DATA_PAGE else None
        if nxt is None or nxt[0] != 1:
            raise LiteDBError(f"corrupt LiteDB file: broken block chain at page {pid}")
        parts.append(nxt[6:])
        pid, idx = struct.unpack_from("<IB", nxt, 1)
    return b"".join(parts)


def _doc(b: bytes, o: int, depth: int) -> tuple[Doc, int]:
    if depth > MAX_DEPTH:
        raise LiteDBError("corrupt LiteDB file: documents nested too deeply")
    (size,) = struct.unpack_from("<i", b, o)
    end = o + size - 1
    if size < 5 or end >= len(b) or b[end] != 0:
        raise LiteDBError("corrupt LiteDB file: bad document length")
    o += 4
    out: Doc = {}
    while o < end:
        kind = b[o]
        key_end = b.find(0, o + 1, end)
        if key_end < 0:
            raise LiteDBError("corrupt LiteDB file: unterminated key")
        key = b[o + 1 : key_end].decode()
        out[key], o = _value(b, key_end + 1, kind, depth)
    if o != end:
        raise LiteDBError("corrupt LiteDB file: value overruns its document")
    return out, end + 1


def _value(b: bytes, o: int, kind: int, depth: int) -> tuple[Any, int]:
    if kind == 0x01:
        return struct.unpack_from("<d", b, o)[0], o + 8
    if kind == 0x02:
        (n,) = struct.unpack_from("<i", b, o)
        if n < 1 or o + 4 + n > len(b):
            raise LiteDBError("corrupt LiteDB file: bad string length")
        return b[o + 4 : o + 3 + n].decode(), o + 4 + n
    if kind == 0x03:
        return _doc(b, o, depth + 1)
    if kind == 0x04:
        items, o = _doc(b, o, depth + 1)
        return list(items.values()), o
    if kind == 0x05:
        (n,) = struct.unpack_from("<i", b, o)
        if n < 0 or o + 5 + n > len(b):
            raise LiteDBError("corrupt LiteDB file: bad binary length")
        data = b[o + 5 : o + 5 + n]
        if b[o + 4] == 0x04 and n == 16:  # LiteDB writes Guid as binary subtype 4
            return str(uuid.UUID(bytes_le=data)), o + 5 + n
        return data, o + 5 + n
    if kind == 0x07:
        if o + 12 > len(b):
            raise LiteDBError("corrupt LiteDB file: truncated ObjectId")
        return b[o : o + 12].hex(), o + 12
    if kind == 0x08:
        return b[o] != 0, o + 1
    if kind == 0x09:
        return _date(struct.unpack_from("<q", b, o)[0]), o + 8
    if kind in (0x0A, 0x7F, 0xFF):  # null, MaxKey, MinKey
        return None, o
    if kind == 0x10:
        return struct.unpack_from("<i", b, o)[0], o + 4
    if kind == 0x12:
        return struct.unpack_from("<q", b, o)[0], o + 8
    if kind == 0x13:
        return _dotnet_decimal(*struct.unpack_from("<IIII", b, o)), o + 16
    raise LiteDBError(f"corrupt LiteDB file: unknown BSON type {kind:#x}")


def _date(ms: int) -> datetime:
    """BSON date (ms since the Unix epoch, UTC), with .NET's MinValue/MaxValue sentinels."""
    if ms >= DATE_MAX_MS:
        return datetime.max.replace(tzinfo=UTC)
    if ms <= DATE_MIN_MS:
        return datetime.min.replace(tzinfo=UTC)
    return EPOCH + timedelta(milliseconds=ms)


def _dotnet_decimal(lo: int, mid: int, hi: int, flags: int) -> Decimal:
    """System.Decimal: a 96-bit mantissa, scale in flags bits 16-23, sign in bit 31."""
    scale = (flags >> 16) & 0xFF
    if scale > 28:
        raise LiteDBError("corrupt LiteDB file: decimal scale out of range")
    mantissa = hi << 64 | mid << 32 | lo
    sign = "-" if flags & 0x80000000 else ""
    return Decimal(f"{sign}{mantissa}E-{scale}")  # from a string, so no context rounding
