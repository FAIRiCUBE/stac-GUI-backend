from http import HTTPStatus
from unittest import mock

import pytest

from open_science_catalog_backend.pull_request import PullRequestBody


@pytest.fixture()
def mock_create_pull_request():
    with mock.patch("open_science_catalog_backend.views.create_pull_request") as mocker:
        yield mocker


@pytest.fixture()
def mock_pull_requests_for_user():
    with mock.patch(
        "open_science_catalog_backend.views.pull_requests_for_user",
        return_value=[
            PullRequestBody(
                username="abc",
                item_type="products",
                filename="pending_item.json",
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
    response = client.post("/items/products/a.json", json={"test": "foo"})

    mock_create_pull_request.assert_called_once()
    assert response.status_code == HTTPStatus.CREATED


@pytest.mark.skip("auth not implemented yet")
def test_create_item_without_auth_fails(client):
    response = client.post("/items", json={})
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_get_items_returns_pending_list_for_user(client, mock_pull_requests_for_user):
    response = client.get("/items/products", params={"filter": "pending"})
    assert response.json()["items"] == ["pending_item.json"]


def test_get_items_returns_confirmed_list_for_user(client, mock_files_in_directory):
    response = client.get("/items/products", params={"filter": "confirmed"})
    assert response.json()["items"] == ["confirmed_item.json"]


def test_put_item_creates_pull_request(client, mock_create_pull_request):
    response = client.put("/items/projects/a", json={"test": "update"})

    mock_create_pull_request.assert_called_once()
    assert response.status_code == HTTPStatus.OK


def test_delete_item_creates_pull_request(client, mock_create_pull_request):
    response = client.delete("/items/products/a")

    assert (
        mock_create_pull_request.mock_calls[0].kwargs["file_to_delete"] == "products/a"
    )
    assert response.status_code == HTTPStatus.NO_CONTENT
