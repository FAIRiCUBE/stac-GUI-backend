import logging

from fastapi import Request
from fastapi.responses import Response

import requests
import requests.exceptions

from open_science_catalog_backend import app

logger = logging.getLogger(__name__)

ALL_METHODS = ["GET", "POST", "PUT", "DELETE", "HEAD"]

URL_PREFIX = "/processing/{remote_backend}/"


def remote_backend_to_url(remote_backend: str) -> str:
    return "https://www.example.com"


def requests_response_to_fastapi_response(response):
    excluded_headers = [
        "content-encoding",
        "content-length",
        "transfer-encoding",
        "connection",
    ]
    headers = {
        name: value
        for (name, value) in response.raw.headers.items()
        if name.lower() not in excluded_headers
    }
    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=headers,
    )


def generate_reverse_proxy(
    service_prefix: str,
):
    async def reverse_proxy_service(
        request: Request,
        remote_backend: str,
        proxy_path: str = "",
    ):
        headers = dict(request.headers)

        url = (
            remote_backend_to_url(remote_backend)
            + "/"
            + service_prefix
            + (f"/{proxy_path}" if proxy_path else "")
        )

        proxy_kwargs = {
            "url": url,
            "params": dict(request.query_params),
            "headers": headers,
            "data": await request.body(),
            "allow_redirects": False,
        }

        logger.debug(f"Requested {request.url}")
        logger.debug(f"Proxying to {proxy_kwargs['url']}")
        response = getattr(requests, request.method.lower())(**proxy_kwargs)

        return requests_response_to_fastapi_response(response)

    # need to change name to avoid confusion
    reverse_proxy_service.__name__ = service_prefix + "_service"

    app.api_route(
        URL_PREFIX + service_prefix,
        methods=ALL_METHODS,
    )(reverse_proxy_service)

    app.api_route(
        URL_PREFIX + service_prefix + "/{proxy_path:path}",
        methods=ALL_METHODS,
    )(reverse_proxy_service)


generate_reverse_proxy(service_prefix="processes")
generate_reverse_proxy(service_prefix="jobs")
