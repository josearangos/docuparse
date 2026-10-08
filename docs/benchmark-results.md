# Benchmark results

- Date: 2026-10-08
- Machine: macOS-26.2-arm64-arm-64bit (arm64), Python 3.12.11
- Runs per file: 3 (best time reported); samples: tests/samples (synthetic)
- Command: `python scripts/benchmark.py rapidocr --out docs/benchmark-results.md`

| Engine | File | Pages | Seconds | Seconds/page | CER |
|---|---|---|---|---|---|
| rapidocr | contrato.pdf | 1 | 1.10 | 1.10 | n/a |
| rapidocr | contrato.png | 1 | 0.77 | 0.77 | n/a |
| rapidocr | en_blanco.png | 1 | 0.15 | 0.15 | n/a |
| rapidocr | escaneado.pdf | 1 | 1.16 | 1.16 | n/a |
| rapidocr | factura.png | 1 | 0.99 | 0.99 | n/a |
| rapidocr | formulas_graficos.png | 1 | 1.31 | 1.31 | n/a |
| rapidocr | informe.pdf | 1 | 1.78 | 1.78 | n/a |
| **rapidocr** | **median** | | | **1.10** | n/a |
