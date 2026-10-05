"""Public, engine-neutral request/response models (see data-model.md)."""

from typing import Literal

from pydantic import BaseModel, Field


class WarningItem(BaseModel):
    code: Literal["no_content_detected", "low_quality_page", "page_failed"]
    message: str
    page_number: int | None = None


class BoundingBox(BaseModel):
    left: float
    top: float
    right: float
    bottom: float


class Element(BaseModel):
    type: Literal["text", "table", "formula", "chart", "other"]
    bbox: BoundingBox
    reading_order: int = Field(ge=1)
    text: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class Cell(BaseModel):
    text: str
    row_span: int = Field(default=1, ge=1)
    col_span: int = Field(default=1, ge=1)


class Table(Element):
    type: Literal["table"] = "table"
    rows: list[list[Cell]] = Field(default_factory=list)


class PageResult(BaseModel):
    page_number: int = Field(ge=1)
    status: Literal["processed", "failed"]
    width: int
    height: int
    text: str
    elements: list[Element] = Field(default_factory=list)
    tables: list[Table] = Field(default_factory=list)
    formulas: list[Element] = Field(default_factory=list)
    charts: list[Element] = Field(default_factory=list)
    warnings: list[WarningItem] = Field(default_factory=list)


class DocumentInfo(BaseModel):
    file_name: str
    file_type: Literal["pdf", "png", "jpeg"]
    size_bytes: int
    page_count: int
    processing_time_ms: int


class OcrResponse(BaseModel):
    document: DocumentInfo
    pages: list[PageResult]
    warnings: list[WarningItem] = Field(default_factory=list)


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class HealthResponse(BaseModel):
    status: Literal["healthy", "not_ready"]
    service: str
    version: str
