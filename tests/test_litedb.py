import zipfile
from decimal import Decimal
from pathlib import Path

import pytest

from lugnut.lubelogger.litedb import LiteDBError, read_collections

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
