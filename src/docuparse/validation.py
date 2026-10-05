"""Upload validation, performed before any inference (FR-002 to FR-006)."""

import io

from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from docuparse.errors import ApiError

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 20

SUPPORTED = "PDF, PNG, JPEG/JPG"


def detect_type(data: bytes) -> str | None:
    if data.startswith(b"%PDF-"):
        return "pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    return None


def validate(data: bytes) -> tuple[str, int]:
    """Return (file_type, page_count) or raise ApiError."""
    if len(data) == 0:
        raise ApiError(422, "unreadable_file", "The file is empty.")
    if len(data) > MAX_BYTES:
        raise ApiError(
            413, "file_too_large", f"The file exceeds the {MAX_BYTES // (1024 * 1024)} MB limit."
        )
    file_type = detect_type(data)
    if file_type is None:
        raise ApiError(415, "unsupported_file_type", f"Unsupported file. Supported: {SUPPORTED}.")
    if file_type == "pdf":
        return file_type, _pdf_pages(data)
    _check_image(data)
    return file_type, 1


def _pdf_pages(data: bytes) -> int:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ApiError(422, "unreadable_file", "Password-protected PDFs are not supported.")
        pages = len(reader.pages)
    except ApiError:
        raise
    except (PyPdfError, ValueError, OSError, KeyError, TypeError):
        raise ApiError(422, "unreadable_file", "The PDF is corrupt or unreadable.") from None
    if pages == 0:
        raise ApiError(422, "unreadable_file", "The PDF has no pages.")
    if pages > MAX_PAGES:
        raise ApiError(413, "too_many_pages", f"The PDF exceeds the {MAX_PAGES} page limit.")
    return pages


def _check_image(data: bytes) -> None:
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.load()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        raise ApiError(422, "unreadable_file", "The image is corrupt or unreadable.") from None
