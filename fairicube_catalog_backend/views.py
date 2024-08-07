import os
import datetime
from enum import Enum
import json
from http import HTTPStatus
from pathlib import PurePath
import logging
import typing
from urllib.parse import urljoin

from fastapi import Request, Response, Depends, HTTPException, Header, UploadFile
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from slugify import slugify


from fairicube_catalog_backend import app
from fairicube_catalog_backend.pull_request import (
    PullRequestState,
    create_pull_request,
    fetch_items,
    get_item,
    get_members,
    get_item_url,
    PullRequestBody,
    ChangeType,
)
from fairicube_catalog_backend import config


logger = logging.getLogger(__name__)

PREFIX_IN_REPO = PurePath("")


class ItemType(str, Enum):
    products = "stac_dist"

def _path_in_repo(item_type: ItemType, filename: typing.Optional[str] = None) -> str:
    return str(PREFIX_IN_REPO / item_type.value / (filename if filename else ""))


def get_user(x_user: typing.Optional[str] = Header(default=None)) -> str:
    # NOTE: this header must be secured by another component in the system
    if not x_user:
        raise HTTPException(status_code=HTTPStatus.UNAUTHORIZED)
    else:
        return x_user


def get_data_owner_role(
    x_FairicubeOwner: str = Header(default=""),
) -> bool:
    # NOTE: this header must be secured by another component in the system
    try:
        return bool(json.loads(x_FairicubeOwner))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Invalid header X-FairicubeOwner"
        )


@app.post(
    "/item-requests/{item_name}",
    status_code=HTTPStatus.OK,
)
async def fetch_item(
    request: Request,
    user=Depends(get_user),
    data_owner=Depends(get_data_owner_role),
):

    request_body = await request.json()
    stac_url = get_item_url(request_body)

    return ResponseSingleItem(
        stac=get_item(stac_url),
    )


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
        filename=f"{os.path.splitext(filename)[0]}/{filename}",
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
    content = contents["stac"]
    assignees = contents["assignees"]
    reviewers = contents["reviewers"]
    path_in_repo = _path_in_repo(item_type, filename)

    if change_type != ChangeType.delete:
        # serialize as formatted json
        serialized_content = json.dumps(
            content,
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
        file_is_updated=contents["state"],
        labels=("FairicubeOwner",) if data_owner else (),
        assignees=assignees,
        reviewers=reviewers,
    )


class ResponseItem(BaseModel):
    filename: str
    change_type: ChangeType
    url: str
    data_owner: bool
    state: PullRequestState
    item_type: ItemType
    created_at: str

class ResponseSingleItem(BaseModel):
    stac: object

class PullRequestLink(BaseModel):
    url:str

class ItemsResponse(BaseModel):
    items: typing.Union[list[ResponseItem], list[object]]
    members: typing.Union[list[ResponseItem], list[object]]


@app.get("/item-requests/items", response_model=ItemsResponse)
async def get_all_items(user=Depends(get_user)):
    """Get list of IDs of items for a certain user/workspace."""
    return ItemsResponse(
        items=fetch_items(),
        members=get_members()
    )


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
        filename=f"{os.path.splitext(filename)[0]}/{filename}",
        change_type=ChangeType.delete,
        user=user,
        data_owner=data_owner,
    )
    return Response(status_code=HTTPStatus.NO_CONTENT)


