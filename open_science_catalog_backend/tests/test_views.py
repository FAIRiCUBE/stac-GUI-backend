import datetime
from http import HTTPStatus
import json
from unittest import mock

import pytest

from open_science_catalog_backend.pull_request import (
    ChangeType,
    PullRequestBody,
    PullRequestState,
)

VALID_HEADERS = {
    "X-User": "foo",
    "X-OSCDataOwner": "true",
}


@pytest.fixture()
def mock_create_pull_request():
    with mock.patch("open_science_catalog_backend.views.create_pull_request") as mocker:
        yield mocker


@pytest.fixture()
def mock_pull_requests():
    with mock.patch(
        "open_science_catalog_backend.views.pull_requests",
        return_value=[
            PullRequestBody(
                item_type="products",
                filename="pending_item.json",
                change_type=ChangeType.add,
                url="https://example.com",
                user="foo",
                data_owner=True,
                state=PullRequestState.pending,
                created_at=datetime.datetime(2000, 1, 1),
            ),
        ],
    ) as mocker:
        yield mocker


@pytest.fixture()
def mock_files_in_directory():
    with mock.patch(
        "open_science_catalog_backend.views.files_in_directory",
        return_value=["confirmed_item.json"],
    ) as mocker:
        yield mocker


def test_post_item_creates_pull_request(client, mock_create_pull_request):
    response = client.post(
        "/item-requests/products/a.json", json={"test": "foo"}, headers=VALID_HEADERS
    )

    mock_create_pull_request.assert_called_once()
    assert response.status_code == HTTPStatus.CREATED


def test_post_item_creates_formats_file(client, mock_create_pull_request):
    client.post(
        "/item-requests/products/a.json", json={"test": "foo"}, headers=VALID_HEADERS
    )

    mock_create_pull_request.assert_called_once()
    assert b"\n" in mock_create_pull_request.mock_calls[0].kwargs["file_to_create"][1]


def test_create_item_without_auth_fails(client):
    response = client.post("/item-requests/products/a.json", json={})
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_get_items_returns_all_items(client, mock_pull_requests):
    response = client.get("/item-requests", headers=VALID_HEADERS)
    assert response.json()["items"][0] == {
        "filename": "pending_item.json",
        "change_type": "Add",
        "url": "https://example.com",
        "data_owner": True,
        "state": "Pending",
        "item_type": "products",
        "created_at": "2000-01-01T00:00:00",
    }


def test_get_items_returns_pending_list_for_user(client, mock_pull_requests):
    response = client.get("/item-requests/products", headers=VALID_HEADERS)
    assert response.json()["items"][0] == {
        "filename": "pending_item.json",
        "change_type": "Add",
        "url": "https://example.com",
        "data_owner": True,
        "state": "Pending",
        "item_type": "products",
        "created_at": "2000-01-01T00:00:00",
    }


def test_put_item_creates_pull_request(client, mock_create_pull_request):
    response = client.put(
        "/item-requests/projects/a", json={"test": "update"}, headers=VALID_HEADERS
    )

    mock_create_pull_request.assert_called_once()
    assert response.status_code == HTTPStatus.OK


def test_delete_item_creates_pull_request(client, mock_create_pull_request):
    response = client.delete("/item-requests/products/a.json", headers=VALID_HEADERS)

    mock_kwargs = mock_create_pull_request.mock_calls[0].kwargs
    assert mock_kwargs["file_to_delete"] == "data/products/a.json"
    assert json.loads(mock_kwargs["pr_body"])["user"] == VALID_HEADERS["X-User"]
    assert response.status_code == HTTPStatus.NO_CONTENT


def test_pr_bodies_can_be_deserialized():
    serialized_body = '{"filename": "foo.json", "item_type": "projects", "change_type": "Add", "user": "Bernhard", "data_owner": true}'
    PullRequestBody.deserialize(
        serialized_body,
        url="",
        state=PullRequestState.pending,
        created_at=datetime.datetime(2000, 1, 1),
    ) == 3
