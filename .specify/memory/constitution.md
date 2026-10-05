<!--
Sync Impact Report
- Version change: (unratified template) → 1.0.0
- Modified principles: none renamed (initial adoption; all placeholders filled)
- Added sections: Core Principles I–V, Technical Constraints, Development Workflow, Governance
- Removed sections: none
- Deferred items: none
-->
# DocuParse Constitution

## Core Principles

### I. PaddleOCR-VL-1.6 as the Document AI Engine
DocuParse MUST use **PaddleOCR-VL-1.6** (0.9B parameters) for document parsing and structured
information extraction. The service MUST handle more than plain text OCR: text, tables, formulas,
charts and other visual elements, and complex document layouts.

Rationale: the project requires structured document understanding, not only text recognition.

### II. Spanish First
Spanish (`es`) is the primary and required language of the initial version. Design, optimization,
and testing MUST target Spanish documents, including Colombian invoices, contracts, financial and
administrative documents, business reports, scanned Spanish documents, and documents with Spanish
tables. Equal coverage of other languages MUST NOT be pursued in the initial version.

Rationale: focusing on one language yields better quality for the intended users.

### III. Model Isolation Behind the Processing Layer
PaddleOCR-VL-1.6 MUST remain isolated behind the Document Processing Service. The REST API MUST NOT
expose PaddleOCR-specific details (model names, native output formats, parameters, errors) to API
consumers. The public API contract MUST be expressible without reference to the underlying model.

Rationale: the model must be replaceable or upgradable without changing the public API contract.

### IV. Structured JSON Output
Every successfully processed document MUST yield structured JSON representing the extracted Spanish
text, tables, formulas, charts, and document layout. The JSON schema is part of the public API
contract and MUST be defined independently of PaddleOCR's native output.

### V. Defined Processing Flow
The initial processing flow MUST be: PDF / Image → FastAPI → Document Processing Service →
PaddleOCR-VL-1.6 → Structured JSON. API handlers MUST NOT call the model directly; all model access
goes through the Document Processing Service.

## Technical Constraints

- Inputs: PDF and image files.
- API: REST, implemented with FastAPI.
- Tests and sample documents MUST primarily use Spanish-language documents, including scanned ones
  and ones containing tables.
- Model replacement or upgrade MUST NOT require changes to the public API contract.

## Development Workflow

- Specs, plans, and tasks MUST be checked against the principles above.
- Changes to the public API or JSON schema MUST be reviewed for leakage of PaddleOCR-specific
  details.
- Any proposal that departs from a principle MUST document the justification in the plan.

## Governance

This constitution supersedes other project practices. Amendments MUST be made by editing this file
with a documented rationale, and MUST update the version according to semantic versioning: MAJOR for
backward-incompatible removals or redefinitions of principles, MINOR for new or materially expanded
principles or sections, PATCH for clarifications and wording fixes. All plans and reviews MUST
verify compliance with the principles; deviations MUST be justified in writing.

**Version**: 1.0.0 | **Ratified**: 2026-10-05 | **Last Amended**: 2026-10-05
