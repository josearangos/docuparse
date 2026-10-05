"""PaddleOCR-VL-1.6 adapter. The only module that imports the engine library."""

import logging
from html.parser import HTMLParser

from docuparse.engine.base import EnginePage
from docuparse.schemas import BoundingBox, Cell, Element, Table

log = logging.getLogger("docuparse.engine")

_FORMULA = {"formula", "display_formula", "inline_formula", "formula_number"}
_CHART = {"chart"}
_OTHER = {"image", "seal", "header_image", "footer_image", "figure", "figure_title"}
_TABLE = {"table"}


class _TableParser(HTMLParser):
    """Turns an HTML table into rows of cells with spans."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[Cell]] = []
        self._row: list[Cell] | None = None
        self._cell: dict | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th"):
            a = dict(attrs)
            self._cell = {
                "text": "",
                "row_span": _span(a.get("rowspan")),
                "col_span": _span(a.get("colspan")),
            }

    def handle_data(self, data):
        if self._cell is not None:
            self._cell["text"] += data

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._cell["text"] = " ".join(self._cell["text"].split())
            self._row.append(Cell(**self._cell))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None


def _span(value) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return 1


def parse_table(content: str) -> list[list[Cell]]:
    parser = _TableParser()
    parser.feed(content or "")
    return parser.rows


def _table_text(rows: list[list[Cell]]) -> str:
    return "\n".join(" | ".join(c.text for c in row) for row in rows)


def map_page(page_number: int, data: dict) -> EnginePage:
    """Convert one native page dict into the neutral page result."""
    page = EnginePage(
        page_number=page_number,
        width=int(data.get("width") or 0),
        height=int(data.get("height") or 0),
    )
    order = 0
    for block in data.get("parsing_res_list") or []:
        label = block.get("block_label") or ""
        content = block.get("block_content") or ""
        box = block.get("block_bbox") or [0, 0, 0, 0]
        bbox = BoundingBox(left=box[0], top=box[1], right=box[2], bottom=box[3])
        order += 1
        if label in _TABLE:
            rows = parse_table(content)
            text = _table_text(rows) if rows else content
            table = Table(bbox=bbox, reading_order=order, text=text, rows=rows)
            page.tables.append(table)
            page.elements.append(table)
            continue
        if label in _FORMULA:
            etype = "formula"
        elif label in _CHART:
            etype = "chart"
        elif label in _OTHER:
            etype = "other"
        else:
            etype = "text"
        page.elements.append(
            Element(type=etype, bbox=bbox, reading_order=order, text=content or None)
        )
    return page


class PaddleVLEngine:
    def __init__(self) -> None:
        self._pipeline = None

    def load(self) -> None:
        from paddleocr import PaddleOCRVL

        self._pipeline = PaddleOCRVL(pipeline_version="v1.6")
        self._warm_up()

    def _warm_up(self) -> None:
        """Run one small inference so the first real request does not pay start-up costs."""
        import os
        import tempfile

        from PIL import Image, ImageDraw

        img = Image.new("RGB", (400, 120), "white")
        ImageDraw.Draw(img).text((20, 40), "Hola mundo", fill="black")
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        try:
            img.save(path)
            list(self._pipeline.predict(path))
        except Exception as exc:  # a failed warm-up must not stop the service
            log.warning("warm-up failed: %s", exc)
        finally:
            os.remove(path)

    def is_ready(self) -> bool:
        return self._pipeline is not None

    def parse(self, path: str) -> list[EnginePage]:
        pages: list[EnginePage] = []
        for index, result in enumerate(self._pipeline.predict(path), start=1):
            try:
                native = result.json
                native = native.get("res", native)
                pages.append(map_page(index, native))
            except Exception as exc:  # one bad page must not fail the document
                log.warning("page %s mapping failed: %s", index, exc)
                pages.append(EnginePage(page_number=index, error="mapping_failed"))
        return pages
