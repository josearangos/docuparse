"""Engine interface. Engine-specific types never cross this boundary."""

from dataclasses import dataclass, field
from typing import Protocol

from docuparse.schemas import Element, Table


@dataclass
class EnginePage:
    """Neutral result for one page; `error` is set when the page failed."""

    page_number: int
    width: int = 0
    height: int = 0
    elements: list[Element] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    error: str | None = None


class DocumentEngine(Protocol):
    def is_ready(self) -> bool: ...

    def parse(self, path: str) -> list[EnginePage]: ...
