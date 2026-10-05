from tests.conftest import SPANISH, make_pdf, make_png


def test_png_one_page(client):
    r = client.post("/ocr", files={"file": ("factura.png", make_png(), "image/png")})
    assert r.status_code == 200
    body = r.json()
    assert body["document"]["file_type"] == "png"
    assert body["document"]["page_count"] == 1
    assert len(body["pages"]) == 1
    assert SPANISH in body["pages"][0]["text"]
    assert "$1.250.000,50" in body["pages"][0]["text"]


def test_pdf_pages_numbered(client):
    r = client.post("/ocr", files={"file": ("c.pdf", make_pdf(3), "application/pdf")})
    assert r.status_code == 200
    assert [p["page_number"] for p in r.json()["pages"]] == [1, 2, 3]


def test_uppercase_extension_and_wrong_declared_type_ok(client):
    r = client.post("/ocr", files={"file": ("F.PNG", make_png(), "application/octet-stream")})
    assert r.status_code == 200


def test_no_engine_details_leak(client):
    body = client.post("/ocr", files={"file": ("f.png", make_png(), "image/png")}).text.lower()
    assert "paddle" not in body
