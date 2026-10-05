# Quickstart: Validating DocuParse

A run-and-verify guide. Request and response shapes are in [contracts/openapi.yaml](contracts/openapi.yaml)
and [data-model.md](data-model.md).

## Prerequisites

- Python 3.12 and `uv`
- Enough disk and memory to download and run the 0.9B model (first start downloads it)
- A few Spanish sample documents in `tests/samples/`: an invoice image, a contract PDF, a
  table-heavy report, and a scanned PDF

## Run

```bash
uv sync
uv run uvicorn docuparse.main:app --port 8000
```

Wait until the health check reports `healthy` (the model loads at startup).

## Validation scenarios

| # | Command | Expected |
|---|---------|----------|
| 1 | `curl -i localhost:8000/health` | `200`, `status: healthy`, service name and version |
| 2 | `curl -F file=@tests/samples/factura.png localhost:8000/ocr` | `200`, one page, Spanish text with accents and `ñ`, a table element if the invoice has one |
| 3 | `curl -F file=@tests/samples/contrato.pdf localhost:8000/ocr` | `200`, one page result per page, numbered from 1 |
| 4 | `curl -F file=@tests/samples/escaneado.pdf localhost:8000/ocr` | `200`, text from the scanned pages |
| 5 | `curl -F file=@tests/samples/informe.pdf localhost:8000/ocr` | table grid (`rows` of cells), formula and chart collections present |
| 6 | `curl -i localhost:8000/ocr` (no file) | `400`, `missing_file` |
| 7 | `curl -F file=@README.md localhost:8000/ocr` | `415`, `unsupported_file_type` |
| 8 | A text file renamed `x.pdf` | `415`, not processed |
| 9 | A file over 10 MB | `413`, `file_too_large` |
| 10 | A PDF over 20 pages | `413`, `too_many_pages` |
| 11 | A corrupt or password-protected PDF, or a zero-byte file | `422`, `unreadable_file` |
| 12 | A blank page image | `200`, empty collections, `no_content_detected` warning |

## Checks across all successful responses

- The body is valid JSON that matches the contract.
- No engine names or native fields appear.
- Every element has `type`, `bbox` (pixels), `reading_order`.
- Empty collections are present, never missing.

## Automated tests

```bash
uv run pytest
```

Contract and integration tests use a fake engine. End-to-end tests on the real samples are opt-in.
