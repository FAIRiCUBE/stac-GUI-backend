from enum import Enum
import json
from http import HTTPStatus
from pathlib import PurePath
import logging
import typing

from fastapi import Request, Response, Depends, HTTPException, Header
from pydantic import BaseModel
from slugify import slugify

from open_science_catalog_backend import app
from open_science_catalog_backend.pull_request import (
    create_pull_request,
    pull_requests,
    PullRequestBody,
    files_in_directory,
    ChangeType,
)


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
    "/items/{item_type}/{filename}",
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


@app.put("/items/{item_type}/{filename}")
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
    change_type: typing.Optional[str]  # only PR
    url: typing.Optional[str]  # only PR
    data_owner: typing.Optional[bool]  # only PR


class ItemsResponse(BaseModel):
    items: typing.Union[list[ResponseItem], list[str]]


class Filtering(str, Enum):
    pending = "pending"
    confirmed = "confirmed"


@app.get("/items/{item_type}", response_model=ItemsResponse)
async def get_items(
    item_type: ItemType, filter: Filtering = Filtering.confirmed, user=Depends(get_user)
):
    """Get list of IDs of items for a certain user/workspace.

    Returns submissions in git repo by default (all users), but can also return
    pending submissions for the current user.
    """

    if filter == Filtering.pending:
        items: typing.Union[list[ResponseItem], list[str]] = [
            ResponseItem(
                filename=pr_body.filename,
                change_type=pr_body.change_type,
                url=pr_body.url,
                data_owner=pr_body.data_owner,
            )
            for pr_body in pull_requests()
            if pr_body.item_type == item_type.value and pr_body.user == user
        ]
    else:
        items = [
            ResponseItem(filename=filename)
            for filename in files_in_directory(
                directory=_path_in_repo(item_type=item_type)
            )
        ]

    return ItemsResponse(items=items)


# TODO: this is not exposed until we figure out if we really need this
# @app.get("/items/{item_id}")
async def get_item(item_id: str):
    """Retrieves STAC item from github repository.

    Does not support fetching pending submissions.
    """
    raise NotImplementedError


@app.delete("/items/{item_type}/{filename}", status_code=HTTPStatus.NO_CONTENT)
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
