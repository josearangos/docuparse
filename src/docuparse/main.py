import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from docuparse import __version__
from docuparse.api import health, ocr
from docuparse.errors import ApiError
from docuparse.service import DocumentService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def create_app(service: DocumentService | None = None) -> FastAPI:
    """Build the app. Pass a service to inject a different engine (used by tests)."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if service is None:
            from docuparse.engine.paddle_vl import PaddleVLEngine

            engine = PaddleVLEngine()
            engine.load()  # the model loads once at startup
            app.state.service = DocumentService(engine)
        else:
            app.state.service = service
        yield

    app = FastAPI(title="DocuParse", version=__version__, lifespan=lifespan)
    app.include_router(ocr.router)
    app.include_router(health.router)

    @app.exception_handler(ApiError)
    async def api_error(_: Request, exc: ApiError):
        return _error(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def bad_request(_: Request, exc: RequestValidationError):
        return _error(400, "missing_file", "The request is malformed.")

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException):
        codes = {404: "not_found", 405: "method_not_allowed"}
        code = codes.get(exc.status_code, "bad_request" if exc.status_code < 500 else "processing_failed")
        return _error(exc.status_code, code, "The request could not be handled.")

    @app.exception_handler(Exception)
    async def unexpected(_: Request, exc: Exception):
        logging.getLogger("docuparse").exception("unexpected error")
        return _error(500, "processing_failed", "The document could not be processed.")

    return app


def __getattr__(name: str):
    # `uvicorn docuparse.main:app` builds the real app lazily
    if name == "app":
        return create_app()
    raise AttributeError(name)
