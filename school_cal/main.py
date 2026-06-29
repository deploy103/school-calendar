from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from school_cal.config import PROJECT_ROOT, Settings, get_settings
from school_cal.models import AppMeta, Event, EventInput, EventPatch, EVENT_TYPE_META, PERIODS
from school_cal.storage import EventNotFoundError, EventStore, StorageError


STATIC_DIR = PROJECT_ROOT / "school_cal" / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    store = EventStore(resolved_settings.data_file)

    app = FastAPI(title="School Calendar", docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        if request.url.path == "/" or request.url.path.startswith("/assets/"):
            response.headers["Cache-Control"] = "no-store, max-age=0, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "base-uri 'none'; "
            "frame-ancestors 'none'; "
            "form-action 'self'"
        )
        return response

    @app.exception_handler(StorageError)
    async def handle_storage_error(request: Request, exc: StorageError):
        return JSONResponse(status_code=500, content={"detail": "일정 데이터를 처리할 수 없습니다."})

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> FileResponse:
        return FileResponse(STATIC_DIR / "favicon.png", media_type="image/png")

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/meta", response_model=AppMeta)
    async def meta() -> AppMeta:
        return AppMeta(
            periods=PERIODS,
            event_types=EVENT_TYPE_META,
            today_rice_url=resolved_settings.today_rice_url,
        )

    @app.get("/api/events", response_model=list[Event])
    async def list_events(start: date | None = None, end: date | None = None) -> list[Event]:
        if start and end and end < start:
            raise HTTPException(status_code=422, detail="end must be greater than or equal to start")
        events = store.list_events()
        if start:
            events = [event for event in events if event.date >= start]
        if end:
            events = [event for event in events if event.date <= end]
        return events

    @app.post("/api/events", response_model=Event, status_code=201)
    async def create_event(payload: EventInput) -> Event:
        return store.create_event(payload)

    @app.patch("/api/events/{event_id}", response_model=Event)
    async def update_event(event_id: str, payload: EventPatch) -> Event:
        try:
            return store.update_event(event_id, payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except EventNotFoundError as exc:
            raise HTTPException(status_code=404, detail="event not found") from exc

    @app.delete("/api/events/{event_id}", status_code=204)
    async def delete_event(event_id: str) -> Response:
        try:
            store.delete_event(event_id)
        except EventNotFoundError as exc:
            raise HTTPException(status_code=404, detail="event not found") from exc
        return Response(status_code=204)

    return app


app = create_app()
