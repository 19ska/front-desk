"""Every API failure becomes {"error": "<something a person can act on>"}."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

SERVER_ERROR = "Something went wrong on our side. Try again."


def error(status: int, message: str) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


def example_body(request: Request) -> str:
    """'{"email": "...", "password": "..."}' built from the route's own body model."""
    route = request.scope.get("route")
    body_field = getattr(route, "body_field", None)
    model = getattr(getattr(body_field, "field_info", None), "annotation", None)
    names = list(getattr(model, "model_fields", {}))
    return "{" + ", ".join(f'"{n}": "..."' for n in names) + "}" if names else "a JSON object"


def validation_message(request: Request, exc: RequestValidationError) -> str:
    first = exc.errors()[0]
    if first.get("type") == "json_invalid":
        return "Request body must be valid JSON."
    loc = [str(part) for part in first.get("loc", ()) if part not in ("body", "query", "path")]
    if not loc:
        # The whole body is missing or the wrong shape: say what to send instead.
        return f"Send a JSON body like {example_body(request)}."
    msg = first["msg"].removeprefix("Value error, ")
    return f"{'.'.join(loc)}: {msg}"


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        # Starlette's own "no route matched" 404 carries the default detail.
        if exc.status_code == 404 and exc.detail == "Not Found":
            return error(404, f"No such endpoint: {request.method} {request.url.path}")
        return error(exc.status_code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def bad_request(request: Request, exc: RequestValidationError):
        return error(400, validation_message(request, exc))

    @app.exception_handler(Exception)
    async def server_error(request: Request, exc: Exception):
        # Never echo the exception: it can contain data the caller mustn't see.
        return error(500, SERVER_ERROR)
