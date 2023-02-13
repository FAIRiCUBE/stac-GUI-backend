from http import HTTPStatus
import logging
from typing import cast
from urllib.parse import urlparse

from fastapi import Request, Response, HTTPException

import requests
import requests.exceptions

from open_science_catalog_backend import app, config

logger = logging.getLogger(__name__)

ALL_METHODS = ["GET", "POST", "PUT", "DELETE", "HEAD"]

URL_PREFIX = "/processing/{remote_backend}/"


def remote_backend_to_url(remote_backend: str) -> str:
    mapping = cast(dict, config.REMOTE_PROCESSING_BACKEND_MAPPING)

    try:
        return mapping[remote_backend]
    except KeyError:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f"Invalid remote backend {remote_backend}",
        )


def requests_response_to_fastapi_response(response) -> Response:
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
        url = (
            remote_backend_to_url(remote_backend)
            + "/"
            + service_prefix
            + (f"/{proxy_path}" if proxy_path else "")
        )

        remote_backend_host = cast(str, urlparse(url).hostname)

        headers = dict(request.headers) | {"Host": remote_backend_host}

        proxy_kwargs = {
            "url": url,
            "params": dict(request.query_params),
            "headers": headers,
            "data": await request.body(),
            "allow_redirects": False,
        }

        logger.info(f"Requested {request.url}")
        logger.info(str(proxy_kwargs))
        logger.info(f"Proxying to {proxy_kwargs['url']}")
        response = getattr(requests, request.method.lower())(**proxy_kwargs)
        logger.info(
            f"Got status {response.status_code} and size {response.headers.get('Content-Length')}"
        )
        logger.info(response.content.decode()[:500])
        # NOTE: don't raise for status, but forward errors
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
