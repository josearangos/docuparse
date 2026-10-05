"""Opt-in end-to-end tests with the real engine: DOCUPARSE_E2E=1 uv run pytest -k e2e."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from docuparse.main import create_app

SAMPLES = Path(__file__).parents[1] / "samples"

pytestmark = pytest.mark.skipif(not os.environ.get("DOCUPARSE_E2E"), reason="set DOCUPARSE_E2E=1")


@pytest.fixture(scope="module")
def real_client():
    with TestClient(create_app()) as c:
        yield c


def test_invoice(real_client):
    r = real_client.post("/ocr", files={"file": ("factura.png", (SAMPLES / "factura.png").read_bytes())})
    assert r.status_code == 200
    page = r.json()["pages"][0]
    assert "Muñoz" in page["text"] and "Medellín" in page["text"]
    assert len(page["tables"]) == 1 and len(page["tables"][0]["rows"]) == 4


def test_blank(real_client):
    r = real_client.post("/ocr", files={"file": ("b.png", (SAMPLES / "en_blanco.png").read_bytes())})
    assert r.status_code == 200
    assert [w["code"] for w in r.json()["warnings"]] == ["no_content_detected"]
