from http import HTTPStatus
from unittest import mock

import pytest

from open_science_catalog_backend.pull_request import PullRequestBody


@pytest.fixture()
def mock_create_pull_request():
    with mock.patch("open_science_catalog_backend.views.create_pull_request") as mocker:
        yield mocker


@pytest.fixture()
def mock_get_pull_requests():
    with mock.patch(
        "open_science_catalog_backend.views.pull_requests_for_user",
        return_value=[
            PullRequestBody(username="abc", item_id="jkl"),
        ],
    ) as mocker:
        yield mocker


def test_create_item_creates_pull_request(client, mock_create_pull_request):
    response = client.post("/items", json={"test": "foo"})
    mock_create_pull_request.assert_called_once()
    mock_create_pull_request.assert_called_once()

    assert response.status_code == HTTPStatus.CREATED


@pytest.mark.skip("auth not implemented yet")
def test_create_item_without_auth_fails(client):
    response = client.post("/items", json={})
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_get_items_returns_list_for_user(client, mock_get_pull_requests):
    response = client.get("/items")
    assert response.json()["items"] == ["jkl"]
