from http import HTTPStatus
import logging

from fastapi import HTTPException, Path, Response, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from open_science_catalog_backend import app, config


# TODO: fix logging output with gunicorn
logger = logging.getLogger(__name__)


@app.post("/test", status_code=HTTPStatus.CREATED)
async def create_test():
    pass
