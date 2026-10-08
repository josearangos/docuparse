"""Compare engines on the sample documents: seconds per page and, with ground truth, CER.

    uv run python scripts/benchmark.py rapidocr paddle_vl
    uv run python scripts/benchmark.py rapidocr --truth truth/   # truth/<sample name>.txt per file
    uv run python scripts/benchmark.py http://localhost:8000 http://localhost:8001 --runs 1   # running servers
    uv run python scripts/benchmark.py rapidocr --out docs/benchmark-results.md
"""

import argparse
import datetime
import platform
import statistics
import sys
import time
from pathlib import Path

SAMPLES = Path(__file__).resolve().parent.parent / "tests" / "samples"


class HttpEngine:
    """Benchmarks a running DocuParse server instead of loading a second copy of the model."""

    def __init__(self, url: str) -> None:
        self.url = url.rstrip("/")

    def load(self) -> None:
        import httpx

        health = httpx.get(f"{self.url}/health", timeout=10).json()
        if health.get("status") != "healthy":
            sys.exit(f"{self.url} is not healthy: {health}")

    def parse(self, path: str):
        import httpx

        from docuparse.engine.base import EnginePage
        from docuparse.schemas import OcrResponse

        with open(path, "rb") as fh:
            r = httpx.post(f"{self.url}/ocr", files={"file": (Path(path).name, fh)}, timeout=600)
        if r.status_code != 200:
            print(f"    {self.url} {Path(path).name}: HTTP {r.status_code} {r.text[:120]}")
            return [EnginePage(page_number=1, error="http_error")]
        data = OcrResponse.model_validate(r.json())
        return [EnginePage(page_number=p.page_number, elements=p.elements) for p in data.pages]


def load_engine(name: str):
    if name.startswith("http"):
        engine = HttpEngine(name)
        engine.load()
        return engine
    if name == "rapidocr":
        from docuparse.engine.rapid import RapidOcrEngine as Engine
    elif name == "paddle_vl":
        from docuparse.engine.paddle_vl import PaddleVLEngine as Engine
    else:
        sys.exit(f"unknown engine {name}")
    engine = Engine()
    t = time.perf_counter()
    engine.load()
    print(f"[{name}] load+warm-up {time.perf_counter() - t:.1f}s")
    return engine


def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def norm(text: str) -> str:
    return " ".join(text.split())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("engines", nargs="+")
    ap.add_argument("--truth", type=Path, help="folder with <file name>.txt ground truth")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--out", type=Path, help="write the results as a Markdown file")
    args = ap.parse_args()
    report: list[str] = []

    files = sorted(p for p in SAMPLES.iterdir() if p.suffix in {".png", ".jpg", ".pdf"})
    for name in args.engines:
        engine = load_engine(name)
        per_page, cers = [], []
        for f in files:
            times, pages = [], []
            for _ in range(args.runs):
                t = time.perf_counter()
                pages = engine.parse(str(f))
                times.append(time.perf_counter() - t)
            best = min(times)
            per_page.append(best / max(len(pages), 1))
            text = "\n".join(e.text or "" for p in pages for e in p.elements)
            line = f"[{name}] {f.name:24} {len(pages)}p {best:6.2f}s ({best / max(len(pages), 1):.2f}s/page)"
            if args.truth and (args.truth / f"{f.name}.txt").exists():
                ref = norm((args.truth / f"{f.name}.txt").read_text())
                cer = edit_distance(norm(text), ref) / max(len(ref), 1)
                cers.append(cer)
                line += f" CER {cer:.3f}"
            print(line)
            report.append(
                f"| {name} | {f.name} | {len(pages)} | {best:.2f} | {best / max(len(pages), 1):.2f} | "
                + (f"{cers[-1]:.3f}" if args.truth and (args.truth / f"{f.name}.txt").exists() else "n/a")
                + " |"
            )
        print(f"[{name}] median {statistics.median(per_page):.2f}s/page", end="")
        print(f", mean CER {statistics.mean(cers):.3f}" if cers else "")
        report.append(
            f"| **{name}** | **median** | | | **{statistics.median(per_page):.2f}** | "
            + (f"**{statistics.mean(cers):.3f}**" if cers else "n/a")
            + " |"
        )

    if args.out:
        head = [
            "# Benchmark results",
            "",
            f"- Date: {datetime.date.today()}",
            f"- Machine: {platform.platform()} ({platform.machine()}), Python {platform.python_version()}",
            f"- Runs per file: {args.runs} (best time reported); samples: tests/samples (synthetic)",
            f"- Command: `python scripts/benchmark.py {' '.join(sys.argv[1:])}`",
            "",
            "| Engine | File | Pages | Seconds | Seconds/page | CER |",
            "|---|---|---|---|---|---|",
        ]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text("\n".join(head + report) + "\n")
        print(f"saved {args.out}")


if __name__ == "__main__":
    main()
