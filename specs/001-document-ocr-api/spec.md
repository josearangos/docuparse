# Feature Specification: DocuParse Document Intelligence API

**Feature Branch**: `001-document-ocr-api`

**Created**: 2026-10-05

**Status**: Draft

**Input**: User description: "Create the functional specification for DocuParse, a lightweight Document Intelligence REST API that receives PDF documents and images (PNG, JPEG/JPG) and extracts structured information (Spanish text, tables, formulas, charts, layout) using PaddleOCR-VL-1.6 (0.9B, primary language Spanish). Endpoints: POST /ocr and GET /health. Synchronous, small portfolio scope."

## Clarifications

### Session 2026-10-05

- Q: How should a table be represented in the JSON response? → A: A structured grid only (rows of cells with text and row/column spans); no HTML or Markdown rendering.
- Q: If one page of a multi-page PDF cannot be processed, should the whole request fail? → A: No; return `200` with all pages, the failed page marked with an error status and empty content, plus a warning.
- Q: In what form should an element's position on the page be reported? → A: A rectangle (left, top, right, bottom) in pixels of the page as processed.
- Q: Can the client choose which element types to get back? → A: No; every request returns all detected element types and takes only the file.
- Q: Should a page carry a warning when recognition is likely incomplete? → A: Yes; add a per-page warning (for example `low_quality_page`) in that case.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Extract structured data from a Spanish document (Priority: P1)

A developer of a downstream application sends a PDF or image of a Spanish business document (for
example a Colombian invoice, a contract, or a scanned administrative form) to `POST /ocr` and
receives, in the same response, structured JSON describing every page: the recognized Spanish text,
detected tables, formulas, charts and other visual elements, and the layout of each page.

**Why this priority**: This is the core value of the product. Without it nothing else is useful.

**Independent Test**: Send a single-page Spanish invoice image to `POST /ocr` and verify the response
is valid JSON with one page result containing the invoice text and its table.

**Acceptance Scenarios**:

1. **Given** a valid single-page PNG of a Spanish invoice, **When** the client sends it to
   `POST /ocr`, **Then** the service responds `200` with JSON containing one page result whose text
   content includes the invoice's Spanish text (accents and `ñ` preserved).
2. **Given** a valid multi-page PDF, **When** the client sends it to `POST /ocr`, **Then** the
   response contains one page result per page, ordered by page number starting at 1.
3. **Given** a scanned (image-only) PDF, **When** it is submitted, **Then** the text of the scanned
   pages is still extracted.
4. **Given** a valid document, **When** processing finishes, **Then** the response is returned
   directly in the same request, with no follow-up request needed to obtain the result.

---

### User Story 2 - Receive tables, formulas, charts and layout as distinct structured elements (Priority: P2)

A developer needs more than raw text. For each page, the response separates the detected elements by
type (text blocks, tables, formulas, charts/visual elements) and describes where each one is on the
page and in what reading order, so downstream applications can use them without re-parsing.

**Why this priority**: Structured elements are what distinguish DocuParse from plain OCR, but the
service is still useful with text alone.

**Independent Test**: Submit a Spanish report page containing one table, one formula, and one chart
and verify that each appears as a separate typed element with position information.

**Acceptance Scenarios**:

1. **Given** a page containing a table, **When** processed, **Then** the response includes a table
   element with its rows and columns and the text of each cell.
2. **Given** a page containing a mathematical formula, **When** processed, **Then** the response
   includes a formula element with the recognized formula content.
3. **Given** a page containing a chart or other visual element, **When** processed, **Then** the
   response includes an element of that type with its position, and any recognized text or data
   when available.
4. **Given** any processed page, **When** the response is read, **Then** every element includes its
   type, its position on the page, and its reading order within the page.
5. **Given** a page with none of tables, formulas or charts, **When** processed, **Then** those
   collections are present and empty rather than missing.

---

### User Story 3 - Get clear errors for invalid or unprocessable input (Priority: P2)

A developer who sends a wrong, oversized, empty, corrupt or unreadable file receives a clear,
machine-readable error with an appropriate HTTP status, so the client can react programmatically.

**Why this priority**: Predictable errors make the API safe to integrate and demonstrate.

**Independent Test**: Submit a text file, an oversized file, and an empty request and verify each
returns the documented status and error body.

**Acceptance Scenarios**:

1. **Given** a request with no file, **When** sent to `POST /ocr`, **Then** the service responds
   `400` with an error body.
2. **Given** a file in an unsupported format (for example `.docx`, `.gif`, `.txt`), **When** sent,
   **Then** the service responds `415` with an error body naming the supported formats.
3. **Given** a file whose content does not match its declared type or extension (for example a text
   file renamed `.pdf`), **When** sent, **Then** the service responds `415` or `422` with an error
   body and does not attempt processing.
4. **Given** a file larger than the maximum size, **When** sent, **Then** the service responds
   `413` with an error body stating the limit.
