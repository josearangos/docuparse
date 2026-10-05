from tests.conftest import make_pdf, make_png


def test_blank_page(client, engine):
    engine.blank = True
    r = client.post("/ocr", files={"file": ("f.png", make_png())})
    assert r.status_code == 200
    body = r.json()
    assert body["pages"][0]["text"] == ""
    assert [w["code"] for w in body["warnings"]] == ["no_content_detected"]


def test_low_quality(client, engine):
    engine.low_confidence = True
    body = client.post("/ocr", files={"file": ("f.png", make_png())}).json()
    assert body["pages"][0]["text"]
    assert "low_quality_page" in [w["code"] for w in body["pages"][0]["warnings"]]


def test_partial_failure(client, engine):
    engine.fail_pages = {2}
    r = client.post("/ocr", files={"file": ("f.pdf", make_pdf(3))})
    assert r.status_code == 200
    body = r.json()
    assert [p["status"] for p in body["pages"]] == ["processed", "failed", "processed"]
    assert body["pages"][1]["text"] == "" and body["pages"][1]["elements"] == []
    assert any(w["code"] == "page_failed" and w["page_number"] == 2 for w in body["warnings"])
    assert body["pages"][1]["warnings"][0]["code"] == "page_failed"


def test_low_resolution_page_warns(client, engine):
    from docuparse.engine.base import EnginePage
    from tests.conftest import BOX
    from docuparse.schemas import Element

    def tiny(n):
        p = EnginePage(page_number=n, width=120, height=90)
        p.elements.append(Element(type="text", bbox=BOX, reading_order=1, text="Texto pequeño"))
        return p

    engine._page = tiny
    page = client.post("/ocr", files={"file": ("f.png", make_png())}).json()["pages"][0]
    assert "low_quality_page" in [w["code"] for w in page["warnings"]]


def test_garbled_text_warns(client, engine):
    from docuparse.engine.base import EnginePage
    from tests.conftest import BOX
    from docuparse.schemas import Element

    def garbled(n):
        p = EnginePage(page_number=n, width=800, height=1000)
        p.elements.append(Element(type="text", bbox=BOX, reading_order=1, text="�§±¬¶∆≈ç√∫~˜µ≤≥÷åß∂ƒ©˙∆˚¬"))
        return p

    engine._page = garbled
    page = client.post("/ocr", files={"file": ("f.png", make_png())}).json()["pages"][0]
    assert "low_quality_page" in [w["code"] for w in page["warnings"]]


def test_clean_spanish_page_does_not_warn(client):
    page = client.post("/ocr", files={"file": ("f.png", make_png())}).json()["pages"][0]
    assert page["warnings"] == []
