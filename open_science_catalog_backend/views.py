from enum import Enum
from http import HTTPStatus
from pathlib import PurePath
import logging

from fastapi import Request, Response
from pydantic import BaseModel
from slugify import slugify

from open_science_catalog_backend import app
from open_science_catalog_backend.pull_request import (
    create_pull_request,
    pull_requests_for_user,
    PullRequestBody,
    files_in_directory,
)


logger = logging.getLogger(__name__)

PREFIX_IN_REPO = PurePath("data")

# TODO: Auth
username = "my-user"


class ItemType(str, Enum):
    projects = "projects"
    products = "products"
    variables = "variables"
    themes = "themes"


def _path_in_repo(item_type: ItemType, filename: str) -> str:
    return str(PREFIX_IN_REPO / item_type.value / filename)


@app.post("/items/{item_type}/{filename}", status_code=HTTPStatus.CREATED)
async def create_item(request: Request, item_type: ItemType, filename: str):
    """Publish request body (stac file) to file in github repo via PR"""

    stac_item = await request.body()

    # NOTE: if this file already exists, this will lead to an override

    _create_upload_pr(
        username=username,
        item_type=item_type,
        filename=filename,
        contents=stac_item,
        is_update=False,
    )
    return Response(status_code=HTTPStatus.CREATED)


@app.put("/items/{item_type}/{filename}")
async def put_item(request: Request, item_type: ItemType, filename: str):
    """Update existing repository item via a PR"""

    logger.info(f"Creating PR to update item {filename}")

    stac_item = await request.body()

    _create_upload_pr(
        username=username,
        item_type=item_type,
        filename=filename,
        contents=stac_item,
        is_update=True,
    )
    return Response()


def _create_upload_pr(
    username: str,
    item_type: ItemType,
    filename: str,
    contents: bytes,
    is_update: bool,
) -> None:

    path_in_repo = _path_in_repo(item_type, filename)

    pr_body = PullRequestBody(
        item_type=item_type.value,
        filename=filename,
        username=username,
    )

    create_pull_request(
        branch_base_name=slugify(path_in_repo)[:30],
        pr_title=f"{'Update' if is_update else 'Add'} {path_in_repo}",
        pr_body=pr_body.serialize(),
        file_to_create=(path_in_repo, contents),
    )


class ItemsResponse(BaseModel):
    items: list[str]


class Filtering(str, Enum):
    pending = "pending"
    confirmed = "confirmed"


@app.get("/items/{item_type}", response_model=ItemsResponse)
async def get_items(item_type: ItemType, filter: Filtering = Filtering.confirmed):
    """Get list of IDs of items for a certain user/workspace.

    Returns submissions in git repo by default (all users), but can also return
    pending submissions for the current user.
    """

    if filter == Filtering.pending:
        items = [
            pr_body.filename
            for pr_body in pull_requests_for_user(username=username)
            if pr_body.item_type == item_type.value
        ]
    else:
        items = files_in_directory(directory=item_type.value)

    return ItemsResponse(items=items)


# TODO: this is not exposed until we figure out if we really need this
# @app.get("/items/{item_id}")
async def get_item(item_id: str):
    """Retrieves STAC item from github repository.

    Does not support fetching pending submissions.
    """
    raise NotImplementedError


@app.delete("/items/{item_type}/{filename}", status_code=HTTPStatus.NO_CONTENT)
async def delete_item(item_type: ItemType, filename: str):
    """Delete existing repository item via a PR"""
    path_in_repo = _path_in_repo(item_type=item_type, filename=filename)
    logger.info(f"Creating PR to delete item {path_in_repo}")
    create_pull_request(
        branch_base_name=slugify(path_in_repo)[:30],
        pr_title=f"Delete {path_in_repo}",
        pr_body="",
        file_to_delete=path_in_repo,
    )
    return Response(status_code=HTTPStatus.NO_CONTENT)
