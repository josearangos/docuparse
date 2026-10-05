from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from docuparse import __version__
from docuparse.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
def health(request: Request):
    ready = request.app.state.service.is_ready()
    body = HealthResponse(
        status="healthy" if ready else "not_ready", service="docuparse", version=__version__
    )
    if ready:
        return body
    return JSONResponse(status_code=503, content=body.model_dump())
