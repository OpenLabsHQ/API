"""Middleware for handling YAML content type."""

import json
from typing import Any

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.datastructures import MutableHeaders
from starlette.middleware.base import RequestResponseEndpoint
from yaml import safe_load
from yaml.scanner import ScannerError


def _propagate_tags(
    data: dict[str, Any], inherited_tags: list[str] | None = None
) -> None:
    if inherited_tags is None:
        inherited_tags = []

    # Combine current tags with inherited ones
    current_tags = inherited_tags + data.get("tags", [])

    # If this is a host, retain only the final tags
    if "hosts" not in data and "vpcs" not in data and "subnets" not in data:
        data["tags"] = current_tags
        return

    # Otherwise, remove tags from this level
    data.pop("tags", None)

    # Recursively apply to vpcs
    for vpc in data.get("vpcs", []):
        _propagate_tags(vpc, current_tags)

    # Recursively apply to subnets
    for subnet in data.get("subnets", []):
        _propagate_tags(subnet, current_tags)

    # Recursively apply to hosts
    for host in data.get("hosts", []):
        _propagate_tags(host, current_tags)


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
                yaml_data = safe_load(body.decode("utf-8"))
                _propagate_tags(yaml_data)
                json_body = json.dumps(yaml_data).encode()
            except ScannerError as e:
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    content={
                        "detail": f"Unable to parse provided YAML configuration: {e!s}."
                    },
                )

            request._body = json_body
            updated_headers = MutableHeaders(request._headers)
            updated_headers["content-length"] = str(len(json_body))
            updated_headers["content-type"] = "application/json"
            request._headers = updated_headers
            request.scope.update(headers=request.headers.raw)

        return await call_next(request)
