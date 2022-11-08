import datetime
from enum import Enum
import json
from http import HTTPStatus
from pathlib import PurePath
import logging
import typing
from urllib.parse import urljoin

from fastapi import (
    Request, Response, Depends, HTTPException, Header, UploadFile
)
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from slugify import slugify
from aiobotocore.session import get_session
import botocore

from open_science_catalog_backend import app
from open_science_catalog_backend.pull_request import (
    PullRequestState,
    create_pull_request,
    pull_requests,
    PullRequestBody,
    ChangeType,
)
from open_science_catalog_backend import config


logger = logging.getLogger(__name__)

PREFIX_IN_REPO = PurePath("data")


class ItemType(str, Enum):
    projects = "projects"
    products = "products"
    variables = "variables"
    themes = "themes"


def _path_in_repo(item_type: ItemType, filename: typing.Optional[str] = None) -> str:
    return str(PREFIX_IN_REPO / item_type.value / (filename if filename else ""))


def get_user(x_user: typing.Optional[str] = Header(default=None)) -> str:
    # NOTE: this header must be secured by another component in the system
    if not x_user:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)
    else:
        return x_user


def get_data_owner_role(
    x_oscdataowner: str = Header(default=""),
) -> bool:
    # NOTE: this header must be secured by another component in the system
    try:
        return bool(json.loads(x_oscdataowner))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Invalid header X-OSCDataOwner"
        )


@app.post(
    "/item-requests/{item_type}/{filename}",
    status_code=HTTPStatus.CREATED,
)
async def create_item(
    request: Request,
    item_type: ItemType,
    filename: str,
    user=Depends(get_user),
    data_owner=Depends(get_data_owner_role),
):
    """Publish request body (stac file) to file in github repo via PR"""

    logger.info(f"Creating PR to create item {filename}")

    request_body = await request.json()

    # NOTE: if this file already exists, this will lead to an override

    _create_file_change_pr(
        item_type=item_type,
        filename=filename,
        contents=request_body,
        change_type=ChangeType.add,
        user=user,
        data_owner=data_owner,
    )
    return Response(status_code=HTTPStatus.CREATED)


@app.put("/item-requests/{item_type}/{filename}")
async def put_item(
    request: Request,
    item_type: ItemType,
    filename: str,
    user=Depends(get_user),
    data_owner=Depends(get_data_owner_role),
):
    """Update existing repository item via a PR"""

    logger.info(f"Creating PR to update item {filename}")

    request_body = await request.json()

    _create_file_change_pr(
        item_type=item_type,
        filename=filename,
        contents=request_body,
        change_type=ChangeType.update,
        user=user,
        data_owner=data_owner,
    )
    return Response()


def _create_file_change_pr(
    item_type: ItemType,
    filename: str,
    change_type: ChangeType,
    user: str,
    data_owner: bool,
    contents: typing.Any = None,
) -> None:
    pr_body = PullRequestBody(
        item_type=item_type.value,
        filename=filename,
        change_type=change_type,
        url=None,  # No url, not submitted yet
        user=user,
        data_owner=data_owner,
        state=PullRequestState.pending,
        created_at=None,
    )

    path_in_repo = _path_in_repo(item_type, filename)

    if change_type != ChangeType.delete:
        # serialize as formatted json
        serialized_content = json.dumps(
            contents,
            indent=2,
        ).encode("utf-8")

        file_to_create = (path_in_repo, serialized_content)
        file_to_delete = None
    else:
        file_to_create = None
        file_to_delete = path_in_repo

    create_pull_request(
        branch_base_name=slugify(path_in_repo)[:30],
        pr_title=f"{change_type} {path_in_repo}",
        pr_body=pr_body.serialize(),
        file_to_create=file_to_create,
        file_to_delete=file_to_delete,
        labels=("OSCDataOwner",) if data_owner else (),
    )


class ResponseItem(BaseModel):
    filename: str
    change_type: ChangeType
    url: str
    data_owner: bool
    state: PullRequestState
    item_type: ItemType
    created_at: str


class ItemsResponse(BaseModel):
    items: typing.Union[list[ResponseItem], list[str]]


@app.get("/item-requests", response_model=ItemsResponse)
async def get_all_items(user=Depends(get_user)):
    """Get list of IDs of items for a certain user/workspace."""

    return ItemsResponse(
        items=_item_requests(
            user=user,
        ),
    )


@app.get("/item-requests/{item_type}", response_model=ItemsResponse)
async def get_items_of_type(item_type: ItemType, user=Depends(get_user)):
    """Get list of IDs of items for a certain user/workspace."""
    return ItemsResponse(
        items=_item_requests(
            user=user,
            item_type=item_type,
        ),
    )


def _item_requests(
    user: str,
    item_type: typing.Optional[ItemType] = None,
) -> typing.List[ResponseItem]:
    return [
        ResponseItem(
            filename=pr_body.filename,
            change_type=pr_body.change_type,
            url=pr_body.url,
            data_owner=pr_body.data_owner,
            state=pr_body.state,
            item_type=pr_body.item_type,
            created_at=typing.cast(datetime.datetime, pr_body.created_at).isoformat(),
        )
        for pr_body in pull_requests()
        if (item_type is None or pr_body.item_type == item_type.value)
        and pr_body.user == user
    ]


@app.delete("/item-requests/{item_type}/{filename}", status_code=HTTPStatus.NO_CONTENT)
async def delete_item(
    item_type: ItemType,
    filename: str,
    user=Depends(get_user),
    data_owner=Depends(get_data_owner_role),
):
    """Delete existing repository item via a PR"""

    logger.info(f"Creating PR to delete item {filename}")

    _create_file_change_pr(
        item_type=item_type,
        filename=filename,
        change_type=ChangeType.delete,
        user=user,
        data_owner=data_owner,
    )
    return Response(status_code=HTTPStatus.NO_CONTENT)


@app.post("/upload/{path:path}", status_code=HTTPStatus.ACCEPTED, response_class=PlainTextResponse)
async def upload_file(upload_file: UploadFile, path: str) -> str:
    session = get_session()

    session.unregister(
        "before-parameter-build.s3",
        botocore.handlers.validate_bucket_name,
    )
    async with session.create_client(
        's3',
        endpoint_url=config.OBJECT_STORAGE_ENDPOINT_URL,
        aws_access_key_id=config.OBJECT_STORAGE_ACCESS_KEY_ID,
        aws_secret_access_key=config.OBJECT_STORAGE_SECRET_ACCESS_KEY,
    ) as client:
        await client.put_object(
            Bucket=config.OBJECT_STORAGE_BUCKET,
            Key=path,
            Body=upload_file.file._file
        )
        return urljoin(config.OBJECT_STORAGE_PUBLIC_URL_BASE, path)
