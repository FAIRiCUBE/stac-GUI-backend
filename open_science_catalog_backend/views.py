from enum import Enum
from http import HTTPStatus
import logging

from fastapi import Request, Response
from pydantic import BaseModel
from slugify import slugify

from open_science_catalog_backend import app
from open_science_catalog_backend.pull_request import (
    create_pull_request,
    pull_requests_for_user,
    PullRequestBody,
    files_for_user,
)


# TODO: fix logging output with gunicorn
logger = logging.getLogger(__name__)


# TODO: Auth
username = "my-user"


@app.post("/items", status_code=HTTPStatus.CREATED)
async def create_item(request: Request):
    """Publish request body (stac file) to file in github repo via PR"""

    filename = "myfile.json"
    # TODO: decide whether to pass content via json body or file upload
    #       possibly use UploadFile https://fastapi.tiangolo.com/tutorial/request-files/
    #       install python-multipart
    stac_item = await request.body()

    # TODO: what if item already exists?

    _create_upload_pr(
        username=username,
        filename=filename,
        contents=stac_item,
        is_update=False,
    )
    return Response(status_code=HTTPStatus.CREATED)


def _path_in_repo(username: str, filename: str) -> str:
    return f"{username}/{filename}"


def _create_upload_pr(
    username: str,
    filename: str,
    contents: bytes,
    is_update: bool,
) -> None:
    # TODO: different item id?
    pr_body = PullRequestBody(
        item_id=filename,
        username=username,
    )

    path_in_repo = _path_in_repo(username=username, filename=filename)
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


@app.get("/items", response_model=ItemsResponse)
async def get_items(filter: Filtering = Filtering.confirmed):
    """Get list of IDs of items for a certain user/workspace.

    Returns submissions in git repo by default, but can also return
    pending submissions.
    """

    if filter == Filtering.pending:
        items = [
            pr_body.item_id for pr_body in pull_requests_for_user(username=username)
        ]
    else:
        items = files_for_user(username=username)

    return ItemsResponse(items=items)


@app.get("/items/{item_id}")
async def get_item(item_id: str):
    """Retrieves STAC item from github repository.

    Does not support fetching pending submissions.
    """
    raise NotImplementedError


@app.put("/items/{item_id}")
async def put_item(item_id: str, request: Request):
    """Update existing repository item via a PR"""

    # TODO: is item_id the filename? keep in sync with POSTconfigconfig
    filename = item_id

    logger.info(f"Creating PR to update item {item_id}")

    # TODO: decide whether to pass content via json body or file upload
    #       possibly use UploadFile https://fastapi.tiangolo.com/tutorial/request-files/
    #       install python-multipart
    stac_item = await request.body()

    _create_upload_pr(
        username=username,
        filename=filename,
        contents=stac_item,
        is_update=True,
    )
    return Response()


@app.delete("/items/{item_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_item(item_id: str):
    """Delete existing repository item via a PR"""
    filename = item_id
    path_in_repo = _path_in_repo(username=username, filename=filename)
    logger.info(f"Creating PR to delete item {path_in_repo}")
    create_pull_request(
        branch_base_name=slugify(path_in_repo)[:30],
        pr_title=f"Delete {path_in_repo}",
        pr_body="",
        file_to_delete=path_in_repo,
    )
    return Response(status_code=HTTPStatus.NO_CONTENT)
