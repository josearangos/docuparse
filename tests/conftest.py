import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter

from docuparse.engine.base import EnginePage
from docuparse.main import create_app
from docuparse.schemas import BoundingBox, Cell, Element, Table
from docuparse.service import DocumentService

BOX = BoundingBox(left=10, top=10, right=200, bottom=40)
SPANISH = "Factura N° 001 – Señor Muñoz: ¡Total! ¿Pagado? $1.250.000,50 áéíóúü"


class FakeEngine:
    """Returns canned neutral pages; behaviour is tweakable per test."""

    def __init__(self):
        self.ready = True
        self.fail_pages: set[int] = set()
        self.blank = False
        self.low_confidence = False
        self.raise_error = False
        self.delay = 0.0

    def is_ready(self):
        return self.ready

    def parse(self, path):
        import time

        time.sleep(self.delay)
        if self.raise_error:
            raise RuntimeError("boom internal paddle detail")
        with open(path, "rb") as f:
            head = f.read(5)
        count = 1
        if head.startswith(b"%PDF"):
            from pypdf import PdfReader

            count = len(PdfReader(path).pages)
        return [self._page(i) for i in range(1, count + 1)]

    def _page(self, n):
        if n in self.fail_pages:
            return EnginePage(page_number=n, width=100, height=100, error="x")
        page = EnginePage(page_number=n, width=800, height=1000)
        if self.blank:
            return page
        conf = 0.2 if self.low_confidence else None
        page.elements.append(
            Element(type="text", bbox=BOX, reading_order=1, text=SPANISH, confidence=conf)
        )
        table = Table(
            bbox=BOX,
            reading_order=2,
            text="a | b",
            rows=[[Cell(text="a"), Cell(text="b", col_span=2)]],
        )
        page.tables.append(table)
        page.elements.append(table)
        page.elements.append(Element(type="formula", bbox=BOX, reading_order=3, text="E=mc^2"))
        page.elements.append(Element(type="chart", bbox=BOX, reading_order=4, text=None))
        return page


@pytest.fixture
def engine():
    return FakeEngine()


@pytest.fixture
def client(engine):
    app = create_app(DocumentService(engine, timeout=1))
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def make_png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), "white").save(buf, "PNG")
    return buf.getvalue()


def make_pdf(pages: int = 1, password: str | None = None) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    if password:
        writer.encrypt(password)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()
