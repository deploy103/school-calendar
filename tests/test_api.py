from concurrent.futures import ProcessPoolExecutor
from itertools import repeat
from pathlib import Path
import time

import pytest
from fastapi.testclient import TestClient

from school_cal.config import Settings
from school_cal.main import create_app
from school_cal.models import EventInput
from school_cal.storage import FILE_LOCK_SUPPORTED, EventStore


def create_event_in_process(data_file: str, index: int, start_at: float) -> str:
    while time.time() < start_at:
        time.sleep(0.001)

    store = EventStore(Path(data_file))
    event = store.create_event(
        EventInput(
            date="2026-06-29",
            period="3교시",
            type="수행평가",
            title=f"동시 일정 {index}",
        )
    )
    return event.id


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


@pytest.mark.parametrize("field", ["date", "period", "type", "title"])
def test_patch_rejects_explicit_null_without_corrupting_event(tmp_path, field):
    client = make_client(tmp_path)
    created = client.post(
        "/api/events",
        json={"date": "2026-06-29", "period": "3교시", "type": "수행평가", "title": "수학 수행평가"},
    ).json()

    rejected = client.patch(f"/api/events/{created['id']}", json={field: None})

    assert rejected.status_code == 422
    listed = client.get("/api/events").json()
    assert listed[0]["id"] == created["id"]
    assert listed[0]["title"] == "수학 수행평가"


def test_patch_rejects_empty_payload(tmp_path):
    client = make_client(tmp_path)
    created = client.post(
        "/api/events",
        json={"date": "2026-06-29", "period": "3교시", "type": "수행평가", "title": "수학 수행평가"},
    ).json()

    rejected = client.patch(f"/api/events/{created['id']}", json={})

    assert rejected.status_code == 422


def test_store_preserves_parallel_process_creates(tmp_path):
    if not FILE_LOCK_SUPPORTED:
        pytest.skip("cross-process file locking is unavailable on this platform")

    data_file = tmp_path / "events.json"
    expected_count = 12
    start_at = time.time() + 0.2

    with ProcessPoolExecutor(max_workers=expected_count) as executor:
        ids = list(
            executor.map(
                create_event_in_process,
                repeat(str(data_file)),
                range(expected_count),
                repeat(start_at),
            )
        )

    events = EventStore(data_file).list_events()

    assert len(events) == expected_count
    assert {event.id for event in events} == set(ids)
