from http import HTTPStatus
import logging

from fastapi import HTTPException, Path, Response, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from open_science_catalog_backend import app, config


# TODO: fix logging output with gunicorn
logger = logging.getLogger(__name__)


# TODO: AUTH: jwt token?


@app.post("/item", status_code=HTTPStatus.CREATED)
async def create_item():
    """Publish request body (stac file) to file in github repo via PR"""
    raise NotImplementedError


@app.get("/item")
async def get_items():
    """Get list of IDs of items for a certain user/workspace.

    Returns submissions in git repo by default, but can also return
    pending submissions.
    """
    raise NotImplementedError


@app.get("/item/{item_id}")
async def get_item(item_id: str):
    """Retrieves STAC item from github repository.

    Does not support fetching pending submissions.
    """
    raise NotImplementedError


@app.put("/item/{item_id}")
async def put_item(item_id: str):
    """Update existing repository item via a PR"""
    raise NotImplementedError


@app.delete("/item/{item_id}")
async def delete_item(item_id: str):
    """Delete existing repository item via a PR"""
    raise NotImplementedError
