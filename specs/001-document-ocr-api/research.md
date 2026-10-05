# Research: DocuParse Document Intelligence API

All Technical Context items are resolved; none remain marked NEEDS CLARIFICATION.

## R1. Engine invocation

- **Decision**: Use the official PaddleOCR document-parsing pipeline,
  `PaddleOCRVL(pipeline_version="v1.6")`, and call `predict(<path>)` per document.
- **Rationale**: The model card states the official pipeline is faster and supports page-level
  document parsing (layout, text, tables, formulas, charts). The plain transformers example only
  supports element-level recognition. Source:
  [PaddleOCR-VL-1.6 on Hugging Face](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6).
- **Alternatives considered**: transformers inference (no page-level parsing, would require
  building layout detection ourselves); classic PaddleOCR text pipeline (no tables/formulas/charts,
  violates Principle I).

## R2. Spanish handling

- **Decision**: Rely on the model's multilingual recognition and verify with Spanish samples; do not
  add language switches to the API.
- **Rationale**: The request takes only the file (clarified). Spanish quality is verified by the
  sample set (SC-003) rather than a parameter.
- **Alternatives considered**: a `lang` request option (rejected; contradicts the no-options
  clarification).

## R3. PDF and image input

- **Decision**: Pass the validated file to the pipeline and let it split PDFs into pages. Validate
  beforehand with `pypdf` (page count, encryption, corruption) and Pillow (image decode).
- **Rationale**: Rejecting bad input before inference gives fast, accurate 4xx errors (FR-003 to
  FR-006) and avoids loading the model for invalid files.
- **Alternatives considered**: rendering PDFs to images ourselves (extra dependency and code, no
  benefit).

## R4. Validation by content

- **Decision**: Sniff the leading bytes (`%PDF-`, PNG signature, JPEG `FFD8FF`) and ignore the
  declared content type and extension for decisions.
- **Rationale**: FR-003 requires content-based validation; magic bytes are simple and reliable.

## R5. Engine loading and concurrency

- **Decision**: Load the pipeline once at application startup; `/health` reports ready only after a
  successful load. Run inference in a worker thread guarded by a lock so one document runs at a
  time; wrap it with a 120 s timeout returning `504`.
- **Rationale**: The model is large, so per-request loading would break SC-002. A lock avoids
  memory blowups on a laptop; concurrent requests still complete (queued), satisfying the edge case
  that simultaneous requests each get their own result.
- **Alternatives considered**: multiple workers (memory heavy), job queue (out of scope).

## R6. Result mapping

- **Decision**: Map the engine's block list into neutral element types: `text`, `table`,
  `formula`, `chart`, plus `other` for visual blocks without a better type. Tables become a cell
  grid with spans; positions become pixel rectangles on the page as processed.
- **Rationale**: Meets FR-010 to FR-019 and keeps native fields out of the response. The adapter is
  the only code that knows the native shape, so it is the single place to adapt if the engine
  output differs from what was assumed.
- **Alternatives considered**: returning native JSON (violates Principle III).
- **Risk**: The native table output may be HTML. The adapter converts it into the grid, which the
  spec requires (no HTML in the response). Confirm the exact native shape when implementing.

## R7. Partial page failure and warnings

- **Decision**: The adapter returns a result or an error per page; the service marks failed pages,
  adds warnings (`page_failed`, `low_quality_page`, `no_content_detected`), and returns `500` only
  when every page fails.
- **Rationale**: Directly implements FR-020, FR-019a and FR-023a. Low quality is flagged when
  recognition confidence is low or a page yields no content while the page is not blank.

## R8. Hardware

- **Decision**: Target CPU inference on the dev machine (macOS arm64); allow a GPU when present.
- **Rationale**: Portfolio scope. CPU inference of the 0.9B model is slow, so the 30 s target
  (SC-002) is for a single page and is verified in the demo environment.
- **Risk**: On CPU the first request after startup and multi-page PDFs may approach the 120 s
  timeout. Mitigation: the 20-page cap and a quickstart note.

## R9. Logging

- **Decision**: Plain structured log lines per request (status, pages, duration), with no document
  content.
- **Rationale**: Covers the observability gap from clarification without adding scope, and respects
  FR-015 (no retention).
