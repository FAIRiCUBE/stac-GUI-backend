import json
import os
import pathlib

GITHUB_TOKEN: str = os.environ["GITHUB_TOKEN"]
GITHUB_REPO_ID: str = os.environ["GITHUB_REPO_ID"]

GITHUB_MAIN_BRANCH: str = os.environ.get("GITHUB_MAIN_BRANCH", "main")

OBJECT_STORAGE_ENDPOINT_URL: str | None = os.environ.get("OBJECT_STORAGE_ENDPOINT_URL")
OBJECT_STORAGE_ACCESS_KEY_ID: str | None = os.environ.get(
    "OBJECT_STORAGE_ACCESS_KEY_ID"
)
OBJECT_STORAGE_SECRET_ACCESS_KEY: str | None = os.environ.get(
    "OBJECT_STORAGE_SECRET_ACCESS_KEY"
)
OBJECT_STORAGE_BUCKET: str | None = os.environ.get("OBJECT_STORAGE_BUCKET")
OBJECT_STORAGE_PUBLIC_URL_BASE: str | None = os.environ.get(
    "OBJECT_STORAGE_PUBLIC_URL_BASE"
)

REMOTE_PROCESSING_BACKEND_MAPPING: dict | None = (
    json.load(pathlib.Path(p).open())
    if (p := os.environ.get("REMOTE_PROCESSING_BACKEND_MAPPING_FILE_PATH"))
    else None
)

RESOURCE_CATALOG_METADATA_URL: str | None = os.environ.get(
    "RESOURCE_CATALOG_METADATA_URL"
)
