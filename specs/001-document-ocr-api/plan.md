# Implementation Plan: DocuParse Document Intelligence API

**Branch**: `001-document-ocr-api` | **Date**: 2026-10-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-document-ocr-api/spec.md`

## Summary

Build a small synchronous REST service with `POST /ocr` (PDF/PNG/JPEG in, structured JSON out) and
`GET /health`. A Document Processing Service validates the upload, runs the PaddleOCR-VL-1.6
document-parsing pipeline (Spanish-first), and maps the engine's native output into a stable,
engine-neutral response schema (pages, typed elements, table grids, pixel bounding boxes,
warnings). The engine is loaded once at startup and sits behind an adapter so the API never leaks
PaddleOCR details. See [research.md](research.md) for decisions.

## Technical Context

**Language/Version**: Python 3.12 (already set in `.python-version` and `pyproject.toml`)

**Primary Dependencies**: FastAPI + Uvicorn (REST); `paddleocr` document-parser extra with
`paddlepaddle` (engine, `PaddleOCRVL(pipeline_version="v1.6")`); `python-multipart` (uploads);
`pypdf` (page count / encryption check); Pillow (image validation); Pydantic (schemas)

**Storage**: N/A (requests are processed from temporary files and deleted before responding)

**Testing**: pytest + FastAPI `TestClient`; engine faked in unit/contract tests; a small set of
real Spanish sample documents for opt-in end-to-end tests

**Target Platform**: Local developer machine (macOS arm64 / Linux), run with `uv`

**Project Type**: web-service

**Performance Goals**: single-page Spanish document returned within 30 s (SC-002); health in under
1 s (SC-006)

**Constraints**: 10 MB max file, 20 max PDF pages, 120 s request timeout; one document per
request; engine inference serialized (one at a time) because the model is heavy

**Scale/Scope**: Portfolio demo, one user at a time; two endpoints; about 5 sample documents

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|-----------|------|--------|
| I. PaddleOCR-VL-1.6 engine | Engine is PaddleOCR-VL-1.6; text, tables, formulas, charts, layout all handled | Pass |
| II. Spanish first | Engine configured and tested for Spanish; sample set is Spanish | Pass |
| III. Model isolation | Engine behind an adapter; response schema has no engine names or native fields | Pass |
| IV. Structured JSON | Response schema defined independently in `contracts/openapi.yaml` | Pass |
| V. Processing flow | Route → Document Processing Service → engine adapter; routes never call the engine | Pass |

Post-design re-check: Pass. The data model and contract use only engine-neutral terms.

## Project Structure

### Documentation (this feature)

```text
specs/001-document-ocr-api/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── openapi.yaml
└── tasks.md             # Created later by /speckit-tasks
```

### Source Code (repository root)

```text
src/docuparse/
├── main.py                 # app creation, startup engine load, error handlers
├── api/
│   ├── ocr.py              # POST /ocr route
│   └── health.py           # GET /health route
├── schemas.py              # public response/error models (engine-neutral)
├── validation.py           # content-type sniffing, size, page-count, encryption checks
├── service.py              # Document Processing Service (orchestrates, maps, warnings)
└── engine/
    ├── base.py             # engine interface returning neutral page results
    └── paddle_vl.py        # PaddleOCR-VL-1.6 adapter (the only place that imports paddle)

tests/
├── contract/               # response/error shape against the OpenAPI contract
├── integration/            # routes with a fake engine
├── unit/                   # validation, mapping
└── samples/                # Spanish sample documents (opt-in end-to-end)
```

**Structure Decision**: Single project, `src` layout. The existing root `main.py` stub is replaced
by `src/docuparse/main.py`. Only `engine/paddle_vl.py` imports the engine library, which enforces
Principle III.

## Complexity Tracking

No constitution violations; nothing to justify.
