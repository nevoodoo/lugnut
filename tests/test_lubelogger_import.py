import io
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
from conftest import CSRF
from sqlalchemy import func, select
from starlette.requests import Request

from lugnut.attachments.models import Attachment
from lugnut.lubelogger import routes
from lugnut.lubelogger.mapper import build_plan
from lugnut.records.models import Record
from lugnut.reminders.models import Reminder
from lugnut.vehicles.models import Vehicle

FIXTURE = Path(__file__).parent / "fixtures" / "lubelogger_demo.zip"
TABLES = (Vehicle, Record, Reminder, Attachment)


@pytest.fixture(autouse=True)
def _auth(logged_in):
    pass


@pytest.fixture
def data_dir(client):
    return client.app.state.settings.data_dir


def upload(client, data: bytes):
    files = {"file": ("backup.zip", data, "application/zip")}
    return client.post("/api/import/lubelogger", files=files, headers=CSRF)


def upload_demo(client):
    res = upload(client, FIXTURE.read_bytes())
    assert res.status_code == 200, res.text
    return res.json()


def commit_demo(client):
    tok = upload_demo(client)["token"]
    res = client.post(f"/api/import/lubelogger/{tok}/commit", json={}, headers=CSRF)
    assert res.status_code == 200, res.text
    return res.json()


def all_records(client):
    out = []
    for v in client.get("/api/vehicles").json():
        out += client.get(f"/api/vehicles/{v['id']}/records", params={"limit": 1000}).json()
    return sorted(out, key=lambda r: r["id"])


def no_record_has_zero_odometer(client):
    recs = all_records(client)
    return recs and all(r["odometer"] != 0 for r in recs if r["type"] != "odometer")


def first_record_title(client):
    return all_records(client)[0]["title"]


def edit_first_record_title(client, title):
    rec = all_records(client)[0]
    res = client.put(f"/api/records/{rec['id']}", json={**rec, "title": title}, headers=CSRF)
    assert res.status_code == 200, res.text


