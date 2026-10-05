from fastapi import APIRouter, Request

from docuparse.errors import ApiError
from docuparse.schemas import ErrorResponse, OcrResponse
from docuparse.validation import MAX_BYTES

router = APIRouter()

_ERRORS = {code: {"model": ErrorResponse} for code in (400, 413, 415, 422, 500, 503, 504)}


@router.post("/ocr", response_model=OcrResponse, responses=_ERRORS)
async def ocr(request: Request) -> OcrResponse:
    form = await request.form()
    files = [v for _, v in form.multi_items() if hasattr(v, "read")]
    if not files:
        raise ApiError(400, "missing_file", "Send one document in the 'file' field.")
    if len(files) > 1:
        raise ApiError(400, "multiple_files", "Send exactly one file per request.")
    upload = files[0]
    # read at most one byte over the limit; validation then rejects it with file_too_large
    data = await upload.read(MAX_BYTES + 1)
    return await _process(request, upload.filename or "upload", data)


async def _process(request: Request, name: str, data: bytes) -> OcrResponse:
    from starlette.concurrency import run_in_threadpool

    service = request.app.state.service
    return await run_in_threadpool(service.process, name, data)
