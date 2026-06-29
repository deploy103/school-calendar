from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    data_file: Path = PROJECT_ROOT / "data" / "events.json"
    today_rice_url: str = "/today-rice"

    def __post_init__(self) -> None:
        object.__setattr__(self, "data_file", Path(self.data_file))
        parsed = urlparse(self.today_rice_url)
        is_relative = self.today_rice_url.startswith("/")
        is_http = parsed.scheme in {"http", "https"} and bool(parsed.netloc)
        if not (is_relative or is_http):
            raise ValueError("today_rice_url must be an absolute path or http(s) URL")


@lru_cache
def get_settings() -> Settings:
    return Settings(
        data_file=Path(os.getenv("SCHOOL_CAL_DATA_FILE", Settings.data_file)),
        today_rice_url=os.getenv("SCHOOL_CAL_TODAY_RICE_URL", Settings.today_rice_url),
    )
