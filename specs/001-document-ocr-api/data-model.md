# Data Model: DocuParse

The model describes the public, engine-neutral response. Nothing is stored; these are response
shapes only. Field names are the contract; see [contracts/openapi.yaml](contracts/openapi.yaml).

## OcrResponse (200 from `POST /ocr`)

| Field | Type | Notes |
|-------|------|-------|
| `document` | DocumentInfo | document-level facts |
| `pages` | list of PageResult | one per page, ordered, starting at 1 |
| `warnings` | list of Warning | overall list; empty when none |

## DocumentInfo

| Field | Type | Notes |
|-------|------|-------|
| `file_name` | string | name as submitted |
| `file_type` | `pdf` \| `png` \| `jpeg` | detected from content |
| `size_bytes` | integer | |
| `page_count` | integer | |
| `processing_time_ms` | integer | |

## PageResult

| Field | Type | Notes |
|-------|------|-------|
| `page_number` | integer | starts at 1 |
| `status` | `processed` \| `failed` | failed pages have empty content |
| `width`, `height` | integer | page size in pixels as processed |
| `text` | string | full page text in reading order |
| `elements` | list of Element | all elements in reading order |
| `tables` | list of Table | tables, same items as `table` elements |
| `formulas` | list of Element | formula elements |
| `charts` | list of Element | chart and visual elements |
| `warnings` | list of Warning | page-level; empty when none |

All collections are always present, empty when nothing is detected (FR-018).

## Element

| Field | Type | Notes |
|-------|------|-------|
| `type` | `text` \| `table` \| `formula` \| `chart` \| `other` | |
| `bbox` | BoundingBox | pixels, page as processed |
| `reading_order` | integer | starts at 1 within the page |
| `text` | string \| null | recognized text, formula content, or chart text/data when available |
| `confidence` | number 0 to 1 \| null | null when the engine gives none |

## BoundingBox

`left`, `top`, `right`, `bottom`: numbers in pixels, with `left < right` and `top < bottom`.

## Table (extends Element, `type = table`)

| Field | Type | Notes |
|-------|------|-------|
| `rows` | list of list of Cell | ordered rows, each an ordered list of cells |

### Cell

| Field | Type | Notes |
|-------|------|-------|
| `text` | string | cell text as printed |
| `row_span` | integer | 1 when not merged |
| `col_span` | integer | 1 when not merged |

There is no HTML or Markdown rendering of tables (clarification).

## Warning

| Field | Type | Notes |
|-------|------|-------|
| `code` | string | `no_content_detected`, `low_quality_page`, `page_failed` |
| `message` | string | human-readable |
| `page_number` | integer \| null | null for document-level warnings |

## ErrorResponse (all non-2xx from `POST /ocr`)

| Field | Type | Notes |
|-------|------|-------|
| `error.code` | string | machine-readable, see table below |
| `error.message` | string | human-readable, no internals |

| HTTP | `error.code` | Cause |
|------|--------------|-------|
| 400 | `missing_file` / `multiple_files` | no file, or more than one |
| 413 | `file_too_large` / `too_many_pages` | over 10 MB, or over 20 pages |
| 415 | `unsupported_file_type` | not PDF/PNG/JPEG, or content mismatches |
| 422 | `unreadable_file` | corrupt, password-protected, zero bytes |
| 500 | `processing_failed` | every page failed |
| 503 | `service_not_ready` | engine not loaded, or still finishing a timed-out job |
| 504 | `processing_timeout` | exceeded 120 s |
| 404 / 405 | `not_found` / `method_not_allowed` | unknown route or wrong method |
| other 4xx | `bad_request` | request could not be handled |

## HealthResponse (`GET /health`)

| Field | Type | Notes |
|-------|------|-------|
| `status` | `healthy` \| `not_ready` | 200 when healthy, 503 otherwise |
| `service` | string | `docuparse` |
| `version` | string | service version |

## State transitions

Page: `processed` or `failed` (final). Service: `not_ready` to `healthy` once the engine has loaded.
