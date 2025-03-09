"""Middleware for handling YAML content type."""

import json

import yaml
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.datastructures import MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class YAMLMiddleware(BaseHTTPMiddleware):
    """Middleware that converts YAML requests to JSON format."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request, converting YAML to JSON if needed.

        Args:
        ----
            request: The incoming request
            call_next: The next middleware or endpoint to call

        Returns:
        -------
            Response: The response from the next middleware or endpoint

        """
        if request.headers.get("content-type") == "application/yaml":
            body = await request.body()
            try:
                json_body = json.dumps(yaml.safe_load(body.decode("utf-8"))).encode()
            except Exception:
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={"detail": "Unable to parse provided YAML configuration."},
                )

            request._body = json_body
            updated_headers = MutableHeaders(request._headers)
            updated_headers["content-length"] = str(len(json_body))
            updated_headers["content-type"] = "application/json"
            request._headers = updated_headers
            request.scope.update(headers=request.headers.raw)

        return await call_next(request)


def add_yaml_middleware(app: FastAPI) -> None:
    """Add YAML middleware to the FastAPI application.

    Args:
    ----
        app: The FastAPI application instance

    """
    app.add_middleware(YAMLMiddleware)


def add_yaml_middleware_to_router(
    app: FastAPI, router_path: str, exclude_paths: list[str] | None = None
) -> None:
    """Add YAML middleware scoped to a specific router.

    Args:
    ----
        app: The FastAPI application instance
        router_path: The router path to apply the middleware to
        exclude_paths: Optional list of paths to exclude from the middleware

    """
    exclude_paths = exclude_paths or []

    @app.middleware("http")
    async def yaml_to_json_middleware(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Convert YAML to JSON for specific routes.

        Args:
        ----
            request: The incoming request
            call_next: The next middleware or endpoint handler

        Returns:
        -------
            Response: The response from the next middleware or endpoint

        """
        # Check if request qualifies for YAML to JSON conversion
        if (
            request.url.path.startswith(router_path)
            and request.url.path not in exclude_paths
            and request.headers.get("content-type") == "application/yaml"
        ):
            body = await request.body()
            try:
                json_body = json.dumps(yaml.safe_load(body.decode("utf-8"))).encode()
            except Exception:
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={"detail": "Unable to parse provided YAML configuration."},
                )

            request._body = json_body
            updated_headers = MutableHeaders(request._headers)
            updated_headers["content-length"] = str(len(json_body))
            updated_headers["content-type"] = "application/json"
            request._headers = updated_headers
            request.scope.update(headers=request.headers.raw)

        return await call_next(request)