5. **Given** a PDF with more pages than the maximum, **When** sent, **Then** the service responds
   `413` or `422` with an error body stating the page limit.
6. **Given** a corrupt, password-protected, or zero-byte file, **When** sent, **Then** the service
   responds `422` with an error body.
7. **Given** a readable file with no detectable content (for example a blank page), **When** sent,
   **Then** the service responds `200` with the pages present and empty content, and a warning
   indicating that no content was detected.
8. **Given** an internal failure while processing a valid file, **When** it occurs, **Then** the
   service responds `500` with an error body that does not expose internal details of the document
   AI engine.

---

### User Story 4 - Check service health (Priority: P3)

An operator or developer calls `GET /health` to confirm the service is running and ready to process
documents, and to see basic service information.

**Why this priority**: Needed for demos and basic operations, but it delivers no document value.

**Independent Test**: Call `GET /health` and verify the status and service information in the
response.

**Acceptance Scenarios**:

1. **Given** the service is running and ready to process documents, **When** `GET /health` is
   called, **Then** it responds `200` with JSON containing a status of healthy, the service name,
   and the service version.
2. **Given** the service is running but not yet able to process documents (for example still
   starting up), **When** `GET /health` is called, **Then** it responds `503` with JSON indicating
   it is not ready.
3. **Given** any health response, **When** read, **Then** it contains no information about the
   documents processed and requires no input.

---

### Edge Cases

- A file with a valid extension but different real content (spoofed type) is rejected based on its
  actual content, not only its name.
- Uppercase extensions (`.PDF`, `.JPG`) and both `.jpg` and `.jpeg` are accepted.
- A PDF mixing digital-text pages and scanned pages returns text for all pages.
- A page that is rotated or skewed is still processed and reported in its page result.
- A document with no tables, formulas or charts returns empty collections for those, not errors.
- A document with a partially unreadable page (blurry, very low resolution) returns what could be
  recognized, with low confidence values where available and a warning for that page.
- A document mostly in a language other than Spanish is still processed; quality is not guaranteed
  (Spanish is the primary supported language).
- Spanish special characters (`á é í ó ú ñ ü ¿ ¡`) and Colombian number and currency formats (for
  example `$1.250.000,50`) are preserved exactly as printed, without normalization.
- Two requests sent at the same time each receive their own complete and independent result.
- A request for a document that takes unusually long to process ends with a clear timeout error
  rather than hanging indefinitely.
- A file is processed only for the duration of the request; nothing from it is available to later
  requests.

## Requirements *(mandatory)*

### Functional Requirements

**Input and validation**

- **FR-001**: The system MUST expose `POST /ocr`, which accepts a single document file in the
  request and returns the extraction result directly in the response (synchronous). The request
  takes only the file; it has no options, and every response includes all detected element types.
- **FR-002**: The system MUST accept PDF, PNG and JPEG/JPG files (extensions `.pdf`, `.png`,
  `.jpg`, `.jpeg`, case-insensitive).
- **FR-003**: The system MUST validate the file by its actual content, not only by extension or
  declared type, and MUST reject unsupported or mismatched files before processing.
- **FR-004**: The system MUST reject files larger than 10 MB with a clear error.
- **FR-005**: The system MUST reject PDFs with more than 20 pages with a clear error.
- **FR-006**: The system MUST reject requests with no file, multiple files, zero-byte files,
  corrupt files, and password-protected PDFs with a clear error.

**Processing**

- **FR-007**: The system MUST use PaddleOCR-VL-1.6 (0.9B parameters) as the document AI engine,
  optimized for Spanish documents.
- **FR-008**: The system MUST process every page of a PDF and the single page of an image file, and
  MUST return one page result for each, in page order.
- **FR-009**: The system MUST extract Spanish text preserving accents, special characters, and the
  numbers, dates and currency amounts exactly as printed.
- **FR-010**: The system MUST detect and extract tables, preserving their row and column structure
  and the text of each cell. A table MUST be represented only as a structured grid: an ordered list
  of rows, each an ordered list of cells carrying the cell text and its row and column spans (1 when
  not merged). The response MUST NOT include HTML or Markdown renderings of tables.
- **FR-011**: The system MUST detect and extract mathematical formulas as formula elements.
- **FR-012**: The system MUST detect charts and other visual elements, reporting them as distinct
  elements with their position and any recognized text or data.
- **FR-013**: The system MUST report layout information for each page: the page dimensions, and for
  each detected element its type, position and reading order.
- **FR-014**: The system MUST report confidence information for recognized content when the engine
  provides it, and MUST omit it or mark it as unavailable (not invent it) otherwise.
- **FR-015**: The system MUST NOT retain the submitted document or its results after the response
  is sent.

**Response**

- **FR-016**: The system MUST return successful results as JSON, with a response structure that is
  the same for every document type and that has these parts:
  - document-level information: source file name, detected file type, page count, and the
    processing time;
  - a list of page results, each with page number, page dimensions, full page text in reading order,
    and collections of elements (text blocks, tables, formulas, charts/visual elements);
  - an overall list of warnings.
