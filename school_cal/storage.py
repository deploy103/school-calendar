from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from school_cal.models import Event, EventInput, EventPatch, PERIODS

try:
    import fcntl
except ImportError:  # pragma: no cover - fcntl is unavailable on Windows.
    fcntl = None

FILE_LOCK_SUPPORTED = fcntl is not None


class EventNotFoundError(Exception):
    pass


class StorageError(Exception):
    pass


class EventStore:
    def __init__(self, data_file: Path) -> None:
        self.data_file = data_file
        self.lock_file = data_file.with_name(f"{data_file.name}.lock")
        self._lock = threading.RLock()

    def list_events(self) -> list[Event]:
        with self._file_lock(exclusive=False):
            events = self._read_events()
        return sorted(events, key=lambda event: (event.date, PERIODS.index(event.period), event.created_at))

    def create_event(self, payload: EventInput) -> Event:
        now = self._now()
        event = Event(
            id=uuid4().hex,
            created_at=now,
            updated_at=now,
            **payload.model_dump(),
        )
        with self._file_lock(exclusive=True):
            events = self._read_events()
            events.append(event)
            self._write_events(events)
        return event

    def update_event(self, event_id: str, payload: EventPatch) -> Event:
        changes = payload.model_dump(exclude_none=True, exclude_unset=True)
        if not changes:
            raise ValueError("at least one field is required")

        with self._file_lock(exclusive=True):
            events = self._read_events()
            for index, event in enumerate(events):
                if event.id == event_id:
                    updated = Event.model_validate(
                        {
                            **event.model_dump(),
                            **changes,
                            "updated_at": self._now(),
                        }
                    )
                    events[index] = updated
                    self._write_events(events)
                    return updated
        raise EventNotFoundError(event_id)

    def delete_event(self, event_id: str) -> None:
        with self._file_lock(exclusive=True):
            events = self._read_events()
            remaining = [event for event in events if event.id != event_id]
            if len(remaining) == len(events):
                raise EventNotFoundError(event_id)
            self._write_events(remaining)

    def _read_events(self) -> list[Event]:
        if not self.data_file.exists():
            return []
        try:
            with self.data_file.open("r", encoding="utf-8") as file:
                raw_events = json.load(file)
            if not isinstance(raw_events, list):
                raise StorageError("event data must be a list")
            return [Event.model_validate(item) for item in raw_events]
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise StorageError("event data could not be loaded") from exc

    def _write_events(self, events: list[Event]) -> None:
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=".events-", suffix=".json", dir=self.data_file.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump([event.model_dump(mode="json") for event in events], file, ensure_ascii=False, indent=2)
                file.write("\n")
            os.replace(temp_name, self.data_file)
        except OSError as exc:
            raise StorageError("event data could not be saved") from exc
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @contextmanager
    def _file_lock(self, *, exclusive: bool) -> Iterator[None]:
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            if fcntl is None:
                yield
                return

            with self.lock_file.open("a+", encoding="utf-8") as lock_file:
                operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
                fcntl.flock(lock_file.fileno(), operation)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
