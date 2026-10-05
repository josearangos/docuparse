from pathlib import Path

import yaml

from tests.conftest import make_png

SPEC = yaml.safe_load(
    (Path(__file__).parents[2] / "specs/001-document-ocr-api/contracts/openapi.yaml").read_text()
)
SCHEMAS = SPEC["components"]["schemas"]


def _check(value, schema):
    if "$ref" in schema:
        return _check(value, SCHEMAS[schema["$ref"].split("/")[-1]])
    if "allOf" in schema:
        for part in schema["allOf"]:
            _check(value, part)
        return
    if value is None:
        assert schema.get("nullable"), f"unexpected null for {schema}"
        return
    t = schema.get("type")
    if t == "object":
        for key in schema.get("required", []):
            assert key in value, f"missing {key}"
        for key, sub in schema.get("properties", {}).items():
            if key in value:
                _check(value[key], sub)
    elif t == "array":
        assert isinstance(value, list)
        for item in value:
            _check(item, schema["items"])
    elif t == "string":
        assert isinstance(value, str)
        if "enum" in schema:
            assert value in schema["enum"], value
    elif t == "integer":
        assert isinstance(value, int)
    elif t == "number":
        assert isinstance(value, (int, float))


def test_success_matches_contract(client):
    r = client.post("/ocr", files={"file": ("f.png", make_png(), "image/png")})
    assert r.status_code == 200
    _check(r.json(), {"$ref": "#/components/schemas/OcrResponse"})


def test_error_matches_contract(client):
    r = client.post("/ocr", files={"file": ("f.txt", b"hola", "text/plain")})
    assert r.status_code == 415
    _check(r.json(), {"$ref": "#/components/schemas/ErrorResponse"})


def test_health_matches_contract(client):
    r = client.get("/health")
    _check(r.json(), {"$ref": "#/components/schemas/HealthResponse"})
