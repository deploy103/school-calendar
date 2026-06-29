from fastapi.testclient import TestClient

from school_cal.config import Settings
from school_cal.main import create_app


def make_client(tmp_path):
    settings = Settings(data_file=tmp_path / "events.json", today_rice_url="/today-rice")
    return TestClient(create_app(settings))


def test_meta_and_health(tmp_path):
    client = make_client(tmp_path)

    assert client.get("/api/health").json() == {"status": "ok"}
    favicon = client.get("/favicon.ico")
    assert favicon.status_code == 200
    assert favicon.headers["content-type"] == "image/png"

    meta = client.get("/api/meta").json()

    assert "1교시" in meta["periods"]
    assert meta["today_rice_url"] == "/today-rice"
    assert {item["value"] for item in meta["event_types"]} >= {"수행평가", "특수수업"}


def test_event_lifecycle(tmp_path):
    client = make_client(tmp_path)

    created = client.post(
        "/api/events",
        json={"date": "2026-06-29", "period": "3교시", "type": "수행평가", "title": " 수학 수행평가  "},
    )
    assert created.status_code == 201
    event = created.json()
    assert event["title"] == "수학 수행평가"

    listed = client.get("/api/events?start=2026-06-01&end=2026-06-30").json()
    assert [item["id"] for item in listed] == [event["id"]]

    updated = client.patch(
        f"/api/events/{event['id']}",
        json={"period": "5교시", "type": "특수수업", "title": "과학실 이동"},
    )
    assert updated.status_code == 200
    assert updated.json()["period"] == "5교시"

    deleted = client.delete(f"/api/events/{event['id']}")
    assert deleted.status_code == 204
    assert client.get("/api/events").json() == []


def test_validation_rejects_bad_payloads(tmp_path):
    client = make_client(tmp_path)

    invalid_type = client.post(
        "/api/events",
        json={"date": "2026-06-29", "period": "3교시", "type": "시험", "title": "국어"},
    )
    assert invalid_type.status_code == 422

    blank_title = client.post(
        "/api/events",
        json={"date": "2026-06-29", "period": "3교시", "type": "수행평가", "title": "   "},
    )
    assert blank_title.status_code == 422

    bad_range = client.get("/api/events?start=2026-07-01&end=2026-06-01")
    assert bad_range.status_code == 422
