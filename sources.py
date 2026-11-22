"""Knowledge-base records loaded from the extracted SCU department pages."""

import json
from dataclasses import dataclass, field
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / "data" / "scu_pages.json"


@dataclass(frozen=True)
class Source:
    id: str
    page: str
    title: str
    url: str
    text: str
    names: list[str]
    links: list[dict] = field(default_factory=list)


def load_sources() -> tuple[Source, ...]:
    return tuple(Source(**record) for record in json.loads(DATA_FILE.read_text(encoding="utf-8")))
