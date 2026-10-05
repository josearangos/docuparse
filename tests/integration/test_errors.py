import pytest

from tests.conftest import make_pdf, make_png


def post(client, name, data, ctype="application/octet-stream"):
    return client.post("/ocr", files={"file": (name, data, ctype)})


def err(r, status, code):
    assert r.status_code == status, r.text
    body = r.json()
    assert set(body) == {"error"} and body["error"]["code"] == code
    assert "Traceback" not in r.text and "paddle" not in r.text.lower()


def test_no_file(client):
    err(client.post("/ocr"), 400, "missing_file")


def test_multiple_files(client):
    r = client.post("/ocr", files=[("file", ("a.png", make_png())), ("file", ("b.png", make_png()))])
    err(r, 400, "multiple_files")


@pytest.mark.parametrize("name", ["a.docx", "a.gif", "a.txt", "fake.pdf"])
def test_unsupported(client, name):
    err(post(client, name, b"PK\x03\x04 not a pdf"), 415, "unsupported_file_type")


def test_too_large(client):
    err(post(client, "a.pdf", b"%PDF-" + b"0" * (10 * 1024 * 1024)), 413, "file_too_large")


def test_too_many_pages(client):
    err(post(client, "a.pdf", make_pdf(21)), 413, "too_many_pages")


def test_zero_byte(client):
    err(post(client, "a.png", b""), 422, "unreadable_file")


def test_corrupt_pdf(client):
    err(post(client, "a.pdf", b"%PDF-1.4 garbage"), 422, "unreadable_file")


def test_corrupt_png(client):
    err(post(client, "a.png", b"\x89PNG\r\n\x1a\n garbage"), 422, "unreadable_file")


def test_encrypted_pdf(client):
    err(post(client, "a.pdf", make_pdf(1, password="x")), 422, "unreadable_file")


def test_not_ready(client, engine):
    engine.ready = False
    err(post(client, "a.png", make_png()), 503, "service_not_ready")


def test_timeout(client, engine):
    engine.delay = 2
    err(post(client, "a.png", make_png()), 504, "processing_timeout")


def test_engine_crash(client, engine):
    engine.raise_error = True
    err(post(client, "a.png", make_png()), 500, "processing_failed")


def test_all_pages_fail(client, engine):
    engine.fail_pages = {1, 2}
    err(post(client, "a.pdf", make_pdf(2)), 500, "processing_failed")


def test_service_survives_failure(client, engine):
    engine.raise_error = True
    post(client, "a.png", make_png())
    engine.raise_error = False
    assert post(client, "a.png", make_png()).status_code == 200


def test_timeout_does_not_block_later_requests(client, engine):
    import time

    engine.delay = 1.5
    err(post(client, "a.png", make_png()), 504, "processing_timeout")
    # the abandoned job is still running: new work is refused with a clear 503
    err(post(client, "a.png", make_png()), 503, "service_not_ready")
    time.sleep(1.2)  # abandoned job finishes
    engine.delay = 0
    assert post(client, "a.png", make_png()).status_code == 200


def test_unknown_route_and_method(client):
    err(client.get("/nope"), 404, "not_found")
    err(client.get("/ocr"), 405, "method_not_allowed")


def test_upload_limit_enforced_while_reading(client):
    r = post(client, "a.png", b"\x89PNG\r\n\x1a\n" + b"0" * (10 * 1024 * 1024 + 10))
    err(r, 413, "file_too_large")