def demo_with_plate(plate: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(FIXTURE) as src, zipfile.ZipFile(buf, "w") as out:
        for info in src.infolist():
            data = src.read(info)
            if info.filename == "data/cartracker.db":
                data = data.replace(b"MOMWAGON", plate)  # same length, so the BSON stays valid
            out.writestr(info, data)
    return buf.getvalue()


def archive_vehicle(client, vid: int) -> None:
    v = client.get(f"/api/vehicles/{vid}").json()
    res = client.put(f"/api/vehicles/{vid}", json={**v, "archived": True}, headers=CSRF)
    assert res.status_code == 200, res.text


def zip_with_member(name: str, data: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(name, data)
    return buf.getvalue()


def bomb_zip() -> bytes:
    # a member the import reads, over the 100 MiB cap
    return zip_with_member("documents/x.pdf", b"\0" * (101 * 2**20))


def test_import_demo_end_to_end(client, data_dir):
    # catches: lost recurrence, odometer 0 kept, files not copied, photo missing
    tok = upload_demo(client)["token"]
    res = client.post(f"/api/import/lubelogger/{tok}/commit", json={}, headers=CSRF).json()
    assert res["created"]["vehicles"] >= 1
    assert any(r["repeat_months"] or r["repeat_km"] for r in client.get("/api/reminders").json())
    assert no_record_has_zero_odometer(client)
    assert any(v["photo_attachment_id"] for v in client.get("/api/vehicles").json())
    assert not (data_dir / "imports" / tok).exists()


def test_second_import_adds_nothing(client):
    # catches: duplicate imports and overwriting edits
    commit_demo(client)
    edit_first_record_title(client, "Mine")
    res = commit_demo(client)
    assert sum(res["created"].values()) == 0 and first_record_title(client) == "Mine"
    # same LubeLogger ids, different car: a backup from another install
    tok = upload(client, demo_with_plate(b"OTHERCAR")).json()["token"]
    res = client.post(f"/api/import/lubelogger/{tok}/commit", json={}, headers=CSRF).json()
    assert res["created"]["vehicles"] == 1 and res["created"]["records"] == 291
    # the same backup mapped by hand onto the first vehicle adds nothing
    first = client.get("/api/vehicles").json()[0]["id"]
    tok = upload(client, demo_with_plate(b"THIRDCAR")).json()["token"]
    body = {"vehicle_map": {"vehicles:1": first}}
    pv = client.post(f"/api/import/lubelogger/{tok}/preview", json=body, headers=CSRF).json()
    assert pv["summary"][0]["matched_vehicle_id"] == first
    res = client.post(f"/api/import/lubelogger/{tok}/commit", json=body, headers=CSRF).json()
    assert sum(res["created"].values()) == 0
    # a car added by hand with the same plate is suggested
    mine = client.post("/api/vehicles", json={"name": "Mine", "plate": "HANDMADE"}, headers=CSRF)
    pv = upload(client, demo_with_plate(b"HANDMADE")).json()["summary"][0]
    assert pv["matched_vehicle_id"] == mine.json()["id"]
    bad = {"vehicle_map": {"vehicles:1": 9999}}
    tok = upload(client, demo_with_plate(b"THIRDCAR")).json()["token"]
    res = client.post(f"/api/import/lubelogger/{tok}/preview", json=bad, headers=CSRF)
    assert res.status_code == 422 and "vehicle_map" in res.json()["detail"][0]["loc"]
    # archived cars: never suggested by plate, still found as a re-import of the same car
    archive_vehicle(client, mine.json()["id"])
    assert (
        upload(client, demo_with_plate(b"HANDMADE")).json()["summary"][0]["matched_vehicle_id"]
        is None
    )
    archive_vehicle(client, first)
    pv = upload_demo(client)["summary"][0]
    assert (pv["matched_vehicle_id"], pv["matched_vehicle_archived"]) == (first, True)
    assert pv["matched_vehicle_name"] == "1992 Jeep Cherokee"
    # source_id alone decides only when neither side has a plate or VIN
    other = next(v for v in client.get("/api/vehicles").json() if v["plate"] == "OTHERCAR")
    res = client.put(f"/api/vehicles/{other['id']}", json={**other, "plate": None}, headers=CSRF)
    assert res.status_code == 200, res.text
    pv = upload(client, demo_with_plate(b"OTHERCAR")).json()["summary"][0]
    assert pv["matched_vehicle_id"] is None


def test_malicious_zip_rejected(client, data_dir, monkeypatch):
    # catches: zip slip, zip bombs, non-LiteDB uploads, reading the body before the login check
    for z in (
        zip_with_member("documents/../../evil.txt", b"x"),
        zip_with_member("data/cartracker.db", b"not litedb"),
    ):
        assert upload(client, z).status_code == 422
    assert upload(client, bomb_zip()).status_code == 413
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for i in range(50_001):
            zf.writestr(f"x{i}", b"")
    assert upload(client, buf.getvalue()).status_code == 413
    assert not (data_dir.parent / "evil.txt").exists()
    assert not (data_dir / "evil.txt").exists()
    assert not any((data_dir / "imports").iterdir())
    read = []
    monkeypatch.setattr(Request, "form", lambda *a, **k: read.append(1))
    client.cookies.clear()
    assert upload(client, FIXTURE.read_bytes()).status_code == 401 and not read


def test_commit_copies_record_files_and_rolls_back(client, data_dir, db_session, monkeypatch):
    # catches: files on the wrong record, a failed commit leaving rows/files or eating the
    # upload, reminder distances stored in the source's miles
    when = datetime(2020, 1, 2, tzinfo=UTC)
    cols = {
        "vehicles": [{"_id": 1, "Year": 2010, "Make": "Ford", "Model": "Falcon"}],
        "servicerecords": [
            {
                "_id": 1,
                "VehicleId": 1,
                "Date": when,
                "Mileage": 1000,
                "Description": "Oil",
                "Files": [{"Name": "inv.pdf", "Location": "/documents/inv.pdf"}],
            }
        ],
        "reminderrecords": [
            {"_id": i, "VehicleId": 1, "Metric": "Odometer", "Mileage": 5000, "Description": "Oil"}
            for i in (1, 2)
        ],
    }
    plan = build_plan(cols, {"UseMPG": True}, {})
    monkeypatch.setattr(routes, "_load_plan", lambda d, opts: plan)
    token = "ab" * 16
    d = data_dir / "imports" / token
    (d / "documents").mkdir(parents=True)
    (d / "documents" / "inv.pdf").write_bytes(b"%PDF-1.4\n" + b"x" * 100)
    url = f"/api/import/lubelogger/{token}/commit"

    real, calls = routes.insert_reminder, []

    def fail_on_second(*a, **k):
        calls.append(1)
        if len(calls) == 2:
            raise RuntimeError("boom")
        return real(*a, **k)

    monkeypatch.setattr(routes, "insert_reminder", fail_on_second)
    with pytest.raises(RuntimeError):
        client.post(url, json={}, headers=CSRF)
    counts = [db_session.scalar(select(func.count()).select_from(m)) for m in TABLES]
    assert counts == [0, 0, 0, 0]
    assert not any(client.app.state.settings.attachments_dir.glob("**/*.*"))
    assert (d / "documents" / "inv.pdf").is_file()

    monkeypatch.setattr(routes, "insert_reminder", real)
    res = client.post(url, json={}, headers=CSRF)
    assert res.status_code == 200, res.text
    rec = db_session.scalars(select(Record)).one()
    att = db_session.scalars(select(Attachment)).one()
    assert (att.record_id, att.filename) == (rec.id, "inv.pdf")
    due = db_session.scalars(select(Reminder.due_km)).all()
    assert due == [pytest.approx(5000 * 1.609344)] * 2
