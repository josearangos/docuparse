from tests.conftest import make_png


def test_typed_elements(client):
    page = client.post("/ocr", files={"file": ("f.png", make_png(), "image/png")}).json()["pages"][0]
    assert len(page["tables"]) == 1
    assert page["tables"][0]["rows"][0][1]["col_span"] == 2
    assert page["tables"][0]["rows"][0][0]["row_span"] == 1
    assert len(page["formulas"]) == 1 and len(page["charts"]) == 1
    assert [e["reading_order"] for e in page["elements"]] == [1, 2, 3, 4]
    assert set(page["elements"][0]["bbox"]) == {"left", "top", "right", "bottom"}
    assert "<table" not in str(page).lower()


def test_empty_collections_present(client, engine):
    engine.blank = True
    page = client.post("/ocr", files={"file": ("f.png", make_png(), "image/png")}).json()["pages"][0]
    for key in ("elements", "tables", "formulas", "charts"):
        assert page[key] == []