- **FR-017**: Every element in a page result MUST include a type, a position on the page, a reading
  order, and (when available) a confidence value. The position MUST be a rectangle given as left,
  top, right and bottom values in pixels, measured on the page as processed and using the same
  page dimensions reported in the page result.
- **FR-018**: Collections with nothing detected MUST be present and empty, never omitted.
- **FR-019**: The response MUST NOT expose details specific to the document AI engine (such as its
  name, internal identifiers or native output formats), so that the engine can change without
  changing the API contract.
- **FR-019a**: When recognition of a page is likely incomplete (for example blurry, very low
  resolution or partly unreadable), the system MUST add a warning with a code (for example
  `low_quality_page`) to that page's warnings and to the overall list, while still returning
  whatever was recognized.
- **FR-020**: When a document is readable but has no detectable content, the system MUST return a
  successful response with empty page content and a warning, not an error.

**Errors**

- **FR-021**: Every error response MUST be JSON with the same structure: a machine-readable error
  code, a human-readable message in Spanish or English, and no internal details such as stack
  traces.
- **FR-022**: The system MUST use these HTTP statuses:

  | Situation | Status |
  |-----------|--------|
  | Success (including documents with no content found) | 200 |
  | No file, multiple files, malformed request | 400 |
  | File too large, or PDF over the page limit | 413 |
  | Unsupported or mismatched file type | 415 |
  | Corrupt, password-protected, empty or unreadable file | 422 |
  | Processing failure inside the service | 500 |
  | Service not ready to process documents | 503 |
  | Processing exceeded the time limit | 504 |

- **FR-023**: A failure on one request MUST NOT affect other requests or stop the service.
- **FR-023a**: If a single page of a multi-page document cannot be processed but others can, the
  system MUST return `200` with a page result for every page; the failed page MUST carry an error
  status and empty content, and a warning identifying the page MUST be added to the overall list of
  warnings. A `500` is returned only when no page can be processed.

**Health**

- **FR-024**: The system MUST expose `GET /health`, which needs no input and returns JSON with the
  status (healthy or not ready), the service name, and the service version.
- **FR-025**: `GET /health` MUST return `200` only when the service is able to process documents,
  and `503` otherwise.

### Key Entities

- **Document**: The submitted file. Attributes: file name, detected type (PDF, PNG, JPEG), size,
  page count.
- **Page Result**: The extraction for one page. Attributes: page number, status (processed or
  failed), dimensions, full page text, collections of elements, and warnings for that page.
- **Element**: A detected item on a page. Attributes: type (text block, table, formula, chart/visual
  element), position, reading order, content, and confidence (when available).
- **Table**: An element made of an ordered grid of rows and cells; each cell has its text and its
  row and column spans.
- **Warning**: A non-fatal notice (for example no content detected, low-quality page) with a code
  and message.
- **Error**: A failure response with an error code and message.
- **Health Status**: The readiness state, service name and version.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A client can obtain structured results for a valid single-page document with one
  request and no further steps, and the response is always valid JSON.
- **SC-002**: For a single-page Spanish document of standard quality, results are returned within 30
  seconds in the demonstration environment.
- **SC-003**: On a demonstration set of at least 5 Spanish documents (including an invoice, a
  contract page, a table-heavy report and a scanned document), at least 90% of the printed words
  are recognized, with accents and `ñ` preserved.
- **SC-004**: In that set, every table that has clear visible borders or alignment is returned as a
  table element with the correct number of rows and columns.
- **SC-005**: 100% of the invalid-input cases listed in User Story 3 return the documented HTTP
  status and an error body in the common error structure.
- **SC-006**: `GET /health` responds within 1 second and its status matches whether documents can be
  processed.
- **SC-007**: A developer can send their first request and read the result in under 5 minutes using
  only the documented endpoints and response structure.
- **SC-008**: No response contains engine-specific details (verified by inspecting every response
  from the demonstration set).

## Assumptions

- The initial version targets Spanish documents; other languages are not tested or guaranteed.
- Supported formats are limited to PDF, PNG and JPEG/JPG; other formats are out of scope.
- The maximum file size is 10 MB and the maximum PDF length is 20 pages; both are assumptions that
  suit a small demonstration project and can be revised.
- The default processing time limit is 120 seconds per request; beyond it the request fails with a
  timeout error.
- Documents are sent one per request; batch submission is out of scope.
- Clients are other applications or developers; there is no end-user interface.
- Confidence values are included only when the engine provides them.
- Out of scope for this version: authentication, user management, persistent storage of documents
  or results, asynchronous or queued processing, search or retrieval over documents, question
  answering, a frontend, and deployment infrastructure.
- Depends on the document AI engine PaddleOCR-VL-1.6 being available to the service, per the
  project constitution.
