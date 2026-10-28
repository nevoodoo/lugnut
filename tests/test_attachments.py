import pytest
from conftest import CSRF
from test_records import _new_vehicle, post_record

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\0" * 32
MINIMAL_WORK = {"type": "work", "date": "2026-09-01", "details": {"category": "service"}}


@pytest.fixture
def vehicle(client, logged_in):
    return _new_vehicle(client)


@pytest.fixture
def data_dir(client):
    return client.app.state.settings.data_dir


def upload(client, vehicle_id, name="a.png", body=PNG_BYTES, record_id=None):
    data = {"record_id": str(record_id)} if record_id is not None else {}
    return client.post(
        f"/api/vehicles/{vehicle_id}/attachments",
        files={"file": (name, body, "application/octet-stream")},
        data=data,
        headers=CSRF,
    )


def test_upload_returns_object_and_never_escapes_dir(client, vehicle, data_dir):
    # catches: JSON-quoted string responses (LubeLogger) and path traversal via filename
    r = upload(client, vehicle, name="../../evil.png", body=PNG_BYTES)
    assert isinstance(r.json(), dict) and r.json()["filename"] == "evil.png"
    assert list((data_dir / "attachments").iterdir())  # stored inside
    assert not (data_dir.parent / "evil.png").exists()
    assert client.get(f"/api/attachments/{r.json()['id']}/file").content == PNG_BYTES


def test_oversized_and_wrong_type_rejected(client, vehicle):
    # catches: unbounded uploads and executable content
    assert upload(client, vehicle, body=PNG_BYTES + b"\0" * (25 * 2**20)).status_code == 413
    assert upload(client, vehicle, name="x.png", body=b"<html>").status_code == 415


def test_deleting_vehicle_removes_records_and_files(client, vehicle, data_dir):
    # catches: orphaned rows or files left on disk
    rec = post_record(client, vehicle, MINIMAL_WORK)
    assert upload(client, vehicle, body=PNG_BYTES, record_id=rec["id"]).status_code == 201
    client.delete(f"/api/vehicles/{vehicle}", headers=CSRF)
    assert not any((data_dir / "attachments").iterdir())
    assert client.get(f"/api/records/{rec['id']}").status_code == 404
