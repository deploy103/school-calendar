from __future__ import annotations

from datetime import date as Date
from datetime import datetime as DateTime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


PERIODS = ["조회", "1교시", "2교시", "3교시", "4교시", "5교시", "6교시", "7교시", "방과후", "종례"]

EVENT_TYPE_META = [
    {"value": "수행평가", "label": "수행평가", "tone": "rose"},
    {"value": "특수수업", "label": "특수수업", "tone": "cyan"},
    {"value": "행사", "label": "학급행사", "tone": "amber"},
    {"value": "기타", "label": "기타일정", "tone": "violet"},
]

Period = Literal["조회", "1교시", "2교시", "3교시", "4교시", "5교시", "6교시", "7교시", "방과후", "종례"]
EventType = Literal["수행평가", "특수수업", "행사", "기타"]


def normalize_title(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise ValueError("title is required")
    return normalized


class EventInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: Date
    period: Period
    type: EventType
    title: str = Field(min_length=1, max_length=80)

    @field_validator("title")
    @classmethod
    def title_must_be_visible_text(cls, value: str) -> str:
        return normalize_title(value)


class EventPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: Date | None = None
    period: Period | None = None
    type: EventType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("title")
    @classmethod
    def title_must_be_visible_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_title(value)


class Event(EventInput):
    id: str
    created_at: DateTime
    updated_at: DateTime


class EventTypeOption(BaseModel):
    value: str
    label: str
    tone: str


class AppMeta(BaseModel):
    periods: list[str]
    event_types: list[EventTypeOption]
    today_rice_url: str
