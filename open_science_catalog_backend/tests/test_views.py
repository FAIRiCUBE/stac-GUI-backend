from http import HTTPStatus
from unittest import mock

import pytest


@pytest.fixture()
def mock_create_pull_request():
    with mock.patch("open_science_catalog_backend.views.create_pull_request") as mocker:
        yield mocker


def test_create_item_creates_pull_request(client, mock_create_pull_request):
    response = client.post("/item", json={"test": "foo"})
    mock_create_pull_request.assert_called_once()
    mock_create_pull_request.assert_called_once()

    assert response.status_code == HTTPStatus.CREATED


def test_create_item_without_auth_fails(client):
    response = client.post("/item", json={})
    assert response.status_code == HTTPStatus.UNAUTHORIZED
