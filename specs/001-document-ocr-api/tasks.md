---
description: "Task list for DocuParse Document Intelligence API"
---

# Tasks: DocuParse Document Intelligence API

**Input**: Design documents from `/specs/001-document-ocr-api/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md

**Tests**: Included, because plan.md and quickstart.md call for contract and integration tests with a
fake engine. Real-engine tests on Spanish samples are opt-in.

**Organization**: Grouped by user story so each can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1 to US4, matching the user stories in spec.md

## Phase 1: Setup

**Purpose**: Project initialization

- [X] T001 Create the package layout from plan.md: `src/docuparse/`, `src/docuparse/api/`, `src/docuparse/engine/`, `tests/contract/`, `tests/integration/`, `tests/unit/`, `tests/samples/`, each Python package with an `__init__.py`
- [X] T002 Update `pyproject.toml` with dependencies (fastapi, uvicorn, python-multipart, pypdf, pillow, pydantic, paddlepaddle, paddleocr with its document-parser extra) and dev dependencies (pytest, httpx), set the `src` layout, then run `uv sync`
- [X] T003 [P] Delete the stub root `main.py` and add `.gitignore` entries for `.venv/`, `__pycache__/`, and model caches

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared pieces every story needs. No story work starts before this is done.

- [X] T004 [P] Define the public models in `src/docuparse/schemas.py` exactly as in data-model.md: OcrResponse, DocumentInfo, PageResult (`status` is `processed` or `failed`; `elements`, `tables`, `formulas`, `charts`, `warnings` always present), Element (`type` is `text`, `table`, `formula`, `chart` or `other`; `confidence` nullable, 0 to 1), BoundingBox (`left`, `top`, `right`, `bottom` in pixels), Table with `rows` of Cell (`text`, `row_span`, `col_span`, spans at least 1), Warning (`code` is `no_content_detected`, `low_quality_page` or `page_failed`; `page_number` nullable), ErrorResponse, HealthResponse
- [X] T005 [P] Define the engine interface in `src/docuparse/engine/base.py`: a protocol with `is_ready()` and `parse(path)` returning one neutral result or error per page (no engine-specific types)
- [X] T006 Create the app in `src/docuparse/main.py`: build the FastAPI app, load the engine once at startup, register routers, and add exception handlers so every error returns `{"error": {"code", "message"}}` with no internals; add a one-line log per request (status, pages, duration, no document content)
- [X] T007 [P] Add `tests/conftest.py` with a fake engine returning canned neutral pages and a `TestClient` fixture that uses it

**Checkpoint**: App starts with a fake engine.

---

## Phase 3: User Story 1 - Extract structured data from a Spanish document (Priority: P1) MVP

**Goal**: `POST /ocr` returns page-by-page structured JSON for a valid PDF or image.

**Independent Test**: Send a valid Spanish invoice image and a multi-page PDF; get `200` with one page result per page, numbered from 1, text with accents and `ñ` preserved.

### Tests for User Story 1

- [X] T008 [P] [US1] Contract test in `tests/contract/test_ocr_contract.py`: a successful response validates against the `OcrResponse` schema in `contracts/openapi.yaml`, with all collections present even when empty
- [X] T009 [P] [US1] Integration test in `tests/integration/test_ocr_success.py`: PNG gives one page, a 3-page PDF gives three pages numbered 1 to 3, and Spanish characters (`á é í ó ú ñ ü ¿ ¡`) and amounts like `$1.250.000,50` pass through unchanged

### Implementation for User Story 1

- [X] T010 [P] [US1] Implement content-based file-type detection in `src/docuparse/validation.py`: PDF (`%PDF-`), PNG (signature), JPEG (`FFD8FF`); ignore declared type and extension
- [X] T011 [US1] Implement the PaddleOCR-VL-1.6 adapter in `src/docuparse/engine/paddle_vl.py`: build `PaddleOCRVL(pipeline_version="v1.6")` once, run `predict` on a file path, and convert each page's native output into the neutral page result (`text`, `table`, `formula`, `chart`, `other` elements; pixel bounding boxes; reading order from 1; confidence only when provided, else null). This is the only module that imports paddle libraries
- [X] T012 [US1] Implement the Document Processing Service in `src/docuparse/service.py`: write the upload to a temporary file, call the engine, build `OcrResponse` (file name, detected type, size, page count, processing time), and delete the temporary file before returning
- [X] T013 [US1] Implement `POST /ocr` in `src/docuparse/api/ocr.py`: accept a single multipart `file` field, delegate to the service, return `200` JSON; the route must not call the engine directly

**Checkpoint**: Valid documents return structured results (MVP).

---

## Phase 4: User Story 2 - Tables, formulas, charts and layout as distinct elements (Priority: P2)

**Goal**: Each page separates element types with positions and reading order.

**Independent Test**: Submit a page with a table, a formula and a chart; each appears as its own typed element with a bounding box.

### Tests for User Story 2

- [X] T014 [P] [US2] Unit test in `tests/unit/test_mapping.py`: native table content (including a table whose native form is HTML) maps to `rows` of cells with `row_span` and `col_span` of 1 when not merged, and the response contains no HTML or Markdown
- [X] T015 [P] [US2] Integration test in `tests/integration/test_elements.py`: a page with table, formula and chart yields matching entries in `tables`, `formulas`, `charts` and `elements`; a plain-text page yields those three collections empty, not missing

### Implementation for User Story 2

- [X] T016 [US2] Extend the mapping in `src/docuparse/engine/paddle_vl.py` so tables become the cell grid (convert any HTML to rows of cells with spans, never pass HTML through), formulas keep their recognized content in `text`, and chart or visual blocks carry any recognized text or data
- [X] T017 [US2] In `src/docuparse/service.py`, populate `tables`, `formulas` and `charts` from the elements, set `reading_order` starting at 1 per page, and report page `width` and `height` in pixels; ensure no engine names or native fields appear in any response

**Checkpoint**: Structured elements work independently of the error handling story.

---

## Phase 5: User Story 3 - Clear errors for invalid or unprocessable input (Priority: P2)

**Goal**: Every bad input gets the documented status and error body; partial failures degrade gracefully.

**Independent Test**: Submit a text file, an oversized file, an empty request, a corrupt PDF and a blank page; each returns the documented result.

### Tests for User Story 3

- [X] T018 [P] [US3] Integration test in `tests/integration/test_errors.py` covering: no file `400 missing_file`; two files `400 multiple_files`; `.docx`, `.gif`, `.txt` and a text file renamed `.pdf` `415 unsupported_file_type`; file over 10 MB `413 file_too_large`; PDF over 20 pages `413 too_many_pages`; zero-byte, corrupt and password-protected PDFs `422 unreadable_file`; engine not ready `503 service_not_ready`; engine timeout `504 processing_timeout`; every page failing `500 processing_failed`; each body matches `ErrorResponse` and exposes no stack trace or engine detail
- [X] T019 [P] [US3] Integration test in `tests/integration/test_warnings.py`: a blank page returns `200` with empty content and a `no_content_detected` warning; a low-quality page returns what was recognized plus `low_quality_page`; a 3-page PDF with one failing page returns `200` with that page `failed`, empty content, and a `page_failed` warning in both the page and the overall list

### Implementation for User Story 3

- [X] T020 [US3] Complete `src/docuparse/validation.py`: reject files over 10 MB (`file_too_large`), zero-byte, corrupt, or encrypted PDFs and undecodable images (`unreadable_file`), unsupported or mismatched types (`unsupported_file_type`), and PDFs over 20 pages using `pypdf` (`too_many_pages`); all checks run before the engine is called
- [X] T021 [US3] In `src/docuparse/api/ocr.py`, return `400` with `missing_file` or `multiple_files` for requests without exactly one file, and map validation failures to the status codes in data-model.md
- [X] T022 [US3] In `src/docuparse/service.py`, run inference in a worker thread guarded by a lock (one document at a time) with a 120 s timeout returning `504 processing_timeout`; return `503 service_not_ready` when the engine is not loaded
- [X] T023 [US3] In `src/docuparse/service.py`, mark failed pages (`status` `failed`, empty content, `page_failed` warning), add `no_content_detected` and `low_quality_page` warnings per page and in the overall list, and return `500 processing_failed` only when every page fails
- [X] T024 [US3] Ensure unexpected exceptions in `src/docuparse/main.py` become `500 processing_failed` without internals and never stop the service or affect later requests

**Checkpoint**: All documented error scenarios behave as specified.

---

## Phase 6: User Story 4 - Health check (Priority: P3)

**Goal**: `GET /health` reports whether the service can process documents.

**Independent Test**: Call `GET /health` when ready and when the engine is not loaded.

### Tests for User Story 4

- [X] T025 [P] [US4] Integration test in `tests/integration/test_health.py`: ready gives `200` with `status` `healthy`, `service` `docuparse` and `version`; engine not loaded gives `503` with `status` `not_ready`; the response contains no document information and the call needs no input

### Implementation for User Story 4

- [X] T026 [US4] Implement `GET /health` in `src/docuparse/api/health.py`, using the engine's `is_ready()`, and register it in `src/docuparse/main.py`

**Checkpoint**: All four stories work independently.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T027 [P] (partial: 4 synthetic samples exist: invoice, contract PNG/PDF, blank; table-heavy report and scanned PDF still missing) Add 5 Spanish sample documents to `tests/samples/` (an invoice image, a contract PDF, a table-heavy report, a scanned PDF, a blank page) with no sensitive real data
- [X] T028 [P] Add opt-in end-to-end tests in `tests/integration/test_samples_e2e.py` (skipped unless an environment flag is set) that run the real engine on the samples
- [X] T029 [P] Replace the `README.md` stub with the run instructions and curl examples from `quickstart.md`
- [ ] T030 (partial: ran invoice, PDF, blank page and 3 error cases live; see timings, 77 s for a one-page invoice on CPU vs the 30 s target) Run the 12 scenarios in `quickstart.md` against the real engine, record timings against the 30 s single-page target, and confirm no response contains engine-specific details

---

## Dependencies & Execution Order

- Phase 1 then Phase 2, which blocks all stories.
- US1 (P1) first: it creates the route, adapter and service the others extend.
- US2 extends the US1 adapter and service (T016 and T017 follow T011 and T012).
- US3 extends the US1 route and service plus validation (T020 to T024 follow T013 and T012).
- US4 depends only on Phase 2 and can be done in parallel with US2 and US3.
- Polish comes last.

## Parallel Examples

- Phase 2: T004, T005 and T007 together.
- US1 tests: T008 and T009 together; T010 can run alongside them.
- US2 tests: T014 and T015 together.
- US3 tests: T018 and T019 together.
- US4 (T025, T026) in parallel with US2 and US3 once Phase 2 is done.

## Implementation Strategy

1. **MVP**: Phases 1 to 3. A valid document returns structured JSON.
2. Add US3 next so invalid input is handled before demonstrating.
3. Add US2 (richer elements), then US4 (health), then Polish.
4. Stop and validate each story with its Independent Test before moving on.

---

## Phase 8: Convergence

- [x] T031 Add an engine-independent `low_quality_page` signal in `src/docuparse/service.py` (for example a page with very little recognized text for its pixel area, or in `src/docuparse/engine/paddle_vl.py` using a quality hint the engine provides), so the warning can fire when the engine gives no confidence values, and cover it in `tests/integration/test_warnings.py` per FR-019a (partial)
- [x] T032 Add the missing samples to `tests/samples/make_samples.py` (a table-heavy Spanish report PDF and a scanned image-only PDF) and generate them as `informe.pdf` and `escaneado.pdf`, matching the names used in `quickstart.md`, per SC-003 and SC-004 (partial)
- [ ] T033 Add a sample with a formula, a chart and a table with merged cells, run it on the real engine, fix the mapping in `src/docuparse/engine/paddle_vl.py` if the native labels or content differ from the assumptions, and add the case to `tests/integration/test_samples_e2e.py` per FR-011, FR-012 (partial)
- [ ] T034 Bring single-page latency toward the 30 s target in SC-002 (for example run one warm-up inference at startup in `src/docuparse/engine/paddle_vl.py`) or, if CPU cannot meet it, restate SC-002 as a GPU target in `specs/001-document-ocr-api/spec.md` Assumptions and record the measured CPU timings in `README.md` per SC-002 (partial)
- [x] T035 Make a timed-out request not block later requests in `src/docuparse/service.py` (for example run inference in a worker that can be abandoned and restarted, or reject new work while an abandoned job is still running with a clear `503`), with a test in `tests/integration/test_errors.py` per FR-023 (partial)
- [ ] T036 Run the remaining quickstart scenarios (3, 4, 5, 7 to 11) on the real engine and record status codes and timings in `specs/001-document-ocr-api/quickstart.md` per T030 (partial)
- [x] T037 Enforce the 10 MB limit while reading the upload in `src/docuparse/api/ocr.py` instead of after loading it fully, and remove the stale comment, with the existing `test_too_large` still passing per FR-004 (partial)
- [x] T038 In `src/docuparse/main.py`, return accurate error codes for routing errors (404 and 405) instead of `processing_failed`, adding the new codes to `contracts/openapi.yaml` and `data-model.md`, per FR-021 (contradicts)
