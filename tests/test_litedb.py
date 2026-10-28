import struct
import zipfile
from decimal import Decimal
from pathlib import Path

import pytest

from lugnut.lubelogger.litedb import MAGIC, PAGE, LiteDBError, read_collections

FIXTURE = Path(__file__).parent / "fixtures" / "lubelogger_demo.zip"


def demo_db_bytes() -> bytes:
    with zipfile.ZipFile(FIXTURE) as zf:
        return zf.read("data/cartracker.db")


def test_reads_demo_backup():
    # catches: wrong block chaining, BSON decimal decoded as Decimal128/float
    cols = read_collections(demo_db_bytes())
    assert len(cols["vehicles"]) >= 1 and "servicerecords" in cols
    assert all(isinstance(r["Cost"], Decimal) for r in cols["servicerecords"])
    oil = next(r for r in cols["servicerecords"] if r["_id"] == 1)
    assert str(oil["Cost"]) == "23.07"
    with pytest.raises(LiteDBError, match="encrypted"):
        read_collections(b"\x01" + demo_db_bytes()[1:])


def test_rejects_blocks_shared_by_two_documents():
    # catches: start blocks sharing one continuation tail, each rebuilding it (memory blowup)
    def page(pid: int, kind: int, blocks: list[bytes]) -> bytes:
        p = bytearray(PAGE)
        struct.pack_into("<IB", p, 0, pid, kind)
        p[23], p[30] = len(blocks), len(blocks) - 1
        pos = 32
        for i, blk in enumerate(blocks):
            p[pos : pos + len(blk)] = blk
            struct.pack_into("<HH", p, PAGE - (i + 1) * 4, len(blk), pos)
            pos += len(blk)
        return bytes(p)

    header = bytearray(PAGE)
    header[32:60] = MAGIC + b"\x08"
    names = b"\x10vehicles\x00" + struct.pack("<i", 0)
    header[192 : 192 + len(names) + 5] = struct.pack("<i", len(names) + 5) + names + b"\x00"
    doc = struct.pack("<i", 15) + b"\x02s\x00" + struct.pack("<i", 3) + b"hi\x00\x00"
    start = b"\x00" + struct.pack("<IB", 2, 0) + doc[:4]
    tail = b"\x01" + struct.pack("<IB", 0xFFFFFFFF, 0) + doc[4:]
    db = bytes(header) + page(1, 4, [start, start]) + page(2, 4, [tail])
    with pytest.raises(LiteDBError, match="used by two documents"):
        read_collections(db)
