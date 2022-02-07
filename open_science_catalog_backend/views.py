from http import HTTPStatus
import logging

from pydantic import BaseModel
from starlette.requests import Request
from slugify import slugify

from open_science_catalog_backend import app
from open_science_catalog_backend.pull_request import (
    create_pull_request,
    pull_requests_for_user,
    PullRequestBody,
)


# TODO: fix logging output with gunicorn
logger = logging.getLogger(__name__)


# TODO: AUTH: jwt token?


@app.post("/items", status_code=HTTPStatus.CREATED)
async def create_item(request: Request):
    """Publish request body (stac file) to file in github repo via PR"""
    username = "my-user"  # TODO

    filename = "myfile.json"
    # TODO: decide whether to pass content via json body or file upload
    #       possibly use UploadFile https://fastapi.tiangolo.com/tutorial/request-files/
    #       install python-multipart
    stac_item = await request.body()

    path_in_repo = f"{username}/{filename}"

    # TODO: different item id?
    pr_body = PullRequestBody(
        item_id=filename,
        username=username,
    )

    create_pull_request(
        branch_base_name=slugify(path_in_repo)[:30],
        pr_title=f"Add {path_in_repo}",
        pr_body=pr_body.serialize(),
        file_to_create=(path_in_repo, stac_item),
    )


class ItemsResponse(BaseModel):
    items: list[str]


@app.get("/items", response_model=ItemsResponse)
async def get_items():
    """Get list of IDs of items for a certain user/workspace.

    Returns submissions in git repo by default, but can also return
    pending submissions.
    """
    username = "my-user"  # TODO

    # TODO: allow choose between pending / confirmed
    # TODO: implement confirmed by listing current main dir (filename must be id!)

    return ItemsResponse(
        items=[pr_body.item_id for pr_body in pull_requests_for_user(username=username)]
    )


@app.get("/items/{item_id}")
async def get_item(item_id: str):
    """Retrieves STAC item from github repository.

    Does not support fetching pending submissions.
    """
    raise NotImplementedError


@app.put("/items/{item_id}")
async def put_item(item_id: str):
    """Update existing repository item via a PR"""
    raise NotImplementedError


@app.delete("/items/{item_id}")
async def delete_item(item_id: str):
    """Delete existing repository item via a PR"""
    raise NotImplementedError
