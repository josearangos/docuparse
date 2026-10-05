"""Document Processing Service: validates, runs the engine, builds the response."""

import logging
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

from docuparse import validation
from docuparse.engine.base import DocumentEngine, EnginePage
from docuparse.errors import ApiError
from docuparse.schemas import DocumentInfo, OcrResponse, PageResult, WarningItem

log = logging.getLogger("docuparse.service")

TIMEOUT_SECONDS = float(os.environ.get("DOCUPARSE_TIMEOUT_SECONDS", "120"))
LOW_CONFIDENCE = 0.5
MIN_PAGE_SIDE = 300  # pixels; smaller pages are too low-resolution to read reliably
MAX_SYMBOL_RATIO = 0.3  # share of odd symbols in recognized text that signals garbling
_COMMON = set(".,;:-–—_/()[]{}$%&'\"“”¿?¡!°ºª#@+=*<>|\\~·•…€£")
_SUFFIX = {"pdf": ".pdf", "png": ".png", "jpeg": ".jpg"}


class DocumentService:
    def __init__(self, engine: DocumentEngine, timeout: float = TIMEOUT_SECONDS):
        self.engine = engine
        self.timeout = timeout
        # one worker: inference runs one document at a time
        self._pool = ThreadPoolExecutor(max_workers=1)
        # a job that timed out cannot be stopped; new work is refused until it finishes
        self._abandoned = None

    def is_ready(self) -> bool:
        return self.engine.is_ready()

    def process(self, file_name: str, data: bytes) -> OcrResponse:
        if not self.engine.is_ready():
            raise ApiError(503, "service_not_ready", "The service is not ready yet.")
        if self._abandoned is not None:
            if not self._abandoned.done():
                raise ApiError(
                    503, "service_not_ready", "The service is still finishing a previous document."
                )
            self._abandoned = None
        file_type, page_count = validation.validate(data)
        started = time.monotonic()
        engine_pages = self._run(data, file_type)

        by_number = {p.page_number: p for p in engine_pages}
        pages: list[PageResult] = []
        overall: list[WarningItem] = []
        for number in range(1, page_count + 1):
            page = by_number.get(number) or EnginePage(page_number=number, error="missing")
            result = self._page_result(page)
            pages.append(result)
            overall.extend(result.warnings)

        if all(p.status == "failed" for p in pages):
            raise ApiError(500, "processing_failed", "The document could not be processed.")

        elapsed_ms = int((time.monotonic() - started) * 1000)
        log.info("processed pages=%d type=%s ms=%d", page_count, file_type, elapsed_ms)
        return OcrResponse(
            document=DocumentInfo(
                file_name=file_name,
                file_type=file_type,
                size_bytes=len(data),
                page_count=page_count,
                processing_time_ms=elapsed_ms,
            ),
            pages=pages,
            warnings=overall,
        )

    def _run(self, data: bytes, file_type: str) -> list[EnginePage]:
        fd, path = tempfile.mkstemp(suffix=_SUFFIX[file_type])
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        future = self._pool.submit(self.engine.parse, path)
        # delete the file as soon as the engine is done, even after a timeout
        future.add_done_callback(lambda _f: _remove(path))
        try:
            return future.result(timeout=self.timeout)
        except FutureTimeout:
            self._abandoned = future
            raise ApiError(504, "processing_timeout", "Processing exceeded the time limit.") from None
        except Exception:
            log.exception("engine failure")
            raise ApiError(500, "processing_failed", "The document could not be processed.") from None

    @staticmethod
    def _page_result(page: EnginePage) -> PageResult:
        n = page.page_number
        if page.error is not None:
            return PageResult(
                page_number=n,
                status="failed",
                width=page.width,
                height=page.height,
                text="",
                warnings=[
                    WarningItem(
                        code="page_failed", message=f"Page {n} could not be processed.", page_number=n
                    )
                ],
            )
        elements = sorted(page.elements, key=lambda e: e.reading_order)
        text = "\n".join(e.text for e in elements if e.text)
        warnings: list[WarningItem] = []
        if not text.strip():
            warnings.append(
                WarningItem(
                    code="no_content_detected",
                    message=f"No content was detected on page {n}.",
                    page_number=n,
                )
            )
        if _low_quality(page, elements, text):
            warnings.append(
                WarningItem(
                    code="low_quality_page",
                    message=f"Recognition on page {n} may be incomplete.",
                    page_number=n,
                )
            )
        return PageResult(
            page_number=n,
            status="processed",
            width=page.width,
            height=page.height,
            text=text,
            elements=elements,
            tables=[t for t in page.tables],
            formulas=[e for e in elements if e.type == "formula"],
            charts=[e for e in elements if e.type == "chart"],
            warnings=warnings,
        )


def _low_quality(page: EnginePage, elements, text: str) -> bool:
    """Engine-independent signals that recognition is likely incomplete."""
    confidences = [e.confidence for e in elements if e.confidence is not None]
    if confidences and min(confidences) < LOW_CONFIDENCE:
        return True
    if page.width and page.height and min(page.width, page.height) < MIN_PAGE_SIDE and text.strip():
        return True
    chars = [c for c in text if not c.isspace()]
    if "\ufffd" in text:
        return True
    if len(chars) >= 20:
        odd = sum(1 for c in chars if not c.isalnum() and c not in _COMMON)
        return odd / len(chars) > MAX_SYMBOL_RATIO
    return False


def _remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass
