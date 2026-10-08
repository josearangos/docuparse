"""RapidOCR adapter (PP-OCRv6 via ONNX Runtime): fast CPU text engine, no table/formula parsing."""

import logging

import numpy as np

from docuparse.engine.base import EnginePage
from docuparse.schemas import BoundingBox, Element

log = logging.getLogger("docuparse.engine")

PDF_SCALE = 2.0  # 72 dpi * 2 = 144 dpi


def map_page(page_number: int, width: int, height: int, boxes, texts, scores) -> EnginePage:
    """Convert one RapidOCR result into the neutral page result, one text element per line."""
    page = EnginePage(page_number=page_number, width=width, height=height)
    lines = []
    for box, text, score in zip(boxes, texts, scores):
        xs = [float(p[0]) for p in box]
        ys = [float(p[1]) for p in box]
        lines.append((min(ys), min(xs), max(xs), max(ys), text, float(score)))
    lines.sort(key=lambda l: (round(l[0] / 10), l[1]))  # top-to-bottom, then left-to-right
    for order, (top, left, right, bottom, text, score) in enumerate(lines, start=1):
        page.elements.append(
            Element(
                type="text",
                bbox=BoundingBox(left=left, top=top, right=right, bottom=bottom),
                reading_order=order,
                text=text,
                confidence=min(max(score, 0.0), 1.0),
            )
        )
    return page


class RapidOcrEngine:
    def __init__(self) -> None:
        self._ocr = None

    def load(self) -> None:
        from rapidocr import OCRVersion, RapidOCR

        version = OCRVersion.PPOCRV6
        self._ocr = RapidOCR(
            params={"Det.ocr_version": version, "Rec.ocr_version": version, "Rec.lang_type": "es"}
        )
        self._ocr(np.full((120, 400, 3), 255, dtype=np.uint8))  # warm-up

    def is_ready(self) -> bool:
        return self._ocr is not None

    def _images(self, path: str):
        if path.lower().endswith(".pdf"):
            import pypdfium2 as pdfium

            pdf = pdfium.PdfDocument(path)
            try:
                for page in pdf:
                    yield np.array(page.render(scale=PDF_SCALE).to_pil().convert("RGB"))
            finally:
                pdf.close()
        else:
            from PIL import Image

            yield np.array(Image.open(path).convert("RGB"))

    def parse(self, path: str) -> list[EnginePage]:
        pages: list[EnginePage] = []
        for index, image in enumerate(self._images(path), start=1):
            try:
                result = self._ocr(image)
                height, width = image.shape[:2]
                if result.txts is None:
                    pages.append(EnginePage(page_number=index, width=width, height=height))
                else:
                    pages.append(
                        map_page(index, width, height, result.boxes, result.txts, result.scores)
                    )
            except Exception as exc:  # one bad page must not fail the document
                log.warning("page %s failed: %s", index, exc)
                pages.append(EnginePage(page_number=index, error="engine_failed"))
        return pages
