"""Optional FastAPI boundary: fixed assets, same-origin JSON, sanitized errors."""

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from nullmark.playground.service import Playground, PlaygroundSettings

ASSETS = Path(__file__).parent / "static"
logger = logging.getLogger("nullmark.playground")


def create_app() -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])
    playground = Playground()

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        origin = request.headers.get("origin")
        if origin and origin != f"{request.url.scheme}://{request.headers.get('host', '')}":
            return JSONResponse({"error": "Use the local playground tab."}, status_code=403)
        if request.method == "POST":
            if request.headers.get("content-type", "").split(";")[0] != "application/json":
                return JSONResponse({"error": "Expected JSON settings."}, status_code=415)
            # No uploads or arbitrary body buffering; settings have a small bounded envelope.
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 100000:
                    return JSONResponse({"error": "Settings are too large."}, status_code=413)
            request._body = bytes(body)
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_settings(request, exc):
        fields = sorted({str(e["loc"][-1]) for e in exc.errors()})
        return JSONResponse(
            {"error": "Check these settings: " + ", ".join(fields)},
            status_code=422,
        )

    @app.get("/")
    def index():
        return FileResponse(ASSETS / "index.html")

    @app.get("/assets/{name}")
    def asset(name: str):
        if name not in {"app.js", "style.css"}:
            return JSONResponse({"error": "Not found."}, status_code=404)
        return FileResponse(ASSETS / name)

    @app.post("/api/key")
    def fresh_key():
        if not playground.lock.acquire(blocking=False):
            return JSONResponse({"error": "Generation is still running."}, status_code=409)
        try:
            return playground.fresh_key()
        finally:
            playground.lock.release()

    @app.post("/api/generate")
    def generate(settings: PlaygroundSettings):
        if not playground.lock.acquire(blocking=False):
            return JSONResponse({"error": "Generation is still running."}, status_code=409)
        try:
            return playground.generate(settings)
        except Exception as exc:
            # Upstream messages may embed keys: terminal logs retain type, never private values.
            logger.error("Generation failed (%s)", type(exc).__name__)
            message = "Generation failed. Check model availability and settings; see terminal logs."
            if isinstance(exc, OSError):
                message = "Model unavailable. Check the GPT-2 download or local model cache."
            elif isinstance(exc, ValueError):
                message = (
                    "Check settings: CUDA must be available; the prompt plus continuation "
                    "must fit the model context (GPT-2: 1024 tokens). Try a shorter prompt."
                )
            return JSONResponse({"error": message}, status_code=400)
        finally:
            playground.lock.release()

    return app


def launch(host: str, port: int) -> None:
    import uvicorn

    uvicorn.run(create_app(), host=host, port=port, access_log=False)
